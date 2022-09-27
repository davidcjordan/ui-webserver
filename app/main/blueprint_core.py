# from flask-socketio-chat:
# from flask import session, redirect, url_for, render_template, request
# from web-ctrl:
# from flask import Flask, render_template, Response, request, redirect, url_for, Markup, send_from_directory

from flask import render_template, request, Markup, send_from_directory, Blueprint, current_app #, url_for
import json

# print(f"blueprint_core_name={__name__}") = app.main.blueprint_core
blueprint_core = Blueprint('blueprint_core', __name__)

from app.main.defines import *
from app.func_base import send_stop_to_base
# from app.func_drills import *

import sys
sys.path.append(f'{user_dir}/{repos_dir}/control_ipc_utils')
try:
   from control_ipc_defines import *
except:
   current_app.logger.error("Problems with 'control_ipc' modules, please run: git clone https://github.com/davidcjordan/control_ipc_utils")
   exit()

workout_select = False

display_customization_dict = {}
base_settings_dict = {}


@blueprint_core.route('/favicon.ico')
def favicon():
   from os import path 
   return send_from_directory(path.join(main.root_path, 'static'),
                               'favicon.ico', mimetype='image/vnd.microsoft.icon')


@blueprint_core.route(MAIN_URL, methods=DEFAULT_METHODS)
def index():
   # global html_horizontal_rule

   # current_app.logger.debug(f"Test of printing function name: in function: {sys._getframe(0).f_code.co_name}")

   # clicking stop on the game_url & drill_url goes to main/home/index, so issue stop.
   send_stop_to_base()

   # if 'customization_dict' not in globals():
   #    current_app.logger.error("customization_dict not in globals()")
   # else:
   #    current_app.logger.debug("customization_dict is in globals()")
   # if 'customization_dict' not in locals():
   #    current_app.logger.debug("customization_dict not in locals()")
   # else:
   #    current_app.logger.debug("customization_dict is in locals()")

   global display_customization_dict 
   # get an unbound error if customization_dict is not declared global
   if 'icon' not in display_customization_dict:
      current_app.logger.debug("reading in customization_dict")
      display_customization_dict = read_display_customization_file()

   global base_settings_dict 
   if GRUNTS_PARAM not in base_settings_dict:
      base_settings_dict = read_base_settings_from_file()
   # update the base settings can happen at game/drill start:
   # send_settings_to_base(settings_dict)

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
      installation_icon = display_customization_dict['icon'], \
      onclick_choices = onclick_choice_list, \
      footer_center = display_customization_dict['title'])


@blueprint_core.route(FAULTS_URL, methods=DEFAULT_METHODS)
def faults():
   if 'icon' not in display_customization_dict:
      read_display_customization_file()

   return render_template(FAULTS_TEMPLATE, \
      page_title = "Problems Detected", \
      installation_icon = display_customization_dict['icon'], \
      footer_center = display_customization_dict['title'])


@blueprint_core.route(SETTINGS_URL, methods=DEFAULT_METHODS)
def settings():
   global base_settings_dict 

   # value is the label of the button
   onclick_choice_list = [\
      {"html_before": "Check:", \
         "value": "Cameras", "onclick_url": CAM_VERIF_URL, "html_after": html_horizontal_rule}, \
      {"html_before": "Calibrate:", \
         "value": "Thrower", "onclick_url": THROWER_CALIB_SELECTION_URL}, \
      {"value": "Left Camera", "onclick_url": CAM_LOCATION_URL, "param_name": CAM_SIDE_ID, "param_value": CAM_SIDE_LEFT_LABEL}, \
      {"value": "Right Cam", "onclick_url": CAM_LOCATION_URL, "param_name": CAM_SIDE_ID, "param_value": CAM_SIDE_RIGHT_LABEL, \
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

   settings_radio_options[0]['buttons'][base_settings_dict[GRUNTS_PARAM]]['checked'] = 1
   settings_radio_options[1]['buttons'][base_settings_dict[TRASHT_PARAM]]['checked'] = 1
   
   page_js = [Markup('<script src="/static/js/radio-button-emit.js"></script>')]

   return render_template(CHOICE_INPUTS_TEMPLATE, \
      home_button = my_home_button, \
      page_title = "Change Settings or Perform Calibration", \
      installation_icon = display_customization_dict['icon'], \
      onclick_choices = onclick_choice_list, \
      radio_options = settings_radio_options, \
      page_specific_js = page_js, \
      footer_center = display_customization_dict['title'])


def read_display_customization_file():
   try:
      with open(f'{settings_dir}/ui_customization.json') as f:
         customization_dict = json.load(f)
   except:
      customization_dict = {"title": "Boomer #1", "icon": "/static/favicon.ico"}
   return customization_dict


def read_base_settings_from_file():
   try:
      with open(f'{settings_dir}/{settings_filename}') as f:
         settings_dict = json.load(f)
         # current_app.logger.debug(f"Settings restored: {settings_dict}")
   except:
      current_app.logger.warning(f"Settings file read failed; using defaults.")
      settings_dict = {GRUNTS_PARAM: 0, TRASHT_PARAM: 0, LEVEL_PARAM: LEVEL_DEFAULT, \
            SERVE_MODE_PARAM: 1, TIEBREAKER_PARAM: 0, \
            SPEED_MOD_PARAM: SPEED_MOD_DEFAULT, DELAY_MOD_PARAM: DELAY_MOD_DEFAULT, \
            ELEVATION_MOD_PARAM: ELEVATION_ANGLE_MOD_DEFAULT}
   return settings_dict


def write_base_settings_to_file():
   try:
      with open(f'{settings_dir}/{settings_filename}', 'w') as f:
            json.dump(base_settings_dict, f)
         # current_app.logger.debug(f"Settings written: {settings_dict}")
   except:
      current_app.logger.error(f"Settings file write failed.")
