
'''
base interaction: check status, update base_settings; this should be the only module that imports send_msg
'''
from flask import current_app
import time
import subprocess

from .main.defines import user_dir, repos_dir, GAME_URL
import sys
sys.path.append(f'{user_dir}/{repos_dir}/control_ipc_utils')
try:
   from ctrl_messaging_routines import send_msg
   from control_ipc_defines import *
except:
   current_app.logger.error("Problems with 'control_ipc' modules, please run: git clone https://github.com/davidcjordan/control_ipc_utils")
   exit()

import logging
try:
   logging.getLogger("ops").info('User Interface launched')
except:
   current_app.logger.error("Couldn't get logger 'ops'")

previous_base_state = base_state_e.BASE_STATE_NONE
faults_table_when_base_not_accessible = None

def check_base():
   global previous_base_state
   global faults_table_when_base_not_accessible
   soft_fault_status = None

   base_pid = None
   p = subprocess.run(['pgrep', 'bbase'], capture_output=True)
   if p.returncode == 0: 
      base_pid = p.stdout
      # current_app.logger.debug(f'bbase pid={base_pid}')
   else:
      base_pid = None

   base_state = base_state_e.BASE_STATE_NONE
   base_fault = None
   faults_table = None

   if base_pid is not None:
      # verify responding to FIFO
      # current_app.logger.info("Getting status message")
      msg_ok, status_msg = send_msg()
      if not msg_ok:
         base_fault = fault_e.CONTROL_PROGRAM_FAILED.value
         base_state = base_state_e.FAULTED
      else:
         if (status_msg is not None):
            if (STATUS_PARAM in status_msg):
               base_state = base_state_e(status_msg[STATUS_PARAM])
            else:
               base_fault = fault_e.CONTROL_PROGRAM_FAILED.value
               base_state = base_state_e.FAULTED

            if (HARD_FAULT_PARAM in status_msg and status_msg[HARD_FAULT_PARAM] > 0):
               #! NOT USED YET:  previous_fault_table = copy.deepcopy(faults_table)
               # current_app.logger.info("Getting fault table")
               msg_ok, faults_table = send_msg(GET_METHOD, FLTS_RSRC)
               if not msg_ok:
                  current_app.logger.error("msg status not OK when getting fault table")
                  base_fault = fault_e.CONTROL_PROGRAM_GET_STATUS_FAILED.value
                  base_state = base_state_e.FAULTED

            if (SOFT_FAULT_PARAM in status_msg):
               soft_fault_status = soft_fault_e(status_msg[SOFT_FAULT_PARAM])
            # current_app.logger.info(f"faults: {faults_table[0]}")
         else:
            current_app.logger.error("received None as status message")
            base_fault = fault_e.CONTROL_PROGRAM_NOT_RUNNING.value
            base_state = base_state_e.FAULTED
   else:
      base_fault = fault_e.CONTROL_PROGRAM_NOT_RUNNING.value
      base_state = base_state_e.FAULTED

   if base_state != previous_base_state:
      current_app.logger.info(f"Base state change: {base_state_e(previous_base_state).name} -> {base_state_e(base_state).name}")

   if base_state == base_state_e.FAULTED:
      if faults_table is None:
         # didn't get faults_tabe from base, so use existing or generate a new one:
         if faults_table_when_base_not_accessible is None:
            faults_table_when_base_not_accessible = [{FLT_CODE_PARAM: base_fault, FLT_LOCATION_PARAM: net_device_e.BASE, FLT_TIMESTAMP_PARAM: time.time()}]
         faults_table = faults_table_when_base_not_accessible
   else:
      faults_table_when_base_not_accessible = None

   previous_base_state = base_state
   return base_state, soft_fault_status, faults_table


def send_stop_to_base():
   rc, code = send_msg(PUT_METHOD, STOP_RSRC)
   if not rc:
      current_app.logger.error(f"function '{sys._getframe(0).f_code.co_name}': PUT STOP failed, code: {code}")

def send_pause_resume_to_base():
   rc, code = send_msg(PUT_METHOD, PAUS_RSRC)
   if not rc:
      current_app.logger.error("PUT PAUSE failed, code: {}".format(code))


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

def send_start_to_base(mode_dict):
   # mode_dict is either: 
   #  {MODE_PARAM: base_mode_e.DRILL.value, ID_PARAM: id}
   #  {MODE_PARAM: base_mode_e.WORKOUT.value, ID_PARAM: id}
   #  {MODE_PARAM: base_mode_e.GAME.value}
   #  {MODE_PARAM: base_mode_e.CREEP_CALIBRATION.value, ID_PARAM: id}
   
   rc, code = send_msg(PUT_METHOD, MODE_RSRC, mode_dict)
   if not rc:
      current_app.logger.error(f"PUT Mode {mode_dict} failed, code: {code}")
   else:
      if mode_dict[MODE_PARAM] == base_mode_e.CREEP_CALIBRATION.value:
         rc, code = send_msg(PUT_METHOD, FUNC_RSRC, {FUNC_CREEP: mode_dict[ID_PARAM]})
         if not rc:
            current_app.logger.error(f"function '{sys._getframe(0).f_code.co_name}': PUT Function failed, code: {code}")
      else:
         rc, code = send_msg(PUT_METHOD, STRT_RSRC)
         if not rc:
            current_app.logger.error("PUT START failed, code: {}".format(code))

def send_gen_vectors_to_base(cam_side):
   rc, code = send_msg(PUT_METHOD, FUNC_RSRC, {FUNC_GEN_CORRECTION_VECTORS: cam_side} )
   if not rc:
      if not code:
         code = "unknown"
      current_app.logger.error("PUT FUNC_GEN_CORRECTION_VECTORS failed, code: {code}")
   return rc
