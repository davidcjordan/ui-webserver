# from flask-socketio-chat:
# from flask import session, redirect, url_for, render_template, request
# from web-ctrl:
# from flask import Flask, render_template, Response, request, redirect, url_for, Markup, send_from_directory

from flask import render_template, request, url_for, Markup, send_from_directory
from . import main

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


my_home_button = Markup('          <button type="submit" onclick="window.location.href=\'/\';"> \
         <img src="/static/home.png" style="height:64px;" alt="Home"> \
         </button>')
html_horizontal_rule =  Markup('<hr>')

DEFAULT_METHODS = ['POST', 'GET']
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

ONCLICK_MODE_KEY = 'mode'
ONCLICK_MODE_WORKOUT_VALUE = 'workouts'

workout_select = False


@main.route('/favicon.ico')
def favicon():
   from os import path 
   return send_from_directory(path.join(main.root_path, 'static'),
                               'favicon.ico', mimetype='image/vnd.microsoft.icon')


@main.route(MAIN_URL, methods=DEFAULT_METHODS)
def index():
   global html_horizontal_rule
   global customization_dict, settings_dict 

   # current_app.logger.debug(f"Test of printing function name: in function: {sys._getframe(0).f_code.co_name}")

   # clicking stop on the game_url & drill_url goes to main/home/index, so issue stop.
   rc, code = send_msg(PUT_METHOD, STOP_RSRC)
   if not rc:
      current_app.logger.error(f"function '{sys._getframe(0).f_code.co_name}': PUT STOP failed, code: {code}")

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


@main.route(FAULTS_URL, methods=DEFAULT_METHODS)
def faults():
   return render_template(FAULTS_TEMPLATE, \
      page_title = "Problems Detected", \
      installation_icon = customization_dict['icon'], \
      footer_center = customization_dict['title'])



def read_customization_file():
   try:
      with open(f'{settings_dir}/ui_customization.json') as f:
         customization_dict = json.load(f)
   except:
      customization_dict = {"title": "Boomer #1", "icon": "/static/favicon.ico"}
   return customization_dict
