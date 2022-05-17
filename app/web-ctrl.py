#!/usr/bin/env python3

#from flask import ? session, abort
from flask import Flask, render_template, Response, request, redirect, url_for, Markup, send_from_directory
try:
   from flask_socketio import SocketIO, emit
except:
   print("Missing package 'flask_socketio', please run: python3 -m pip install flask-socketio")
   exit()

import logging
# logging.basicConfig(level=logging.INFO)
# logging.basicConfig(level=logging.DEBUG, format='%(levelname)s %(asctime)s %(message)s')

app = Flask(__name__)
from waitress import serve

import inspect
import os  # for sending favicon & checking the base is running (pgrep)
import json
import enum
import copy
import datetime
from threading import Thread
from subprocess import Popen
import time
from random import randint # for score updates - will be deleted
import sys # for sys.path to search

user_dir = '/home/pi'
boomer_dir = 'boomer'
@app.before_first_request
def before_first_request():
    log_level = logging.DEBUG

    for handler in app.logger.handlers:
      app.logger.removeHandler(handler)
      # https://betterstack.com/community/guides/logging/how-to-start-logging-with-flask/
      #  root = os.path.dirname(os.path.abspath(__file__))
      #  logdir = os.path.join(root, 'logs')
      #  if not os.path.exists(logdir):
      #      os.mkdir(logdir)
      #  log_file = os.path.join(logdir, 'app.log')
      handler = logging.FileHandler('/run/shm/ui.log')
      defaultFormatter = logging.Formatter('[%(asctime)s]%(levelname)s: %(message)s')
      handler.setFormatter(defaultFormatter)
      handler.setLevel(log_level)
      app.logger.addHandler(handler)
      app.logger.setLevel(log_level)

site_data_dir = 'this_boomers_data'
settings_dir = f'{user_dir}/{boomer_dir}/{site_data_dir}'
settings_filename = "drill_game_settings.json"
execs_dir = f"{user_dir}/{boomer_dir}/execs"

# the following requires: export PYTHONPATH='/Users/tom/Documents/Projects/Boomer/control_ipc_utils'
repos_dir = 'repos'
sys.path.append(f'{user_dir}/{repos_dir}/control_ipc_utils')
# print(sys.path)
try:
   from ctrl_messaging_routines import send_msg
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

base_state = None
previous_base_state = None
client_state = False

try:
   with open(f'{settings_dir}/ui_customization.json') as f:
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
CAM_CALIB_DONE_URL = '/cam_calib_done'
SETTINGS_URL = '/settings'
FAULTS_URL = '/faults'
THROWER_CALIB_SELECTION_URL = '/thrower_calibration'
CREEP_CALIB_URL = '/creep_calib'
BEEP_SELECTION_URL = '/beep_selection'

# Flask looks for following in the 'templates' directory
MAIN_TEMPLATE = 'index.html'
GAME_OPTIONS_TEMPLATE = '/layouts' + GAME_OPTIONS_URL + '.html'
GAME_TEMPLATE = '/layouts' + GAME_URL + '.html'
CHOICE_INPUTS_TEMPLATE = '/layouts' + '/choice_inputs' + '.html'
SELECT_TEMPLATE = '/layouts' + SELECT_URL + '.html'
DRILL_TEMPLATE = '/layouts' + DRILL_URL + '.html'
CAM_CALIBRATION_TEMPLATE = '/layouts' + CAM_CALIB_URL + '.html'
CAM_POSITION_TEMPLATE = '/layouts' + CAM_POSITION_URL + '.html'
FAULTS_TEMPLATE = '/layouts' + FAULTS_URL + '.html'

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
DRILL_ID = 'drill_id'
CREEP_ID = "creep_type"
ONCLICK_MODE_KEY = 'mode'
ONCLICK_MODE_WORKOUT_VALUE = 'workouts'

previous_url = None
back_url = None

cam_side = None  # a global on which camera is being calibrated
cam_side_left_label = 'Left'
cam_side_right_label = 'Right'
class Measurement(enum.Enum):
   a = 0
   b = 1
   z = 2
class Axis(enum.Enum):
   x = 0
   y = 1
   z = 2
class English_units(enum.Enum):
   feet = 0
   inch = 1
   quar = 2 #quarter
class Metric_units(enum.Enum):
   meter = 0
   cm = 1
   mm = 2

Units = English_units
INCHES_TO_MM = 25.4

COURT_POINT_KEYS = ['fblx','fbly','fbrx','fbry', \
   'nslx', 'nsly', 'nscx', 'nscy', 'nsrx', 'nsry', 'nblx', 'nbly', 'nbrx', 'nbry']
court_points_dict = {}
new_cam_measurement_mm = [0]*3

beep_mode_choices = {"Stroke":["Ground","Volley","Mini-Tennis"], \
   "Ground Stroke Type": ["Flat","Chip","Topspin","Heavy Topspin","Random"], \
   "Difficulty": ["Very Easy","Easy","Medium","Hard","Very Hard"]}

faults_table = {}
#TODO: generate the dict by parsing the name in the drill description in the file
thrower_calib_drill_dict = {"ROTARY":(THROWER_CALIB_DRILL_NUMBER_START), "ELEVATOR": (THROWER_CALIB_DRILL_NUMBER_START+1)}
for i in range(balltype_e.SERVE.value, balltype_e.CUSTOM.value):
   thrower_calib_drill_dict[balltype_e(i).name] = THROWER_CALIB_DRILL_NUMBER_START+i+1
THROWER_CALIBRATION_WORKOUT_ID = 2

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
   global cam_side, Units
   if request.method=='POST':
      # print(f"POST to CAM_POSITION request.form: {request.form}")
      # POST to CAM_POSITION request.form: ImmutableMultiDict([('choice', 'Left Cam Calib')])
      if ('choice' in request.form) and request.form['choice'].lower().startswith('r'):
         cam_side = cam_side_right_label
      else:
         cam_side = cam_side_left_label

   cam_loc_filepath = f'{settings_dir}/{cam_side.lower()}_cam_measurements.json'
   try:
      with open(cam_loc_filepath) as infile:
         previous_cam_measurement_mm = json.load(infile)
   except:
      app.logger.info(f"using default values for cam_location; couldn't read {cam_loc_filepath}")
      if cam_side == cam_side_left_label:
         previous_cam_measurement_mm = [6402, 12700, 2440]
      else:
         previous_cam_measurement_mm = [12700, 6402, 2440]


   unit_lengths = [[0 for i in range(len(Measurement))] for j in range(len(Units))]
   for measurement, value in enumerate(previous_cam_measurement_mm):
      # need the following 8-digit precision in order to maintain the measurements
      inches = 0.03937008 * value
      unit_lengths[measurement][0] = int(inches / 12)
      unit_lengths[measurement][1] = int(inches % 12)
      unit_lengths[measurement][2] = int((inches % 12 % 1)/.25)
  
   position_options = {}
   for i in Measurement:
      for j in Units:
         main_key = f"{Measurement(i).name}_{Units(j).name}"
         position_options[main_key] = {"dflt":unit_lengths[Measurement(i).value][Units(j).value], "step":1}
         # customize min, max and row title
         if j == Units(0):
            if i == Measurement(0):
               position_options[main_key]["start_div"] = "A"
               # the fence should be 21 ft from the baseline, but allowing smaller
               if cam_side == cam_side_left_label:
                  # A should be short; B should be long for on LEFT side
                  position_options[main_key]["min"] = 17
                  position_options[main_key]["max"] = 30
               else:
                  position_options[main_key]["min"] = 25
                  position_options[main_key]["max"] = 70
            if i == Measurement(1):
               position_options[main_key]["start_div"] = "B"
               if cam_side == cam_side_right_label:
                  # A should be short; B should be long for on RIGHT side
                  position_options[main_key]["min"] = 17
                  position_options[main_key]["max"] = 30
               else:
                  position_options[main_key]["min"] = 25
                  position_options[main_key]["max"] = 70
            if i == Measurement(2):
               position_options[main_key]["start_div"] = "Height"
               position_options[main_key]["min"] = 7
               position_options[main_key]["max"] = 16
         if j == Units(1):
               position_options[main_key]["min"] = 0
               position_options[main_key]["max"] = 11
         if j == Units(2):
            position_options[main_key]["min"] = 0
            position_options[main_key]["max"] = 3
            position_options[main_key]["end_div"] = "Y"
   # print(f"position_options={position_options}")

   return render_template(CAM_POSITION_TEMPLATE, \
      home_button = my_home_button, \
      installation_title = customization_dict['title'], \
      installation_icon = customization_dict['icon'], \
      options = position_options, \
      footer_center = f"Mode: Get {cam_side} Cam Position")


@app.route(CAM_CALIB_URL, methods=DEFAULT_METHODS)
def cam_calib():
   global cam_side, Units, new_cam_measurement_mm

   if request.method=='POST':
      app.logger.info(f"POST to CALIB (location) request.form: {request.form}")
      # example: 
      # POST to CALIB (location) request.form: ImmutableMultiDict([('x_feet', '6'), ('x_inch', '6'), ('x_quar', '2'), ('y_feet', '54'), ('y_inch', '6'), ('y_quar', '3'), ('z_feet', '13'), ('z_inch', '8'), ('z_quar', '3')])
      for i in Measurement:
         new_cam_measurement_mm[Measurement(i).value] = 0
         for j in Units:
            key = f"{Measurement(i).name}_{Units(j).name}"
            # app.logger.info(f"key={key} in_post={key in request.form}")
            if key in request.form:
               if j == Units['feet']:
                  new_cam_measurement_mm[Measurement(i).value] += int(request.form[key]) * 12 * INCHES_TO_MM
               if j == Units['inch']:
                  new_cam_measurement_mm[Measurement(i).value] += int(request.form[key]) * INCHES_TO_MM
               if j == Units['quar']:
                  new_cam_measurement_mm[Measurement(i).value] += int(request.form[key]) * (INCHES_TO_MM/4)
            else:
               app.logger.error("Unknown key '{key}' in POST of camera location measurement")
      # if ('cam_x_ft' in request.form) and ('cam_x_in' in request.form):
      #    cam_location_mm[Measurement.a.value] = int(((int(request.form['cam_a_ft']) * 12) + int(request.form['cam_a_ft'])) * INCHES_TO_MM)
      # if ('cam_y_ft' in request.form) and ('cam_y_in' in request.form):
      #    cam_location_mm[Measurement.b.value] = int(((int(request.form['cam_b_ft']) * 12) + int(request.form['cam_b_ft'])) * INCHES_TO_MM)
      # if ('cam_z_ft' in request.form) and ('cam_z_in' in request.form):
      #    cam_location_mm[Measurement.z.value] = int(((int(request.form['cam_z_ft']) * 12) + int(request.form['cam_z_ft'])) * INCHES_TO_MM)
      if len(new_cam_measurement_mm) == 3:
         # convert from floating point to integer:
         for i in Measurement:
            new_cam_measurement_mm[Measurement(i).value] = new_cam_measurement_mm[Measurement(i).value]
         #persist values for next calibration, so they don't have to be re-entered
         with open(f"{settings_dir}/{cam_side.lower()}_cam_measurements.json", "w") as outfile:
            json.dump(new_cam_measurement_mm, outfile)
         # convert measurements (A & B) to camera_location X and Y and save in file
         new_cam_location_mm = [0]*3
         court_width_mm = 36 * 12 * INCHES_TO_MM
         doubles_width_mm = 4.5 * 12 * INCHES_TO_MM
         court_depth_mm = 78/2 * 12 * INCHES_TO_MM
         
         # Dave's code: (in C)
         # 		x1 = (1296 + A*A - B*B)/72;
			# 		y1 = sqrt(A*A - x1*x1);
			# 		Xworld = x1 - 4.5;	// in feet
			# 		Yworld = y1 + 39;	// in feet
         # A=20.00 B=20.00 x1=18.00 y1=8.72 Xworld=4114.8 Yworld=14544.4
         # A=25.45 B=25.45 x1=18.00 y1=17.99 Xworld=4114.8 Yworld=17371.1

         A = new_cam_measurement_mm[Measurement.a.value]
         B = new_cam_measurement_mm[Measurement.b.value]
         # pow(number, 2) is the same as squaring;  pow(number, 0.5) is squareroot
         x1 = (pow(court_width_mm, 2) + pow(A, 2) - pow(B, 2)) / (court_width_mm*2)
         new_cam_location_mm[Axis.x.value] = int(x1 - doubles_width_mm)
         if new_cam_location_mm[Axis.x.value] < 0:
            app.logger.error(f"x1 distance calculation error; x={x1}")
            x1 = 0
         Y = pow((pow(A, 2) - pow(x1, 2)), 0.5) + court_depth_mm
         if not isinstance(Y,float):
            app.logger.error(f"Y distance calculation error; y={Y}")
            Y = 0
         new_cam_location_mm[Axis.y.value] = int(Y)
         new_cam_location_mm[Axis.z.value] = new_cam_measurement_mm[Measurement.z.value]
         with open(f"{settings_dir}/{cam_side.lower()}_cam_location.json", "w") as outfile:
            json.dump(new_cam_location_mm, outfile)
      else:
         app.logger.error("Missing or extra measurement in cam_measurements: {new_cam_measurement_mm}")

   mode_str = f"{cam_side} Court Coord"
   cam_lower = cam_side.lower()
   # copy the lastest PNG from the camera to the base
   DO_SCP_FOR_CALIBRATION = True #False
   if DO_SCP_FOR_CALIBRATION:
      p = Popen(["scp", f"{cam_lower}:/run/shm/frame_even.png", f"/home/pi/boomer/{cam_lower}_court.png"])
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


@app.route(CAM_CALIB_DONE_URL, methods=DEFAULT_METHODS)
def cam_calib_done():
   global cam_side, new_cam_location_mm

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
            f" --camx {new_cam_location_mm[Axis.x.value]} --camy {new_cam_location_mm[Axis.y.value]} --camz {new_cam_location_mm[Axis.z.value]}" )
      else:
         app.logger.info(f"POST to CALIB_DONE request.form: {request.form}")
         # example: ImmutableMultiDict
         coord_args = ""
         for key in COURT_POINT_KEYS:
            if key in request.form:
               court_points_dict[key] = int(request.form[key])
               coord_args = coord_args + f"--{key} {court_points_dict[key]} "
            else:
               app.logger.error(f"Missing key in cam_calib_done post: {key}")
         coord_args = coord_args + \
            f" --camx {new_cam_location_mm[Axis.x.value]} --camy {new_cam_location_mm[Axis.y.value]} --camz {new_cam_location_mm[Axis.z.value]}"

         if cam_side == None:
            # this happens during debug, when using the browser 'back' to navigate to CAM_CALIB_URL
            cam_side == "Left"
            app.logger.warning("cam_side was None in cam_calib_done")
         cmd = f"{execs_dir}/gen_cam_params.out --{cam_side.lower()} {coord_args}"
         app.logger.info(f"gen_cam_cmd: {cmd}")
         process_data = True
         if (process_data):
            #persist values for next calibration, so they don't necessarily have to be re-entered
            with open(f"{settings_dir}/{cam_side.lower()}_court_points.json", "w") as outfile:
               json.dump(court_points_dict, outfile)
            p = Popen(cmd, shell=True)
            stdoutdata, stderrdata = p.communicate()
            if p.returncode != 0:
               app.logger.error(f"gen_cam_params failed: {p.returncode}")
            # NOTE:  process_staged_files.sh incron script copies cam_parameters.new files to the appropriate places
 
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
      {"value": "Beep Drills", "onclick_url": BEEP_SELECTION_URL },\
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
      {"value": "Thrower Calibration", "onclick_url": THROWER_CALIB_SELECTION_URL}
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


@app.route(THROWER_CALIB_SELECTION_URL, methods=DEFAULT_METHODS)
def thrower_calib():
   # value is the label of the button
   onclick_choice_list = [\
      {"value": "Calibrate All", "onclick_url": DRILL_URL, "param_name": WORKOUT_ID,"param_value": THROWER_CALIBRATION_WORKOUT_ID},
      {"value": "Rotary Creep", "onclick_url": CREEP_CALIB_URL, "param_name": CREEP_ID,"param_value": ROTARY_CALIB_NAME},
      {"value": "Elevator Creep", "onclick_url": CREEP_CALIB_URL, "param_name": CREEP_ID,"param_value": ELEVATOR_CALIB_NAME}
   ]
   for parameter, drill_num in thrower_calib_drill_dict.items():
      button_label = f"Calibrate {parameter.title()}"
      onclick_choice_list.append({"value": button_label, "param_name": DRILL_ID, "onclick_url": DRILL_URL, "param_value": drill_num})

   return render_template(CHOICE_INPUTS_TEMPLATE, \
      home_button = my_home_button, \
      installation_title = customization_dict['title'], \
      installation_icon = customization_dict['icon'], \
      onclick_choices = onclick_choice_list, \
      footer_center = "Mode: --")


@app.route(CREEP_CALIB_URL, methods=DEFAULT_METHODS)
def creep_calib():
   # enter page from thrower calibration page
   # extract which button was pushed (rotary or elevator and issue command)

   # app.logger.debug(f"select request: {request}")
   creep_type = request.args.get(CREEP_ID)
   app.logger.debug(f"request for creep; type: {creep_type}")

   if creep_type is None:
      app.logger.error(f"request for creep; type is None")
   else:
      rc, code = send_msg(PUT_METHOD, FUNC_RSRC, {FUNC_CREEP: creep_type})
      if not rc:
         app.logger.error("PUT Function Creep failed, code: {}".format(code))

   button_label = "OK"
   return render_template(CHOICE_INPUTS_TEMPLATE, \
      home_button = my_home_button, \
      installation_title = customization_dict['title'], \
      installation_icon = customization_dict['icon'], \
      # example of setting button disabled and a button ID
      # onclick_choices = [{"value": button_label, "onclick_url": MAIN_URL, "disabled": 1, "id": "Done"}], \
      onclick_choices = [{"value": button_label, "onclick_url": MAIN_URL}], \
      footer_center = "Mode: Creep Calibration")


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
      url_for_post = GAME_URL, \
      # optional_form_begin = Markup('<form action ="' + GAME_URL + '" method="post">'), \
      # optional_form_end = Markup('</form>'), \
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

   rc, code = send_msg(PUT_METHOD, MODE_RSRC, {MODE_PARAM: base_mode_e.GAME.value})
   if not rc:
      app.logger.error("GAME_URL: PUT Mode failed, code: {}".format(code))
   else:
      rc, code = send_msg(PUT_METHOD, STRT_RSRC)
      if not rc:
         app.logger.error("PUT START failed, code: {}".format(code))


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
   select_post_param = []
   filter_list = []
   if request.args.get(ONCLICK_MODE_KEY) == ONCLICK_MODE_WORKOUT_VALUE:
      is_workout = True
      selection_list = workout_list
      select_post_param = {"name": ONCLICK_MODE_KEY, "value": ONCLICK_MODE_WORKOUT_VALUE}
   else:
      is_workout = False
      drill_select_type = None
      if request.method=='POST':
         app.logger.info(f"request_form_getlist_type: {request.form.getlist('choice')}")
         drill_select_type = request.form.getlist('choice')[0]

      # refer to /home/pi/boomer/drills/ui_drill_selection_lists.py for drill_list format
      if drill_select_type == DRILL_SELECT_TYPE_TEST:
         selection_list = drill_list_test
      elif drill_select_type == DRILL_SELECT_TYPE_INSTRUCTORS:
         selection_list = drill_list_instructor
      else:
         selection_list = drill_list_player
         filter_list = ['data-Type', 'data-Stroke', 'data-Difficulty']

   if len(filter_list) > 0:
      page_js = filter_js
   else:
      page_js = []

   return render_template(SELECT_TEMPLATE, \
      home_button = my_home_button, \
      installation_title = customization_dict['title'], \
      installation_icon = customization_dict['icon'], \
      url_for_post = DRILL_URL, \
      post_param = select_post_param, \
      choices = selection_list, \
      filters = filter_list, \
      footer_center = "Mode: " + MODE_DRILL_NOT_SELECTED, \
      page_specific_js = page_js
   )
 
@app.route(DRILL_URL, methods=DEFAULT_METHODS)
def drill():
   global beep_mode_choices
   global back_url, previous_url
   back_url = previous_url

   '''
   There are multiple ways of getting to this page
      - select_url: the post contains the drill ID (choice) or there is a workout param with ID
      = thrower_calib: the post contains a workout/drill param and an drill/workout ID
      - beep_select: the post contains radio buttons selections (stroke, difficulty) which are mapped to a drillID
   example from beep test:
      DRILL_URL request_form: ImmutableMultiDict([('Stroke', 'Mini-Tennis'), ('Ground Stroke Type', 'Topspin'), ('Difficulty', 'Medium')])
      DRILL_URL request_args: ImmutableMultiDict([])
   '''
   app.logger.info(f"DRILL_URL request_form: {request.form}")
   app.logger.info(f"DRILL_URL request_args: {request.args}")
   is_workout = request.args.get(ONCLICK_MODE_KEY)
   app.logger.info(f"is_workout in request_args: {is_workout}")
   id = request.args.get(WORKOUT_ID)
   app.logger.info(f"WORKOUT_ID in request_args: {id}")
   if id is not None:
      # workout mode
      id = int(id)
      mode = {MODE_PARAM: base_mode_e.WORKOUT.value, ID_PARAM: id}
      mode_string = f"'{id}' Workout"
   elif request.method=='POST':
      # drill or beep mode
      if 'choice_id' in request.form:
         # drill mode
         id = int(request.form['choice_id'])
      elif 'Stroke' in request.form:
         # beep drill mode
         for key in beep_mode_choices:
            if key in request.form:
               print(f"Beep choice {key} is {request.form[key]}")
         id = BEEP_DRILL_NUMBER_START
         #BEEP_DRILL_NUMBER_END = 949
      else:
         app.logger.error("DRILL_URL - no drill ID or beep Stroke in POST form")
         id = 1
      mode = {MODE_PARAM: base_mode_e.DRILL.value, ID_PARAM: id}
      mode_string = f"'{id}' Drill"
   else:
      app.logger.error("DRILL_URL - no form (didn't get POST) or args (workout ID")

   if id is None:
      app.logger.error("DRILL_URL - no drill or workout id!")
   else:
      rc, code = send_msg(PUT_METHOD, MODE_RSRC, mode)
      if not rc:
         app.logger.error("DRILL_URL: PUT Mode failed, code: {}".format(code))
      else:
         rc, code = send_msg(PUT_METHOD, STRT_RSRC)
         if not rc:
            app.logger.error("PUT START failed, code: {}".format(code))

   thrower_calib_drill_number_end = THROWER_CALIB_DRILL_NUMBER_START + thrower_calib_drill_dict.len() + 1
   if id not in range(THROWER_CALIB_DRILL_NUMBER_START, thrower_calib_drill_number_end):
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


@app.route(BEEP_SELECTION_URL, methods=DEFAULT_METHODS)
def beep_selection():
   global beep_mode_choices

   beep_radio_options = {}
   # in the for loop - options is the list of radio buttons and choice is the legend
   for choice, options in beep_mode_choices.items():
      button_list = []
      for i, option in enumerate(options):
         button_list.append({"label":option, "value":option})
         if i == 2:
            button_list[i].update({"checked":1})
      beep_radio_options.update({choice: {"legend":choice, "buttons": button_list}})
      # print(f"choice={choice}, buttons={button_list}, radio_opts={beep_radio_options}")

   # app.logger.info(f"beep_radio_options: {beep_radio_options}")

   # beep_radio_options = { \
   #    "stroke_choices":{"legend":"Stroke", "buttons":[\
   #       {"label":"Ground", "value":"Ground", "checked":1}, \
   #       {"label":"Volley","value":"Volley"}, \
   #       {"label":"Mini-Tennis","value":"Mini"} ]}, \
   #    "groundstroke_choices":{"legend":"Ground Stroke Type", "buttons":[\
   #       {"label":"Flat", "value":"FLAT"}, \
   #       {"label":"Chip","value":"CHIP"}, \
   #       {"label":"Topspin","value":"TOPSPIN", "checked":1}, \
   #       {"label":"Heavy Topspin","value":"HEAVY"}, \
   #       {"label":"Random","value":"RANDOM"} ]}, \
   #    "difficulty_choices":{"legend":"Difficulty", "buttons":[\
   #       {"label":"Very Easy", "value":"VeryEasy"}, \
   #       {"label":"Easy","value":"Easy"}, \
   #       {"label":"Medium","value":"Medium", "checked":1}, \
   #       {"label":"Hard","value":"Hard"}, \
   #       {"label":"Very Hard","value":"VeryHard"} ]} \
   # }

   # page_js = []
   # page_js.append(Markup('<script src="/static/js/radio-button-emit.js"></script>'))

   return render_template(GAME_OPTIONS_TEMPLATE, \
      home_button = my_home_button, \
      installation_title = customization_dict['title'], \
      installation_icon = customization_dict['icon'], \
      radio_options = beep_radio_options, \
      url_for_post = DRILL_URL, \
      footer_center = "Mode: " + MODE_DRILL_NOT_SELECTED)


@app.route(FAULTS_URL, methods=DEFAULT_METHODS)
def faults():
   global back_url, previous_url
   back_url = previous_url

   return render_template(FAULTS_TEMPLATE, \
      installation_title = customization_dict['title'], \
      installation_icon = customization_dict['icon'], \
      footer_center = "Mode: " + "--")


@app.route('/favicon.ico')
def favicon():
    return send_from_directory(os.path.join(app.root_path, 'static'),
                               'favicon.ico', mimetype='image/vnd.microsoft.icon')

@socketio.on('message')
def handle_message(data):
   app.logger.debug('received message: ' + data)

def textify_faults_table():
   global faults_table
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
      app.logger.error(f"bogus fault table in fault_request: {faults_table}")
   return textified_faults_table

@socketio.on('fault_request')
def handle_fault_request():
   global faults_table
   app.logger.info('received fault_request')
   # emit('faults_update', json.dumps(textified_faults_table))
   emit('faults_update', json.dumps(textify_faults_table()))
 
# @socketio.on('client_connected')
# def handle_client_connected(data):
   # app.logger.info(f"received client_connected: {data}")

@socketio.on('change_params')     # Decorator to catch an event named change_params
def handle_change_params(data):          # change_params() is the event callback function.
   #  print('change_params data: ', data)      # data is a json string: {"speed":102}
   #  item_to_change = json.loads(data)
   app.logger.info(f'received change_params: {data}')
   for k in data.keys():
      if data[k] == None:
         new_value = 0
         app.logger.warning(f'Received NoneType for {k}')
      else:
         new_value = int(data[k])
      app.logger.debug(f'Setting: {k} to {new_value}')
      if (k == LEVEL_PARAM):
         settings_dict[k] = new_value*10
      elif (k == DELAY_MOD_PARAM):
         settings_dict[k] = new_value*1000
      else:
         settings_dict[k] = new_value
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
   global base_state
   json_data = json.loads(data)
   # print(f"json_data: {json_data}")
   if ("page" in json_data):
      if (json_data["page"] == "game"):
         emit('state_update', {"base_state": base_state, "pp": randint(0,3), \
            "bp": 1, "pg": 3, "bg": 2, "ps": 5, "bs": 4, "pt": 6, "bt": 7, "server": "b"})
      # if (json_data["page"] == "faults"):
      #    #TODO: if (len(faults_table) != len(previous_faults_table)):
      #    emit('faults_update', json.dumps(textified_faults_table()))

   emit('state_update', {"base_state": base_state})


def check_base(process_name):
   global base_state, previous_base_state, client_state, socketio
   global faults_table, previous_fault_table
   while True:
      base_pid = os.popen(f"pgrep {process_name}").read()
      #base_pid is empty if base is not running
      if base_pid:
         # verify responding to FIFO
         # app.logger.info("Getting status message")
         msg_ok, status_msg = send_msg()
         if not msg_ok:
            base_state = STATUS_NOT_RESPONDING
         else:
            if (status_msg is not None):
               if (STATUS_PARAM in status_msg):
                  base_state = base_state_e(status_msg[STATUS_PARAM]).name.title()
               if (HARD_FAULT_PARAM in status_msg and status_msg[HARD_FAULT_PARAM] > 0):
                  previous_fault_table = copy.deepcopy(faults_table)
                  # app.logger.info("Getting fault table")
                  msg_ok, faults_table = send_msg(GET_METHOD, FLTS_RSRC)
                  if not msg_ok:
                     app.logger.info("Error getting fault table")
               # app.logger.info(f"faults: {faults_table[0]}")
            else:
               app.logger.error("received None as status message")
               base_state = "Error"

      else:
         base_state = STATUS_NOT_RUNNING

      if base_state != previous_base_state:
         app.logger.info(f"Base state change: {previous_base_state} -> {base_state}")

      if (0 and base_state != previous_base_state and not \
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
      time.sleep(2.0)

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
   serve(app, host="0.0.0.0", port=IP_PORT)
   app.logger.info("started server")

   check_base_thread.join()
