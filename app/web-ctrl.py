#!/usr/bin/env python3

#from flask import ? session, abort
from flask import Flask, render_template, Response, request, redirect, url_for, Markup, send_from_directory
try:
   from flask_socketio import SocketIO, emit
except:
   print("Missing package 'flask_socketio', please run: python3 -m pip install flask-socketio")
   exit()

import inspect
import os  # for sending favicon 

# the following requires: export PYTHONPATH='/Users/tom/Documents/Projects/Boomer/control_ipc_utils'
import sys
sys.path.append('/home/pi/repos/control_ipc_utils')
try:
   from ctrl_messaging_routines import send_msg, is_active
   from control_ipc_defines import *
except:
   print("Missing 'control_ipc' modules, please run: git clone https://github.com/manningt/control_ipc_utils")
   exit()

sys.path.append('/home/pi/boomer/drills')
try:
   from ui_drill_selection_lists import *
except:
   print("Missing 'ui_drill_selection_lists' modules, please run: git clone https://github.com/davidcjordon/drills")
   exit()

from threading import Thread
from subprocess import Popen
import time
import json
from random import randint

base_state = None
client_state = False

DO_SCP_FOR_CALIBRATION = False

IP_PORT = 1111 # picked what is hopefully an unused port  (can't use 44)
DEFAULT_METHODS = ['POST', 'GET']

MAIN_URL = '/'
GAME_OPTIONS_URL = '/game_options'
GAME_URL = '/game'
DRILL_SELECT_TYPE_URL = '/drill_select_type'
DRILL_SELECT_URL = '/drill_select' # does not have a template
DRILL_URL = '/drill'
CALIB_URL = '/calib'
CAM_POSITION_URL = '/cam_position'
# WORKOUT_SELECTION_URL = '/workout_selection'
# SETTINGS_URL = '/settings'

# Flask looks for following in the 'templates' directory
MAIN_TEMPLATE = 'index.html'
GAME_OPTIONS_TEMPLATE = '/layouts' + GAME_OPTIONS_URL + '.html'
GAME_TEMPLATE = '/layouts' + GAME_URL + '.html'
CHOICE_INPUTS_TEMPLATE = '/layouts' + '/choice_inputs' + '.html'
DRILL_SELECT_FILTERED_TEMPLATE = '/layouts' + '/drill_select_filtered' + '.html'
DRILL_SELECT_UNFILTERED_TEMPLATE = '/layouts' + '/drill_select_unfiltered' + '.html'
DRILL_TEMPLATE = '/layouts' + DRILL_URL + '.html'
CALIBRATION_TEMPLATE = '/layouts' + CALIB_URL + '.html'
CAM_POSITION_TEMPLATE = '/layouts' + CAM_POSITION_URL + '.html'
# WORKOUT_SELECTION_TEMPLATE = '/layouts' + WORKOUT_SELECTION_URL + '.html'
# SETTINGS_TEMPLATE = '/layouts' + SETTINGS_URL + '.html'

# base process status strings:
STATUS_NOT_RUNNING = "Down"
STATUS_RUNNING = "Running"
STATUS_NOT_RESPONDING = "Faulted"
STATUS_IDLE = "Idle"
STATUS_ACTIVE = "Active"
MODE_NONE = " --"
MODE_GAME = "Game --"
MODE_DRILL_NOT_SELECTED = "Drills --"
MODE_WORKOUT_NOT_SELECTED = "Workout --"
MODE_WORKOUT_SELECTED = "Workout: "
MODE_SETTINGS = "Boomer Options"

DRILL_SELECT_TYPE_PLAYER = 'Player(s)'
DRILL_SELECT_TYPE_INSTRUCTORS = 'Instructors'
DRILL_SELECT_TYPE_TEST ='Test'

previous_url = None
back_url = None

cam_side = None  # a global on which camera is being calibrated
cam_mm = [0]*3 # global camera location
X=0;Y=1;Z=2 # cam array enum
INCHES_TO_MM = 25.4

app = Flask(__name__)
app.config['SECRET_KEY'] = 'secret!'
# didn't find how to have multiple allowed origins
# socketio = SocketIO(app, cors_allowed_origins="https://cdnjs.cloudflare.com http://localhost")
# socketio = SocketIO(app, cors_allowed_origins="http://localhost")
# socketio = SocketIO(app, cors_allowed_origins="http://127.0.0.1")
socketio = SocketIO(app, cors_allowed_origins="*")

@app.route(CAM_POSITION_URL, methods=DEFAULT_METHODS)
def cam_position():
   try:
      with open("/home/pi/boomer/site_data/left_cam_location.json") as infile:
         loc_dict = json.load(infile)
   except:
      # default values if not persisted from a previous calibration
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
      installation_title = custom_installation_title, \
      installation_icon = custom_installation_icon, \
      options = position_options, \
      footer_center = "Mode: " + "Get Cam Position")


@app.route(CALIB_URL, methods=DEFAULT_METHODS)
def calib():
   global cam_side, cam_mm, X, Y, Z
   cam_side = "Left"
   loc_dict = {}
   if request.method=='POST':
      print(f"POST to CALIB request.form: {request.form}")
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
         with open(f"/home/pi/boomer/site_data/{cam_side.lower()}_cam_location.json", "w") as outfile:
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
      print(f"scp of camera's frame.png to court.png failed: {p.returncode}")
   # status = os.waitpid(p.pid, 0)

   return render_template(CALIBRATION_TEMPLATE, \
      court_pic = "static/" + cam_lower + "_court.png", \
      home_button = my_home_button, \
      installation_title = custom_installation_title, \
      installation_icon = custom_installation_icon, \
      footer_center = "Mode: " + mode_str)


@app.route('/calib_done', methods=DEFAULT_METHODS)
def calib_done():
   global cam_side, cam_mm, X, Y, Z
   if request.method=='POST':
      if (request.content_type.startswith('application/json')):
         print(f"request to calib: {request.json}")
         # request.json example: {'fblx': 883, 'fbly': 77, 'fbrx': 1193, 'fbry': 91,\
         #  'nslx': 503, 'nsly': 253, 'nscx': 747, 'nscy': 289, 'nsrx': 1065, 'nsry': 347,\
         #  'nblx': 187, 'nbly': 397, 'nbrx': 933, 'nbry': 653}
         c = request.json
         if cam_side.lower() == "left":
            cam_arg = "--left"
         else:
            cam_arg = "--right"
         coord_args = (f"--fblx {c['fblx']} --fbly {c['fbly']}"
            f" --fbrx {c['fbrx']} --fbry {c['fbry']} --nblx {c['nblx']} --nbly {c['nbly']}"
            f" --nbrx {c['nbrx']} --nbry {c['nbry']} --nslx {c['nslx']} --nsly {c['nsly']}"
            f" --nscx {c['nscx']} --nscy {c['nscy']} --nsrx {c['nsrx']} --nsry {c['nsry']}"
            f" --camx {cam_mm[X]} --camy {cam_mm[Y]} --camz {cam_mm[Z]}" )
         cmd = "/home/pi/boomer/staged/gen_cam_params.out " + cam_arg + " " + coord_args
         # p = Popen(["/home/pi/boomer/staged/gen_cam_params.out", cam_arg, f"--fblx {c['fblx']}", f"--fbly {c['fbly']}", \
         #    f"--fbrx {c['fbrx']}", f"--fbry {c['fbry']}", f"--nblx {c['nblx']}", f"--nbly {c['nbly']}", \
         #    f"--nbrx {c['nbrx']}", f"--nbry {c['nbry']}", f"--nslx {c['nslx']}", f"--nsly {c['nsly']}", \
         #    f"--nscx {c['nscx']}", f"--nscy {c['nscy']}", f"--nsrx {c['nsrx']}", f"--nsry {c['nsry']}",  \
         #    f"--camx {cam_mm[X]}", f"--camy {cam_mm[Y]}", f"--camz {cam_mm[Z]}" ])
         p = Popen(cmd, shell=True)
         stdoutdata, stderrdata = p.communicate()
         if p.returncode != 0:
            print(f"gen_cam_params failed: {p.returncode}")
         else:
            print("TODO: send parameters.txt, restart the cam, reload the param on the base")

         # after javascript does the post, it redirects to calib_done
      else:
         print("Recieved a non-json POST at calib_done")
 
   button_label = cam_side + " Calib Done"
   choice_list = [\
      {"value": button_label, "onclick_url": MAIN_URL}
   ]
   return render_template(CHOICE_INPUTS_TEMPLATE, \
      home_button = my_home_button, \
      installation_title = custom_installation_title, \
      installation_icon = custom_installation_icon, \
      onclick_choices = choice_list, \
      footer_center = "Mode: " + button_label)

 
@app.route(MAIN_URL, methods=DEFAULT_METHODS)
def index():
   global back_url, previous_url
   back_url = previous_url = "/"

   onclick_choice_list = [\
      {"value": "Game Mode", "onclick_url": GAME_OPTIONS_URL},\
      {"value": "Drills", "onclick_url": DRILL_SELECT_TYPE_URL},\
      {"value": "Cam Calibration", "onclick_url": CAM_POSITION_URL}\
   ]
   # form_choice_list = [\
   #    {"value": "Left Cam Calib"},\
   #    {"value": "Right Cam Calib"}\
   # ]

   return render_template(CHOICE_INPUTS_TEMPLATE, \
      installation_title = custom_installation_title, \
      installation_icon = custom_installation_icon, \
      onclick_choices = onclick_choice_list, \
      # form_choices = form_choice_list, \
      url_for_post = CALIB_URL, \
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

@app.route(GAME_OPTIONS_URL, methods=DEFAULT_METHODS)
def game_options():
   # clicking stop when the game is active goes to this page, so stop the game
   rc, code = send_msg(PUT_METHOD, STOP_RSRC)
   if not rc:
      app.logger.error("PUT STOP failed, code: {}".format(code))

   global back_url, previous_url
   back_url = '/'
   previous_url = "/" + inspect.currentframe().f_code.co_name
   return render_template(GAME_OPTIONS_TEMPLATE, \
      home_button = my_home_button, \
      installation_title = custom_installation_title, \
      installation_icon = custom_installation_icon, \
      optional_form_begin = Markup('<form action ="' + GAME_URL + '" method="post">'), \
      optional_form_end = Markup('</form>'), \
      point_delay_dflt = GAME_POINT_DELAY_DEFAULT, \
      point_delay_min = GAME_POINT_DELAY_MIN, \
      point_delay_max = GAME_POINT_DELAY_MAX, \
      point_delay_step = GAME_POINT_DELAY_STEP, \
      footer_center = "Mode: " + MODE_GAME)

@app.route(GAME_URL, methods=DEFAULT_METHODS)
def game():
   global back_url, previous_url
   back_url = previous_url

   # print("{} on {}, data: {}".format(request.method, inspect.currentframe().f_code.co_name, request.data))
   if request.method=='POST':
      if 'serve_mode' in request.form:
         print("serve_mode: {}".format(request.form['serve_mode']))
      if 'scoring' in request.form:
         print("scoring: {}".format(request.form['scoring']))
      if 'running' in request.form:
         print("running: {}".format(request.form['running']))
      if 'point_delay' in request.form:
         print("point_delay: {}".format(request.form['point_delay']))
      if 'grunts' in request.form:
         print("grunts: {}".format(request.form['grunts']))
      
   return render_template(GAME_TEMPLATE, \
      installation_title = custom_installation_title, \
      installation_icon = custom_installation_icon, \
      level_dflt = LEVEL_DEFAULT/LEVEL_UI_FACTOR, \
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

   drill_select_type_list = [\
      {'value': DRILL_SELECT_TYPE_PLAYER},\
      {'value': DRILL_SELECT_TYPE_INSTRUCTORS},\
      {'value': DRILL_SELECT_TYPE_TEST},\
   ]

   return render_template(CHOICE_INPUTS_TEMPLATE, \
      home_button = my_home_button, \
      installation_title = custom_installation_title, \
      installation_icon = custom_installation_icon, \
      form_choices = drill_select_type_list, \
      url_for_post = DRILL_SELECT_URL, \
      footer_center = "Mode: " + MODE_DRILL_NOT_SELECTED)


@app.route(DRILL_SELECT_URL, methods=DEFAULT_METHODS)
def drill_select():
   global back_url, previous_url
   back_url = '/'
   previous_url = "/" + inspect.currentframe().f_code.co_name

   drill_select_type = None
   if request.method=='POST':
      print(f"request_form_getlist_type: {request.form.getlist('choice')}")
      drill_select_type = request.form.getlist('choice')[0]

   # refer to /home/pi/boomer/drills/ui_drill_selection_lists for drill_list format
   if drill_select_type == DRILL_SELECT_TYPE_TEST:
      drill_list = drill_list_test
   elif drill_select_type == DRILL_SELECT_TYPE_INSTRUCTORS:
      drill_list = drill_list_instructor
   else:
      drill_list = drill_list_player

   if len(drill_list[0]) > 2:
      return render_template(DRILL_SELECT_FILTERED_TEMPLATE, \
         home_button = my_home_button, \
         installation_title = custom_installation_title, \
         installation_icon = custom_installation_icon, \
         optional_form_begin = Markup('<form action ="' + DRILL_URL + '" method="post">'), \
         drills = drill_list, \
         optional_form_end = Markup('</form>'), \
         footer_center = "Mode: " + MODE_DRILL_NOT_SELECTED)
   else:
      return render_template(DRILL_SELECT_UNFILTERED_TEMPLATE, \
         home_button = my_home_button, \
         installation_title = custom_installation_title, \
         installation_icon = custom_installation_icon, \
         optional_form_begin = Markup('<form action ="' + DRILL_URL + '" method="post">'), \
         drills = drill_list, \
         optional_form_end = Markup('</form>'), \
         footer_center = "Mode: " + MODE_DRILL_NOT_SELECTED)


@app.route(DRILL_URL, methods=DEFAULT_METHODS)
def drill():
   global back_url, previous_url
   back_url = previous_url

   print("request_form: {}".format(request.form))

   mode_string = "FIX-ME"
   if request.method=='POST' and 'drill_id' in request.form:
      mode_string = "'" + request.form['drill_id'] + "'" + " Drill"
      mode = {MODE_PARAM: DRILL_MODE_E, ID_PARAM: request.form['drill_id']}
      rc, code = send_msg(PUT_METHOD, MODE_RSRC, mode)
      if not rc:
         app.logger.error("PUT Mode failed, code: {}".format(code))
      else:
         rc, code = send_msg(PUT_METHOD, STRT_RSRC)
         if not rc:
            app.logger.error("PUT START failed, code: {}".format(code))

   
   stepper_options = { \
      "level":{"legend":"Level", "dflt":LEVEL_DEFAULT/LEVEL_UI_FACTOR, "min":LEVEL_MIN/LEVEL_UI_FACTOR, \
         "max":LEVEL_MAX/LEVEL_UI_FACTOR, "step":LEVEL_UI_STEP/LEVEL_UI_FACTOR}, \
      "speed":{"legend":"Speed", "dflt":SPEED_DEFAULT, "min":SPEED_MIN, "max":SPEED_MAX, "step":SPEED_STEP}, \
      "delay":{"legend":"Delay", "dflt":DELAY_DEFAULT/DELAY_UI_FACTOR, "min":DELAY_MIN/DELAY_UI_FACTOR, \
         "max":DELAY_MAX/DELAY_UI_FACTOR, "step":DELAY_UI_STEP/DELAY_UI_FACTOR}, \
      "height":{"legend":"Height", "dflt":HEIGHT_DEFAULT, "min":HEIGHT_MIN, "max":HEIGHT_MAX, "step":HEIGHT_STEP} \
   }
         
   previous_url = "/" + inspect.currentframe().f_code.co_name
   return render_template(DRILL_TEMPLATE, \
      installation_title = custom_installation_title, \
      installation_icon = custom_installation_icon, \
      options = stepper_options, \
      footer_center = "Mode: " + mode_string)


@app.route('/favicon.ico')
def favicon():
    return send_from_directory(os.path.join(app.root_path, 'static'),
                               'favicon.ico', mimetype='image/vnd.microsoft.icon')

@socketio.on('message')
def handle_message(data):
    print('received message: ' + data)

@socketio.on('change_params')     # Decorator to catch an event named change_params
def handle_change_params(data):          # change_params() is the event callback function.
    print('change_params data: ', data)      # data is a json string: {"speed":102}
    item_to_change = json.loads(data)
    print('change opts: {}'.format(item_to_change))
    # send_msg(PUT_METHOD, OPTS_RSRC, item_to_change)

@socketio.on('pause')
def handle_pause():
    print('received pause.')

@socketio.on('resume')
def handle_resume():
    print('received resume.')

@socketio.on('get_updates')
def handle_get_updates(data):
   # print('get_updates data: ', data)
   json_data = json.loads(data)
   # print(f"json_data: {json_data}")
   if (("page" in json_data) and (json_data["page"] == "game")):
      emit('state_update', {"base_state": base_state, "pp": randint(0,3), \
         "bp": 1, "pg": 3, "bg": 2, "ps": 5, "bs": 4, "pt": 6, "bt": 7, "server": "b"})
   else:
      emit('state_update', {"base_state": base_state})


def check_base(process_name):
   global base_state, client_state, socketio
   while True:
      base_pid = os.popen(f"pgrep {process_name}").read()
      #base_pid is empty if base is not running
      if base_pid:
         # verify responding to FIFO
         base_state_tmp = is_active()
         if base_state_tmp:
            base_state = STATUS_ACTIVE
         elif (base_state_tmp == False):
            base_state = STATUS_IDLE
         else:
            base_state = STATUS_NOT_RESPONDING
      else:
         base_state = STATUS_NOT_RUNNING
      # the following didn't work: the emit didn't get to the client
      # if client_state:
      #    print(f"emitting: {{'base_state_update', {{\"base_state\": \"{base_state}\"}}}}")
      #    socketio.emit('base_state_update', {"base_state": base_state})
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

   # TODO: customize header from a file
   custom_installation_title = "Red Oak Sports Club  --  Boomer 1"
   custom_installation_icon = "/static/red-oaks-icon.png"
   my_home_button = Markup('          <button type="submit" onclick="window.location.href=\'/\';"> \
            <img src="/static/home.png" style="height:64px;"> \
          </button>')

   # app.run(host="0.0.0.0", port=IP_PORT, debug = True)
   socketio.run(app, host="0.0.0.0", port=IP_PORT, debug = True)

   check_base_thread.join()
