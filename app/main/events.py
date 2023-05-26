from flask import current_app
from flask_socketio import emit

from .. import socketio
import json
import time

from app.main.defines import *
from app.func_base import check_base, send_pause_resume_to_base, send_settings_to_base, get_game_state, send_game_help_to_base
from app.main.blueprint_core import write_base_settings_to_file
from app.func_drills import get_drill_info, get_workout_info
from app.main.blueprint_camera import scp_court_png

import sys
sys.path.append(f'{user_dir}/{repos_dir}/control_ipc_utils')
try:
   from control_ipc_defines import *
except:
   current_app.logger.error("Problems with 'control_ipc' modules, please run: git clone https://github.com/davidcjordan/control_ipc_utils")
   exit()


@socketio.on('pause_resume')
def handle_pause_resume():
   current_app.logger.info('received pause_resume.')
   send_pause_resume_to_base()


@socketio.on('refresh_image')
def handle_refresh_image(data):
   current_app.logger.info(f'received refresh_image: {data}')
   scp_court_png(data['side'], data['frame'])


@socketio.on('get_drill_desc')
def handle_get_drill(data):
   # current_app.logger.debug(f"get_drill_desc data: {data}")
   if 'drill_id' in data:
      drill_id = data['drill_id']
      if (('mode' in data) and 'work' in data['mode']):
         current_app.logger.debug(f"get_workout_desc for workout={drill_id}")
         drill_info_dict = get_workout_info(drill_id)
      else:
         current_app.logger.debug(f"get_drill_desc for drill={drill_id}")
         drill_info_dict = get_drill_info(drill_id)
      if 'desc' in drill_info_dict:
         emit('drill_desc', drill_info_dict['desc'])
      else:
         current_app.logger.warning(f"no description for drill number={drill_id}")
   else:
      current_app.logger.error(f"no drill number in get_drill_desc message")


@socketio.on('get_updates')
def handle_get_updates(data):
   json_data = json.loads(data)
   # current_app.logger.info(f"get_update data= {json_data}")

   base_state, soft_fault_status, faults_table = check_base()
   try:
      base_state_text = base_state_e(base_state).name.title() #title changes it from uppercase to capital for 1st char
   except:
      current_app.logger.error(f"base_state_e to name failed")
      base_state_text = "unknown"
   update_dict = {"base_state": base_state_text}

   if ("page" in json_data):
      current_page = '/' + json_data["page"]
      # current_app.logger.debug(f"current_page={current_page}; base_state={base_state_e(base_state).name}")
      # if (current_page == MAIN_URL):
      #    current_app.logger.debug("current_page is MAIN_URL")
      # if (base_state == base_state_e.FAULTED):
      #    current_app.logger.debug("base_state is FAULTED")
      # else:
      #   current_app.logger.debug(f"base_state is not FAULTED; its={base_state}")
 
      if ((base_state == base_state_e.FAULTED) and (current_page != FAULTS_URL)):
         update_dict['new_url'] = FAULTS_URL

      if ((base_state != base_state_e.FAULTED) and (current_page == FAULTS_URL)):
         update_dict['new_url'] = MAIN_URL
 
      if ((base_state == base_state_e.FAULTED) and (current_page == FAULTS_URL)):
         #TODO: if (len(faults_table) != len(previous_faults_table)):
         emit('faults_update', json.dumps(textify_faults_table(faults_table)))

      if (((current_page == GAME_URL) or (current_page == DRILL_URL) or (current_page == MOTOR_CALIB_URL)) and
         (base_state == base_state_e.IDLE)):
         update_dict['new_url'] = DONE_URL

      if (current_page == GAME_URL):
         game_state = get_game_state()
         if game_state is not None:
            # current_app.logger.info(f"sending score={game_state}")
            # score= {'time': 36611, 'server': 'b', 'b_sets': 0, 'p_sets': 0, 'b_games': 0, 'p_games': 0, 'b_pts': 0, 'p_pts': 0, 'b_t_pts': 0, 'p_t_pts': 0}
            update_dict["game_state"] = game_state
   else:
      current_app.logger.error(f"'page' not in get_update data= {json_data}")

   if (soft_fault_status is not None):
      try:
         update_dict['soft_fault'] = soft_fault_e(soft_fault_status).value
      except:
         current_app.logger.error(f"soft_fault enum to value failed")

   if ("new_url" in update_dict):
      current_app.logger.info(f"Changing URL from '{current_page}' to {update_dict['new_url']} since base_state={base_state_e(base_state).name}")

   emit('state_update', update_dict)


@socketio.on('change_params')     # Decorator to catch an event named change_params
def handle_change_params(data):          # change_params() is the event callback function.
   #  print('change_params data: ', data)      # data is a json string: {"speed":102}
   current_app.logger.info(f'received change_params: {data}')

   # using 'global' for settings_dict doesn't work; a local is created.
   from app.main.blueprint_core import base_settings_dict

   for k in data.keys():
      if data[k] == None:
         current_app.logger.warning(f'Received NoneType for {k}')
      else:
         # current_app.logger.debug(f'data[k] is not None; Setting: {k} to {data[k]}')
         if (k == LEVEL_PARAM):
            base_settings_dict[k] = int(data[k]*10)
         elif (k == DELAY_MOD_PARAM):
            base_settings_dict[k] = int(data[k]*1000)
         else:
            base_settings_dict[k] = int(data[k])
         current_app.logger.debug(f'Setting: {k} to {base_settings_dict[k]}')

   write_base_settings_to_file() #writes global, hence no argument
   send_settings_to_base(base_settings_dict)


@socketio.on('game_help')
def handle_game_help():
   current_app.logger.info(f'received game_help')
   send_game_help_to_base()


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
         try:
            row_dict[FLT_CODE_PARAM] = fault_e(fault[FLT_CODE_PARAM]).name
         except:
            current_app.logger.error(f"hard_fault enum to name failed")
            row_dict[FLT_CODE_PARAM] = "lookup err"
         try:
            row_dict[FLT_LOCATION_PARAM] = net_device_e(fault[FLT_LOCATION_PARAM]).name
         except:
            current_app.logger.error(f"net_device enum to name failed")
            row_dict[FLT_LOCATION_PARAM] = "lookup err"
         try:
            timestamp = datetime.datetime.fromtimestamp(fault[FLT_TIMESTAMP_PARAM])
         except:
            current_app.logger.error(f"get fault timestamp failed")
            timestamp = time.time()
         #TODO: compare date and put "yesterday" or "days ago"
         row_dict[FLT_TIMESTAMP_PARAM] = timestamp.strftime("%H:%M:%S")
         textified_faults_table.append(row_dict)
   else:
      current_app.logger.error(f"bogus fault table in fault_request: {faults_table}")
   return textified_faults_table
