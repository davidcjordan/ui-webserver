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
   send_stop_to_base()

   customization_dict = read_customization_file()
   settings_dict = read_settings_from_file()
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
      installation_icon = customization_dict['icon'], \
      onclick_choices = onclick_choice_list, \
      footer_center = customization_dict['title'])


@main.route(FAULTS_URL, methods=DEFAULT_METHODS)
def faults():
   return render_template(FAULTS_TEMPLATE, \
      page_title = "Problems Detected", \
      installation_icon = customization_dict['icon'], \
      footer_center = customization_dict['title'])


@main.route(SETTINGS_URL, methods=DEFAULT_METHODS)
def settings():
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


def read_customization_file():
   try:
      with open(f'{settings_dir}/ui_customization.json') as f:
         customization_dict = json.load(f)
   except:
      customization_dict = {"title": "Boomer #1", "icon": "/static/favicon.ico"}
   return customization_dict
