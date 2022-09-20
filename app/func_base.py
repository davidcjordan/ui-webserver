
'''
base interaction: check status, make fault table, read/write config files
'''
from flask import current_app
import json
import subprocess
# import copy # for deepcopy

import sys
user_dir = '/home/pi'
boomer_dir = 'boomer'
repos_dir = 'repos'

sys.path.append(f'{user_dir}/{repos_dir}/control_ipc_utils')
try:
   from ctrl_messaging_routines import send_msg
   from control_ipc_defines import *
except:
   current_app.logger.error("Problems with 'control_ipc' modules, please run: git clone https://github.com/davidcjordan/control_ipc_utils")
   exit()

site_data_dir = 'this_boomers_data'
settings_dir = f'{user_dir}/{boomer_dir}/{site_data_dir}'
settings_filename = "drill_game_settings.json"
previous_base_state = base_state_e.BASE_STATE_NONE
base_faulted_timestamp = None

def check_base():
   import time
   global previous_base_state
   global base_faulted_timestamp
   soft_fault_status = None

   base_pid = None
   p = subprocess.run(['pgrep', 'bbase'], capture_output=True)
   if p.returncode == 0: 
      base_pid = p.stdout
      # current_app.logger.debug(f'bbase pid={base_pid}')
   else:
      base_pid = None

   if base_pid is not None:
      # verify responding to FIFO
      # current_app.logger.info("Getting status message")
      msg_ok, status_msg = send_msg()
      if not msg_ok:
         faults_table = [{FLT_CODE_PARAM: fault_e.CONTROL_PROGRAM_FAILED, FLT_LOCATION_PARAM: net_device_e.BASE, FLT_TIMESTAMP_PARAM: base_faulted_timestamp}]
         base_state = base_state_e.FAULTED
      else:
         if (status_msg is not None):
            if (STATUS_PARAM in status_msg):
               base_state = base_state_e(status_msg[STATUS_PARAM])
            else:
               faults_table = [{FLT_CODE_PARAM: fault_e.CONTROL_PROGRAM_FAILED, FLT_LOCATION_PARAM: net_device_e.BASE, FLT_TIMESTAMP_PARAM: base_faulted_timestamp}]
               base_state = base_state_e.FAULTED

            if (HARD_FAULT_PARAM in status_msg and status_msg[HARD_FAULT_PARAM] > 0):
               #! NOT USED YET:  previous_fault_table = copy.deepcopy(faults_table)
               # current_app.logger.info("Getting fault table")
               msg_ok, faults_table = send_msg(GET_METHOD, FLTS_RSRC)
               if not msg_ok:
                  current_app.logger.error("msg status not OK when getting fault table")
                  faults_table = [{FLT_CODE_PARAM: fault_e.CONTROL_PROGRAM_GET_STATUS_FAILED, FLT_LOCATION_PARAM: net_device_e.BASE, FLT_TIMESTAMP_PARAM: base_faulted_timestamp}]
                  base_state = base_state_e.FAULTED

            if (SOFT_FAULT_PARAM in status_msg):
               soft_fault_status = soft_fault_e(status_msg[SOFT_FAULT_PARAM])
            # current_app.logger.info(f"faults: {faults_table[0]}")
         else:
            current_app.logger.error("received None as status message")
            faults_table = [{FLT_CODE_PARAM: fault_e.CONTROL_PROGRAM_GET_STATUS_FAILED, FLT_LOCATION_PARAM: net_device_e.BASE, FLT_TIMESTAMP_PARAM: base_faulted_timestamp}]
            base_state = base_state_e.FAULTED
   else:
      faults_table = [{FLT_CODE_PARAM: fault_e.CONTROL_PROGRAM_NOT_RUNNING, FLT_LOCATION_PARAM: net_device_e.BASE, FLT_TIMESTAMP_PARAM: base_faulted_timestamp}]
      base_state = base_state_e.FAULTED

   if base_state != previous_base_state:
      current_app.logger.info(f"Base state change: {base_state_e(previous_base_state).name} -> {base_state_e(base_state).name}")
      if base_state == base_state_e.FAULTED:
         base_faulted_timestamp = time.time()

   previous_base_state = base_state
   return base_state, soft_fault_status, faults_table


def send_settings_to_base(settings_dict):
   rc, code = send_msg(PUT_METHOD, BCFG_RSRC, \
      {LEVEL_PARAM: settings_dict[LEVEL_PARAM], \
         GRUNTS_PARAM: settings_dict[GRUNTS_PARAM], \
         TRASHT_PARAM: settings_dict[TRASHT_PARAM]})

   rc, code = send_msg(PUT_METHOD, DCFG_RSRC, \
      {SPEED_MOD_PARAM: settings_dict[SPEED_MOD_PARAM], \
         DELAY_MOD_PARAM: settings_dict[DELAY_MOD_PARAM], \
         ELEVATION_MOD_PARAM: settings_dict[ELEVATION_MOD_PARAM]})

   rc, code = send_msg(PUT_METHOD, GCFG_RSRC, \
      {SERVE_MODE_PARAM: settings_dict[SERVE_MODE_PARAM], \
         TIEBREAKER_PARAM: settings_dict[TIEBREAKER_PARAM]})
         # POINTS_DELAY_PARAM: settings_dict[POINTS_DELAY_PARAM]})


def read_settings_from_file():
   try:
      with open(f'{settings_dir}/{settings_filename}') as f:
         settings_dict = json.load(f)
         # current_app.logger.debug(f"Settings restored: {settings_dict}")
   except:
      current_app.logger.warning(f"Settings file read failed; using defaults.")
      settings_dict = {GRUNTS_PARAM: 0, TRASHT_PARAM: 0, LEVEL_PARAM: LEVEL_DEFAULT, \
            SERVE_MODE_PARAM: 1, TIEBREAKER_PARAM: 0, \
            SPEED_MOD_PARAM: SPEED_MOD_DEFAULT, DELAY_MOD_PARAM: DELAY_MOD_DEFAULT, \
            ELEVATION_MOD_PARAM: ELEVATION_ANGLE_MOD_DEFAULT}
   return settings_dict


def scp_court_png(side='Left', frame='even'):
   # current_app.logger.debug(f"scp_court_png: side={side} frame={frame}")
   source_path = f"{side.lower()}:/run/shm/frame_{frame}.png"
   destination_path = f"{user_dir}/{boomer_dir}/{side.lower()}_court.png"
   # current_app.logger.info(f"BEFORE: scp {source_path} {destination_path}")
   # the q is for quiet
   p = subprocess.Popen(["scp", "-q", source_path, destination_path], shell=False)
   rc = p.wait()
   stdoutdata, stderrdata = p.communicate()
   if p.returncode != 0:
      current_app.logger.error(f"FAILED: scp {source_path} {destination_path}; error_code={p.returncode}")
   else:
      current_app.logger.info(f"OK: scp {source_path} {destination_path}")


def read_court_points_file(side_name = 'left'):
   court_points_dict = {}
   read_ok = True
   try:
      with open(f'{settings_dir}/{side_name}_court_points.json') as f:
         file_lines = f.readlines()
         first_line_json = file_lines[0].split("}")[0] + "}"
         # current_app.logger.debug(f"first_line_json={first_line_json}")
         court_points_dict = json.loads(first_line_json)
         current_app.logger.debug(f"{side_name} court_points={court_points_dict}")
   except:
      current_app.logger.warning(f"read failed: {settings_dir}/{side_name}_court_points.json")
      read_ok = False

   return read_ok, court_points_dict


def textify_faults_table(faults_table):
   import datetime
   # example fault table:
   # faults: [{'fCod': 20, 'fLoc': 3, 'fTim': 1649434841}, {'fCod': 22, 'fLoc': 3, 'fTim': 1649434841}, {'fCod': 15, 'fLoc': 3, 'fTim': 1649434841}, {'fCod': 6, 'fLoc': 0, 'fTim': 1649434843}, {'fCod': 6, 'fLoc': 1, 'fTim': 1649434843}, {'fCod': 6, 'fLoc': 2, 'fTim': 1649434843}]

   # the faults_table gets erroneously populated with the status when multiple instances are running.
   textified_faults_table = []
   if (type(faults_table) is list):
      for fault in faults_table:
         # print(f"fault: {fault}")
         row_dict = {}
         row_dict[FLT_CODE_PARAM] = fault_e(fault[FLT_CODE_PARAM]).name
         row_dict[FLT_LOCATION_PARAM] = net_device_e(fault[FLT_LOCATION_PARAM]).name
         timestamp = datetime.datetime.fromtimestamp(fault[FLT_TIMESTAMP_PARAM])
         #TODO: compare date and put "yesterday" or "days ago"
         row_dict[FLT_TIMESTAMP_PARAM] = timestamp.strftime("%H:%M:%S")
         textified_faults_table.append(row_dict)
   else:
      current_app.logger.error(f"bogus fault table in fault_request: {faults_table}")
   return textified_faults_table
