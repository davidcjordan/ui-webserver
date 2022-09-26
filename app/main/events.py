from flask import current_app
from flask_socketio import emit

from .. import socketio
import json

import os, sys
current_dir = os.path.dirname(os.path.realpath(__file__))
parent_dir = os.path.dirname(current_dir)

sys.path.append(current_dir)
from defines import *

sys.path.append(parent_dir)
try:
   from func_base import *
   from func_drills import *
except:
   current_app.logger.error("Problems with 'func_base' modules")
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
   base_state_text = base_state_e(base_state).name.title() #title changes it from uppercase to capital for 1st char
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
 
      if (current_page == FAULTS_URL):
         #TODO: if (len(faults_table) != len(previous_faults_table)):
         emit('faults_update', json.dumps(textify_faults_table(faults_table)))

      if (((current_page == GAME_URL) or (current_page == DRILL_URL) or (current_page == CREEP_CALIB_URL)) and
         (base_state == base_state_e.IDLE)):
         update_dict['new_url'] = DONE_URL

      elif (current_page is GAME_URL):
         msg_ok, game_state = send_msg(GET_METHOD, SCOR_RSRC)
         if not msg_ok:
            current_app.logger.error("GET GAME SCORE failed, score= {}".format(game_state))
         else:
            # current_app.logger.info(f"score= {game_state}")
            # score= {'time': 36611, 'server': 'b', 'b_sets': 0, 'p_sets': 0, 'b_games': 0, 'p_games': 0, 'b_pts': 0, 'p_pts': 0, 'b_t_pts': 0, 'p_t_pts': 0}
            update_dict["game_state"] = game_state

   if (soft_fault_status is not None):
      update_dict['soft_fault'] = soft_fault_e(soft_fault_status).value

   if ("new_url" in update_dict):
      current_app.logger.info(f"Changing URL from '{current_page}' to {update_dict['new_url']} since base_state={base_state_e(base_state).name}")

   emit('state_update', update_dict)
