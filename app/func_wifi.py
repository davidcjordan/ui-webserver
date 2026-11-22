'''
WiFi helpers used by the WiFi settings page (blueprint_wifi.py + the wifi_* socketio events).

Raspberry Pi OS Buster manages WiFi with dhcpcd + wpa_supplicant (not NetworkManager), so
networks are scanned, added and saved through wpa_cli, which talks to wpa_supplicant's control
socket.  The stock /etc/wpa_supplicant/wpa_supplicant.conf contains:
   ctrl_interface=DIR=/var/run/wpa_supplicant GROUP=netdev
   update_config=1
The 'pi' user is in the 'netdev' group, so no sudo is needed.  update_config=1 is what allows
'save_config' to write new networks to wpa_supplicant.conf so they survive a reboot.

Link details come from 'wpa_cli signal_poll', 'iw', /proc/net/wireless and 'ip'.  Any of these
can be missing; the corresponding fields are simply left out.

Passwords are never logged.  WPA-PSK passphrases are converted to the 256-bit PSK (the same
thing wpa_passphrase does), so the plain-text password is not written to wpa_supplicant.conf.
'''
from flask import current_app
import subprocess
import shutil
import hashlib
import logging
import os
import re
import socket
import string
import time

from app.main.defines import WIFI_INTERFACE

# --- tunables -----------------------------------------------------------------------------------
SCAN_WAIT_SECONDS = 5        # time for wpa_supplicant to finish a scan (2.4 + 5 GHz) on a Pi 4
CONNECT_TIMEOUT = 30         # time allowed to associate + authenticate before giving up
DHCP_TIMEOUT = 15            # extra time to wait for dhcpcd to assign an IPv4 address
STATUS_CACHE_SECONDS = 1.0   # coalesce status polls from multiple browsers
CMD_TIMEOUT = 10

# file locations (module level so they can be pointed elsewhere for testing)
PROC_NET_WIRELESS = '/proc/net/wireless'
SYS_CLASS_NET = '/sys/class/net'
SYS_CLASS_RFKILL = '/sys/class/rfkill'
RESOLV_CONF = '/etc/resolv.conf'

# cfg80211's wireless-extensions compatibility layer reports link quality out of 70
PROC_LINK_QUALITY_MAX = 70

SECURITY_TYPES = ('open', 'psk', 'sae', 'eap')   # the ones we know how to configure

WPA_STATE_TEXT = {
   'COMPLETED': 'Connected',
   'DISCONNECTED': 'Disconnected',
   'INACTIVE': 'Not connected',
   'INTERFACE_DISABLED': 'WiFi interface disabled',
   'SCANNING': 'Searching for networks',
   'AUTHENTICATING': 'Authenticating',
   'ASSOCIATING': 'Associating',
   'ASSOCIATED': 'Associated',
   '4WAY_HANDSHAKE': 'Checking password',
   'GROUP_HANDSHAKE': 'Finishing handshake',
}

_fallback_logger = logging.getLogger(__name__)


def _logger():
   # the connect job runs in a background task; use the flask logger when there is an app context
   try:
      return current_app.logger
   except RuntimeError:
      return _fallback_logger


# --- running commands ---------------------------------------------------------------------------
_SEARCH_DIRS = ['/sbin', '/usr/sbin', '/bin', '/usr/bin', '/usr/local/sbin', '/usr/local/bin']
_cmd_cache = {}


def _find_cmd(name):
   # wpa_cli & iw live in /sbin on Buster, which may not be on the PATH of the web server's service
   if name not in _cmd_cache:
      path = shutil.which(name)
      if path is None:
         for directory in _SEARCH_DIRS:
            candidate = os.path.join(directory, name)
            if os.path.isfile(candidate) and os.access(candidate, os.X_OK):
               path = candidate
               break
      _cmd_cache[name] = path
   return _cmd_cache[name]


def _run(args, timeout=CMD_TIMEOUT):
   ''' Runs a command given as a list.  Returns (returncode, stdout, stderr); returncode is None if
       the command is not installed, timed out or could not be started.  Never raises. '''
   cmd = _find_cmd(args[0])
   if cmd is None:
      return None, '', f"'{args[0]}' is not installed"
   try:
      p = subprocess.run([cmd] + [str(a) for a in args[1:]], stdout=subprocess.PIPE,
         stderr=subprocess.PIPE, timeout=timeout)
   except subprocess.TimeoutExpired:
      return None, '', f"'{args[0]}' timed out"
   except Exception as e:
      return None, '', f"'{args[0]}' failed: {e}"
   return p.returncode, p.stdout.decode('utf-8', errors='replace'), p.stderr.decode('utf-8', errors='replace')


_last_logged_wpa_error = None


def _wpa(*args):
   ''' Runs 'wpa_cli -i <iface> args...'.  Returns (ok, output, error_message).
       ok is False if wpa_cli is missing, could not reach wpa_supplicant, or wpa_supplicant replied FAIL. '''
   global _last_logged_wpa_error
   rc, out, err = _run(['wpa_cli', '-i', wifi_interface()] + list(args))
   text = out.strip()
   error = None
   # only look at the start of the output: SSIDs in it are chosen by whoever runs the access point
   if rc is None:
      error = err
   elif text.startswith('FAIL'):
      error = f'wpa_supplicant replied {text}'
   elif rc != 0 or text.startswith('Failed to connect'):
      combined = f'{text} {err}'
      if 'Permission denied' in combined:
         error = "Permission denied talking to wpa_supplicant (the web server's user must be in the 'netdev' group)"
      elif 'timed out' in combined:
         error = 'wpa_supplicant did not respond'
      else:
         error = f'wpa_supplicant is not running on {wifi_interface()}'

   if error is not None:
      # don't flood the log when the page polls and wpa_supplicant is down; never log set_network values
      logged_args = ' '.join(str(a) for a in args[:3]) if args and args[0] == 'set_network' else ' '.join(str(a) for a in args)
      log_text = f'wpa_cli {logged_args}: {error}'
      if log_text != _last_logged_wpa_error:
         _logger().warning(log_text)
         _last_logged_wpa_error = log_text
      return False, text, error
   return True, text, None


# --- small parsers & formatters -----------------------------------------------------------------
_PRINTF_ESCAPES = {'\\': 0x5c, '"': 0x22, 'n': 0x0a, 'r': 0x0d, 't': 0x09, 'e': 0x1b}


def printf_decode(text):
   ''' Undoes wpa_supplicant's printf_encode(), which wpa_cli uses for SSIDs (non-printable and
       non-ASCII bytes are shown as \\xNN).  Returns the raw SSID bytes. '''
   out = bytearray()
   i = 0
   n = len(text)
   while i < n:
      c = text[i]
      if c == '\\' and i + 1 < n:
         nxt = text[i + 1]
         if nxt in _PRINTF_ESCAPES:
            out.append(_PRINTF_ESCAPES[nxt])
            i += 2
            continue
         if nxt == 'x':
            digits = text[i + 2:i + 4]
            m = re.match(r'[0-9a-fA-F]{1,2}', digits)
            if m:
               out.append(int(m.group(0), 16))
               i += 2 + len(m.group(0))
               continue
         if nxt in '01234567':
            m = re.match(r'[0-7]{1,3}', text[i + 1:i + 4])
            out.append(int(m.group(0), 8) & 0xff)
            i += 1 + len(m.group(0))
            continue
         i += 1   # unknown escape: drop the backslash, like wpa_supplicant does
         continue
      out.extend(c.encode('utf-8'))
      i += 1
   return bytes(out)


def ssid_display(raw):
   return raw.decode('utf-8', errors='replace')


def _parse_kv(text, sep='='):
   result = {}
   for line in text.splitlines():
      if sep in line:
         key, value = line.split(sep, 1)
         result[key.strip()] = value.strip()
   return result


def _int_or_none(value):
   try:
      return int(value)
   except (TypeError, ValueError):
      return None


def _first_int(text):
   m = re.search(r'-?\d+', text or '')
   return int(m.group(0)) if m else None


def freq_to_channel(freq):
   if freq is None:
      return None
   if freq == 2484:
      return 14
   if 2412 <= freq < 2484:
      return (freq - 2407) // 5
   if freq == 5935:
      return 2
   if 5950 < freq <= 7125:
      return (freq - 5950) // 5
   if 5000 <= freq <= 5950:
      return (freq - 5000) // 5
   if 4910 <= freq <= 4980:
      return (freq - 4000) // 5
   return None


def freq_to_band(freq):
   if freq is None:
      return ''
   if freq < 3000:
      return '2.4 GHz'
   if freq < 5925:
      return '5 GHz'
   return '6 GHz'


def signal_quality(dbm):
   ''' Returns (percent, bars 0-4, label) for a signal level in dBm. '''
   if dbm is None or dbm >= 0:
      return None, 0, ''
   percent = max(0, min(100, 2 * (dbm + 100)))
   if dbm >= -55:
      return percent, 4, 'Excellent'
   if dbm >= -65:
      return percent, 3, 'Good'
   if dbm >= -72:
      return percent, 2, 'Fair'
   if dbm >= -80:
      return percent, 1, 'Weak'
   return percent, 1, 'Poor'


def _fmt_bytes(n):
   if n is None:
      return ''
   value = float(n)
   for unit in ('B', 'KB', 'MB', 'GB'):
      if value < 1024 or unit == 'GB':
         return f'{value:.0f} {unit}' if unit == 'B' else f'{value:.1f} {unit}'
      value /= 1024
   return ''


def _fmt_duration(seconds):
   if seconds is None:
      return ''
   seconds = int(seconds)
   days, rem = divmod(seconds, 86400)
   hours, rem = divmod(rem, 3600)
   minutes, secs = divmod(rem, 60)
   if days:
      return f'{days}d {hours}h {minutes:02d}m'
   if hours:
      return f'{hours}h {minutes:02d}m'
   if minutes:
      return f'{minutes}m {secs:02d}s'
   return f'{secs}s'


def _wifi_standard(bitrate):
   ''' Infers the WiFi generation from an iw bitrate string, e.g. "433.3 MBit/s VHT-MCS 9 80MHz short GI VHT-NSS 1" '''
   if not bitrate:
      return ''
   if 'EHT-MCS' in bitrate:
      return 'WiFi 7 (802.11be)'
   if 'HE-MCS' in bitrate:
      return 'WiFi 6 (802.11ax)'
   if 'VHT-MCS' in bitrate:
      return 'WiFi 5 (802.11ac)'
   if 'MCS' in bitrate:
      return 'WiFi 4 (802.11n)'
   return '802.11a/b/g'


def _read_file(path):
   try:
      with open(path) as f:
         return f.read().strip()
   except (OSError, UnicodeDecodeError):
      return None


# --- interface & radio state --------------------------------------------------------------------
def wifi_interface():
   if WIFI_INTERFACE:
      return WIFI_INTERFACE
   try:
      names = sorted(os.listdir(SYS_CLASS_NET))
   except OSError:
      names = []
   wireless = [n for n in names if os.path.exists(os.path.join(SYS_CLASS_NET, n, 'wireless')) or
               os.path.exists(os.path.join(SYS_CLASS_NET, n, 'phy80211'))]
   if 'wlan0' in wireless or not wireless:
      return 'wlan0'
   return wireless[0]


def rfkill_state():
   ''' Returns (soft_blocked, hard_blocked) for the WiFi radio.  On Buster WiFi is soft-blocked at boot
       until a WiFi country has been set (raspi-config -> Localisation -> WLAN Country). '''
   soft = hard = False
   try:
      entries = os.listdir(SYS_CLASS_RFKILL)
   except OSError:
      return soft, hard
   for entry in entries:
      base = os.path.join(SYS_CLASS_RFKILL, entry)
      if _read_file(os.path.join(base, 'type')) != 'wlan':
         continue
      soft = soft or _read_file(os.path.join(base, 'soft')) == '1'
      hard = hard or _read_file(os.path.join(base, 'hard')) == '1'
   return soft, hard


# --- saved networks & scan results --------------------------------------------------------------
def list_saved_networks():
   ''' Returns (ok, networks, error) where networks are the ones configured in wpa_supplicant. '''
   ok, out, error = _wpa('list_networks')
   if not ok:
      return False, [], error
   networks = []
   for line in out.splitlines():
      if line.startswith('network id'):
         continue
      parts = line.split('\t')
      if len(parts) < 2 or not parts[0].strip().isdigit():
         continue
      flags = parts[3] if len(parts) > 3 else ''
      raw = printf_decode(parts[1])
      networks.append({'id': int(parts[0]), 'ssid_bytes': raw, 'ssid': ssid_display(raw),
         'current': '[CURRENT]' in flags, 'disabled': '[DISABLED]' in flags,
         'temp_disabled': '[TEMP-DISABLED]' in flags})
   return True, networks, None


def classify_security(flags):
   ''' Maps wpa_cli scan flags, e.g. "[WPA2-PSK-CCMP][WPS][ESS]", to (security type, label).
       Returns (None, None) for ad-hoc/mesh/P2P entries, which are not shown. '''
   if '[IBSS]' in flags or '[MESH]' in flags or '[P2P]' in flags:
      return None, None
   wpa3 = 'SAE' in flags
   wpa2 = 'WPA2' in flags or 'RSN' in flags
   if 'PSK' in flags:
      if wpa3:
         return 'psk', 'WPA2/WPA3 Personal'
      return 'psk', 'WPA2 Personal' if wpa2 else 'WPA Personal'
   if 'EAP' in flags:
      return 'eap', 'Enterprise'
   if wpa3:
      return 'sae', 'WPA3 Personal'
   if 'WEP' in flags:
      return 'wep', 'WEP (not supported)'
   if 'OWE' in flags:
      return 'owe', 'Enhanced Open (not supported)'
   return 'open', 'Open'


def _parse_scan_results(text):
   bsses = []
   for line in text.splitlines():
      if line.startswith('bssid /'):
         continue
      parts = line.split('\t', 4)
      if len(parts) < 4:
         continue
      freq = _int_or_none(parts[1])
      level = _int_or_none(parts[2])
      if freq is None or level is None:
         continue
      raw = printf_decode(parts[4]) if len(parts) > 4 else b''
      bsses.append({'bssid': parts[0], 'freq': freq, 'signal': level, 'flags': parts[3], 'ssid_bytes': raw})
   return bsses


def request_scan():
   ''' Asks wpa_supplicant to start a scan.  Returns (ok, error). '''
   soft, hard = rfkill_state()
   if hard or soft:
      return False, 'WiFi is turned off (rfkill).  Set the WiFi country with raspi-config.'
   ok, out, error = _wpa('scan')
   if not ok and 'FAIL-BUSY' in out:
      return True, None       # a scan is already running; its results will show up
   return ok, error


def get_networks():
   ''' Returns the scan results grouped by SSID (strongest access point first), plus saved networks
       that are not currently in range.  Hidden (empty) SSIDs are left out. '''
   ok, out, error = _wpa('scan_results')
   if not ok:
      return {'ok': False, 'error': error, 'networks': []}

   _, saved, _ = list_saved_networks()
   saved_by_ssid = {}
   for net in saved:
      # prefer the entry wpa_supplicant is using, then any enabled one
      existing = saved_by_ssid.get(net['ssid_bytes'])
      if existing is None or net['current'] or (existing['disabled'] and not net['disabled']):
         saved_by_ssid[net['ssid_bytes']] = net
   current = [n for n in saved if n['current']]
   current_ssid = current[0]['ssid_bytes'] if current else None
   wpa_ok, status_text, _ = _wpa('status')
   connected = wpa_ok and _parse_kv(status_text).get('wpa_state') == 'COMPLETED'

   grouped = {}
   for bss in _parse_scan_results(out):
      raw = bss['ssid_bytes']
      if not raw or raw.strip(b'\x00') == b'':
         continue
      security, label = classify_security(bss['flags'])
      if security is None:
         continue
      net = grouped.get(raw)
      if net is None:
         net = {'ssid_bytes': raw, 'signal': None, 'bands': set(), 'ap_count': 0}
         grouped[raw] = net
      net['bands'].add(freq_to_band(bss['freq']))
      net['ap_count'] += 1
      if net['signal'] is None or bss['signal'] > net['signal']:
         net.update({'signal': bss['signal'], 'freq': bss['freq'], 'bssid': bss['bssid'],
            'security': security, 'security_label': label})

   networks = []
   for raw, net in grouped.items():
      percent, bars, quality = signal_quality(net['signal'])
      saved_net = saved_by_ssid.get(raw)
      networks.append({
         'ssid': ssid_display(raw), 'ssid_hex': raw.hex(),
         'signal': net['signal'], 'quality': percent, 'bars': bars, 'quality_label': quality,
         'security': net['security'], 'security_label': net['security_label'],
         'supported': net['security'] in SECURITY_TYPES,
         'bands': sorted(b for b in net['bands'] if b), 'channel': freq_to_channel(net['freq']),
         'freq': net['freq'], 'ap_count': net['ap_count'], 'in_range': True,
         'saved': saved_net is not None, 'network_id': saved_net['id'] if saved_net else None,
         'connected': connected and raw == current_ssid})
   networks.sort(key=lambda n: (not n['connected'], -(n['signal'] if n['signal'] is not None else -200)))

   # saved networks that weren't seen in the scan (out of range, or hidden), so they can be forgotten
   for raw, saved_net in saved_by_ssid.items():
      if raw in grouped or not raw:
         continue
      networks.append({
         'ssid': ssid_display(raw), 'ssid_hex': raw.hex(), 'signal': None, 'quality': None, 'bars': 0,
         'quality_label': '', 'security': None, 'security_label': 'Saved', 'supported': True,
         'bands': [], 'channel': None, 'freq': None, 'ap_count': 0, 'in_range': False,
         'saved': True, 'network_id': saved_net['id'],
         'connected': connected and raw == current_ssid})
   return {'ok': True, 'error': None, 'networks': networks}


# --- status & link details ----------------------------------------------------------------------
def _parse_iw_block(text):
   ''' Parses "key: value" lines of 'iw dev X link' / 'iw dev X station dump' (first station only). '''
   result = {}
   stations = 0
   for line in text.splitlines():
      if line.startswith('Station ') or line.startswith('Connected to '):
         stations += 1
         if stations > 1:
            break
         m = re.search(r'([0-9a-fA-F]{2}(:[0-9a-fA-F]{2}){5})', line)
         if m:
            result['bssid'] = m.group(1)
         continue
      if ':' in line:
         key, value = line.split(':', 1)
         result[key.strip().lower()] = value.strip()
   return result


def _packets(iw_link_value):
   # 'iw dev X link' shows traffic as "RX: 12345 bytes (100 packets)"
   m = re.search(r'\((\d+) packets\)', iw_link_value or '')
   return m.group(1) if m else None


def _parse_iw_info(text):
   result = {}
   for line in text.splitlines():
      line = line.strip()
      if line.startswith('channel '):
         m = re.search(r'width:\s*([\d.]+ MHz)', line)
         if m:
            result['width'] = m.group(1)
      elif line.startswith('txpower '):
         result['txpower'] = line[len('txpower '):].strip()
      elif line.startswith('addr '):
         result['addr'] = line[len('addr '):].strip()
   return result


def _read_proc_wireless(iface):
   ''' /proc/net/wireless: "wlan0: 0000   56.  -54.  -256  0  0  0  0  0  0"
       = status, link quality, level, noise, discarded nwid/crypt/frag/retry/misc, missed beacons '''
   try:
      with open(PROC_NET_WIRELESS) as f:
         lines = f.readlines()
   except OSError:
      return None
   for line in lines[2:]:
      if ':' not in line:
         continue
      name, rest = line.split(':', 1)
      if name.strip() != iface:
         continue
      fields = rest.split()
      if len(fields) < 10:
         return None
      try:
         return {'link': float(fields[1].rstrip('.')), 'level': float(fields[2].rstrip('.')),
            'noise': float(fields[3].rstrip('.')), 'discard_retry': int(fields[7]),
            'discard_misc': int(fields[8]), 'missed_beacon': int(fields[9])}
      except ValueError:
         return None
   return None


def _ip_info(iface):
   info = {'ipv4': [], 'ipv6': [], 'gateway': None, 'route': None}
   rc, out, _ = _run(['ip', '-o', '-4', 'addr', 'show', 'dev', iface])
   if rc == 0:
      info['ipv4'] = re.findall(r'\binet\s+(\S+)', out)
   rc, out, _ = _run(['ip', '-o', '-6', 'addr', 'show', 'dev', iface, 'scope', 'global'])
   if rc == 0:
      info['ipv6'] = re.findall(r'\binet6\s+(\S+)', out)
   rc, out, _ = _run(['ip', 'route', 'show', 'default', 'dev', iface])
   if rc == 0:
      m = re.search(r'\bvia\s+(\S+)', out)
      if m:
         info['gateway'] = m.group(1)
   # which interface would be used to reach the internet (doesn't send any packets)
   rc, out, _ = _run(['ip', 'route', 'get', '1.1.1.1'])
   if rc == 0:
      dev = re.search(r'\bdev\s+(\S+)', out)
      via = re.search(r'\bvia\s+(\S+)', out)
      if dev:
         info['route'] = dev.group(1) + (f' via {via.group(1)}' if via else '')
   return info


def _dns_servers():
   text = _read_file(RESOLV_CONF) or ''
   return [line.split()[1] for line in text.splitlines() if line.startswith('nameserver') and len(line.split()) > 1]


def _wifi_country():
   ok, out, _ = _wpa('get', 'country')
   if ok and re.fullmatch(r'[A-Z]{2}', out):
      return out
   rc, out, _ = _run(['iw', 'reg', 'get'])
   if rc == 0:
      m = re.search(r'country ([A-Z0-9]{2}):', out)
      if m and m.group(1) != '00':
         return m.group(1)
   return None


_status_cache = {'time': 0.0, 'value': None}


def get_status():
   ''' Returns a dict describing the WiFi connection, with a 'details' list of
       {'title': section, 'rows': [[label, value], ...]} for display. '''
   now = time.time()
   if _status_cache['value'] is not None and now - _status_cache['time'] < STATUS_CACHE_SECONDS:
      status = dict(_status_cache['value'])
   else:
      status = _read_status()
      _status_cache['time'] = now
      _status_cache['value'] = status
      status = dict(status)
   status['job'] = job_state()
   return status


def _read_status():
   iface = wifi_interface()
   soft, hard = rfkill_state()
   status = {'interface': iface, 'available': False, 'connected': False, 'error': None,
      'state': 'Unavailable', 'wpa_state': '', 'ssid': '', 'signal': None, 'quality': None,
      'bars': 0, 'quality_label': '', 'ip_address': '', 'band': '', 'channel': None,
      'blocked': soft or hard, 'details': []}

   ok, out, error = _wpa('status')
   wpa = _parse_kv(out) if ok else {}
   if ok:
      status['available'] = True
      wpa_state = wpa.get('wpa_state', '')
      status['wpa_state'] = wpa_state
      status['state'] = WPA_STATE_TEXT.get(wpa_state, wpa_state.title())
      status['connected'] = wpa_state == 'COMPLETED'
   else:
      status['error'] = error
   if hard:
      status['error'] = 'WiFi is blocked by a hardware switch (rfkill)'
   elif soft:
      status['error'] = 'WiFi is turned off (rfkill).  Set the WiFi country with raspi-config.'

   connection, signal, traffic, network = [], [], [], []
   if status['connected'] or wpa.get('ssid'):
      raw = printf_decode(wpa.get('ssid', ''))
      status['ssid'] = ssid_display(raw)
      freq = _int_or_none(wpa.get('freq'))
      status['band'] = freq_to_band(freq)
      status['channel'] = freq_to_channel(freq)
      connection.append(['Network', status['ssid']])
      if wpa.get('bssid'):
         connection.append(['Access point', wpa['bssid']])
      if freq:
         connection.append(['Band', f"{status['band']}, channel {status['channel']} ({freq} MHz)"])
      security = wpa.get('key_mgmt', '')
      if wpa.get('pairwise_cipher') and wpa.get('pairwise_cipher') != 'NONE':
         security += f" ({wpa['pairwise_cipher']})"
      if security:
         connection.append(['Security', 'Open' if security == 'NONE' else security])

   if status['connected']:
      _, poll_text, _ = _wpa('signal_poll')
      poll = _parse_kv(poll_text)
      rc, link_text, _ = _run(['iw', 'dev', iface, 'link'])
      link = _parse_iw_block(link_text) if rc == 0 else {}
      rc, station_text, _ = _run(['iw', 'dev', iface, 'station', 'dump'])
      station = _parse_iw_block(station_text) if rc == 0 else {}
      rc, info_text, _ = _run(['iw', 'dev', iface, 'info'])
      info = _parse_iw_info(info_text) if rc == 0 else {}
      rc, ps_text, _ = _run(['iw', 'dev', iface, 'get', 'power_save'])
      power_save = ps_text.split(':', 1)[1].strip() if rc == 0 and ':' in ps_text else None
      proc = _read_proc_wireless(iface)

      rssi = _int_or_none(poll.get('RSSI'))
      if rssi is None:
         rssi = _first_int(station.get('signal') or link.get('signal'))
      if rssi is None and proc:
         rssi = int(proc['level'])
      status['signal'] = rssi
      status['quality'], status['bars'], status['quality_label'] = signal_quality(rssi)

      width = info.get('width') or poll.get('WIDTH')
      if width:
         for row in connection:
            if row[0] == 'Band':
               row[1] += f', {width} wide'
      tx_bitrate = station.get('tx bitrate') or link.get('tx bitrate')
      standard = _wifi_standard(tx_bitrate)
      if standard:
         connection.append(['Standard', standard])
      connected_time = _int_or_none(_first_int(station.get('connected time')))
      if connected_time is not None:
         connection.append(['Connected for', _fmt_duration(connected_time)])

      if rssi is not None:
         signal.append(['Signal strength', f"{rssi} dBm ({status['quality_label']}, {status['quality']}%)"])
      avg = _first_int(station.get('signal avg')) if station.get('signal avg') else _int_or_none(poll.get('AVG_RSSI'))
      if avg is not None:
         signal.append(['Average signal', f'{avg} dBm'])
      if station.get('beacon signal avg'):
         signal.append(['Beacon signal', station['beacon signal avg']])
      if proc:
         signal.append(['Link quality', f"{proc['link']:.0f}/{PROC_LINK_QUALITY_MAX}"])
      noise = _int_or_none(poll.get('NOISE'))
      if noise is None and proc and -150 < proc['noise'] < 0:
         noise = int(proc['noise'])
      if noise is not None and noise != 9999 and -150 < noise < 0:
         signal.append(['Noise', f'{noise} dBm'])
         if rssi is not None:
            signal.append(['Signal to noise', f'{rssi - noise} dB'])
      if tx_bitrate:
         signal.append(['Transmit rate', tx_bitrate])
      rx_bitrate = station.get('rx bitrate') or link.get('rx bitrate')
      if rx_bitrate:
         signal.append(['Receive rate', rx_bitrate])
      if not tx_bitrate and poll.get('LINKSPEED'):
         signal.append(['Link speed', f"{poll['LINKSPEED']} Mbit/s"])
      if station.get('expected throughput'):
         signal.append(['Expected throughput', station['expected throughput']])
      if info.get('txpower'):
         signal.append(['Transmit power', info['txpower']])
      if power_save:
         signal.append(['Power saving', power_save])

      rx_bytes = _int_or_none(station.get('rx bytes'))
      tx_bytes = _int_or_none(station.get('tx bytes'))
      if rx_bytes is None and link.get('rx'):
         rx_bytes = _first_int(link['rx'])
      if tx_bytes is None and link.get('tx'):
         tx_bytes = _first_int(link['tx'])
      rx_packets = station.get('rx packets') or _packets(link.get('rx'))
      tx_packets = station.get('tx packets') or _packets(link.get('tx'))
      if rx_bytes is not None:
         traffic.append(['Received', _fmt_bytes(rx_bytes) + (f' ({rx_packets} packets)' if rx_packets else '')])
      if tx_bytes is not None:
         traffic.append(['Sent', _fmt_bytes(tx_bytes) + (f' ({tx_packets} packets)' if tx_packets else '')])
      for key, label in (('tx retries', 'Transmit retries'), ('tx failed', 'Transmit failures'),
                         ('rx drop misc', 'Receive drops'), ('beacon loss', 'Beacons lost')):
         if station.get(key) is not None:
            traffic.append([label, station[key]])
      if proc:
         traffic.append(['Missed beacons', str(proc['missed_beacon'])])
         traffic.append(['Discarded (retry limit)', str(proc['discard_retry'])])
      if station.get('inactive time'):
         traffic.append(['Inactive time', station['inactive time']])
      if link.get('dtim period'):
         traffic.append(['DTIM period', link['dtim period']])
      if link.get('beacon int'):
         traffic.append(['Beacon interval', f"{link['beacon int']} TU"])

   ip = _ip_info(iface)
   status['ip_address'] = ip['ipv4'][0].split('/')[0] if ip['ipv4'] else ''
   network.append(['IPv4 address', ', '.join(ip['ipv4']) or 'None'])
   if ip['gateway']:
      network.append(['Gateway', ip['gateway']])
   dns = _dns_servers()
   if dns:
      network.append(['DNS servers', ', '.join(dns)])
   if ip['ipv6']:
      network.append(['IPv6 address', ', '.join(ip['ipv6'])])
   if ip['route']:
      network.append(['Internet route', ip['route']])
   mac = wpa.get('address') or _read_file(os.path.join(SYS_CLASS_NET, iface, 'address'))
   if mac:
      network.append(['MAC address', mac])
   network.append(['Hostname', socket.gethostname()])
   operstate = _read_file(os.path.join(SYS_CLASS_NET, iface, 'operstate'))
   network.append(['Interface', f'{iface} ({operstate})' if operstate else iface])
   if status['available']:
      country = _wifi_country()
      network.append(['WiFi country', country or 'Not set (use raspi-config)'])
      network.append(['Supplicant state', status['wpa_state'] or 'unknown'])
   if soft or hard:
      network.append(['Radio', 'Blocked by rfkill' + (' (hardware)' if hard else '')])

   status['details'] = [{'title': title, 'rows': rows} for title, rows in
      (('Connection', connection), ('Signal', signal), ('Traffic', traffic), ('Network', network)) if rows]
   return status


# --- connecting ---------------------------------------------------------------------------------
_job = {'state': 'idle', 'ssid': '', 'message': '', 'finished': None}


def job_state():
   job = {'state': _job['state'], 'ssid': _job['ssid'], 'message': _job['message'], 'age': None}
   if _job['finished'] is not None:
      job['age'] = round(time.time() - _job['finished'])
   return job


def _set_job(state, message, ssid=None):
   _job['state'] = state
   _job['message'] = message
   if ssid is not None:
      _job['ssid'] = ssid
   _job['finished'] = time.time() if state in ('connected', 'failed') else None
   _status_cache['value'] = None   # make the next status poll fresh


def _byte_len(text):
   return len(text.encode('utf-8'))


def validate_connect_request(data):
   ''' Checks a 'wifi_connect' request from the page.  Returns (params, error_message). '''
   if not isinstance(data, dict):
      return None, 'Invalid request'
   ssid_hex = str(data.get('ssid_hex') or '')
   try:
      ssid_bytes = bytes.fromhex(ssid_hex) if ssid_hex else str(data.get('ssid') or '').encode('utf-8')
   except ValueError:
      return None, 'Invalid network name'
   if not 1 <= len(ssid_bytes) <= 32:
      return None, 'The network name must be 1 to 32 characters'
   security = data.get('security')
   password = str(data.get('password') or '')
   identity = str(data.get('identity') or '').strip()
   network_id = _int_or_none(data.get('network_id'))
   # a saved network with no new credentials entered is connected using what's already saved
   use_saved = network_id is not None and password == '' and identity == ''
   if not use_saved and security not in SECURITY_TYPES:
      return None, 'This type of network security is not supported'
   if network_id is not None:
      ok, saved, error = list_saved_networks()
      if not ok:
         return None, error
      match = [n for n in saved if n['id'] == network_id and n['ssid_bytes'] == ssid_bytes]
      if not match:
         if use_saved:
            return None, 'That saved network no longer exists; please scan again'
         network_id = None

   if not use_saved:
      if security == 'psk':
         is_hex_key = len(password) == 64 and all(c in string.hexdigits for c in password)
         if not is_hex_key and not 8 <= _byte_len(password) <= 63:
            return None, 'WiFi passwords are 8 to 63 characters long'
      elif security == 'sae':
         if not password:
            return None, 'Please enter the password'
      elif security == 'eap':
         if not identity:
            return None, 'Please enter the username'
         if not password:
            return None, 'Please enter the password'

   params = {'ssid_bytes': ssid_bytes, 'ssid': ssid_display(ssid_bytes), 'security': security,
      'password': password, 'identity': identity, 'hidden': bool(data.get('hidden')),
      'network_id': network_id if use_saved else None}
   return params, None


def start_connect(data):
   ''' Validates the request and starts connecting in a background task.  Returns (ok, message). '''
   if _job['state'] == 'connecting':
      return False, f"Already connecting to {_job['ssid']}"
   params, error = validate_connect_request(data)
   if error:
      return False, error
   _set_job('connecting', f"Connecting to {params['ssid']}", params['ssid'])
   from app import socketio
   app = current_app._get_current_object()
   socketio.start_background_task(_connect_job, app, params)
   return True, _job['message']


def _connect_job(app, params):
   with app.app_context():
      try:
         state, message = _connect(params)
      except Exception as e:
         _logger().exception('WiFi connect failed')
         state, message = 'failed', f'Unexpected error: {e}'
      finally:
         params['password'] = ''
      _logger().info(f"WiFi connect to '{params['ssid']}': {state}: {message}")
      _set_job(state, message)


def psk_hex(password, ssid_bytes):
   ''' The WPA pre-shared key (what wpa_passphrase calculates): PBKDF2-HMAC-SHA1(passphrase, ssid, 4096, 32).
       A 64 hex-digit password is already a raw key. '''
   if len(password) == 64 and all(c in string.hexdigits for c in password):
      return password.lower()
   return hashlib.pbkdf2_hmac('sha1', password.encode('utf-8'), ssid_bytes, 4096, 32).hex()


def _configure_network(net_id, params):
   # hex-encoded (unquoted) values avoid any quoting problems with unusual characters
   settings = [('ssid', params['ssid_bytes'].hex())]
   security = params['security']
   if security == 'open':
      settings.append(('key_mgmt', 'NONE'))
   elif security == 'psk':
      settings += [('key_mgmt', 'WPA-PSK'), ('psk', psk_hex(params['password'], params['ssid_bytes']))]
   elif security == 'sae':
      # WPA3-only networks: needs driver support, which the Pi's brcmfmac on Buster may not have
      settings += [('key_mgmt', 'SAE'), ('ieee80211w', '2'),
         ('sae_password', params['password'].encode('utf-8').hex())]
   elif security == 'eap':
      # PEAP or TTLS with MSCHAPv2 covers most enterprise networks (e.g. eduroam).  No CA certificate
      # is configured, so the server's certificate is not verified.
      settings += [('key_mgmt', 'WPA-EAP'), ('eap', 'PEAP TTLS'),
         ('identity', params['identity'].encode('utf-8').hex()),
         ('password', params['password'].encode('utf-8').hex()),
         ('phase2', '"auth=MSCHAPV2"')]
   if params['hidden']:
      settings.append(('scan_ssid', '1'))
   for name, value in settings:
      ok, _, error = _wpa('set_network', net_id, name, value)
      if not ok:
         return False, f"Could not set '{name}' for the network: {error}"
   return True, None


def _ipv4_address(iface):
   rc, out, _ = _run(['ip', '-o', '-4', 'addr', 'show', 'dev', iface])
   m = re.search(r'\binet\s+(\d+\.\d+\.\d+\.\d+)', out) if rc == 0 else None
   return m.group(1) if m else None


def _connect(params):
   ''' Adds (or reuses) the network, connects to it, and saves it if the connection works.
       If it fails, the new entry is removed and the previous networks are re-enabled, so the Pi
       goes back to the network it was on.  Returns (job state, message). '''
   from app import socketio
   ssid = params['ssid']
   iface = wifi_interface()

   soft, hard = rfkill_state()
   if hard:
      return 'failed', 'WiFi is blocked by a hardware switch (rfkill)'
   if soft:
      rc, _, _ = _run(['sudo', '-n', 'rfkill', 'unblock', 'wifi'])
      if rc != 0:
         return 'failed', 'WiFi is turned off (rfkill) and could not be turned on.  Set the WiFi country with raspi-config.'
      socketio.sleep(2)

   ok, saved, error = list_saved_networks()
   if not ok:
      return 'failed', error
   previously_enabled = [n['id'] for n in saved if not n['disabled']]

   new_id = None
   if params['network_id'] is not None:
      target_id = params['network_id']
      if any(n['id'] == target_id and n['temp_disabled'] for n in saved):
         # left over from an earlier failure; select_network doesn't clear it, but disable + enable does
         _wpa('disable_network', target_id)
         _wpa('enable_network', target_id)
   else:
      ok, out, error = _wpa('add_network')
      if not ok or not out.isdigit():
         return 'failed', f'Could not add the network: {error or out}'
      target_id = new_id = int(out)
      ok, error = _configure_network(new_id, params)
      if not ok:
         _wpa('remove_network', new_id)
         return 'failed', error

   # select_network connects now and temporarily disables the other networks
   ok, _, error = _wpa('select_network', target_id)
   connected = False
   if ok:
      connected, failure = _wait_for_connection(target_id, params)
   else:
      failure = f'Could not select the network: {error}'

   if not connected:
      if new_id is not None:
         _wpa('remove_network', new_id)
      elif target_id not in previously_enabled:
         _wpa('disable_network', target_id)
      for net_id in previously_enabled:
         if net_id != new_id:
            _wpa('enable_network', net_id)
      _wpa('reassociate')
      return 'failed', failure

   # success: drop older entries for the same SSID (stale credentials) and re-enable the others
   removed = set()
   if new_id is not None:
      for net in saved:
         if net['ssid_bytes'] == params['ssid_bytes'] and net['id'] != new_id:
            _wpa('remove_network', net['id'])
            removed.add(net['id'])
   for net_id in previously_enabled:
      if net_id not in removed and net_id != target_id:
         _wpa('enable_network', net_id)
   saved_ok, _, _ = _wpa('save_config')

   _set_job('connecting', f'Connected to {ssid}; waiting for an IP address')
   address = _ipv4_address(iface)
   deadline = time.time() + DHCP_TIMEOUT
   while address is None and time.time() < deadline:
      socketio.sleep(1)
      address = _ipv4_address(iface)

   message = f'Connected to {ssid}' + (f' ({address})' if address else ', but no IP address was assigned (DHCP)')
   if not saved_ok:
      message += ".  It could not be saved and will be forgotten after a reboot (wpa_supplicant.conf needs 'update_config=1')."
   return 'connected', message


def _wait_for_connection(target_id, params):
   ''' Polls wpa_supplicant until the network is connected, disabled after an authentication
       failure, or CONNECT_TIMEOUT expires.  Returns (connected, failure_message). '''
   from app import socketio
   ssid = params['ssid']
   security = params['security']
   states_seen = set()
   deadline = time.time() + CONNECT_TIMEOUT
   while time.time() < deadline:
      socketio.sleep(1)
      ok, out, _ = _wpa('status')
      status = _parse_kv(out) if ok else {}
      state = status.get('wpa_state', '')
      states_seen.add(state)
      if state == 'COMPLETED' and status.get('id') == str(target_id):
         return True, None
      if state:
         _set_job('connecting', f'Connecting to {ssid}: {WPA_STATE_TEXT.get(state, state.title())}')

      # wpa_supplicant temporarily disables a network after a failed authentication (e.g. wrong password)
      ok, saved, _ = list_saved_networks()
      if any(n['id'] == target_id and n['temp_disabled'] for n in saved):
         if security == 'eap':
            return False, f'Could not connect to {ssid}.  Check the username and password.'
         if security == 'open':
            return False, f'Could not connect to {ssid}.'
         return False, f'Could not connect to {ssid}.  The password may be wrong.'

   if states_seen <= {'SCANNING', 'DISCONNECTED', 'INACTIVE', ''}:
      return False, f'{ssid} was not found.  Is it in range?'
   if security == 'open':
      return False, f'Timed out connecting to {ssid}.'
   return False, f'Timed out connecting to {ssid}.  Check the password.'


def forget_network(data):
   ''' Removes a saved network.  Returns (ok, message). '''
   if _job['state'] == 'connecting':
      return False, 'Please wait until the current connection attempt finishes'
   if not isinstance(data, dict):
      return False, 'Invalid request'
   network_id = _int_or_none(data.get('network_id'))
   try:
      ssid_bytes = bytes.fromhex(str(data.get('ssid_hex') or ''))
   except ValueError:
      return False, 'Invalid network name'
   ok, saved, error = list_saved_networks()
   if not ok:
      return False, error
   # remove every entry for this SSID so it is really forgotten
   matches = [n for n in saved if n['ssid_bytes'] == ssid_bytes or (network_id is not None and n['id'] == network_id and not ssid_bytes)]
   if not matches:
      return False, 'That network is not saved'
   for net in matches:
      ok, _, error = _wpa('remove_network', net['id'])
      if not ok:
         return False, f'Could not forget the network: {error}'
   _status_cache['value'] = None
   saved_ok, _, _ = _wpa('save_config')
   name = matches[0]['ssid']
   _logger().info(f"WiFi network '{name}' forgotten")
   if not saved_ok:
      return True, f"Forgot {name}, but wpa_supplicant.conf could not be updated ('update_config=1' is needed), so it will come back after a reboot."
   return True, f'Forgot {name}'
