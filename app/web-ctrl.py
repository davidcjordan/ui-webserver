#!/usr/bin/env python3

#from flask import ? session, abort
from operator import contains
from tkinter import FALSE
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

# the following requires: export PYTHONPATH='/Users/tom/Documents/Projects/Boomer/control_ipc_utils'
user_dir = '/home/pi'
boomer_dir = 'boomer'
repos_dir = 'repos'
site_data_dir = 'this_boomers_data'
settings_dir = f'{user_dir}/{boomer_dir}/{site_data_dir}'
drills_dir = f'{user_dir}/{boomer_dir}/drills'
execs_dir = f"{user_dir}/{boomer_dir}/execs"
settings_filename = "drill_game_settings.json"
recents_filename = "recents.json"

sys.path.append(f'{user_dir}/{repos_dir}/control_ipc_utils')
# print(sys.path)
try:
   from ctrl_messaging_routines import send_msg
   from control_ipc_defines import *
except:
   app.logger.error("Missing 'control_ipc' modules, please run: git clone https://github.com/davidcjordan/control_ipc_utils")
   exit()

# sys.path.append(f'{user_dir}/{boomer_dir}/drills')
# try:
#    from ui_drill_selection_lists import *
# except:
#    app.logger.error("Missing 'ui_drill_selection_lists' modules, please run: git clone https://github.com/davidcjordon/drills")
#    exit()
# TODO: restore getting lists from ui_drill_selection_lists
workout_list = [\
{'id': '001', 'title': 'Example Workout'},\
{'id': '002', 'title': 'Thrower Calibration'},\
]

customization_dict = None
settings_dict = None

base_state = base_state_e.BASE_STATE_NONE
previous_base_state = base_state_e.BASE_STATE_NONE
soft_fault_status = soft_fault_e.SOFT_FAULT_NONE
client_state = False
bbase_down_timestamp = None
printout_counter = 0
workout_select = False

my_home_button = Markup('          <button type="submit" onclick="window.location.href=\'/\';"> \
         <img src="/static/home.png" style="height:64px;" alt="Home"> \
         </button>')

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
CAM_LOCATION_URL = '/cam_location'
CAM_CALIB_DONE_URL = '/cam_calib_done'
SETTINGS_URL = '/settings'
FAULTS_URL = '/faults'
THROWER_CALIB_SELECTION_URL = '/thrower_calibration'
CREEP_CALIB_URL = '/creep_calib'
BEEP_SELECTION_URL = '/beep_selection'
CAM_VERIF_URL = '/cam_verif'
DONE_URL = '/done'
RECENTS_URL = '/recent_drills'

# Flask looks for following in the 'templates' directory
MAIN_TEMPLATE = 'index.html'
GAME_OPTIONS_TEMPLATE = '/layouts' + GAME_OPTIONS_URL + '.html'
GAME_TEMPLATE = '/layouts' + GAME_URL + '.html'
CHOICE_INPUTS_TEMPLATE = '/layouts' + '/choice_inputs' + '.html'
SELECT_TEMPLATE = '/layouts' + SELECT_URL + '.html'
DRILL_TEMPLATE = '/layouts' + DRILL_URL + '.html'
CAM_CALIBRATION_TEMPLATE = '/layouts' + CAM_CALIB_URL + '.html'
CAM_LOCATION_TEMPLATE = '/layouts' + CAM_LOCATION_URL + '.html'
CAM_VERIFICATION_TEMPLATE = '/layouts' + CAM_VERIF_URL + '.html'
FAULTS_TEMPLATE = '/layouts' + FAULTS_URL + '.html'

# base process status strings:
MODE_NONE = " --"
MODE_GAME = "Game"
MODE_DRILL_NOT_SELECTED = "Drill Selection"
MODE_DRILL_SELECTED = "Drill #"
MODE_WORKOUT_NOT_SELECTED = "Workout Selection"
MODE_WORKOUT_SELECTED = "Workout #"
MODE_SETTINGS = "Boomer Options"

DRILL_SELECT_TYPE_PLAYER = 'Player(s)'
DRILL_SELECT_TYPE_INSTRUCTORS = 'Instructors'
DRILL_SELECT_TYPE_TEST ='Test'

WORKOUT_ID = 'workout_id'
DRILL_ID = 'drill_id' # indicates drill_id for thrower calibration, which doesn't use a POST
CREEP_ID = "creep_type"
ONCLICK_MODE_KEY = 'mode'
ONCLICK_MODE_WORKOUT_VALUE = 'workouts'

THROWER_CALIB_WORKOUT_NUMBER = 2

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

# COURT_POINT_KEYS = ['fblx','fbly','fbrx','fbry', \
#    'nslx', 'nsly', 'nscx', 'nscy', 'nsrx', 'nsry', 'nblx', 'nbly', 'nbrx', 'nbry']
COURT_POINT_KEYS = ['FBL','FBR', 'NSL', 'NSC', 'NSR', 'NBL', 'NBR']
court_points_dict_list = [{}, {}]
for key in COURT_POINT_KEYS:
   court_points_dict_list[0][key] = [0,0]
   court_points_dict_list[1][key] = [0,0]

COURT_POINT_KEYS_W_AXIS = []
for court_point_id in COURT_POINT_KEYS:
   for axis in Axis:
      if (axis.name == 'z'):
         continue
      else:
         COURT_POINT_KEYS_W_AXIS.append(f"{court_point_id}{axis.name.upper()}")

# unit_lengths are the measurements (A,B,Z) converted to feet, inches and quarter inches
unit_lengths = [[0 for _ in range(len(Measurement))] for _ in range(len(Units))]

class beep_options(enum.Enum):
   Type = 0
   Stroke = 1
   Difficulty = 2
class beep_type(enum.Enum):
   Ground = 0
   Volley = 1
   Mini_Tennis = 2

class beep_stroke(enum.Enum):
   Topspin = 0
   Flat = 1
   Chip = 2
   Loop = 3
   Random = 4
class beep_difficulty(enum.Enum):
   Very_Easy = 0
   Easy = 1
   Medium = 2
   Hard = 3
   Very_Hard = 4

beep_mode_choices = {\
   beep_options.Type:[beep_type.Ground, beep_type.Volley, beep_type.Mini_Tennis,], \
   beep_options.Stroke: [beep_stroke.Topspin, beep_stroke.Flat, beep_stroke.Chip, \
      beep_stroke.Loop, beep_stroke.Random], \
   beep_options.Difficulty: [beep_difficulty.Very_Easy, beep_difficulty.Easy, \
      beep_difficulty.Medium, beep_difficulty.Hard, beep_difficulty.Very_Hard] \
}

class drill_type_options(enum.Enum):
   Group = 0
   Lines = 1
   Focus = 2
   Stroke = 3

class group_options(enum.Enum):
   Individual = 0
   Group = 1

class line_options(enum.Enum):
   One = 1
   Two = 2
   Three = 3

class focus_options(enum.Enum):
   Development = 0
   Situational = 1
   Movement = 2

drill_type_choices = {\
   drill_type_options.Group:[group_options.Individual, group_options.Group], \
   drill_type_options.Lines:[line_options.One, line_options.Two, line_options.Three], \
   drill_type_options.Focus:[focus_options.Development, focus_options.Situational, focus_options.Movement], \
   drill_type_options.Stroke: [beep_stroke.Topspin, beep_stroke.Flat, beep_stroke.Chip, \
      beep_stroke.Loop, beep_stroke.Random], \
}


recent_drills = []

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


@app.route(CAM_LOCATION_URL, methods=DEFAULT_METHODS)
def cam_location():
   global cam_side, Units, unit_lengths
   if request.method=='POST':
      app.logger.debug(f"POST to CAM_LOCATION request.form: {request.form}")
      # POST to CAM_LOCATION request.form: ImmutableMultiDict([('choice', 'Left Cam Calib')])
      if ('choice' in request.form) and request.form['choice'].lower().startswith('r'):
         cam_side = cam_side_right_label
      else:
         cam_side = cam_side_left_label
   else:
      app.logger.warning(f"Did not get POST to CAM_LOCATION; request.method: {request.method}")
      cam_side = cam_side_right_label

   # restore measurements, which are A (camera to left doubles), B (cam to right doubles), and Z (cam height)
   cam_measurements_filepath = f'{settings_dir}/{cam_side.lower()}_cam_measurements.json'
   try:
      with open(cam_measurements_filepath) as infile:
         full_line = infile.readline()
         bracket_index = full_line.find(']')
         previous_cam_measurement_mm = json.loads(full_line[0:bracket_index+1])
         # previous_cam_measurement_mm = json.load(infile)
   except:
      app.logger.warning(f"using default values for cam_location; couldn't read {cam_measurements_filepath}")
      if cam_side == cam_side_left_label:
         previous_cam_measurement_mm = [6402, 12700, 2440]
      else:
         previous_cam_measurement_mm = [12700, 6402, 2440]

   for measurement, value in enumerate(previous_cam_measurement_mm):
      # need the following 8-digit precision in order to maintain the measurements
      inches = 0.03937008 * value
      unit_lengths[measurement][Units.quar.value] = 0
      unit_lengths[measurement][Units.feet.value] = int(inches / 12)
      unit_lengths[measurement][Units.inch.value] = int(inches % 12)
      if ((inches % 12) > (11+ 7/8)):
         unit_lengths[measurement][Units.inch.value] = 0
         unit_lengths[measurement][Units.feet.value] += 1
      else:
         remaining_inches_remainder = inches % 12 % 1
         unit_lengths[measurement][Units.quar.value] = 0
         if (remaining_inches_remainder < 1/8):
            continue
         if (remaining_inches_remainder < 3/8):
            unit_lengths[measurement][Units.quar.value] = 1
         elif (remaining_inches_remainder < 5/8):
            unit_lengths[measurement][Units.quar.value] = 2
         elif (remaining_inches_remainder < 7/8):
            unit_lengths[measurement][Units.quar.value] = 3
         else:
            unit_lengths[measurement][Units.inch.value] += 1
  
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
                  position_options[main_key]["min"] = 10
                  position_options[main_key]["max"] = 30
               else:
                  position_options[main_key]["min"] = 20
                  position_options[main_key]["max"] = 70
            if i == Measurement(1):
               position_options[main_key]["start_div"] = "B"
               if cam_side == cam_side_right_label:
                  # A should be short; B should be long for on RIGHT side
                  position_options[main_key]["min"] = 10
                  position_options[main_key]["max"] = 30
               else:
                  position_options[main_key]["min"] = 20
                  position_options[main_key]["max"] = 70
            if i == Measurement(2):
               position_options[main_key]["start_div"] = "Height"
               position_options[main_key]["min"] = 7
               position_options[main_key]["max"] = 20
         if j == Units(1):
               position_options[main_key]["min"] = 0
               position_options[main_key]["max"] = 11
         if j == Units(2):
            position_options[main_key]["min"] = 0
            position_options[main_key]["max"] = 3
            position_options[main_key]["end_div"] = "Y"
   # print(f"position_options={position_options}")

   return render_template(CAM_LOCATION_TEMPLATE, \
      home_button = my_home_button, \
      installation_title = customization_dict['title'], \
      installation_icon = customization_dict['icon'], \
      options = position_options, \
      footer_center = f"Mode: Cam Location")


@app.route(CAM_CALIB_URL, methods=DEFAULT_METHODS)
def cam_calib():
   global cam_side, Units, unit_lengths

   new_cam_measurement_mm = [0]*3
   new_cam_location_mm = [0]*3

   change_from_persisted_measurement = False

   if request.method=='POST':
      app.logger.debug(f"POST to CALIB (location) request.form: {request.form}")
      # example: 
      # POST to CALIB (location) request.form: ImmutableMultiDict([('x_feet', '6'), ('x_inch', '6'), ('x_quar', '2'), ('y_feet', '54'), ('y_inch', '6'), ('y_quar', '3'), ('z_feet', '13'), ('z_inch', '8'), ('z_quar', '3')])
      for i in Measurement:
         for j in Units:
            key = f"{Measurement(i).name}_{Units(j).name}"
            if key in request.form:
               # if the measurement differs, set that there was a change
               new_value = int(request.form[key])
               if ((new_value != unit_lengths[Measurement(i).value][Units(j).value]) and not change_from_persisted_measurement):
                  change_from_persisted_measurement = True
               app.logger.debug(f"key={key} prev={unit_lengths[Measurement(i).value][Units(j).value]} new={new_value} change={change_from_persisted_measurement}")
               if j == Units['feet']:
                  new_cam_measurement_mm[Measurement(i).value] += new_value * 12 * INCHES_TO_MM
               if j == Units['inch']:
                  new_cam_measurement_mm[Measurement(i).value] += new_value * INCHES_TO_MM
               if j == Units['quar']:
                  new_cam_measurement_mm[Measurement(i).value] += new_value * (INCHES_TO_MM/4)
            else:
               app.logger.error("Unknown key '{key}' in POST of camera location measurement")

      if change_from_persisted_measurement:
         app.logger.debug(f"Updating {cam_side} cam_measurements and cam_location")
         #persist new A,B, Z measurements and cam_location for base to use to generate correction vectors
         dt = datetime.datetime.now()
         dt_str = dt.strftime("%Y-%m-%d_%H-%M")

         # convert from floating point to integer:
         for i in Measurement:
            new_cam_measurement_mm[Measurement(i).value] = int(new_cam_measurement_mm[Measurement(i).value])

         output_line = json.dumps(new_cam_measurement_mm) + " " +  dt_str + "\n"
         with open(f'{settings_dir}/{cam_side.lower()}_cam_measurements.json', 'r+') as outfile:
            lines = outfile.readlines() # read old content
            outfile.seek(0) # go back to the beginning of the file
            outfile.write(output_line) # write new content at the beginning
            for line in lines: # write old content after new
               outfile.write(line)
         # with open(f"{settings_dir}/{cam_side.lower()}_cam_measurements.json", "w") as outfile:
         #    json.dump(new_cam_measurement_mm, outfile)

         # convert measurements (A & B) to camera_location X and Y and save in file
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

         cam_to_left_doubles = new_cam_measurement_mm[Measurement.a.value]
         cam_to_right_doubles = new_cam_measurement_mm[Measurement.b.value]

         # pow(number, 2) is the same as squaring;  pow(number, 0.5) is squareroot
         x1 = (pow(court_width_mm, 2) + pow(cam_to_left_doubles, 2) - pow(cam_to_right_doubles, 2)) / (court_width_mm*2)
         new_cam_location_mm[Axis.x.value] = int(x1 - doubles_width_mm)
         if new_cam_location_mm[Axis.x.value] < 0:
            app.logger.error(f"x1 distance calculation error; x={x1}")
            x1 = 0
         Y = pow((pow(cam_to_left_doubles, 2) - pow(x1, 2)), 0.5) + court_depth_mm
         if not isinstance(Y,float):
            app.logger.error(f"Y distance calculation error; y={Y}")
            Y = 0
         new_cam_location_mm[Axis.y.value] = int(Y)
         new_cam_location_mm[Axis.z.value] = new_cam_measurement_mm[Measurement.z.value]

         output_line = json.dumps(new_cam_location_mm) + " " +  dt_str + "\n"
         with open(f'{settings_dir}/{cam_side.lower()}_cam_location.json', 'r+') as outfile:
            lines = outfile.readlines() # read old content
            outfile.seek(0) # go back to the beginning of the file
            outfile.write(output_line) # write new content at the beginning
            for line in lines: # write old content after new
               outfile.write(line)
         # with open(f"{settings_dir}/{cam_side.lower()}_cam_location.json", "w") as outfile:
         #    json.dump(new_cam_location_mm, outfile)
      else:
         app.logger.debug(f"No change in {cam_side} cam measurements, not updating cam_measurements or cam_location")


   # copy the lastest PNG from the camera to the base
   scp_court_png(side = cam_side.lower())

   page_styles = []
   page_styles.append(Markup('<link rel="stylesheet" href="/static/css/cam-calib.css">'))

   court_point_dict_index = 0
   if cam_side is cam_side_right_label:
      court_point_dict_index = 1

   mode_str = f"Court Points"
   return render_template(CAM_CALIBRATION_TEMPLATE, \
      page_specific_styles = page_styles, \
      home_button = my_home_button, \
      installation_title = customization_dict['title'], \
      installation_icon = customization_dict['icon'], \
      image_path = "/static/" + cam_side.lower() + "_court.png", \
      court_point_coords = court_points_dict_list[court_point_dict_index], \
      # court_point_coords = COURT_POINT_KEYS_W_AXIS, \
      footer_center = "Mode: " + mode_str)


@app.route(CAM_CALIB_DONE_URL, methods=DEFAULT_METHODS)
def cam_calib_done():
   global cam_side, new_cam_location_mm

   # app.logger.debug(f"POST to CALIB_DONE request: {request}")
   # app.logger.debug(f"POST to CALIB_DONE request.content_type: {request.content_type}")

   if request.method=='POST':

      if cam_side == None:
         # this happens during debug, when using the browser 'back' to navigate to CAM_CALIB_URL
         cam_side = "Left"
         app.logger.warning("cam_side was None in cam_calib_done")

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
         app.logger.debug(f"POST to CALIB_DONE request.form: {request.form}")
         # example: ImmutableMultiDict([('FBLX', '322'), ('FBLY', '72'), ('FBRX', '612'), ('FBRY', '54'), ('NSLX', '248'), ('NSLY', '328'), ('NSCX', '602'), ('NSCY', '292'), ('NSRX', '904'), ('NSRY', '262'), ('NBLX', '146'), ('NBLY', '686'), ('NBRX', '1244'), ('NBRY', '482')])
         court_point_dict_index = 0
         if cam_side is cam_side_right_label:
            court_point_dict_index = 1

         if len(request.form) > 0:
            for coordinate_id in COURT_POINT_KEYS_W_AXIS:
               if coordinate_id in request.form:
                  this_coord_point = coordinate_id[0:3]
                  this_coord_axis = Axis[coordinate_id[3:4].lower()].value
                  # app.logger.info(f"Before: court_point_dict_index={court_point_dict_index} this_coord_point={this_coord_point} this_coord_axis={this_coord_axis}")
                  court_points_dict_list[court_point_dict_index][this_coord_point][this_coord_axis] = int(request.form[coordinate_id])
               else:
                  app.logger.error(f"Missing {coordinate_id} in cam_calib_done post.")
         else:
            app.logger.debug("POST to CALIB_DONE request.form is zero length; using emit data instead")

         # do some sanity checking:
         if court_points_dict_list[court_point_dict_index]["NBR"][1] < 1:
            app.logger.error(f"Invalid court_point values: {court_points_dict_list[court_point_dict_index]}")
            status = f"FAILED: {cam_side} camera court points are invalid."
         else:
            #persist values for base to use to generate correction vectors
            dt = datetime.datetime.now()
            dt_str = dt.strftime("%Y-%m-%d_%H-%M")
            output_line = json.dumps(court_points_dict_list[court_point_dict_index]) + " " +  dt_str + "\n"
            with open(f'{settings_dir}/{cam_side.lower()}_court_points.json', 'r+') as outfile:
               lines = outfile.readlines() # read old content
               outfile.seek(0) # go back to the beginning of the file
               outfile.write(output_line) # write new content at the beginning
               for line in lines: # write old content after new
                  outfile.write(line)

            # tell the bbase to regenerate correction vectors; the '1' in the value is not used and is there for completeness
            rc, code = send_msg(PUT_METHOD, FUNC_RSRC, {FUNC_GEN_CORRECTION_VECTORS: 1} )
            if not rc:
               if not code:
                  code = "unknown"
               app.logger.error("PUT FUNC_GEN_CORRECTION_VECTORS failed, code: {code}")
               status = f"FAILED: {cam_side} camera correction vector generation failed."
            else:
               status = f"{cam_side} camera calibration finished."


   page_js = []
   page_js.append(Markup('<script src="/static/js/timed-redirect.js"></script>'))
 
   button_label = "Camera Calibration"
   return render_template(CHOICE_INPUTS_TEMPLATE, \
      home_button = my_home_button, \
      installation_title = customization_dict['title'], \
      installation_icon = customization_dict['icon'], \
      message = status, \
      page_specific_js = page_js, \
      # onclick_choices = [{"value": button_label, "onclick_url": MAIN_URL}], \
      footer_center = "Mode: " + button_label)

@app.route(CAM_VERIF_URL, methods=DEFAULT_METHODS)
def cam_verif():
   court_point_dict_index = 0
   cam_name = 'left'

   if request.method=='POST':
      app.logger.debug(f"POST to CAM_VERIF_URL request.form: {request.form}")
      # POST to CAM_LOCATION request.form: ImmutableMultiDict([('choice', 'Left Cam Calib')])
      if ('image_path' in request.form) and 'left' in request.form['image_path']:
         court_point_dict_index = 1
         cam_name = 'right'
 
   read_court_point_files()

   scp_court_png(side = cam_name)

   #TODO: handle scp or court_points failure

   return render_template(CAM_VERIFICATION_TEMPLATE, \
      home_button = my_home_button, \
      installation_title = customization_dict['title'], \
      installation_icon = customization_dict['icon'], \
      image_path = "/static/" + cam_name + "_court.png", \
      court_point_coords = court_points_dict_list[court_point_dict_index], \
      footer_center = "Mode: " + "Check Camera")

 
@app.route(MAIN_URL, methods=DEFAULT_METHODS)
def index():
   global back_url, previous_url
   back_url = previous_url = "/"

   # app.logger.debug(f"Test of printing function name: in function: {sys._getframe(0).f_code.co_name}")

   # clicking stop on the game_url & drill_url goes to main/home/index, so issue stop.
   rc, code = send_msg(PUT_METHOD, STOP_RSRC)
   if not rc:
      app.logger.error(f"function '{sys._getframe(0).f_code.co_name}': PUT STOP failed, code: {code}")

   read_settings_from_file()

   # example of setting button disabled and a button ID
   # TODO: fix disable CSS
   # onclick_choices = [{"value": button_label, "onclick_url": MAIN_URL, "disabled": 1, "id": "Done"}], \

   html_horizontal_rule =  Markup('<hr>')

   onclick_choice_list = [\
      {"html_before": "Game:", "value": "Play", "onclick_url": GAME_URL, "id": "game_button"},\
      {"value": "Options", "onclick_url": GAME_OPTIONS_URL, "id": "game_button", "html_after": html_horizontal_rule},\
      {"html_before": "Drill:", "value": "Recents", "onclick_url": RECENTS_URL},\
      {"value": "Select", "onclick_url": DRILL_SELECT_TYPE_URL},\
      {"value": "Beep", "onclick_url": BEEP_SELECTION_URL, "html_after": html_horizontal_rule},\
      {"value": "Workouts", "onclick_url": SELECT_URL, \
         "param_name": ONCLICK_MODE_KEY, "param_value": ONCLICK_MODE_WORKOUT_VALUE, "disabled": 0, "html_after": html_horizontal_rule}, \
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
      {"value": "Check Camera", "onclick_url": CAM_VERIF_URL}, \
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

   read_settings_from_file()
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
      url_for_post = CAM_LOCATION_URL, \
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
      #TODO: do a redirect to an error page

   rc, code = send_msg(PUT_METHOD, MODE_RSRC, {MODE_PARAM: base_mode_e.CREEP_CALIBRATION.value})
   if not rc:
      app.logger.error(f"function '{sys._getframe(0).f_code.co_name}': PUT Mode failed, code: {code}")
   else:
      app.logger.debug(f"sending FUNC_CREEP to bbase")
      rc, code = send_msg(PUT_METHOD, FUNC_RSRC, {FUNC_CREEP: creep_type})
      if not rc:
         app.logger.error(f"function '{sys._getframe(0).f_code.co_name}': PUT Function failed, code: {code}")

   return render_template(CHOICE_INPUTS_TEMPLATE, \
      home_button = my_home_button, \
      installation_title = customization_dict['title'], \
      installation_icon = customization_dict['icon'], \
      message = f"{creep_type.title()} creep calibration in progress.", \
      footer_center = "Mode: Creep Calibration")


@app.route(GAME_OPTIONS_URL, methods=DEFAULT_METHODS)
def game_options():
   global back_url, previous_url
   back_url = '/'
   previous_url = "/" + inspect.currentframe().f_code.co_name

   # clicking stop when the game is active goes to this page, so stop the game
   rc, code = send_msg(PUT_METHOD, STOP_RSRC)
   if not rc:
      app.logger.error("PUT STOP failed, code: {}".format(code))

   send_settings_to_base() #restore level, delay, speed, etc

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
      footer_center = "Mode: " + "Game Options")

@app.route(GAME_URL, methods=DEFAULT_METHODS)
def game():
   global back_url, previous_url
   back_url = previous_url

   # ignore the POST data: wServes & tiebreaker are set using emit(change_params)
   # app.logger.debug(f"GAME_URL request_form: {request.form}")
   #ImmutableMultiDict([('wServes', '0'), ('tiebreaker', '0')])

   read_settings_from_file()
   send_settings_to_base() #restore settings

   rc, code = send_msg(PUT_METHOD, MODE_RSRC, {MODE_PARAM: base_mode_e.GAME.value})
   if not rc:
      app.logger.error("GAME_URL: PUT Mode failed, code: {}".format(code))
   else:
      rc, code = send_msg(PUT_METHOD, STRT_RSRC)
      if not rc:
         app.logger.error("PUT START failed, code: {}".format(code))

   # print("{} on {}, data: {}".format(request.method, inspect.currentframe().f_code.co_name, request.data))
   # Using emit on radio buttons instead of taking the post data

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
   global drill_type_choices

   drill_type_radio_options = {}
   # in the for loop - options is the list of radio buttons and choice is the legend
   for choice, options in drill_type_choices.items():
      button_list = []
      for i, option in enumerate(options):
         button_list.append({"label":option.name.replace("_","-"), "value":option.value})
         if i == 0:
            button_list[i].update({"checked":1})
      drill_type_radio_options.update({choice: {"legend":choice.name, "buttons": button_list}})

   return render_template(GAME_OPTIONS_TEMPLATE, \
      home_button = my_home_button, \
      installation_title = customization_dict['title'], \
      installation_icon = customization_dict['icon'], \
      radio_options = drill_type_radio_options, \
      url_for_post = SELECT_URL, \
      footer_center = "Mode: " + MODE_DRILL_NOT_SELECTED)


@app.route(RECENTS_URL, methods=DEFAULT_METHODS)
def recents():
   global recent_drills
   selection_list = []

   try:
      with open(f'{settings_dir}/{recents_filename}') as f:
         recent_drills = json.load(f)
   except:
      app.logger.error(f"Error reading '{settings_dir}/{recents_filename}'; using defaults")
      #TODO: read a factory defaults from drill directory
      recent_drills = [1, 2, 5, 6, 8, 9, 11, 22, 26, 27]
#      , 811, 812, 813, 814, 815, 816, 817, 818, 822, 823, 825, 826, 827]

   for drill_id in recent_drills:
      # drill filename format: DRL123.csv
      try:
         with open(f'{drills_dir}/DRL{drill_id:03}.csv') as f:
            lines = f.readlines()
            # remove quotes from title string, if they exist
            selection_list.append({'id': f"{drill_id:03}", 'title': lines[0].replace('"','')})
      except:
         app.logger.error(f"Error reading DRL{drill_id:03}.csv; not including in choices")

   page_js = []
   page_js.append(Markup('<script src="/static/js/get_drill_info.js"></script>'))

   return render_template(SELECT_TEMPLATE, \
      home_button = my_home_button, \
      installation_title = customization_dict['title'], \
      installation_icon = customization_dict['icon'], \
      footer_center = "Mode: " + MODE_DRILL_NOT_SELECTED, \
      url_for_post = DRILL_URL, \
      choices = selection_list, \
      page_specific_js = page_js
   )


@app.route(SELECT_URL, methods=DEFAULT_METHODS)
def select():
   global back_url, previous_url
   global workout_select
   back_url = '/'
   previous_url = "/" + inspect.currentframe().f_code.co_name

   # app.logger.debug(f"select [drill/workout] request: {request}")
   app.logger.debug(f"SELECT_URL request_form: {request.form}")

   send_settings_to_base() #restore level, delay, speed, etc

   #enter this page from drill categories (player, instructor), or from Main (workflows)
   # a parameter (mode) indicates the if workflow or drills should be selected
   select_post_param = []
   filter_list = []
   if request.args.get(ONCLICK_MODE_KEY) == ONCLICK_MODE_WORKOUT_VALUE:
      workout_select = True
      selection_list = workout_list
      # select_post_param = {"name": ONCLICK_MODE_KEY, "value": ONCLICK_MODE_WORKOUT_VALUE}
      mode_string = MODE_WORKOUT_NOT_SELECTED
   else:
      workout_select = False
      # drill_select_type = None
      mode_string = MODE_DRILL_NOT_SELECTED
      selection_list = [\
         {'id': '001', 'title': 'Ground: Random'},\
         {'id': '002', 'title': 'Net: Random'},\
         {'id': '003', 'title': 'Volley: Random'},\
      ]
      # if request.method=='POST':
      #    app.logger.debug(f"request_form_getlist_type: {request.form.getlist('choice')}")
      #    drill_select_type = request.form.getlist('choice')[0]

   

      # # refer to /home/pi/boomer/drills/ui_drill_selection_lists.py for drill_list format
      # if drill_select_type == DRILL_SELECT_TYPE_TEST:
      #    selection_list = drill_list_test
      # elif drill_select_type == DRILL_SELECT_TYPE_INSTRUCTORS:
      #    selection_list = drill_list_instructor
      # else:
      #    selection_list = drill_list_player
      #    filter_list = ['data-Type', 'data-Stroke', 'data-Difficulty']

   # if len(filter_list) > 0:
   #    page_js = filter_js
   # else:
   #    page_js = []
   page_js = []
   page_js.append(Markup('<script src="/static/js/get_drill_info.js"></script>'))

   return render_template(SELECT_TEMPLATE, \
      home_button = my_home_button, \
      installation_title = customization_dict['title'], \
      installation_icon = customization_dict['icon'], \
      url_for_post = DRILL_URL, \
      # the following doesn't work: the query parameter is now stripped by the browser.  TODO: remove from template
      # post_param = select_post_param, \
      choices = selection_list, \
      filters = filter_list, \
      footer_center = "Mode: " + mode_string, \
      page_specific_js = page_js
   )
 
@app.route(DRILL_URL, methods=DEFAULT_METHODS)
def drill():
   global beep_mode_choices
   global back_url, previous_url
   global workout_select
   global recent_drills
   back_url = previous_url

   read_settings_from_file()
   send_settings_to_base() #restore settings

   '''
   There are multiple ways of getting to this page
      - select_url: the post contains the choice_id  The global variable 'workout_select' indicates workout or drill
      = thrower_calib: the post contains a drill_id  or workout ID
      - beep_select: the post contains radio buttons selections (stroke, difficulty) which are mapped to a drillID
   example from beep test:
      DRILL_URL request_form: ImmutableMultiDict([('Stroke', 'Mini-Tennis'), ('Ground Stroke Type', 'Topspin'), ('Difficulty', 'Medium')])
      DRILL_URL request_args: ImmutableMultiDict([])
   '''
   app.logger.debug(f"DRILL_URL request_form: {request.form}")
   app.logger.debug(f"DRILL_URL request_args: {request.args}")

   # app.logger.info(f"request.form is of type: {type(request.form)}")
   # for key, value in request.form.items():
   #    print(key, '->', value)
   id = None
   beep_type_value = None
   if 'choice_id' in request.form:
      #INFO:flask.app:DRILL_URL request_form: ImmutableMultiDict([('choice_id', '100')])
      id = int(request.form['choice_id'])
      app.logger.info(f"Setting drill_id= {id} from request.form")
   elif DRILL_ID in request.args:
      #DRILL_URL request_args: ImmutableMultiDict([('choice_id', '781')])
      id = int(request.args[DRILL_ID])
      app.logger.info(f"Setting drill_id= {id} from request.args")
   elif WORKOUT_ID in request.args:
      #DRILL_URL request_args: ImmutableMultiDict([('workout_id', '2')])
      id = int(request.args[WORKOUT_ID])
      workout_select = True
      app.logger.info(f"Setting workout_id= {id} from request.args")
   elif 'beep_options.Type' in request.form:
      beep_type_value = int(request.form['beep_options.Type'])
      # beep drill mode
      #request_form: ImmutableMultiDict([('beep_options.Type', '2'), ('beep_options.Stroke', '5'), ('beep_options.Difficulty', '2')])
      # for key in request.form:
      #    app.logger.info(f"Beep choice {key} = {request.form[key]}")
      # example beep drill ranges - consult the drills repository for the real thing:
      #mini-tennis: 901-905; volley: 906-910; 911-915 flat, 916-920 loop, 921-925 chip, 926-930 topspin, 931-935 random
      stroke_type_offset = 0
      difficulty_offset = 3
      if 'beep_options.Difficulty' in request.form:
         difficulty_offset = int(request.form['beep_options.Difficulty'])
         # app.logger.info(f"beep_type={beep_type(beep_type_value).name}; Increasing id by {difficulty_offset}, e.g. {beep_difficulty(difficulty_offset).name}")
      else:
         app.logger.warning(f"beep_options.Difficulty not in request.form")
      if beep_type_value is beep_type.Volley.value:
         stroke_type_offset = 5
      if beep_type_value is beep_type.Ground.value:
         stroke_type = int(request.form['beep_options.Stroke'])
         stroke_type_offset = (stroke_type * 5) + 10
         app.logger.info(f"Ground beep type, so using stroke_type={beep_stroke(stroke_type).name}")

      id = BEEP_DRILL_NUMBER_START + difficulty_offset + stroke_type_offset
      app.logger.info(f"drill_id={id}: {beep_type(beep_type_value).name}, difficulty_offset={difficulty_offset}, stroke_type_offset={stroke_type_offset}")
   else:
      app.logger.error("DRILL_URL - no drill or workout id!")
      mode_string = f"ERROR: no drill selected"

   drill_stepper_options = {}
   if id is not None:
      if not workout_select and beep_type_value is None:
         if id in recent_drills:
            recent_drills.remove(id)
         else:
            recent_drills = recent_drills[:-1] #remove oldest drill_id
         # re-write recents file putting drill at top         
         recent_drills.insert(0, id)
         try:
            with open(f'{settings_dir}/{recents_filename}', 'w') as f:
               json.dump(recent_drills, f)
         except:
            app.logger.error(f"Error writing '{settings_dir}/{recents_filename}'")

      if workout_select:
         mode = {MODE_PARAM: base_mode_e.WORKOUT.value, ID_PARAM: id}
         mode_string = f"{MODE_WORKOUT_SELECTED}{id}"
         workout_select = False
      #TODO: test BEEP enum: currently beep drills are using the DRILL enum
      # elif beep_type_value is not None:
      #    mode = {MODE_PARAM: base_mode_e.BEEP.value, ID_PARAM: id}
      else:
         mode = {MODE_PARAM: base_mode_e.DRILL.value, ID_PARAM: id}
         mode_string = f"{MODE_DRILL_SELECTED}{id}"
      
      rc, code = send_msg(PUT_METHOD, MODE_RSRC, mode)
      if not rc:
         app.logger.error("DRILL_URL: PUT Mode failed, code: {}".format(code))
      else:
         rc, code = send_msg(PUT_METHOD, STRT_RSRC)
         if not rc:
            app.logger.error("PUT START failed, code: {}".format(code))

      thrower_calib_drill_number_end = THROWER_CALIB_DRILL_NUMBER_START + len(thrower_calib_drill_dict) + 1
      if (id not in range(THROWER_CALIB_DRILL_NUMBER_START, thrower_calib_drill_number_end)) and \
         (id != THROWER_CALIB_WORKOUT_NUMBER):
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
         
   previous_url = "/" + inspect.currentframe().f_code.co_name
   return render_template(DRILL_TEMPLATE, \
      installation_title = customization_dict['title'], \
      installation_icon = customization_dict['icon'], \
      stepper_options = drill_stepper_options, \
      footer_center = "Mode: " + mode_string)


@app.route(BEEP_SELECTION_URL, methods=DEFAULT_METHODS)
def beep_selection():
   global beep_mode_choices

   send_settings_to_base() #restore level, delay, speed, etc

   beep_radio_options = {}
   # in the for loop - options is the list of radio buttons and choice is the legend
   for choice, options in beep_mode_choices.items():
      button_list = []
      for i, option in enumerate(options):
         button_list.append({"label":option.name.replace("_","-"), "value":option.value})
         if i == 0:
            button_list[i].update({"checked":1})
      beep_radio_options.update({choice: {"legend":choice.name, "buttons": button_list}})

   # app.logger.info(f"beep_radio_options: {beep_radio_options}")

   page_js = []
   page_js.append(Markup('<script src="/static/js/radio-button-disable.js"></script>'))

   return render_template(GAME_OPTIONS_TEMPLATE, \
      home_button = my_home_button, \
      installation_title = customization_dict['title'], \
      installation_icon = customization_dict['icon'], \
      radio_options = beep_radio_options, \
      url_for_post = DRILL_URL, \
      page_specific_js = page_js, \
      footer_center = "Mode: " + MODE_DRILL_NOT_SELECTED)


@app.route(FAULTS_URL, methods=DEFAULT_METHODS)
def faults():
   global back_url, previous_url
   back_url = previous_url
   read_settings_from_file()

   return render_template(FAULTS_TEMPLATE, \
      installation_title = customization_dict['title'], \
      installation_icon = customization_dict['icon'], \
      footer_center = "Mode: " + "--")


@app.route(DONE_URL, methods=DEFAULT_METHODS)
def done():

   msg_ok, base_mode_register = send_msg(GET_METHOD, MODE_RSRC)
   if not msg_ok:
      app.logger.error(f"function '{sys._getframe(0).f_code.co_name}': GET STOP MODE_RSRC failed")
      status = "Error occurred on obtaining Boomer mode"
   else:
      status = f"{base_mode_e(base_mode_register[MODE_PARAM]).name.title()} Finished."
 
      # page_js = []
      # page_js.append(Markup('<script src="/static/js/timed-redirect.js"></script>'))

   return render_template(CHOICE_INPUTS_TEMPLATE, \
      installation_title = customization_dict['title'], \
      installation_icon = customization_dict['icon'], \
      message = status, \
      onclick_choices = [{"value": "OK", "onclick_url": MAIN_URL}], \
      # page_specific_js = page_js, \
      footer_center = "Mode: " + "Finished")


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

# the following is not necessary: state_update sends fault info.
# @socketio.on('fault_request')
# def handle_fault_request():
#    global faults_table
#    app.logger.info('received fault_request')
#    emit('faults_update', json.dumps(textify_faults_table()))
 
@socketio.on('client_connected')
def handle_client_connected(data):
   app.logger.debug(f"received client_connected: {data}")
   global client_state
   client_state = True

@socketio.on('change_params')     # Decorator to catch an event named change_params
def handle_change_params(data):          # change_params() is the event callback function.
   #  print('change_params data: ', data)      # data is a json string: {"speed":102}
   app.logger.info(f'received change_params: {data}')
   for k in data.keys():
      if data[k] == None:
         app.logger.warning(f'Received NoneType for {k}')
      else:
         if (k == LEVEL_PARAM):
            settings_dict[k] = int(data[k]*10)
         elif (k == DELAY_MOD_PARAM):
            settings_dict[k] = int(data[k]*1000)
         else:
            settings_dict[k] = int(data[k])
         app.logger.debug(f'Setting: {k} to {settings_dict[k]}')
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
   app.logger.info('received pause_resume.')
   rc, code = send_msg(PUT_METHOD, PAUS_RSRC)
   if not rc:
      app.logger.error("PUT PAUSE failed, code: {}".format(code))

@socketio.on('refresh_image')
def handle_refresh_image(data):
   app.logger.info(f'received refresh_image: {data}')
   scp_court_png(data['side'], data['frame'])

'''
@socketio.on('coord')
def handle_coord_array(data):
   global court_points_dict
   # app.logger.info(f"received coord_array: {data}")
   point_id_w_axis = list(data.keys())[0]
   value = int(data[point_id_w_axis])
   court_point_id = str(point_id_w_axis)[:3].upper()
   axis_letter = str(point_id_w_axis)[3]
   if axis_letter is 'x':
      axis = 0
   elif axis_letter is 'y':
      axis = 1
   else:
      app.logger.error(f"unknown axis in court coord: {axis_letter}")
   app.logger.info(f"court_point_id={court_point_id} axis={axis} value={value}")
   court_points_dict[court_point_id][axis] = value
   # app.logger.info(f"court_point_dict={court_points_dict}")
'''

@socketio.on('get_drill_desc')
def handle_get_drill(data):
   # app.logger.debug(f"get_drill_desc data: {data}")
   if 'drill_id' in data:
      drill_id = data['drill_id']
      app.logger.debug(f"get_drill_desc for drill={drill_id}")
      drill_info_dict = get_drill_info(drill_id)
      if 'desc' in drill_info_dict:
         emit('drill_desc', drill_info_dict['desc'])
      else:
         app.logger.warning(f"no description for drill number={drill_id}")
   else:
      app.logger.error(f"no drill number in get_drill_desc message")


@socketio.on('get_updates')
def handle_get_updates(data):
   json_data = json.loads(data)
   # app.logger.info(f"get_update data= {json_data}")
   global base_state
   # local_previous_base_state = base_state
   check_base()
   base_state_text = base_state_e(base_state).name.title() #title changes it from uppercase to capital for 1st char
   update_dict = {"base_state": base_state_text}

   if ("page" in json_data):
      current_page = '/' + json_data["page"]
      # app.logger.debug(f"current_page={current_page}; base_state={base_state_e(base_state).name}")
      # if (current_page == MAIN_URL):
      #    app.logger.debug("current_page is MAIN_URL")
      # if (base_state == base_state_e.FAULTED):
      #    app.logger.debug("base_state is FAULTED")
      # else:
      #   app.logger.debug(f"base_state is not FAULTED; its={base_state}")
 
      if ((base_state == base_state_e.FAULTED) and (current_page != FAULTS_URL)):
         update_dict['new_url'] = FAULTS_URL

      if ((base_state != base_state_e.FAULTED) and (current_page == FAULTS_URL)):
         update_dict['new_url'] = MAIN_URL
 
      if (current_page == FAULTS_URL):
         #TODO: if (len(faults_table) != len(previous_faults_table)):
         emit('faults_update', json.dumps(textify_faults_table()))

      if (((current_page == GAME_URL) or (current_page == DRILL_URL) or (current_page == CREEP_CALIB_URL)) and
         (base_state == base_state_e.IDLE)):
         update_dict['new_url'] = DONE_URL

      elif (current_page is GAME_URL):
         msg_ok, game_state = send_msg(GET_METHOD, SCOR_RSRC)
         if not msg_ok:
            app.logger.error("GET GAME SCORE failed, score= {}".format(game_state))
         else:
            # app.logger.info(f"score= {game_state}")
            # score= {'time': 36611, 'server': 'b', 'b_sets': 0, 'p_sets': 0, 'b_games': 0, 'p_games': 0, 'b_pts': 0, 'p_pts': 0, 'b_t_pts': 0, 'p_t_pts': 0}
            update_dict["game_state"] = game_state

   update_dict['soft_fault'] = soft_fault_e(soft_fault_status).value

   if ("new_url" in update_dict):
      app.logger.info(f"Changing URL from '{current_page}' to {update_dict['new_url']} since base_state={base_state_e(base_state).name}")

   emit('state_update', update_dict)


def set_base_state_on_failure(fault_code = fault_e.CONTROL_PROGRAM_GET_STATUS_FAILED):
   global base_state
   global faults_table
   global bbase_down_timestamp

   base_state = base_state_e.FAULTED
   if bbase_down_timestamp is None:
      bbase_down_timestamp = time.time()
   faults_table = [{FLT_CODE_PARAM: fault_code, FLT_LOCATION_PARAM: net_device_e.BASE, FLT_TIMESTAMP_PARAM: bbase_down_timestamp}]


def check_base():
   threaded = False
   process_name = 'bbase'
   global base_state, previous_base_state
   global client_state, socketio
   global printout_counter
   global faults_table, previous_fault_table
   global bbase_down_timestamp
   global soft_fault_status
   done = False
   while not done:
      base_pid = os.popen(f"pgrep {process_name}").read()
      #base_pid is empty if base is not running
      if base_pid:
         # verify responding to FIFO
         # app.logger.info("Getting status message")
         msg_ok, status_msg = send_msg()
         if not msg_ok:
            set_base_state_on_failure(fault_e.CONTROL_PROGRAM_FAILED)
         else:
            if (status_msg is not None):
               if (STATUS_PARAM in status_msg):
                  bbase_down_timestamp = None
                  base_state = base_state_e(status_msg[STATUS_PARAM])
               else:
                  set_base_state_on_failure(fault_e.CONTROL_PROGRAM_FAILED)

               if (HARD_FAULT_PARAM in status_msg and status_msg[HARD_FAULT_PARAM] > 0):
                  previous_fault_table = copy.deepcopy(faults_table)
                  # app.logger.info("Getting fault table")
                  msg_ok, faults_table = send_msg(GET_METHOD, FLTS_RSRC)
                  if not msg_ok:
                     app.logger.error("msg status not OK when getting fault table")
                     set_base_state_on_failure(fault_e.CONTROL_PROGRAM_GET_STATUS_FAILED)

               if (SOFT_FAULT_PARAM in status_msg):
                  soft_fault_status = soft_fault_e(status_msg[SOFT_FAULT_PARAM])

               # app.logger.info(f"faults: {faults_table[0]}")
            else:
               app.logger.error("received None as status message")
               set_base_state_on_failure(fault_e.CONTROL_PROGRAM_GET_STATUS_FAILED)
      else:
         set_base_state_on_failure(fault_e.CONTROL_PROGRAM_NOT_RUNNING)

      if base_state != previous_base_state:
         app.logger.info(f"Base state change: {base_state_e(previous_base_state).name} -> {base_state_e(base_state).name}")
         # app.logger.info(f"Base state change: {previous_base_state} -> {base_state}")
          
      if threaded:
         # the following didn't work when in a seperate thread: the emit didn't get to the client
         printout_counter += 1
         if printout_counter > 35:
            printout_counter = 0
            if client_state:
               socketio.emit('base_state_update', {"base_state": base_state})
               app.logger.debug(f"emitting: {{'base_state_update', {{\"base_state\": \"{base_state}\"}}}}")
               # print(f"emitting: {{'base_state_update', {{\"base_state\": \"{base_state}\"}}}}")
            else:
               app.logger.debug(f"client_state is false")
               # print(f"client_state is false")
         time.sleep(0.3)
      else:
         done = True
      previous_base_state = base_state
   # end while loop

def send_settings_to_base():
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
   global customization_dict, settings_dict
   try:
      with open(f'{settings_dir}/ui_customization.json') as f:
         customization_dict = json.load(f)
   except:
      customization_dict = {"title": "Welcome to Boomer", "icon": "/static/favicon.ico"}

   try:
      with open(f'{settings_dir}/{settings_filename}') as f:
         settings_dict = json.load(f)
         # app.logger.debug(f"Settings restored: {settings_dict}")
   except:
      app.logger.warning(f"Settings file read failed; using defaults.")
      settings_dict = {GRUNTS_PARAM: 0, TRASHT_PARAM: 0, LEVEL_PARAM: LEVEL_DEFAULT, \
            SERVE_MODE_PARAM: 1, TIEBREAKER_PARAM: 0, \
            SPEED_MOD_PARAM: SPEED_MOD_DEFAULT, DELAY_MOD_PARAM: DELAY_MOD_DEFAULT, \
            ELEVATION_MOD_PARAM: ELEVATION_ANGLE_MOD_DEFAULT}

def scp_court_png(side='Left', frame='even'):

   source_path = f"{side.lower()}:/run/shm/frame_{frame}.png"
   destination_path = f"{user_dir}/{boomer_dir}/{side.lower()}_court.png"
   # the q is for quiet
   p = Popen(["scp", "-q", source_path, destination_path])
   stdoutdata, stderrdata = p.communicate()
   if p.returncode != 0:
      app.logger.error(f"FAILED: scp {source_path} {destination_path}; error_code={p.returncode}")
   else:
      app.logger.info(f"OK: scp {source_path} {destination_path}")

def read_court_point_files():
   global court_point_dict_list
   for side in range(2):
      if side == 0:
         side_name = 'left'
      else:
         side_name = 'right'
      try:
         with open(f'{settings_dir}/{side_name}_court_points.json') as f:
            file_lines = f.readlines()
            first_line_json = file_lines[0].split("}")[0] + "}"
            # app.logger.debug(f"first_line_json={first_line_json}")
            court_points_dict_list[side] = json.loads(first_line_json)
            app.logger.debug(f"court_points_dict_list[{side_name}]={court_points_dict_list[side]}")
      except:
         app.logger.warning(f"court_points_dict_list[{side_name}] load failed")


def get_drill_info(drill_id):
   global workout_select
   if (workout_select):
      prefix = "WORK"
   else:
      prefix = "DRL"

   drill_info = {}
   try:
      file_path = f'{drills_dir}/{prefix}{drill_id}.csv'
      app.logger.debug(f"get_drill_info file_path='{file_path}'")
      with open(file_path) as f:
         lines = f.readlines()
         # remove quotes from title string, if they exist
         drill_info['desc'] = lines[1].replace('"','')
   except:
      app.logger.error(f"get_drill_info: Error reading '{file_path}'")
   return drill_info


if __name__ == '__main__':

   do_threaded_base_checks = False
   if do_threaded_base_checks:
      check_base_thread = Thread(target = check_base, args =("bbase", ))
      check_base_thread.daemon = True
      check_base_thread.start()
      # refer to: https://newbedev.com/python-flask-socketio-send-message-from-thread-not-always-working
      socketio.start_background_task(target = check_base)
   
   do_status_printout = False
   if do_status_printout:
      print_base_thread = Thread(target = print_base_status, args =(20, ))
      print_base_thread.daemon = True
      print_base_thread.start() 

   # app.run(host="0.0.0.0", port=IP_PORT, debug = True)
   socketio.run(app, host="0.0.0.0", port=IP_PORT, debug = True)
   try:
      serve(app, host="0.0.0.0", port=IP_PORT)
      app.logger.info("started server")
   except Exception as e:
      print(e)
      sys.exit(1)
   
   # check_base_thread.join()
