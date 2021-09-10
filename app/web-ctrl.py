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

from threading import Thread
import time
import json
from random import randint

base_state = None
client_state = False

IP_PORT = 1111 # picked what is hopefully an unused port  (can't use 44)
DEFAULT_METHODS = ['POST', 'GET']

MAIN_URL = '/'
GAME_OPTIONS_URL = '/game_options'
GAME_URL = '/game'
DRILL_SELECT_TYPE_URL = '/drill_select_type'
DRILL_SELECT_PLAYER_URL = '/drill_select_player'
DRILL_SELECT_INSTRUCTOR_URL = '/drill_select_instructor'
DRILL_SELECT_TEST_URL = '/drill_select_test'
DRILL_URL = '/drill'
# WORKOUT_SELECTION_URL = '/workout_selection'
# SETTINGS_URL = '/settings'

# Flask looks for following in the 'templates' directory
MAIN_TEMPLATE = 'index.html'
GAME_OPTIONS_TEMPLATE = '/layouts' + GAME_OPTIONS_URL + '.html'
GAME_TEMPLATE = '/layouts' + GAME_URL + '.html'
DRILL_SELECT_TYPE_TEMPLATE = '/layouts' + DRILL_SELECT_TYPE_URL + '.html'
DRILL_SELECT_PLAYER_TEMPLATE = '/layouts' + DRILL_SELECT_PLAYER_URL + '.html'
DRILL_SELECT_INSTRUCTOR_TEMPLATE = '/layouts' + DRILL_SELECT_INSTRUCTOR_URL + '.html'
DRILL_SELECT_TEST_TEMPLATE = '/layouts' + DRILL_SELECT_TEST_URL + '.html'
DRILL_TEMPLATE = '/layouts' + DRILL_URL + '.html'
CALIBRATION_TEMPLATE = '/layouts/calib.html'
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

previous_url = None
back_url = None


app = Flask(__name__)
app.config['SECRET_KEY'] = 'secret!'
# didn't find how to have multiple allowed origins
# socketio = SocketIO(app, cors_allowed_origins="https://cdnjs.cloudflare.com http://localhost")
# socketio = SocketIO(app, cors_allowed_origins="http://localhost")
# socketio = SocketIO(app, cors_allowed_origins="http://127.0.0.1")
socketio = SocketIO(app, cors_allowed_origins="*")

@app.route('/calib', methods=DEFAULT_METHODS)
def calib():
   # if request.method=='POST':
   #    if 'serve_mode' in request.form:

    return render_template(CALIBRATION_TEMPLATE, \
      home_button = my_home_button, \
      installation_title = custom_installation_title, \
      installation_icon = custom_installation_icon, \
      footer_left = "Status: " + STATUS_IDLE, \
      footer_center = "Mode: " + "Calibration")
 
@app.route(MAIN_URL, methods=DEFAULT_METHODS)
def index():
   global back_url, previous_url
   back_url = previous_url = "/"
   
   return render_template(MAIN_TEMPLATE, \
      installation_title = custom_installation_title, \
      installation_icon = custom_installation_icon, \
      footer_left = "Status: Idle", \
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
      footer_left = "Status: " + STATUS_IDLE, \
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
      footer_left = "Status: " + STATUS_ACTIVE, \
      footer_center = "Mode: " + MODE_GAME)


@app.route(DRILL_SELECT_TYPE_URL, methods=DEFAULT_METHODS)
def drill_select_type():

   return render_template(DRILL_SELECT_TYPE_TEMPLATE, \
      home_button = my_home_button, \
      installation_title = custom_installation_title, \
      installation_icon = custom_installation_icon, \
      footer_left = "Status: " + STATUS_IDLE, \
      footer_center = "Mode: " + MODE_DRILL_NOT_SELECTED)


@app.route(DRILL_SELECT_PLAYER_URL, methods=DEFAULT_METHODS)
def drill_select_player():
   global back_url, previous_url
   back_url = '/'
   previous_url = "/" + inspect.currentframe().f_code.co_name

   from drill_titles_player import drill_list

   return render_template(DRILL_SELECT_PLAYER_TEMPLATE, \
      home_button = my_home_button, \
      installation_title = custom_installation_title, \
      installation_icon = custom_installation_icon, \
      optional_form_begin = Markup('<form action ="' + DRILL_URL + '" method="post">'), \
      drills = drill_list, \
      optional_form_end = Markup('</form>'), \
      footer_left = "Status: " + STATUS_IDLE, \
      footer_center = "Mode: " + MODE_DRILL_NOT_SELECTED)


@app.route(DRILL_SELECT_INSTRUCTOR_URL, methods=DEFAULT_METHODS)
def drill_select_instructor():
   global back_url, previous_url
   back_url = '/'
   previous_url = "/" + inspect.currentframe().f_code.co_name

   # The following is to be replaced with fetching from a database of drills based on tags
   # drill_d = {}
   # drill_d["001"] = {"name": "speed", "type":"movement", "lvl": "medium", "stroke": "forehand" }
   # drill_d["002"] = {"name": "1-line 5 ball net", "type":"net", "lvl": "easy", "stroke": "backhand" }
   # drill_d["003"] = {"name": "Volley Kill footwork", "type":"volley, movement", "lvl": "hard", "stroke": "forehand" }

   drill_list = [\
      {'id': '001', 'name': 'speed'},\
      {'id': '002', 'name': '1-line 5 ball net'},\
      {'id': '003', 'name': 'Volley Kill footwork'},\
   ]
   # TODO change the following to: DRILL_SELECT_INSTRUCTOR_TEMPLATE
   return render_template(DRILL_SELECT_TEST_TEMPLATE, \
      home_button = my_home_button, \
      installation_title = custom_installation_title, \
      installation_icon = custom_installation_icon, \
      optional_form_begin = Markup('<form action ="' + DRILL_URL + '" method="post">'), \
      drills = drill_list, \
      optional_form_end = Markup('</form>'), \
      footer_left = "Status: " + STATUS_IDLE, \
      footer_center = "Mode: " + MODE_DRILL_NOT_SELECTED)


@app.route(DRILL_SELECT_TEST_URL, methods=DEFAULT_METHODS)
def drill_select_test():
   global back_url, previous_url
   back_url = '/'
   previous_url = "/" + inspect.currentframe().f_code.co_name

   from drill_titles_test import drill_list

   return render_template(DRILL_SELECT_TEST_TEMPLATE, \
      home_button = my_home_button, \
      installation_title = custom_installation_title, \
      installation_icon = custom_installation_icon, \
      optional_form_begin = Markup('<form action ="' + DRILL_URL + '" method="post">'), \
      drills = drill_list, \
      optional_form_end = Markup('</form>'), \
      footer_left = "Status: " + STATUS_IDLE, \
      footer_center = "Mode: " + MODE_DRILL_NOT_SELECTED)


@app.route(DRILL_URL, methods=DEFAULT_METHODS)
def drill():
   global back_url, previous_url
   back_url = previous_url

   # print("request_form: {}".format(request.form))

   mode_string = "FIX-ME"
   if request.method=='POST' and 'drill_id' in request.form:
      mode_string = "'" + request.form['drill_id'] + "'" + " Drill"
      mode = {MODE_PARAM: DRILL_MODE_E, ID_PARAM: request.form['drill_id']}
      rc, code = send_msg(PUT_METHOD, MODE_RSRC, mode)
      if not rc:
         app.logger.error("PUT Mode failed, code: {}".format(code))
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
      footer_left = "Status: " + STATUS_ACTIVE, \
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
   emit('base_state_update', {"base_state": base_state})
   # could combine the 2 emits, but it's more parsing work...
   if (("page" in json_data) and (json_data["page"] == "game")):
      emit('score_update', {"pp": randint(0,3), \
         "bp": 1, "pg": 3, "bg": 2, "ps": 5, "bs": 4, "pt": 6, "bt": 7, "server": "b"})


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
