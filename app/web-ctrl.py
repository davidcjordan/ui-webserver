#!/usr/bin/env python3


#from flask import ? session, abort
from flask import Flask, render_template, Response, request, redirect, url_for, Markup, send_from_directory
try:
   from flask_socketio import SocketIO, emit
except:
   print("Missing package 'flask_socketio', please run: python3 -m pip install flask-socketio")
   exit()

import logging
logging.basicConfig(level=logging.INFO)

app = Flask(__name__)

import inspect
import os  # for sending favicon 
import json
user_dir = '/home/pi'
boomer_dir = 'boomer'
repos_dir = 'repos'
site_data_dir = 'this_boomers_data'
settings_dir = f'{user_dir}/{boomer_dir}/{site_data_dir}'
settings_filename = "drill_game_settings.json"

# the following requires: export PYTHONPATH='/Users/tom/Documents/Projects/Boomer/control_ipc_utils'
import sys
sys.path.append(f'{user_dir}/{repos_dir}/control_ipc_utils')
# print(sys.path)
try:
   from ctrl_messaging_routines import send_msg, is_state
   from control_ipc_defines import *
except:
   app.logger.error("Missing 'control_ipc' modules, please run: git clone https://github.com/davidcjordan/control_ipc_utils")
   exit()

sys.path.append(f'{user_dir}/{boomer_dir}/drills')
try:
   from ui_drill_selection_lists import *
except:
   app.logger.error("Missing 'ui_drill_selection_lists' modules, please run: git clone https://github.com/davidcjordon/drills")
   exit()

from threading import Thread
from subprocess import Popen
import time
import json
from random import randint

base_state = None
previous_base_state = None
client_state = False

try:
   with open(f'{settings_dir}/{ui_customization.json}') as f:
      customization_dict = json.load(f)
except:
   customization_dict = {"title": "Welcome to Boomer", "icon": "/static/favicon.ico"}

my_home_button = Markup('          <button type="submit" onclick="window.location.href=\'/\';"> \
         <img src="/static/home.png" style="height:64px;"> \
         </button>')

try:
   with open(f'{settings_dir}/{settings_filename}') as f:
      settings_dict = json.load(f)
      app.logger.debug("Settings restored: {settings_dict}")
except:
   settings_dict = {GRUNTS_PARAM: 0, TRASHT_PARAM: 0, LEVEL_PARAM: LEVEL_DEFAULT, \
         SERVE_MODE_PARAM: 1, TIEBREAKER_PARAM: 0, \
         SPEED_MOD_PARAM: SPEED_MOD_DEFAULT, DELAY_MOD_PARAM: DELAY_MOD_DEFAULT, \
         ELEVATION_MOD_PARAM: ELEVATION_ANGLE_MOD_DEFAULT}

DO_SCP_FOR_CALIBRATION = False

IP_PORT = 1111 # picked what is hopefully an unused port  (can't use 44)
DEFAULT_METHODS = ['POST', 'GET']

#NOTE: drill and workout use the same pages and templates, but populate based on the mode (drill/workout)

MAIN_URL = '/'
GAME_OPTIONS_URL = '/game_options'
GAME_URL = '/game'
DRILL_SELECT_TYPE_URL = '/drill_select_type'
SELECT_URL = '/select'
DRILL_URL = '/drill'
CAM_CALIB_URL = '/cam_calib'
CAM_POSITION_URL = '/cam_position'
WORKOUT_SELECTION_URL = '/workout_selection'
SETTINGS_URL = '/settings'

# Flask looks for following in the 'templates' directory
MAIN_TEMPLATE = 'index.html'
GAME_OPTIONS_TEMPLATE = '/layouts' + GAME_OPTIONS_URL + '.html'
GAME_TEMPLATE = '/layouts' + GAME_URL + '.html'
CHOICE_INPUTS_TEMPLATE = '/layouts' + '/choice_inputs' + '.html'
SELECT_TEMPLATE = '/layouts' + SELECT_URL + '.html'
DRILL_TEMPLATE = '/layouts' + DRILL_URL + '.html'
CAM_CALIBRATION_TEMPLATE = '/layouts' + CAM_CALIB_URL + '.html'
CAM_POSITION_TEMPLATE = '/layouts' + CAM_POSITION_URL + '.html'

# base process status strings:
STATUS_NOT_RUNNING = "Down"
STATUS_NOT_RESPONDING = "Error"
MODE_NONE = " --"
MODE_GAME = "Game --"
MODE_DRILL_NOT_SELECTED = "Drills --"
MODE_WORKOUT_NOT_SELECTED = "Workout --"
MODE_WORKOUT_SELECTED = "Workout: "
MODE_SETTINGS = "Boomer Options"

DRILL_SELECT_TYPE_PLAYER = 'Player(s)'
DRILL_SELECT_TYPE_INSTRUCTORS = 'Instructors'
DRILL_SELECT_TYPE_TEST ='Test'

WORKOUT_ID = 'workout_id'
ONCLICK_MODE_KEY = 'mode'
ONCLICK_MODE_WORKOUT_VALUE = 'workouts'

previous_url = None
back_url = None

cam_side = None  # a global on which camera is being calibrated
cam_mm = [0]*3 # global camera location
X=0;Y=1;Z=2 # cam array enum
INCHES_TO_MM = 25.4

ROTARY_CALIB_ID = 780

filter_js = []
filter_js.append(Markup('<script src="/static/js/jquery-3.3.1.min.js"></script>'))
filter_js.append(Markup('<script src="/static/js/b_filtrify.js"></script>'))
filter_js.append(Markup('<script src="/static/js/invoke_filtrify.js"></script>'))
filter_js.append(Markup('<link rel="stylesheet" href="/static/css/b_filtrify.css">'))
# unused/alternate scripts:
# <script src="/static/js/filtrify.min.js"></script>
# <script src="/static/js/highlight.pack.js"></script>
# <script src="/static/js/script.js"></script>

app.config['SECRET_KEY'] = 'secret!'
# didn't find how to have multiple allowed origins
# socketio = SocketIO(app, cors_allowed_origins="https://cdnjs.cloudflare.com http://localhost")
# socketio = SocketIO(app, cors_allowed_origins="http://localhost")
# socketio = SocketIO(app, cors_allowed_origins="http://127.0.0.1")
socketio = SocketIO(app, cors_allowed_origins="*")

@app.route(CAM_POSITION_URL, methods=DEFAULT_METHODS)
def cam_position():
   global cam_side
   if request.method=='POST':
      # print(f"POST to CAM_POSITION request.form: {request.form}")
      # POST to CAM_POSITION request.form: ImmutableMultiDict([('choice', 'Left Cam Calib')])
      if ('choice' in request.form) and request.form['choice'].lower().startswith('r'):
         cam_side = 'Right'
      else:
         cam_side = 'Left'

   cam_loc_filepath = f'{settings_dir}/{cam_side}_cam_location.json'
   try:
      with open(cam_loc_filepath) as infile:
         loc_dict = json.load(infile)
   except:
      pass

   if "loc_dict" not in locals() or "cam_x_ft" not in loc_dict:
      # default values if not persisted from a previous calibration or the loaded file does have the parameters
      loc_dict = {"cam_x_ft": "0", "cam_x_in": "0", "cam_y_ft": "47", "cam_y_in": "0", "cam_z_ft": "0", "cam_z_in": "0"}

   position_options = { \
      "cam_x_ft":{"legend":"Feet", "dflt":loc_dict['cam_x_ft'], "min":-10, "max":20, "step":1, "start_div":"From Left Singles"}, \
      "cam_x_in":{"legend":"Inches", "dflt":loc_dict['cam_x_in'], "min":-11, "max":11, "step":1, "end_div":"Y"}, \
      "cam_y_ft":{"legend":"Feet", "dflt":loc_dict['cam_y_ft'], "min":39, "max":60, "step":1, "start_div":"From Net"}, \
      "cam_y_in":{"legend":"Inches", "dflt":loc_dict['cam_y_in'], "min":0, "max":11, "step":1, "end_div":"Y"}, \
      "cam_z_ft":{"legend":"Feet", "dflt":loc_dict['cam_z_ft'], "min":0, "max":20, "step":1, "start_div":"Height"}, \
      "cam_z_in":{"legend":"Inches", "dflt":loc_dict['cam_z_in'], "min":0, "max":11, "step":1, "end_div":"Y"} \
   }
   return render_template(CAM_POSITION_TEMPLATE, \
      home_button = my_home_button, \
      installation_title = customization_dict['title'], \
      installation_icon = customization_dict['icon'], \
      options = position_options, \
      footer_center = f"Mode: Get {cam_side} Cam Position")


@app.route(CAM_CALIB_URL, methods=DEFAULT_METHODS)
def cam_calib():
   global cam_side, cam_mm, X, Y, Z
   loc_dict = {}
   if request.method=='POST':
      app.logger.info(f"POST to CALIB request.form: {request.form}")
      # example: ImmutableMultiDict([('cam_id', 'l'), ('cam_x_ft', '0'), ('cam_x_in', '0'), ('cam_y_ft', '47'), ('cam_y_in', '0'), ('cam_z_ft', '8'), ('cam_z_in', '0')])
      if ('cam_id' in request.form) and request.form['cam_id'].lower().startswith('r'):
         cam_side = 'Right'
      if ('cam_x_ft' in request.form) and ('cam_x_in' in request.form):
         loc_dict['cam_x_ft'] = int(request.form['cam_x_ft'])
         loc_dict['cam_x_in'] = int(request.form['cam_x_in'])
         cam_mm[X] = int(((loc_dict['cam_x_ft'] * 12) + loc_dict['cam_x_in']) * INCHES_TO_MM)
      if ('cam_y_ft' in request.form) and ('cam_y_in' in request.form):
         loc_dict['cam_y_ft'] = int(request.form['cam_y_ft'])
         loc_dict['cam_y_in'] = int(request.form['cam_y_in'])
         cam_mm[Y] = int(((loc_dict['cam_y_ft'] * 12) + loc_dict['cam_y_in']) * INCHES_TO_MM)
      if ('cam_z_ft' in request.form) and ('cam_z_in' in request.form):
         loc_dict['cam_z_ft'] = int(request.form['cam_z_ft'])
         loc_dict['cam_z_in'] = int(request.form['cam_z_in'])
         cam_mm[Z] = int(((loc_dict['cam_z_ft'] * 12) + loc_dict['cam_z_in']) * INCHES_TO_MM)
      if len(cam_mm) > 2:
         #persist values for next calibration, so they don't have to be re-entered
         with open(f"{settings_dir}/{cam_side.lower()}_cam_location.json", "w") as outfile:
            json.dump(loc_dict, outfile)
      # print(f"cam_mm set to: {cam_mm}")

   mode_str = f"{cam_side} Court Coord"
   cam_lower = cam_side.lower()
   # copy the lastest PNG from the camera to the base
   if DO_SCP_FOR_CALIBRATION:
      p = Popen(["scp", f"{cam_lower}:/run/shm/frame.png", f"/home/pi/boomer/{cam_lower}_court.png"])
   else:
      p = Popen(["cp", "/run/shm/frame.png", f"/home/pi/boomer/{cam_lower}_court.png"])
   stdoutdata, stderrdata = p.communicate()
   if p.returncode != 0:
      app.logger.error(f"scp of camera's frame.png to court.png failed: {p.returncode}")
   # status = os.waitpid(p.pid, 0)

   return render_template(CAM_CALIBRATION_TEMPLATE, \
      court_pic = "static/" + cam_lower + "_court.png", \
      home_button = my_home_button, \
      installation_title = customization_dict['title'], \
      installation_icon = customization_dict['icon'], \
      footer_center = "Mode: " + mode_str)


@app.route('/cam_calib_done', methods=DEFAULT_METHODS)
def cam_calib_done():
   global cam_side, cam_mm, X, Y, Z
   if cam_side.lower() == "left":
      cam_arg = "--left"
   else:
      cam_arg = "--right"

   if request.method=='POST':
      if (request.content_type.startswith('application/json')):
         # >> not supporting a javascript POST of json; left for reference
         # print(f"request to calib: {request.json}")
         # request.json example: {'fblx': 883, 'fbly': 77, 'fbrx': 1193, 'fbry': 91,\
         #  'nslx': 503, 'nsly': 253, 'nscx': 747, 'nscy': 289, 'nsrx': 1065, 'nsry': 347,\
         #  'nblx': 187, 'nbly': 397, 'nbrx': 933, 'nbry': 653}
         c = request.json
         coord_args = (f"--fblx {c['fblx']} --fbly {c['fbly']}"
            f" --fbrx {c['fbrx']} --fbry {c['fbry']} --nblx {c['nblx']} --nbly {c['nbly']}"
            f" --nbrx {c['nbrx']} --nbry {c['nbry']} --nslx {c['nslx']} --nsly {c['nsly']}"
            f" --nscx {c['nscx']} --nscy {c['nscy']} --nsrx {c['nsrx']} --nsry {c['nsry']}"
            f" --camx {cam_mm[X]} --camy {cam_mm[Y]} --camz {cam_mm[Z]}" )
      else:
         app.logger.debug(f"POST to CALIB_DONE request.form: {request.form}")
         # example: ImmutableMultiDict
         coord_args = (f"--fblx {int(request.form['fblx'])} --fbly {int(request.form['fbly'])}"
            f" --fbrx {int(request.form['fbrx'])} --fbry {int(request.form['fbry'])}"
            f" --nblx {int(request.form['nblx'])} --nbly {int(request.form['nbly'])}"
            f" --nbrx {int(request.form['nbrx'])} --nbry {int(request.form['nbry'])}"
            f" --nslx {int(request.form['nslx'])} --nsly {int(request.form['nsly'])}"
            f" --nscx {int(request.form['nscx'])} --nscy {int(request.form['nscy'])}"
            f" --nsrx {int(request.form['nsrx'])} --nsry {int(request.form['nsry'])}"
            f" --camx {cam_mm[X]} --camy {cam_mm[Y]} --camz {cam_mm[Z]}" )
         cmd = "/home/pi/boomer/staged/gen_cam_params.out " + cam_arg + " " + coord_args
         process_data = True
         if (process_data):
            p = Popen(cmd, shell=True)
            stdoutdata, stderrdata = p.communicate()
            if p.returncode != 0:
               app.logger.error(f"gen_cam_params failed: {p.returncode}")
            else:
               app.logger.warning("TODO: send parameters.txt, restart the cam, reload the param on the base")
 
   button_label = cam_side + " Cam Calib Done"
   return render_template(CHOICE_INPUTS_TEMPLATE, \
      home_button = my_home_button, \
      installation_title = customization_dict['title'], \
      installation_icon = customization_dict['icon'], \
      onclick_choices = [{"value": button_label, "onclick_url": MAIN_URL}], \
      footer_center = "Mode: " + button_label)

 
@app.route(MAIN_URL, methods=DEFAULT_METHODS)
def index():
   global back_url, previous_url
   back_url = previous_url = "/"

   onclick_choice_list = [\
      {"value": "Game Mode", "onclick_url": GAME_OPTIONS_URL},\
      {"value": "Drills", "onclick_url": DRILL_SELECT_TYPE_URL},\
      {"value": "Workouts", "onclick_url": SELECT_URL, \
         "param_name": ONCLICK_MODE_KEY, "param_value": ONCLICK_MODE_WORKOUT_VALUE}, \
      {"value": "Settings", "onclick_url": SETTINGS_URL}
   ]

   return render_template(CHOICE_INPUTS_TEMPLATE, \
      installation_title = customization_dict['title'], \
      installation_icon = customization_dict['icon'], \
      onclick_choices = onclick_choice_list, \
      footer_center = "Mode: --")

'''
@app.route('/back')
def go_to_main():
   global back_url
   if back_url is None:
      back_url = '/'
   # return redirect(url_for(back_url))
   # url_for() causes a werkzeug-routing-builderror-could-not-build-url-for-endpoint
   # the same error happens when using the following on a webpage
   #       href='{{ url_for('back') }}'
   return redirect(back_url)
'''

@app.route(SETTINGS_URL, methods=DEFAULT_METHODS)
def settings():
   global back_url, previous_url
   back_url = previous_url = "/"

   # value is the label of the button
   onclick_choice_list = [\
      {"value": "Rotary Calibration", "onclick_url": DRILL_URL, "param_name": WORKOUT_ID,"param_value": ROTARY_CALIB_ID}
 		# rotary_calibration_mode= (drill_number==780)	   ? true : false;
		# elevator_calibration_mode= (drill_number==781)	? true : false;
		# lob_calibration_mode= (drill_number==782)	      ? true : false;
		# serve_calibration_mode=(drill_number==784)      ? true : false;
		# drop_calibration_mode=(drill_number==785)       ? true : false;
		# flat_calibration_mode=(drill_number==786)			? true : false;
   ]
   form_choice_list = [\
      {"value": "Left Cam Calib"},\
      {"value": "Right Cam Calib"}\
   ]

   settings_radio_options = { \
   GRUNTS_PARAM:{"legend":"Grunts", "buttons":[{"label":"Off", "value":0},{"label":"On","value":1}]}, \
   TRASHT_PARAM:{"legend":"Trash Talking", "buttons":[{"label":"Off", "value":0},{"label":"On"}]}, \
   }
   # the following adds checked to  param[buttons][index]
   settings_radio_options[GRUNTS_PARAM]["buttons"][settings_dict[GRUNTS_PARAM]]["checked"] = 1
   settings_radio_options[TRASHT_PARAM]["buttons"][settings_dict[TRASHT_PARAM]]["checked"] = 1

   page_js = []
   page_js.append(Markup('<script src="/static/js/radio-button-emit.js"></script>'))

   return render_template(CHOICE_INPUTS_TEMPLATE, \
      home_button = my_home_button, \
      installation_title = customization_dict['title'], \
      installation_icon = customization_dict['icon'], \
      onclick_choices = onclick_choice_list, \
      radio_options = settings_radio_options, \
      form_choices = form_choice_list, \
      url_for_post = CAM_POSITION_URL, \
      page_specific_js = page_js, \
      footer_center = "Mode: --")


@app.route(GAME_OPTIONS_URL, methods=DEFAULT_METHODS)
def game_options():
   # clicking stop when the game is active goes to this page, so stop the game
   rc, code = send_msg(PUT_METHOD, STOP_RSRC)
   if not rc:
      app.logger.error("PUT STOP failed, code: {}".format(code))

   global back_url, previous_url
   back_url = '/'
   previous_url = "/" + inspect.currentframe().f_code.co_name

   game_radio_options = { \
      SERVE_MODE_PARAM:{"legend":"Serves", "buttons":[{"label":"Alternate", "value":0},\
         {"label":"All Player","value":1},{"label":"All Boomer","value":2}]}, \
      TIEBREAKER_PARAM:{"legend":"Scoring", "buttons":[{"label":"Standard", "value":0},{"label":"Tie Breaker", "value":1}]}, \
      # RUN_REDUCE_PARAM:{"legend":"Running", "buttons":[{"label":"Standard", "value":0},{"label":"Less", "value":1}]} \
   }
   game_radio_options[SERVE_MODE_PARAM]["buttons"][settings_dict[SERVE_MODE_PARAM]]["checked"] = 1
   game_radio_options[TIEBREAKER_PARAM]["buttons"][settings_dict[TIEBREAKER_PARAM]]["checked"] = 1

   page_js = []
   page_js.append(Markup('<script src="/static/js/radio-button-emit.js"></script>'))

   return render_template(GAME_OPTIONS_TEMPLATE, \
      home_button = my_home_button, \
      installation_title = customization_dict['title'], \
      installation_icon = customization_dict['icon'], \
      optional_form_begin = Markup('<form action ="' + GAME_URL + '" method="post">'), \
      optional_form_end = Markup('</form>'), \
      radio_options = game_radio_options, \
      # point_delay_dflt = GAME_POINT_DELAY_DEFAULT, \
      # point_delay_min = GAME_POINT_DELAY_MIN, \
      # point_delay_max = GAME_POINT_DELAY_MAX, \
      # point_delay_step = GAME_POINT_DELAY_STEP, \
      page_specific_js = page_js, \
      footer_center = "Mode: " + MODE_GAME)

@app.route(GAME_URL, methods=DEFAULT_METHODS)
def game():
   global back_url, previous_url
   back_url = previous_url

   # print("{} on {}, data: {}".format(request.method, inspect.currentframe().f_code.co_name, request.data))
   # Using emit on radio buttons instead of taking the post data
   '''
   if request.method=='POST':
      if SERVE_MODE_PARAM in request.form:
         print("serve_mode: {}".format(request.form[SERVE_MODE_PARAM]))
      if TIEBREAKER_PARAM in request.form:
         print("scoring: {}".format(request.form[TIEBREAKER_PARAM]))
      if 'running' in request.form:
         print("running: {}".format(request.form['running']))
      if 'point_delay' in request.form:
         print("point_delay: {}".format(request.form['point_delay']))
   '''
   return render_template(GAME_TEMPLATE, \
      installation_title = customization_dict['title'], \
      installation_icon = customization_dict['icon'], \
      level_dflt = settings_dict[LEVEL_PARAM]/LEVEL_UI_FACTOR, \
      level_min = LEVEL_MIN/LEVEL_UI_FACTOR, \
      level_max = LEVEL_MAX/LEVEL_UI_FACTOR, \
      level_step = LEVEL_UI_STEP/LEVEL_UI_FACTOR, \
      footer_center = "Mode: " + MODE_GAME)


@app.route(DRILL_SELECT_TYPE_URL, methods=DEFAULT_METHODS)
def drill_select_type():
   # clicking stop when the drill is active goes to this page, so stop the drill
   rc, code = send_msg(PUT_METHOD, STOP_RSRC)
   if not rc:
      app.logger.error("PUT STOP failed, code: {}".format(code))

   global back_url, previous_url
   back_url = previous_url

   drill_select_type_list = [\
      {'value': DRILL_SELECT_TYPE_PLAYER},\
      {'value': DRILL_SELECT_TYPE_INSTRUCTORS},\
      {'value': DRILL_SELECT_TYPE_TEST},\
   ]

   return render_template(CHOICE_INPUTS_TEMPLATE, \
      home_button = my_home_button, \
      installation_title = customization_dict['title'], \
      installation_icon = customization_dict['icon'], \
      form_choices = drill_select_type_list, \
      url_for_post = SELECT_URL, \
      footer_center = "Mode: " + MODE_DRILL_NOT_SELECTED)


@app.route(SELECT_URL, methods=DEFAULT_METHODS)
def select():
   global back_url, previous_url
   back_url = '/'
   previous_url = "/" + inspect.currentframe().f_code.co_name

   app.logger.debug(f"select request: {request}")

   #enter this page from drill categories (player, instructor), or from Main (workflows)
   # a parameter (mode) indicates the if workflow or drills should be selected
   if request.args.get(ONCLICK_MODE_KEY) == ONCLICK_MODE_WORKOUT_VALUE:
      is_workout = True
   else:
      is_workout = False
   app.logger.debug(f"select: is_workout={is_workout}")

   drill_select_type = None
   if request.method=='POST':
      app.logger.info(f"request_form_getlist_type: {request.form.getlist('choice')}")
      drill_select_type = request.form.getlist('choice')[0]

   drill_filter_list = []
   # refer to /home/pi/boomer/drills/ui_drill_selection_lists.py for drill_list format
   if drill_select_type == DRILL_SELECT_TYPE_TEST:
      drill_list = drill_list_test
   elif drill_select_type == DRILL_SELECT_TYPE_INSTRUCTORS:
      drill_list = drill_list_instructor
   else:
      # drill_list = drill_list_player
      drill_filter_list = ['data-Type', 'data-Stroke', 'data-Difficulty']
      drill_list = [\
         {'id': '005', 'name': 'Groundstrokes Random 20 balls', \
            # 'filters': {'type': 'Development', 'stroke': 'Ground', 'difficulty': 'Medium'}},\
            'filter_values': ['Development', 'Ground', 'Medium']},\
         {'id': '006', 'name': 'Net Random 9 balls', \
            # 'filters': {'type': 'Development', 'stroke': 'Net', 'difficulty': 'Medium'}},\
            'filter_values': ['Development', 'Net', 'Medium']},\
         {'id': '007', 'name': 'Volley Random 12 balls', \
            # 'filters': {'type': 'Development', 'stroke': 'Volley', 'difficulty': 'Medium'}},\
            'filter_values': ['Development', 'Volley', 'Medium']},\
      ]

   if len(drill_filter_list) > 0:
      page_js = filter_js
   else:
      page_js = []

   return render_template(SELECT_TEMPLATE, \
      home_button = my_home_button, \
      installation_title = customization_dict['title'], \
      installation_icon = customization_dict['icon'], \
      optional_form_begin = Markup('<form action ="' + DRILL_URL + '" method="post">'), \
      drills = drill_list, \
      filters = drill_filter_list, \
      optional_form_end = Markup('</form>'), \
      footer_center = "Mode: " + MODE_DRILL_NOT_SELECTED, \
      page_specific_js = page_js
   )
 
@app.route(DRILL_URL, methods=DEFAULT_METHODS)
def drill():
   global back_url, previous_url
   back_url = previous_url

   app.logger.info(f"DRILL_URL request_form: {request.form}")
   app.logger.info(f"DRILL_URL request_args: {request.args}")
   is_workout = request.args.get(ONCLICK_MODE_KEY)
   app.logger.info(f"is_workout in request_args: {is_workout}")
   id = request.args.get(WORKOUT_ID)
   app.logger.info(f"WORKOUT_ID in request_args: {WORKOUT_ID}")
   if id is not None:
      id = int(id)
      mode = {MODE_PARAM: base_mode_e.WORKOUT.value, ID_PARAM: id}
      mode_string = f"'{id}' Workout"
   else:
      if request.method=='POST' and 'drill_id' in request.form:
         id = int(request.form['drill_id'])
         mode = {MODE_PARAM: base_mode_e.DRILL.value, ID_PARAM: id}
         mode_string = f"'{id}' Drill"

   # app.logger.info(f"workout_id: {id}")

   if id is None:
      app.logger.error("DRILL_URL - no drill_id!")
   else:
      rc, code = send_msg(PUT_METHOD, MODE_RSRC, mode)
      if not rc:
         app.logger.error("DRILL_URL: PUT Mode failed, code: {}".format(code))
      else:
         rc, code = send_msg(PUT_METHOD, STRT_RSRC)
         if not rc:
            app.logger.error("PUT START failed, code: {}".format(code))

   if (id != ROTARY_CALIB_ID):
      # the defaults are set from what was last saved in the settings file
      drill_stepper_options = { \
         LEVEL_PARAM:{"legend":"Level", "dflt":settings_dict[LEVEL_PARAM]/LEVEL_UI_FACTOR, \
            "min":LEVEL_MIN/LEVEL_UI_FACTOR, "max":LEVEL_MAX/LEVEL_UI_FACTOR, "step":LEVEL_UI_STEP/LEVEL_UI_FACTOR}, \
         SPEED_MOD_PARAM:{"legend":"Speed", "dflt":settings_dict[SPEED_MOD_PARAM], \
            "min":SPEED_MOD_MIN, "max":SPEED_MOD_MAX, "step":SPEED_MOD_STEP}, \
         DELAY_MOD_PARAM:{"legend":"Delay", "dflt":settings_dict[DELAY_MOD_PARAM]/DELAY_UI_FACTOR, \
            "min":DELAY_MOD_MIN/DELAY_UI_FACTOR, "max":DELAY_MOD_MAX/DELAY_UI_FACTOR, "step":DELAY_UI_STEP/DELAY_UI_FACTOR}, \
         ELEVATION_MOD_PARAM:{"legend":"Height", "dflt":settings_dict[ELEVATION_MOD_PARAM], \
            "min":ELEVATION_ANGLE_MOD_MIN, "max":ELEVATION_ANGLE_MOD_MAX, "step":ELEVATION_ANGLE_MOD_STEP} \
      }
   else:
      drill_stepper_options = {}
         
   previous_url = "/" + inspect.currentframe().f_code.co_name
   return render_template(DRILL_TEMPLATE, \
      installation_title = customization_dict['title'], \
      installation_icon = customization_dict['icon'], \
      stepper_options = drill_stepper_options, \
      footer_center = "Mode: " + mode_string)


   return render_template(DRILL_TEMPLATE, \
      installation_title = customization_dict['title'], \
      installation_icon = customization_dict['icon'], \
      footer_center = "Mode: " + mode_string)


@app.route('/favicon.ico')
def favicon():
    return send_from_directory(os.path.join(app.root_path, 'static'),
                               'favicon.ico', mimetype='image/vnd.microsoft.icon')

@socketio.on('message')
def handle_message(data):
    app.logger.debug('received message: ' + data)

@socketio.on('change_params')     # Decorator to catch an event named change_params
def handle_change_params(data):          # change_params() is the event callback function.
   #  print('change_params data: ', data)      # data is a json string: {"speed":102}
   #  item_to_change = json.loads(data)
   app.logger.info(f'received change_params: {data}')
   for k in data.keys():
      app.logger.debug(f'Setting: {k} to {int(data[k])}')
      if (k == LEVEL_PARAM):
         settings_dict[k] = 10* int(data[k])
      elif (k == DELAY_MOD_PARAM):
         settings_dict[k] = int(data[k]*1000)
      else:
         settings_dict[k] = int(data[k])
      if (k == LEVEL_PARAM or k == GRUNTS_PARAM or k == TRASHT_PARAM):
         rc, code = send_msg(PUT_METHOD, BCFG_RSRC, {k: settings_dict[k]})
      elif (k == SPEED_MOD_PARAM or k == DELAY_MOD_PARAM or k == ELEVATION_MOD_PARAM):
         rc, code = send_msg(PUT_METHOD, DCFG_RSRC, {k: settings_dict[k]})
      elif (k == SERVE_MODE_PARAM or k == TIEBREAKER_PARAM or k == POINTS_DELAY_PARAM):
         rc, code = send_msg(PUT_METHOD, GCFG_RSRC, {k: settings_dict[k]})
      elif (k == 'drill_id'):
         # ignore for now - taking ID on POST
         rc = True
      else:
         app.logger.error(f"Unrecognized key in change_params: {k}")
         rc = True
      if not rc:
         app.logger.error(f"PUT base_config {k} failed, code: {code}")
      with open(f'{settings_dir}/{settings_filename}', 'w') as f:
         json.dump(settings_dict, f)


@socketio.on('pause_resume')
def handle_pause_resume():
   app.logger.debug('received pause_resume.')
   rc, code = send_msg(PUT_METHOD, PAUS_RSRC)
   if not rc:
      app.logger.error("PUT PAUSE failed, code: {}".format(code))


@socketio.on('get_updates')
def handle_get_updates(data):
   json_data = json.loads(data)
   # print(f"json_data: {json_data}")
   if (("page" in json_data) and (json_data["page"] == "game")):
      emit('state_update', {"base_state": base_state, "pp": randint(0,3), \
         "bp": 1, "pg": 3, "bg": 2, "ps": 5, "bs": 4, "pt": 6, "bt": 7, "server": "b"})
   else:
      emit('state_update', {"base_state": base_state})


def check_base(process_name):
   global base_state, previous_base_state, client_state, socketio
   while True:
      base_pid = os.popen(f"pgrep {process_name}").read()
      #base_pid is empty if base is not running
      if base_pid:
         # verify responding to FIFO
         msg_ok, status_msg = send_msg()
         if not msg_ok:
            base_state = STATUS_NOT_RESPONDING
         else:
            if (status_msg is not None):
               if (STATUS_PARAM in status_msg):
                  base_state = base_state_e(status_msg[STATUS_PARAM]).name.title()
               # if (HARD_FAULT_PARAM in status_msg):
               #    fault_count = int(status_msg[HARD_FAULT_PARAM])
      else:
         base_state = STATUS_NOT_RUNNING
      if (base_state != previous_base_state and not \
            (base_state == STATUS_NOT_RUNNING or base_state == STATUS_NOT_RESPONDING)):
         app.logger.info("Base (or UI) started - configuring settings")
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
 
      # the following didn't work: the emit didn't get to the client
      # if client_state:
      #    print(f"emitting: {{'base_state_update', {{\"base_state\": \"{base_state}\"}}}}")
      #    socketio.emit('base_state_update', {"base_state": base_state})
      previous_base_state = base_state
      time.sleep(1)

def print_base_status(iterations = 20):
   global base_state
   while iterations > 0:
      print(f"{base_state}")
      time.sleep(1)
      iterations -=1

if __name__ == '__main__':
   global customized_header, original_footer

   check_base_thread = Thread(target = check_base, args =("bbase", ))
   check_base_thread.daemon = True
   check_base_thread.start()
   do_status_printout = False
   if do_status_printout:
      print_base_thread = Thread(target = print_base_status, args =(20, ))
      print_base_thread.daemon = True
      print_base_thread.start() 

   # app.run(host="0.0.0.0", port=IP_PORT, debug = True)
   socketio.run(app, host="0.0.0.0", port=IP_PORT, debug = True)

   check_base_thread.join()
