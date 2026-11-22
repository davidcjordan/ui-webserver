// WiFi page (wifi.html): connection status polling, network list, connect dialog and on-screen keyboard.
// Server side: the wifi_* socketio events in app/main/events.py, which use app/func_wifi.py.
// 'socket' is created by state_update.js, which base.html loads before this file.
// SSIDs are chosen by whoever runs a nearby access point, so they are only ever set with textContent.
(function () {
  'use strict';

  var STATUS_POLL_MS = 2000;
  var JOB_MESSAGE_SECONDS = 60;   // how long the result of a connect attempt stays on screen

  function $(id) { return document.getElementById(id); }

  function el(tag, className, text) {
    var e = document.createElement(tag);
    if (className) e.className = className;
    if (text !== undefined && text !== null) e.textContent = text;
    return e;
  }

  function utf8Length(text) { return new TextEncoder().encode(text).length; }

  var dialog = $('wifi_dialog');
  var ssidInput = $('wifi_ssid_input');
  var identityInput = $('wifi_identity_input');
  var passwordInput = $('wifi_password_input');
  var connectButton = $('wifi_connect_button');
  var forgetButton = $('wifi_forget_button');
  var showPasswordButton = $('wifi_show_password');
  var scanButton = $('wifi_scan_button');
  var keyboard = $('wifi_keyboard');

  var dialogNetwork = null;    // the network the dialog is for; {hidden: true, ...} for "Other..."
  var hiddenSecurity = 'psk';  // security chosen for a hidden network
  var activeInput = null;      // where the on-screen keyboard types
  var waitingForAck = false;
  var forgetArmed = false;
  var forgetTimer = null;
  var lastJobState = null;
  var detailsKey = '';
  var noteTimer = null;

  // ---------------- connection status ----------------
  function setBars(elem, bars) { elem.setAttribute('data-bars', String(bars || 0)); }

  function renderStatus(st) {
    setBars($('wifi_status_bars'), st.connected ? st.bars : 0);
    $('wifi_state').textContent = st.available ? st.state : 'WiFi unavailable';
    $('wifi_ssid').textContent = st.ssid || '';
    var summary = [];
    if (st.connected && st.signal !== null) summary.push(st.signal + ' dBm ' + st.quality_label);
    if (st.connected && st.band) summary.push(st.band + (st.channel ? ' ch ' + st.channel : ''));
    if (st.ip_address) summary.push(st.ip_address);
    $('wifi_summary').textContent = summary.join(' · ');

    var errorBox = $('wifi_status_error');
    errorBox.textContent = st.error || '';
    errorBox.hidden = !st.error;

    renderJob(st.job);
    renderDetails(st.details || []);
  }

  function renderJob(job) {
    var box = $('wifi_job');
    if (!job) {
      box.hidden = true;
      return;
    }
    var finished = job.state === 'connected' || job.state === 'failed';
    var show = job.state === 'connecting' || (finished && job.age !== null && job.age < JOB_MESSAGE_SECONDS);
    box.hidden = !show;
    if (show) {
      box.textContent = job.message + (job.state === 'connecting' ? '…' : '');
      box.className = 'wifi-message ' + (job.state === 'connecting' ? 'wifi-message-busy' :
        (job.state === 'connected' ? 'wifi-message-ok' : 'wifi-message-error'));
    }
    if (lastJobState === 'connecting' && job.state !== 'connecting') {
      // the attempt finished: refresh the Connected/Saved marks in the list
      socket.emit('wifi_scan', {rescan: false});
    }
    lastJobState = job.state;
  }

  function renderDetails(sections) {
    var container = $('wifi_details');
    // rebuild only when the rows change; otherwise update values in place so scrolling isn't disturbed
    var key = sections.map(function (s) {
      return s.title + ':' + s.rows.map(function (r) { return r[0]; }).join('|');
    }).join(';');
    if (key !== detailsKey) {
      detailsKey = key;
      container.textContent = '';
      sections.forEach(function (section) {
        container.appendChild(el('div', 'wifi-detail-title', section.title));
        section.rows.forEach(function (row) {
          var r = el('div', 'wifi-detail-row');
          r.appendChild(el('span', 'wifi-detail-label', row[0]));
          r.appendChild(el('span', 'wifi-detail-value', row[1]));
          container.appendChild(r);
        });
      });
      return;
    }
    var values = container.querySelectorAll('.wifi-detail-value');
    var i = 0;
    sections.forEach(function (section) {
      section.rows.forEach(function (row) {
        if (values[i] && values[i].textContent !== row[1]) values[i].textContent = row[1];
        i++;
      });
    });
  }

  function requestStatus() { socket.emit('wifi_get_status'); }

  socket.on('wifi_status', renderStatus);
  requestStatus();
  setInterval(requestStatus, STATUS_POLL_MS);

  // ---------------- network list ----------------
  function networkSubtitle(net) {
    if (!net.in_range) return 'Not in range';
    var parts = [net.security_label];
    if (net.bands.length) parts.push(net.bands.join(' & '));
    if (net.channel) parts.push('ch ' + net.channel);
    if (net.ap_count > 1) parts.push(net.ap_count + ' access points');
    return parts.join(' · ');
  }

  function makeBars(bars) {
    var span = el('span', 'wifi-bars');
    for (var i = 0; i < 4; i++) span.appendChild(el('i'));
    setBars(span, bars);
    return span;
  }

  function renderNetworks(result) {
    scanButton.disabled = !!result.scanning;
    $('wifi_scan_state').textContent = result.scanning ? 'Scanning…' : '';
    var errorBox = $('wifi_network_error');
    errorBox.textContent = result.error || '';
    errorBox.hidden = !result.error;

    var list = $('wifi_network_list');
    var scrollTop = list.scrollTop;
    list.textContent = '';
    var networks = result.networks || [];
    if (networks.length === 0) {
      list.appendChild(el('div', 'wifi-empty',
        result.scanning ? 'Looking for networks…' : 'No networks found.  Tap Scan to look again.'));
    }
    networks.forEach(function (net) {
      var row = el('div', 'wifi-net');
      if (net.connected) row.classList.add('wifi-net-connected');
      if (!net.supported) row.classList.add('wifi-net-unsupported');
      if (!net.in_range) row.classList.add('wifi-net-out-of-range');
      row.appendChild(makeBars(net.bars));
      var text = el('div', 'wifi-net-text');
      text.appendChild(el('div', 'wifi-net-name', net.ssid));
      text.appendChild(el('div', 'wifi-net-sub', networkSubtitle(net)));
      row.appendChild(text);
      var right = el('div', 'wifi-net-right');
      if (net.signal !== null) right.appendChild(el('div', null, net.signal + ' dBm'));
      if (net.connected) right.appendChild(el('div', 'wifi-badge', 'Connected'));
      else if (net.saved) right.appendChild(el('div', 'wifi-badge wifi-badge-saved', 'Saved'));
      row.appendChild(right);
      row.addEventListener('click', function () { openDialog(net); });
      list.appendChild(row);
    });
    list.scrollTop = scrollTop;
  }

  function showNote(text) {
    var note = $('wifi_network_note');
    note.textContent = text;
    note.hidden = false;
    clearTimeout(noteTimer);
    noteTimer = setTimeout(function () { note.hidden = true; }, 8000);
  }

  socket.on('wifi_networks', renderNetworks);
  scanButton.addEventListener('click', function () {
    scanButton.disabled = true;
    $('wifi_scan_state').textContent = 'Scanning…';
    socket.emit('wifi_scan');
  });
  $('wifi_other_button').addEventListener('click', function () {
    openDialog({hidden: true, saved: false, supported: true, in_range: true});
  });
  socket.emit('wifi_scan');

  // ---------------- connect dialog ----------------
  function setMessage(text, isError) {
    var box = $('wifi_dialog_message');
    box.textContent = text || '';
    box.classList.toggle('wifi-dialog-message-error', !!isError);
  }

  function dialogSecurity() {
    return dialogNetwork.hidden ? hiddenSecurity : dialogNetwork.security;
  }

  function setActiveInput(input, fromFocusEvent) {
    activeInput = input;
    [ssidInput, identityInput, passwordInput].forEach(function (i) {
      i.classList.toggle('wifi-input-active', i === input);
    });
    if (input && !fromFocusEvent) input.focus();
  }

  function visibleInputs() {
    return [ssidInput, identityInput, passwordInput].filter(function (input) {
      return !input.parentNode.hidden;
    });
  }

  function setPasswordVisible(visible) {
    passwordInput.type = visible ? 'text' : 'password';
    showPasswordButton.textContent = visible ? 'Hide' : 'Show';
  }

  function disarmForget() {
    forgetArmed = false;
    clearTimeout(forgetTimer);
    forgetButton.textContent = 'Forget';
  }

  function updateDialogFields() {
    var net = dialogNetwork;
    var hidden = !!net.hidden;
    var security = dialogSecurity();
    var needsPassword = security === 'psk' || security === 'sae' || security === 'eap';

    $('wifi_row_ssid').hidden = !hidden;
    $('wifi_row_security').hidden = !hidden;
    $('wifi_row_identity').hidden = security !== 'eap';
    $('wifi_row_password').hidden = !needsPassword;
    Array.prototype.forEach.call(document.querySelectorAll('.wifi-segment'), function (button) {
      button.classList.toggle('wifi-segment-selected', button.getAttribute('data-security') === hiddenSecurity);
    });
    var placeholder = net.saved ? 'Saved – leave empty to use the saved one' : '';
    passwordInput.placeholder = placeholder;
    identityInput.placeholder = placeholder;

    var inputs = visibleInputs();
    keyboard.hidden = inputs.length === 0;
    connectButton.disabled = !net.supported;
    if (!net.supported) {
      setMessage(net.security_label.replace(' (not supported)', '') + ' networks are not supported.', true);
    } else if (!net.in_range) {
      setMessage('This saved network is not in range right now.  You can still try to connect, or forget it.');
    } else if (!hidden && security === 'open') {
      setMessage(net.saved ? '' : 'This network is open (no password).');
    } else if (security === 'sae') {
      setMessage('WPA3-only network: this may not work with the Pi’s WiFi on Buster.');
    } else {
      setMessage('');
    }
    if (inputs.indexOf(activeInput) < 0) setActiveInput(inputs.length ? inputs[0] : null);
  }

  function openDialog(net) {
    dialogNetwork = net;
    waitingForAck = false;
    var hidden = !!net.hidden;
    $('wifi_dialog_title').textContent = hidden ? 'Hidden network' : net.ssid;
    var info = [];
    if (hidden) {
      info.push('Enter the name of a network that doesn’t broadcast it');
    } else {
      if (net.in_range) info.push(net.security_label);
      if (net.bands.length) info.push(net.bands.join(' & '));
      if (net.signal !== null) info.push(net.signal + ' dBm (' + net.quality_label + ')');
      info.push(net.connected ? 'Connected' : (net.saved ? 'Saved' : 'Not saved'));
    }
    $('wifi_dialog_info').textContent = info.join(' · ');
    ssidInput.value = '';
    identityInput.value = '';
    passwordInput.value = '';
    setPasswordVisible(false);
    forgetButton.hidden = !net.saved;
    disarmForget();
    activeInput = null;
    keyboardMode = 'letters';
    shiftOn = false;
    capsLock = false;
    buildKeyboard();
    dialog.hidden = false;
    updateDialogFields();
  }

  function closeDialog() {
    dialog.hidden = true;
    // don't leave the password lying around in the page
    ssidInput.value = '';
    identityInput.value = '';
    passwordInput.value = '';
    setPasswordVisible(false);
    disarmForget();
    if (activeInput) activeInput.blur();
    activeInput = null;
    dialogNetwork = null;
    waitingForAck = false;
  }

  function fail(text, input) {
    setMessage(text, true);
    if (input) setActiveInput(input);
  }

  function connect() {
    if (waitingForAck || !dialogNetwork || connectButton.disabled) return;
    var net = dialogNetwork;
    var hidden = !!net.hidden;
    var security = dialogSecurity();
    var request = {security: security, hidden: hidden, password: '', identity: ''};

    if (hidden) {
      var name = ssidInput.value;
      if (name.length === 0) return fail('Please enter the network name', ssidInput);
      if (utf8Length(name) > 32) return fail('Network names are at most 32 characters', ssidInput);
      request.ssid = name;
    } else {
      request.ssid_hex = net.ssid_hex;
      if (net.saved) request.network_id = net.network_id;
    }
    if (!$('wifi_row_password').hidden) request.password = passwordInput.value;
    if (!$('wifi_row_identity').hidden) request.identity = identityInput.value.trim();

    var useSaved = !hidden && net.saved && request.password === '' && request.identity === '';
    if (!useSaved) {
      if (security === 'psk') {
        var length = utf8Length(request.password);
        var hexKey = /^[0-9a-fA-F]{64}$/.test(request.password);
        if (!hexKey && (length < 8 || length > 63)) {
          return fail('WiFi passwords are 8 to 63 characters long (' + length + ' entered)', passwordInput);
        }
      } else if (security === 'eap') {
        if (!request.identity) return fail('Please enter the username', identityInput);
        if (!request.password) return fail('Please enter the password', passwordInput);
      } else if (security === 'sae') {
        if (!request.password) return fail('Please enter the password', passwordInput);
      }
    }
    waitingForAck = true;
    connectButton.disabled = true;
    setMessage('Starting…');
    socket.emit('wifi_connect', request);
  }

  socket.on('wifi_connect_ack', function (ack) {
    if (!waitingForAck) return;
    waitingForAck = false;
    connectButton.disabled = false;
    if (ack.ok) {
      closeDialog();
      requestStatus();
    } else {
      setMessage(ack.message, true);
    }
  });

  forgetButton.addEventListener('click', function () {
    if (!forgetArmed) {
      forgetArmed = true;
      forgetButton.textContent = 'Tap again to forget';
      forgetTimer = setTimeout(disarmForget, 4000);
      return;
    }
    disarmForget();
    socket.emit('wifi_forget', {network_id: dialogNetwork.network_id, ssid_hex: dialogNetwork.ssid_hex});
  });

  socket.on('wifi_forget_result', function (result) {
    if (result.ok) {
      if (!dialog.hidden) closeDialog();
      showNote(result.message);
      socket.emit('wifi_scan', {rescan: false});
      requestStatus();
    } else if (!dialog.hidden) {
      setMessage(result.message, true);
    }
  });

  connectButton.addEventListener('click', connect);
  $('wifi_cancel_button').addEventListener('click', closeDialog);
  showPasswordButton.addEventListener('click', function () {
    setPasswordVisible(passwordInput.type === 'password');
  });
  Array.prototype.forEach.call(document.querySelectorAll('.wifi-segment'), function (button) {
    button.addEventListener('click', function () {
      hiddenSecurity = button.getAttribute('data-security');
      updateDialogFields();
    });
  });
  [ssidInput, identityInput, passwordInput].forEach(function (input) {
    input.addEventListener('focus', function () { setActiveInput(input, true); });
  });
  // for remote browsers with a real keyboard
  dialog.addEventListener('keydown', function (e) {
    if (e.key === 'Enter') {
      e.preventDefault();
      connect();
    } else if (e.key === 'Escape') {
      closeDialog();
    }
  });

  // ---------------- on-screen keyboard ----------------
  // multi-character entries are special keys; together the two layouts cover all printable ASCII
  var KEY_ROWS = {
    letters: [
      ['1', '2', '3', '4', '5', '6', '7', '8', '9', '0', '{bksp}'],
      ['q', 'w', 'e', 'r', 't', 'y', 'u', 'i', 'o', 'p'],
      ['a', 's', 'd', 'f', 'g', 'h', 'j', 'k', 'l'],
      ['{shift}', 'z', 'x', 'c', 'v', 'b', 'n', 'm', '-', '_'],
      ['{symbols}', '@', '{space}', '.', '{clear}']
    ],
    symbols: [
      ['1', '2', '3', '4', '5', '6', '7', '8', '9', '0', '{bksp}'],
      ['!', '@', '#', '$', '%', '^', '&', '*', '(', ')'],
      ['-', '_', '=', '+', '[', ']', '{', '}', '\\', '|'],
      [';', ':', '\'', '"', ',', '.', '<', '>', '/', '?', '`', '~'],
      ['{letters}', '{space}', '{clear}']
    ]
  };
  var SPECIAL_LABELS = {'{bksp}': '⌫', '{shift}': 'Shift', '{symbols}': '#+=', '{letters}': 'ABC',
    '{space}': 'space', '{clear}': 'Clear'};
  var keyboardMode = 'letters';
  var shiftOn = false;
  var capsLock = false;
  var lastShiftTap = 0;

  function buildKeyboard() {
    keyboard.textContent = '';
    var upper = shiftOn || capsLock;
    KEY_ROWS[keyboardMode].forEach(function (keys) {
      var row = el('div', 'wifi-key-row');
      keys.forEach(function (key) {
        var button = el('button', 'wifi-key');
        button.type = 'button';
        button.setAttribute('data-key', key);
        if (key.length > 1) {
          button.classList.add('wifi-key-wide');
          button.textContent = SPECIAL_LABELS[key];
          if (key === '{space}') button.classList.add('wifi-key-space');
          if (key === '{shift}' && capsLock) button.classList.add('wifi-key-locked');
          else if (key === '{shift}' && shiftOn) button.classList.add('wifi-key-on');
        } else {
          button.textContent = upper ? key.toUpperCase() : key;
        }
        row.appendChild(button);
      });
      keyboard.appendChild(row);
    });
  }

  function insertText(input, text) {
    var start = input.selectionStart;
    var end = input.selectionEnd;
    if (input.maxLength > 0 && input.value.length - (end - start) + text.length > input.maxLength) return;
    if (typeof start === 'number') {
      input.setRangeText(text, start, end, 'end');
    } else {
      input.value += text;
    }
  }

  function deleteBackward(input) {
    var start = input.selectionStart;
    var end = input.selectionEnd;
    if (typeof start !== 'number') {
      input.value = input.value.slice(0, -1);
    } else if (start !== end) {
      input.setRangeText('', start, end, 'end');
    } else if (start > 0) {
      input.setRangeText('', start - 1, start, 'end');
    }
  }

  function pressKey(key) {
    if (key === '{shift}') {
      var now = Date.now();
      if (capsLock) {
        capsLock = false;
        shiftOn = false;
      } else if (shiftOn && now - lastShiftTap < 500) {
        capsLock = true;            // double tap = caps lock
      } else {
        shiftOn = !shiftOn;
      }
      lastShiftTap = now;
      buildKeyboard();
      return;
    }
    if (key === '{symbols}' || key === '{letters}') {
      keyboardMode = key === '{symbols}' ? 'symbols' : 'letters';
      buildKeyboard();
      return;
    }
    if (!activeInput) return;
    if (key === '{bksp}') {
      deleteBackward(activeInput);
    } else if (key === '{clear}') {
      activeInput.value = '';
    } else {
      var ch = key === '{space}' ? ' ' : key;
      if (shiftOn || capsLock) ch = ch.toUpperCase();
      insertText(activeInput, ch);
      if (shiftOn && !capsLock) {
        shiftOn = false;            // shift applies to one character
        buildKeyboard();
      }
    }
    if ($('wifi_dialog_message').classList.contains('wifi-dialog-message-error') && !connectButton.disabled) {
      setMessage('');
    }
  }

  // keep focus (and the caret) in the text field when a key is tapped
  keyboard.addEventListener('mousedown', function (e) { e.preventDefault(); });
  keyboard.addEventListener('click', function (e) {
    var button = e.target.closest('.wifi-key');
    if (button) pressKey(button.getAttribute('data-key'));
  });
  buildKeyboard();
})();
