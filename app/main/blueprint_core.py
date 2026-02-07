# from flask-socketio-chat:
# from flask import session, redirect, url_for, render_template, request
# from web-ctrl:
# from flask import Flask, render_template, Response, request, redirect, url_for, Markup, send_from_directory

from flask import render_template, request, Markup, send_from_directory, Blueprint, current_app #, url_for
import json
import os.path

# print(f"blueprint_core_name={__name__}") = app.main.blueprint_core
blueprint_core = Blueprint('blueprint_core', __name__)

from app.main.defines import *
from app.func_base import send_stop_to_base, send_settings_to_base

import sys
sys.path.append(f'{user_dir}/{repos_dir}/control_ipc_utils')
try:
   from control_ipc_defines import *
except:
   current_app.logger.error("Problems with 'control_ipc' modules, please run: git clone https://github.com/davidcjordan/control_ipc_utils")
   exit()


def read_display_customization_file():
   try:
      with open(f'{settings_dir}/ui_customization.json') as f:
         customization_dict = json.load(f)
   except:
      customization_dict = {"title": "", "icon": "/static/favicon.ico"}
   return customization_dict

def read_base_settings_from_file():
   try:
      with open(f'{settings_dir}/{settings_filename}') as f:
         settings_dict = json.load(f)
         # current_app.logger.debug(f"Settings restored: {settings_dict}")
   except:
      current_app.logger.warning(f"Read of '{settings_dir}/{settings_filename}' failed; using defaults.")
      settings_dict = {GRUNTS_PARAM: 0, TRASHT_PARAM: 0, LEVEL_PARAM: LEVEL_DEFAULT, \
            SERVE_MODE_PARAM: 1, TIEBREAKER_PARAM: 0, \
            SPEED_MOD_PARAM: SPEED_MOD_DEFAULT, DELAY_MOD_PARAM: DELAY_MOD_DEFAULT, \
            ELEVATION_MOD_PARAM: ELEVATION_ANGLE_MOD_DEFAULT,
            CONTINUOUS_MOD_PARAM: 0, ADVANCED_GAME_PARAM: 0}
   # !! need to add defaults to new settings as they are added:
   if CONTINUOUS_MOD_PARAM not in settings_dict:
      settings_dict[CONTINUOUS_MOD_PARAM] = 0
   if ADVANCED_GAME_PARAM not in settings_dict:
      settings_dict[ADVANCED_GAME_PARAM] = 0
   return settings_dict

display_customization_dict = read_display_customization_file()
base_settings_dict = read_base_settings_from_file()


@blueprint_core.route('/favicon.ico')
def favicon():
   from os import path 
   return send_from_directory(path.join(current_app.root_path, 'static'),
                               'favicon.ico', mimetype='image/vnd.microsoft.icon')


@blueprint_core.route(MAIN_URL, methods=DEFAULT_METHODS)
def index():

   # current_app.logger.debug(f"Test of printing function name: in function: {sys._getframe(0).f_code.co_name}")

   # clicking stop on the game_url & drill_url goes to main/home/index, so issue stop.
   send_stop_to_base()

   # clear the previous drill id ; there wasn't a central place to clear it in blueprint_drills.py
   set_previous_drill_id(None)

   global display_customization_dict 
   # get an unbound error if customization_dict is not declared global
   if 'icon' not in display_customization_dict:
      current_app.logger.debug("reading in customization_dict")
      display_customization_dict = read_display_customization_file()

   global base_settings_dict 
   if GRUNTS_PARAM not in base_settings_dict:
      base_settings_dict = read_base_settings_from_file()
   # updating the base settings (drill/game) occurs at game/drill start:
   # send settings to base also happens here (index) so that the settings are updated when the base is restarted
   send_settings_to_base(base_settings_dict)
   current_app.logger.info("sent base settings to base")

   # example of setting button disabled and a button ID
   # TODO: fix disable CSS
   # onclick_choices = [{"value": button_label, "onclick_url": MAIN_URL, "disabled": 1, "id": "Done"}], \

   onclick_choice_list = [\
      {"html_before": "Game:", "value": "Play", "onclick_url": GAME_URL, "id": "game_button"},\
      {"value": "Settings", "onclick_url": GAME_OPTIONS_URL, "id": "game_settings", "html_after": html_horizontal_rule},\
      # {"value": "Help", "id": "game_help_button", "html_after": html_horizontal_rule},\
      {"html_before": "Drill:", "value": "Recents", "onclick_url": RECENTS_URL},\
      {"value": "Select", "onclick_url": DRILL_LIST_URL, "html_after": html_horizontal_rule},\
      {"value": "Workouts", "onclick_url": SELECT_WORKOUT_URL, "html_after": html_horizontal_rule}, \
      {"value": "Settings", "onclick_url": SETTINGS_URL}
   ]

   # page_js = [Markup('<script src="/static/js/game_help.js" defer></script>')]

   # added try/except because sometimes the display_custom_dict seems to be missing - this is a workaround to avoid a web server fault
   try:
      this_template = render_template(CHOICE_INPUTS_TEMPLATE, \
         page_title = "Welcome to Boomer", \
         installation_icon = display_customization_dict['icon'], \
         onclick_choices = onclick_choice_list, \
         # page_specific_js = page_js, \
         footer_center = display_customization_dict['title'])
   except:
      this_template = render_template(CHOICE_INPUTS_TEMPLATE, \
         page_title = "Welcome to Boomer", \
         onclick_choices = onclick_choice_list)
      
   return this_template


@blueprint_core.route(FAULTS_URL, methods=DEFAULT_METHODS)
def faults():
   if 'icon' not in display_customization_dict:
      read_display_customization_file()

   return render_template(FAULTS_TEMPLATE, \
      page_title = "Problems Detected")
      # installation_icon = display_customization_dict['icon'], \
      # footer_center = display_customization_dict['title'])


@blueprint_core.route(SETTINGS_URL, methods=DEFAULT_METHODS)
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

   # intermittently, the code will get here without the reading the base_settings being loaded.
   # so the following are defensive, in addition to the try/except around the 'checked' statements
   if GRUNTS_PARAM not in base_settings_dict or ELEVATION_MOD_PARAM not in base_settings_dict:
      current_app.logger.warning(f"GRUNTS_PARAM not in base_settings_dict; re-reading base_settings")
      read_base_settings_from_file()

   if GRUNTS_PARAM not in base_settings_dict:
      current_app.logger.error(f"GRUNTS_PARAM not in base_settings_dict AFTER re-reading base_settings")

   try:
      settings_radio_options[0]['buttons'][base_settings_dict[GRUNTS_PARAM]]['checked'] = 1
      settings_radio_options[1]['buttons'][base_settings_dict[TRASHT_PARAM]]['checked'] = 1
   except:
      pass
   
   page_js = [Markup('<script src="/static/js/radio-button-emit.js" defer></script>')]

   return render_template(CHOICE_INPUTS_TEMPLATE, \
      home_button = my_home_button, \
      page_title = "Change Settings or Perform Calibration", \
      installation_icon = display_customization_dict['icon'], \
      onclick_choices = onclick_choice_list, \
      radio_options = settings_radio_options, \
      page_specific_js = page_js, \
      footer_center = display_customization_dict['title'])


@blueprint_core.route(DONE_URL, methods=DEFAULT_METHODS)
def done():

   # from app.func_base import previous_drill_id
   global previous_drill_id

   send_stop_to_base()

   this_page_title = "Finished"
   onclick_choice_list = [{"value": "OK", "onclick_url": MAIN_URL}]

   if previous_drill_id is not None:
      onclick_choice_list.append({"value": "Repeat", "onclick_url": DRILL_URL, \
                                  "param_name": "drill_id", "param_value": previous_drill_id})
      this_page_title += f" Drill #{previous_drill_id}"
   else:
      current_app.logger.info(f"previous_drill_id is None")

   return render_template(CHOICE_INPUTS_TEMPLATE, \
      page_title = this_page_title, \
      installation_icon = display_customization_dict['icon'], \
      onclick_choices = onclick_choice_list, \
      footer_center = display_customization_dict['title'])
      
@blueprint_core.route(WORKOUT_RESULT_URL, methods=DEFAULT_METHODS)
def workout_result_screen():
   if 'icon' not in display_customization_dict:
      read_display_customization_file()

   return render_template(WORKOUT_RESULT_TEMPLATE, \
      home_button = my_home_button, \
      page_title = "Workout Results")

def write_base_settings_to_file():
   try:
      with open(f'{settings_dir}/{settings_filename}', 'w') as f:
            json.dump(base_settings_dict, f)
         # current_app.logger.debug(f"Settings written: {settings_dict}")
   except:
      current_app.logger.error(f"Settings file write failed.")


previous_drill_id = None
# using a function instead of importing the variable from blueprint_drills
# because the calibration_value did not appear to written by the event handler
def set_previous_drill_id(value):
   global previous_drill_id
   previous_id = previous_drill_id
   previous_drill_id = value
   current_app.logger.info(f'Change calibration_value: previous={previous_id} new={previous_drill_id}')

@blueprint_core.route('/save_wifi', methods=['POST'])
def save_wifi():
    # 1. Capture the data
    ssid = request.form.get('ssid')
    password = request.form.get('password')

    if ssid and password:
        base_settings_dict['wifi_ssid'] = ssid
        base_settings_dict['wifi_password'] = password
        
        try:
            os.system(f"sudo wpa_passphrase \"{ssid}\" \"{password}\" | sudo tee -a /etc/wpa_supplicant/wpa_supplicant.conf")
            os.system("sudo wpa_cli -i wlan0 reconfigure")
            current_app.logger.info(f"SUCCESS: Settings saved for {ssid}")
        except Exception as e:
            print(f"WRITE ERROR: {e}")

    return redirect('/settings')