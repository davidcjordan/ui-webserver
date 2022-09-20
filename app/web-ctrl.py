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
import enum
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

user_dir = '/home/pi'
boomer_dir = 'boomer'
repos_dir = 'repos'
site_data_dir = 'this_boomers_data'
settings_dir = f'{user_dir}/{boomer_dir}/{site_data_dir}'
execs_dir = f"{user_dir}/{boomer_dir}/execs"
recents_filename = "recents.json"

# the following requires: export PYTHONPATH='/Users/tom/Documents/Projects/Boomer/control_ipc_utils'
sys.path.append(f'{user_dir}/{repos_dir}/control_ipc_utils')
# print(sys.path)
try:
   from ctrl_messaging_routines import send_msg
   from control_ipc_defines import *
except:
   app.logger.error("Problems with 'control_ipc' modules, please run: git clone https://github.com/davidcjordan/control_ipc_utils")
   exit()

sys.path.append(f'{user_dir}/{boomer_dir}/drills')
try:
   from ui_drill_selection_lists import *
except:
   app.logger.error("Problems with 'ui_drill_selection_lists' modules, please run: git clone https://github.com/davidcjordon/drills")
   exit()

try:
   from func_drills import *
except:
   app.logger.error("Problems with 'func_drill.py' module")
   exit()

try:
   from func_base import *
except:
   app.logger.error("Problems with 'func_base.py' module")
   exit()

customization_dict = None
settings_dict = None

workout_select = False

my_home_button = Markup('          <button type="submit" onclick="window.location.href=\'/\';"> \
         <img src="/static/home.png" style="height:64px;" alt="Home"> \
         </button>')

html_horizontal_rule =  Markup('<hr>')

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

MODE_DRILL_SELECTED = "Drill #"
MODE_WORKOUT_SELECTED = "Workout #"

# the following are used as URL args/parameters
WORKOUT_ID = 'workout_id'
DRILL_ID = 'drill_id' # indicates drill_id for thrower calibration, which doesn't use a POST
CREEP_ID = "creep_type"
CAM_SIDE_ID = "cam_side"
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
class stroke_category(enum.Enum):
   Ground = 0
   Volley = 1
   Mini_Tennis = 2
   Net = 3 

# converted to balltype_e so, the following will be deleted:
# class beep_stroke(enum.Enum):
#    Flat = 0
#    Loop = 1
#    Chip = 2
#    Topspin = 3
#    Random = 4
class beep_difficulty(enum.Enum):
   Very_Easy = 0
   Easy = 1
   Medium = 2
   Hard = 3
   Very_Hard = 4

# having the name seperate from the legend allows the name to be a parameter name instead of what is on the screen
beep_mode_choices = [\
   {'name': beep_options.Type.name, 'legend':beep_options.Type.name, 'buttons':[ \
      {'label': stroke_category.Ground.name, 'value': stroke_category.Ground.value, 'enable': 1, 'checked' : 1}, \
      {'label': stroke_category.Volley.name, 'value': stroke_category.Volley.value, 'enable': 0}, \
      {'label': stroke_category.Mini_Tennis.name.replace("_","-"), 'value': stroke_category.Mini_Tennis.value, 'enable': 0} \
   ], 'disables': beep_options.Stroke.name}, \
   {'name': beep_options.Stroke.name, 'legend':beep_options.Stroke.name, 'buttons':[ \
      {'label': balltype_e.FLAT.name.title(), 'value': 0, 'checked' : 1}, \
      {'label': balltype_e.LOOP.name.title(), 'value': 1}, \
      {'label': balltype_e.CHIP.name.title(), 'value': 2}, \
      {'label': balltype_e.TOPSPIN.name.title(), 'value': 3}, \
      {'label': "Random", 'value': 4} \
   ]}, \
   {'name': beep_options.Difficulty.name,'legend':beep_options.Difficulty.name, 'buttons':[ \
      {'label': beep_difficulty.Very_Easy.name.replace("_","-"), 'value': beep_difficulty.Very_Easy.value}, \
      {'label': beep_difficulty.Easy.name, 'value': beep_difficulty.Easy.value, 'checked' : 1}, \
      {'label': beep_difficulty.Medium.name, 'value': beep_difficulty.Medium.value}, \
      {'label': beep_difficulty.Hard.name, 'value': beep_difficulty.Hard.value}, \
      {'label': beep_difficulty.Very_Hard.name.replace("_","-"), 'value': beep_difficulty.Very_Hard.value} \
   ]} \
]
class drill_type_options(enum.Enum):
   Group = 0
   Lines = 1
   Focus = 2
   Stroke = 3

class group_options(enum.Enum):
   Individual = 0
   Group = 1

class focus_options(enum.Enum):
   Development = 0
   Situational = 1
   Movement = 2

# the Lines radio-buttons are disabled until the 'Group' button is pushed:
#If a radio button in a fieldset (choice dictionary) disables a different fieldset then:
#  add 'disables' to the fieldset dict
#  for each button, add 'enable' to the button dictionary.
drill_type_choices = [\
   {'name': drill_type_options.Group.name, 'legend': "Type", 'buttons':[ \
      {'label': group_options.Individual.name, 'value': group_options.Individual.value, 'enable': 0, 'checked' : 1}, \
      {'label': group_options.Group.name, 'value': group_options.Group.value, 'enable': 1}, \
   ], 'disables': drill_type_options.Lines.name}, \
   {'name': drill_type_options.Lines.name, 'legend':drill_type_options.Lines.name, 'buttons':[ \
      {'label': "1-Line", 'value': "1-line"}, \
      {'label': "2-Lines", 'value':"2-line"}, \
      {'label': "3-Lines", 'value': "3-line"}, \
      {'label': "Mini-Tennis", 'value': "mini"}, \
   ], 'disabled': 1}, \
   {'name': drill_type_options.Focus.name,'legend':drill_type_options.Focus.name, 'buttons':[ \
      {'label': focus_options.Development.name, 'value': focus_options.Development.value, 'enable': 1, 'checked' : 1}, \
      {'label': focus_options.Situational.name, 'value': focus_options.Situational.value, 'enable': 0}, \
      {'label': focus_options.Movement.name, 'value': focus_options.Movement.value, 'enable': 0}, \
   ], 'disables': beep_options.Stroke.name}, \
   {'name': beep_options.Stroke.name, 'legend':beep_options.Stroke.name, 'buttons':[ \
      {'label': stroke_category.Ground.name.title(), 'value': stroke_category.Ground.name.lower(), 'checked' : 1}, \
      {'label': stroke_category.Volley.name.title(), 'value': stroke_category.Volley.name.lower()}, \
      {'label': stroke_category.Net.name.title(), 'value': stroke_category.Net.name.lower()}, \
      {'label': "Overhead", 'value': balltype_e.LOB.name.lower()}, \
   ]}, \
]

recent_drill_list = []

faults_table = {}
#TODO: generate the dict by parsing the name in the drill description in the file
# thrower_calib_drill_dict = {"ROTARY":(THROWER_CALIB_DRILL_NUMBER_START), "ELEVATOR": (THROWER_CALIB_DRILL_NUMBER_START+1)}
thrower_calib_drill_dict = {"ROTARY":(THROWER_CALIB_DRILL_NUMBER_START)}
for i in range(balltype_e.SERVE.value, balltype_e.CUSTOM.value):
   thrower_calib_drill_dict[balltype_e(i).name] = THROWER_CALIB_DRILL_NUMBER_START+i+1
THROWER_CALIBRATION_WORKOUT_ID = 2

filter_js = []
filter_js.append(Markup('<script src="/static/js/jquery-3.3.1.min.js"></script>'))
# filter_js.append(Markup('<script src="/static/js/b_filtrify.js"></script>'))
# filter_js.append(Markup('<script src="/static/js/invoke_filtrify.js"></script>'))
# filter_js.append(Markup('<link rel="stylesheet" href="/static/css/b_filtrify.css">'))
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
 
   app.logger.debug(f"CAM_LOCATION_URL request_args: {request.args}")
   cam_side = request.args.get(CAM_SIDE_ID)
   # app.logger.debug(f"request for CAM_LOCATION_URL; {CAM_SIDE_ID}={cam_side}")
   if cam_side is None:
      app.logger.error(f"request for CAM_LOCATION_URL is missing {CAM_SIDE_ID} arg")
      cam_side = cam_side_left_label

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
      page_title = f"Enter {cam_side} Camera Location", \
      installation_icon = customization_dict['icon'], \
      options = position_options, \
      footer_center = customization_dict['title'])


@app.route(CAM_CALIB_URL, methods=DEFAULT_METHODS)
def cam_calib():
   import datetime
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
         #TODO: move persist values to func_base

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

         #TODO: move persist values to func_base
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
      page_title = f"Enter Court Coordinates", \
      installation_icon = customization_dict['icon'], \
      image_path = "/static/" + cam_side.lower() + "_court.png", \
      court_point_coords = court_points_dict_list[court_point_dict_index], \
      # court_point_coords = COURT_POINT_KEYS_W_AXIS, \
      footer_center = customization_dict['title'])


@app.route(CAM_CALIB_DONE_URL, methods=DEFAULT_METHODS)
def cam_calib_done():
   global cam_side, new_cam_location_mm
   import datetime

   # app.logger.debug(f"POST to CALIB_DONE request: {request}")
   # app.logger.debug(f"POST to CALIB_DONE request.content_type: {request.content_type}")

   if request.method=='POST':
      if cam_side == None:
         # this happens during debug, when using the browser 'back' to navigate to CAM_CALIB_URL
         cam_side = cam_side_left_label
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

         result = ""
         # do some sanity checking:
         if court_points_dict_list[court_point_dict_index]["NBR"][1] < 1:
            app.logger.error(f"Invalid court_point values: {court_points_dict_list[court_point_dict_index]}")
            result = f"FAILED: {cam_side} camera court points are invalid."
         else:
            #TODO: move persist values to func_base
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
               result = f"FAILED: {cam_side} camera correction vector generation failed."

   page_js = []
   page_js.append(Markup('<script src="/static/js/timed-redirect.js"></script>'))
 
   button_label = "Camera Calibration"
   return render_template(CHOICE_INPUTS_TEMPLATE, \
      home_button = my_home_button, \
      page_title = f"{cam_side} Camera Calibration Finished.", \
      installation_icon = customization_dict['icon'], \
      message = result, \
      # UI decision: redirect after seconds  -or-  have user click 'OK'
      page_specific_js = page_js, \
      # onclick_choices = [{"value": "OK", "onclick_url": MAIN_URL}], \
      footer_center = customization_dict['title'])

@app.route(CAM_VERIF_URL, methods=DEFAULT_METHODS)
def cam_verif():
   court_point_dict_index = 0
   cam_name = cam_side_left_label.lower()

   if request.method=='POST':
      app.logger.debug(f"POST to CAM_VERIF_URL request.form: {request.form}")
      # POST to CAM_LOCATION request.form: ImmutableMultiDict([('choice', 'Left Cam Calib')])
      if ('image_path' in request.form) and 'left' in request.form['image_path']:
         court_point_dict_index = 1
         cam_name = cam_side_right_label.lower()
 
   read_ok, temp_dict = read_court_points_file(cam_name)
   if read_ok:
      court_points_dict_list[court_point_dict_index] = temp_dict
   # app.logger.debug(f"cam_verif; court_points={court_points_dict_list}")

   scp_court_png(side = cam_name)

   #TODO: handle scp or court_points failure

   return render_template(CAM_VERIFICATION_TEMPLATE, \
      home_button = my_home_button, \
      page_title = "Check court point locations.", \
      installation_icon = customization_dict['icon'], \
      image_path = "/static/" + cam_name + "_court.png", \
      court_point_coords = court_points_dict_list[court_point_dict_index], \
      footer_center = customization_dict['title'])

 
@app.route(MAIN_URL, methods=DEFAULT_METHODS)
def index():
   global back_url, previous_url
   back_url = previous_url = "/"
   global html_horizontal_rule
   global customization_dict, settings_dict 

   # app.logger.debug(f"Test of printing function name: in function: {sys._getframe(0).f_code.co_name}")

   # clicking stop on the game_url & drill_url goes to main/home/index, so issue stop.
   rc, code = send_msg(PUT_METHOD, STOP_RSRC)
   if not rc:
      app.logger.error(f"function '{sys._getframe(0).f_code.co_name}': PUT STOP failed, code: {code}")

   customization_dict = read_customization_file()
   settings_dict = read_settings_from_file()
   send_settings_to_base(settings_dict)

   # example of setting button disabled and a button ID
   # TODO: fix disable CSS
   # onclick_choices = [{"value": button_label, "onclick_url": MAIN_URL, "disabled": 1, "id": "Done"}], \

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
      page_title = "Welcome to Boomer", \
      installation_icon = customization_dict['icon'], \
      onclick_choices = onclick_choice_list, \
      footer_center = customization_dict['title'])

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
      {"html_before": "Check:", \
         "value": "Cameras", "onclick_url": CAM_VERIF_URL, "html_after": html_horizontal_rule}, \
      {"html_before": "Calibrate:", \
         "value": "Thrower", "onclick_url": THROWER_CALIB_SELECTION_URL}, \
      {"value": "Left Camera", "onclick_url": CAM_LOCATION_URL, "param_name": CAM_SIDE_ID, "param_value": cam_side_left_label}, \
      {"value": "Right Cam", "onclick_url": CAM_LOCATION_URL, "param_name": CAM_SIDE_ID, "param_value": cam_side_right_label, \
         "html_after": html_horizontal_rule}
   ]

   settings_radio_options = [\
   {'name': GRUNTS_PARAM, 'legend':"Grunts", 'buttons':[ \
      {'label': "Off", 'value': 0}, \
      {'label': "On", 'value': 1}, \
   ]}, \
   {'name': TRASHT_PARAM,'legend':"Trash Talking", 'buttons':[ \
      {'label': "Off", 'value': 0}, \
      {'label': "On", 'value': 1}, \
   ]} \
   ]

   settings_radio_options[0]['buttons'][settings_dict[GRUNTS_PARAM]]['checked'] = 1
   settings_radio_options[1]['buttons'][settings_dict[TRASHT_PARAM]]['checked'] = 1
   
   page_js = [Markup('<script src="/static/js/radio-button-emit.js"></script>')]

   return render_template(CHOICE_INPUTS_TEMPLATE, \
      home_button = my_home_button, \
      page_title = "Change Settings or Perform Calibration", \
      installation_icon = customization_dict['icon'], \
      onclick_choices = onclick_choice_list, \
      radio_options = settings_radio_options, \
      page_specific_js = page_js, \
      footer_center = customization_dict['title'])


@app.route(THROWER_CALIB_SELECTION_URL, methods=DEFAULT_METHODS)
def thrower_calib():
   global html_horizontal_rule
   # value is the label of the button
   onclick_choice_list = [\
      {"html_before": "Motor Creep:", \
         "value": ROTARY_CALIB_NAME.title(), "onclick_url": CREEP_CALIB_URL, "param_name": CREEP_ID,"param_value": ROTARY_CALIB_NAME}, \
      {"value": ELEVATOR_CALIB_NAME.title(), "onclick_url": CREEP_CALIB_URL, "param_name": CREEP_ID,"param_value": ELEVATOR_CALIB_NAME, \
          "html_after": html_horizontal_rule}, \
      {"value": "All", "onclick_url": DRILL_URL, "param_name": WORKOUT_ID,"param_value": THROWER_CALIBRATION_WORKOUT_ID} \
   ]
   for parameter, drill_num in thrower_calib_drill_dict.items():
      button_label = f"{parameter.title()}"
      onclick_choice_list.append({"value": button_label, "param_name": DRILL_ID, "onclick_url": DRILL_URL, "param_value": drill_num})

   return render_template(CHOICE_INPUTS_TEMPLATE, \
      home_button = my_home_button, \
      page_title = "Select Thrower Calibration Type", \
      installation_icon = customization_dict['icon'], \
      onclick_choices = onclick_choice_list, \
      footer_center = customization_dict['title'])


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
      page_title = "Motor Calibration", \
      installation_icon = customization_dict['icon'], \
      message = f"{creep_type.title()} creep calibration in progress.", \
      footer_center = customization_dict['title'])


@app.route(GAME_OPTIONS_URL, methods=DEFAULT_METHODS)
def game_options():
   global back_url, previous_url
   back_url = '/'
   previous_url = "/" + inspect.currentframe().f_code.co_name

   # clicking stop when the game is active goes to this page, so stop the game
   rc, code = send_msg(PUT_METHOD, STOP_RSRC)
   if not rc:
      app.logger.error("PUT STOP failed, code: {}".format(code))

   game_radio_options = [\
   {'name': SERVE_MODE_PARAM, 'legend':"Serves", 'buttons':[ \
      {'label': "Alternate", 'value': 0}, \
      {'label': "All Player", 'value': 1}, \
      {'label': "All Boomer", 'value': 2} \
   ]}, \
   {'name': TIEBREAKER_PARAM,'legend':"Scoring", 'buttons':[ \
      {'label': "Standard", 'value': 0}, \
      {'label': "Tie Breaker", 'value': 1}, \
   ]} \
   # RUN_REDUCE_PARAM:{"legend":"Running", "buttons":[{"label":"Standard", "value":0},{"label":"Less", "value":1}]} \
]

   game_radio_options[0]['buttons'][settings_dict[SERVE_MODE_PARAM]]['checked'] = 1
   # app.logger.debug(f"settings_dict[SERVE_MODE_PARAM]= {settings_dict[SERVE_MODE_PARAM]}")
   # if (settings_dict[TIEBREAKER_PARAM] == 1):
   # app.logger.debug(f"settings_dict[TIEBREAKER_PARAM]= {settings_dict[TIEBREAKER_PARAM]}")
   game_radio_options[1]['buttons'][settings_dict[TIEBREAKER_PARAM]]['checked'] = 1
   # app.logger.debug(f"game_radio_options= {game_radio_options}")

   page_js = [Markup('<script src="/static/js/radio-button-emit.js"></script>')]

   return render_template(GAME_OPTIONS_TEMPLATE, \
      home_button = my_home_button, \
      page_title = "Select Game Mode Options", \
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
      footer_center = customization_dict['title'])

@app.route(GAME_URL, methods=DEFAULT_METHODS)
def game():
   global back_url, previous_url
   back_url = previous_url

   # ignore the POST data: wServes & tiebreaker are set using emit(change_params)
   # app.logger.debug(f"GAME_URL request_form: {request.form}")
   #ImmutableMultiDict([('wServes', '0'), ('tiebreaker', '0')])

   send_settings_to_base(settings_dict)

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
      page_title = "Game Mode", \
      installation_icon = customization_dict['icon'], \
      level_dflt = settings_dict[LEVEL_PARAM]/LEVEL_UI_FACTOR, \
      level_min = LEVEL_MIN/LEVEL_UI_FACTOR, \
      level_max = LEVEL_MAX/LEVEL_UI_FACTOR, \
      level_step = LEVEL_UI_STEP/LEVEL_UI_FACTOR, \
      footer_center = customization_dict['title'])


@app.route(DRILL_SELECT_TYPE_URL, methods=DEFAULT_METHODS)
def drill_select_type():
   global drill_type_choices

   page_js = [Markup('<script src="/static/js/radio-button-disable.js"></script>')]

   return render_template(GAME_OPTIONS_TEMPLATE, \
      home_button = my_home_button, \
      page_title = "Select Type of Drill", \
      installation_icon = customization_dict['icon'], \
      radio_options = drill_type_choices, \
      url_for_post = SELECT_URL, \
      footer_center = customization_dict['title'], \
      page_specific_js = page_js \
   )


@app.route(RECENTS_URL, methods=DEFAULT_METHODS)
def recents():
   global recent_drill_list
   global drills_dict
   selection_list = []

   try:
      with open(f'{settings_dir}/{recents_filename}') as f:
         recent_drill_list = json.load(f)
   except:
      app.logger.error(f"Error reading '{settings_dir}/{recents_filename}'; using defaults")
      #TODO: read a factory defaults from drill directory
      recent_drill_list = default_recents_drill_list

   for drill_id in recent_drill_list:
      drill_id_str = f"{drill_id:03}"
      if (fetch_into_drills_dict(drill_id_str)):
         selection_list.append({'id': drill_id_str, 'title': drills_dict[drill_id_str]['name']})
      else:
         app.logger.error(f"DRL{drill_id_str} missing from drill_dict; not including in choices")

   # app.logger.debug(f"drills_dict={drills_dict}")

   page_js = []
   page_js.append(Markup('<script src="/static/js/get_drill_info.js"></script>'))

   return render_template(SELECT_TEMPLATE, \
      home_button = my_home_button, \
      page_title = "Select Drill", \
      installation_icon = customization_dict['icon'], \
      footer_center = customization_dict['title'], \
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
   # DEBUG:flask.app:SELECT_URL request_form: ImmutableMultiDict([('Group', '1'), ('Lines', '4'), ('Focus', '0'), ('Stroke', '0')])

   #enter this page from drill categories (player, instructor), or from Main (workflows)
   # a parameter (mode) indicates the if workflow or drills should be selected
   select_post_param = []
   filter_list = []
   drill_list = None
   page_title_str = "Select Drill"
   if request.args.get(ONCLICK_MODE_KEY) == ONCLICK_MODE_WORKOUT_VALUE:
      # select_post_param = {"name": ONCLICK_MODE_KEY, "value": ONCLICK_MODE_WORKOUT_VALUE}
      workout_select = True
      selection_list = []
      for workout_id in workout_list:
         # app.logger.debug(f"workout_id={workout_id} is of type {type(workout_id)}")
         workout_id_str = f"{workout_id:03}"
         if (fetch_into_workout_dict(workout_id_str)):
            selection_list.append({'id': workout_id_str, 'title': workouts_dict[workout_id_str]['name']})
         else:
            app.logger.error(f"WORK{workout_id_str} missing from workouts_dict; not including in choices")
      page_title_str = "Select Workout"
   else:
      workout_select = False
      # parse drill selection criteria to make list of drills:
      if ((drill_type_options.Group.name in request.form) and (request.form[drill_type_options.Group.name] == '1')):
         if (drill_type_options.Lines.name in request.form):
            # drill_list = globals()[request.form[drill_type_options.Lines.name]]
            drill_list = line_drill_dict[request.form[drill_type_options.Lines.name]]
         else:
            app.logger.error(f"request.form missing [drill_type_options.Lines.name]: using 1-line drills")
            drill_list = line_drill_dict['1-line']
      elif (drill_type_options.Focus.name in request.form):
         app.logger.debug(f"request.form[drill_type_options.Focus.name]={request.form[drill_type_options.Focus.name]}")
         if (request.form[drill_type_options.Focus.name] == str(focus_options.Movement.value)):
            drill_list = movement_drill_list
         elif (request.form[drill_type_options.Focus.name] == str(focus_options.Situational.value)):
            drill_list = situational_drill_list
         elif (request.form[drill_type_options.Focus.name] == str(focus_options.Development.value)):
            drill_list = stroketype_drill_dict[request.form[beep_options.Stroke.name]]
         else:
            app.logger.error(f"Unrecognized Drill Select Focus: {request.form[drill_type_options.Focus.name]}; using recent_drill_list")
            drill_list = recent_drill_list

      # app.logger.debug(f"Group test: drill_list={drill_list}; drill_list_name={request.form[drill_type_options.Lines.name]}")
      if drill_list is None:
         app.logger.error(f"Drill list was None after drill selection processing; using recent_drill_list")
         drill_list = recent_drill_list
         
      # now make drill selection list (array of ID & name dicts) from drill list
      selection_list = []
      for drill_id in drill_list:
         # app.logger.debug(f"drill_id={drill_id} is of type {type(drill_id)}")
         if len(selection_list) > 9: #limit to 10 entries
            break
         drill_id_str = f"{drill_id:03}"
         if (fetch_into_drills_dict(drill_id_str)):
            selection_list.append({'id': drill_id_str, 'title': drills_dict[drill_id_str]['name']})
         else:
            app.logger.error(f"DRL{drill_id_str} missing from drill_dict; not including in choices")

   page_js = [Markup('<script src="/static/js/get_drill_info.js"></script>')]

   return render_template(SELECT_TEMPLATE, \
      home_button = my_home_button, \
      page_title = page_title_str, \
      installation_icon = customization_dict['icon'], \
      url_for_post = DRILL_URL, \
      # the following doesn't work: the query parameter is now stripped by the browser.  TODO: remove from template
      # post_param = select_post_param, \
      choices = selection_list, \
      footer_center = customization_dict['title'], \
      page_specific_js = page_js
   )
 
@app.route(DRILL_URL, methods=DEFAULT_METHODS)
def drill():
   global beep_mode_choices
   global back_url, previous_url
   global workout_select
   global recent_drill_list
   back_url = previous_url

   send_settings_to_base(settings_dict)

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
   elif beep_options.Type.name in request.form:
      beep_type_value = int(request.form[ beep_options.Type.name])
      # beep drill mode
      #request_form: ImmutableMultiDict([('Type', '2'), ('Stroke', '5'), ('Difficulty', '2')])
      # for key in request.form:
      #    app.logger.info(f"Beep choice {key} = {request.form[key]}")
      # example beep drill ranges - consult the drills repository for the real thing:
      #mini-tennis: 901-905; volley: 906-910; 911-915 flat, 916-920 loop, 921-925 chip, 926-930 topspin, 931-935 random
      #set defaults if missing keys in form:
      stroke_type_offset = 0 #default to mini-tennis
      difficulty_offset = 2

      if beep_options.Difficulty.name in request.form:
         difficulty_offset = int(request.form[beep_options.Difficulty.name])
         # app.logger.info(f"beep_type={beep_type(beep_type_value).name}; Increasing id by {difficulty_offset}, e.g. {beep_difficulty(difficulty_offset).name}")
      else:
         app.logger.warning(f"Beep drill option: {beep_options.Difficulty.name} not in request.form")

      if beep_type_value is stroke_category.Volley.value:
         stroke_type_offset = 5

      if beep_type_value is stroke_category.Ground.value:
         if beep_options.Stroke.name in request.form:
            stroke_type = int(request.form[beep_options.Stroke.name])
         else:
            app.logger.warning(f"Beep drill option: {beep_options.Stroke.name} not in request.form")
            stroke_type = 1
         stroke_type_offset = (stroke_type * 5) + 10
         # app.logger.info(f"Ground beep type, so using stroke_type={beep_stroke(stroke_type).name}")

      id = BEEP_DRILL_NUMBER_START + difficulty_offset + stroke_type_offset
      app.logger.info(f"drill_id={id}: {stroke_category(beep_type_value).name}, difficulty_offset={difficulty_offset}, stroke_type_offset={stroke_type_offset}")
   else:
      app.logger.error("DRILL_URL - no drill or workout id!")
      mode_string = f"ERROR: no drill selected"

   drill_stepper_options = {}
   if id is not None:
      if not workout_select and beep_type_value is None:
         if (len(recent_drill_list) < 6):
            app.logger.error(f"recent_drill_list only had {len(recent_drill_list)} drills; restoring with defaults.")
            recent_drill_list = default_recents_drill_list
         # move to beginning of list
         if id in recent_drill_list:
            recent_drill_list.remove(id)
         recent_drill_list.insert(0,id)
         while len(recent_drill_list) > 10:
            recent_drill_list = recent_drill_list[:-1] #remove oldest drill_id
         # re-write recents file putting drill at top
         app.logger.debug(f"Updating '{recents_filename}' with {len(recent_drill_list)} drill ids.")
         try:
            with open(f'{settings_dir}/{recents_filename}', 'w') as f:
               json.dump(recent_drill_list, f)
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
      page_title = f"Running {mode_string}", \
      installation_icon = customization_dict['icon'], \
      stepper_options = drill_stepper_options, \
      footer_center = customization_dict['title'])


@app.route(BEEP_SELECTION_URL, methods=DEFAULT_METHODS)
def beep_selection():
   global beep_mode_choices

   # app.logger.info(f"beep_mode_choices: {beep_mode_choices}")

   page_js = []
   page_js.append(Markup('<script src="/static/js/radio-button-disable.js"></script>'))

   return render_template(GAME_OPTIONS_TEMPLATE,
      home_button = my_home_button, \
      page_title = "Select Type of Beep Drill", \
      installation_icon = customization_dict['icon'], \
      radio_options = beep_mode_choices, \
      url_for_post = DRILL_URL, \
      page_specific_js = page_js, \
      footer_center = customization_dict['title'])


@app.route(FAULTS_URL, methods=DEFAULT_METHODS)
def faults():
   global back_url, previous_url
   back_url = previous_url
   customization_dict = read_customization_file()

   return render_template(FAULTS_TEMPLATE, \
      page_title = "Problems Detected", \
      installation_icon = customization_dict['icon'], \
      footer_center = customization_dict['title'])


@app.route(DONE_URL, methods=DEFAULT_METHODS)
def done():

   result = "Finished"
   msg_ok, base_mode_register = send_msg(GET_METHOD, MODE_RSRC)
   if not msg_ok:
      app.logger.error(f"function '{sys._getframe(0).f_code.co_name}': GET STOP MODE_RSRC failed")
   else:
      result = f"{base_mode_e(base_mode_register[MODE_PARAM]).name.title()} Finished."
 
   return render_template(CHOICE_INPUTS_TEMPLATE, \
      page_title = result, \
      installation_icon = customization_dict['icon'], \
      onclick_choices = [{"value": "OK", "onclick_url": MAIN_URL}], \
      footer_center = customization_dict['title'])


@app.route('/favicon.ico')
def favicon():
   from os import path 
   return send_from_directory(path.join(app.root_path, 'static'),
                               'favicon.ico', mimetype='image/vnd.microsoft.icon')

@socketio.on('message')
def handle_message(data):
   app.logger.debug('received message: ' + data)
 
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
         # app.logger.debug(f'data[k] is not None; Setting: {k} to {data[k]}')
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

   base_state, soft_fault_status, faults_table = check_base()
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
         emit('faults_update', json.dumps(textify_faults_table(faults_table)))

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

   if (soft_fault_status is not None):
      update_dict['soft_fault'] = soft_fault_e(soft_fault_status).value

   if ("new_url" in update_dict):
      app.logger.info(f"Changing URL from '{current_page}' to {update_dict['new_url']} since base_state={base_state_e(base_state).name}")

   emit('state_update', update_dict)


def read_customization_file():
   try:
      with open(f'{settings_dir}/ui_customization.json') as f:
         customization_dict = json.load(f)
   except:
      customization_dict = {"title": "Boomer #1", "icon": "/static/favicon.ico"}
   return customization_dict


if __name__ == '__main__':
   # app.run(host="0.0.0.0", port=IP_PORT, debug = True)
   socketio.run(app, host="0.0.0.0", port=IP_PORT, debug = True)
   try:
      serve(app, host="0.0.0.0", port=IP_PORT)
      app.logger.info("started server")
   except Exception as e:
      print(e)
      sys.exit(1)
