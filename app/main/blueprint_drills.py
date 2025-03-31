from flask import Blueprint, current_app, request, render_template, redirect

blueprint_drills = Blueprint('blueprint_drills', __name__)
'''
  These pages are shown after 'Drills' or 'Workouts' are selected
  'Workouts' goes to: 
  'Drills' goes to a page showing 3 ways of selecting a drill: 'Recents', Select by Type, 'Beep Drills'
  After a workout or drill has been selected, both workouts and drills go to: 'Drills'
'''

import json
import enum
import os
from app.main.defines import *
from app.func_drills import get_drill_workout_info, read_drill_csv, make_drill_options, save_drill
from app.func_base import send_start_to_base, send_settings_to_base, get_servo_params

import sys

sys.path.append(f'{user_dir}/{boomer_dir}/drills')
try:
   from ui_drill_selection_lists import workout_list, default_recents_drill_list, \
      line_drill_dict, movement_drill_list, situational_drill_list, stroketype_drill_dict
except:
   current_app.logger.error("Problems with 'ui_drill_selection_lists' modules, please run: git clone https://github.com/davidcjordon/drills")
   exit()

sys.path.append(f'{user_dir}/{repos_dir}/control_ipc_utils')
try:
   from control_ipc_defines import *
except:
   current_app.logger.error("Problems with 'control_ipc' modules, please run: git clone https://github.com/davidcjordan/control_ipc_utils")
   exit()


WORKOUT_ID = 'workout_id'
DRILL_ID = 'drill_id' # indicates drill_id for thrower calibration, which doesn't use a POST
CALIB_ID = "motor_type"
ONCLICK_MODE_KEY = 'mode'
ONCLICK_MODE_WORKOUT_VALUE = 'workouts'

THROWER_CALIB_WORKOUT_ID = 2

MODE_DRILL_SELECTED = "Drill #"
MODE_WORKOUT_SELECTED = "Workout #"
EXAMPLE_CUSTOM_DRILL_FILENAME = "DRL401.csv"

drills_dict = {} # holds copies of drills read in from DRLxxx.csv files; keys are the drill numbers
workouts_dict = {} #as above, but using WORKxxx.csv files
recent_drill_list = []
custom_drill_list = []
previous_drill_id = None
calibration_setting = None # passed to done_url to send to base

radio_button_disable_js = [Markup('<script src="/static/js/radio-button-disable.js" defer></script>')]
get_drill_info_js = [Markup('<script src="/static/js/get_drill_info.js" defer></script>')]

thrower_calib_drill_dict = {"ROTARY":(THROWER_CALIB_DRILL_NUMBER_START)}
for i in range(balltype_e.SERVE.value, balltype_e.CUSTOM.value):
   thrower_calib_drill_dict[balltype_e(i).name] = THROWER_CALIB_DRILL_NUMBER_START+i


class beep_options(enum.Enum):
   Type = 0
   Stroke = 1
   Difficulty = 2
class stroke_category(enum.Enum):
   Ground = 0
   Volley = 1
   Mini_Tennis = 2
   Net = 3 

class beep_difficulty(enum.Enum):
   Very_Easy = 0
   Easy = 1
   Medium = 2
   Hard = 3
   Very_Hard = 4

# having the name seperate from the legend allows the name to be a parameter name instead of what is on the screen
beep_mode_choices = [\
   {'name': beep_options.Type.name, 'legend':beep_options.Type.name, 'buttons':[ \
      {'label': stroke_category.Ground.name, 'value': stroke_category.Ground.value, 'disables': beep_options.Difficulty.name, 'checked' : 1}, \
      {'label': stroke_category.Volley.name, 'value': stroke_category.Volley.value, 'disables': beep_options.Stroke.name}, \
      {'label': stroke_category.Mini_Tennis.name.replace("_","-"), 'value': stroke_category.Mini_Tennis.value, 'disables': beep_options.Stroke.name} \
   ]}, \
   {'name': beep_options.Stroke.name, 'legend':beep_options.Stroke.name, 'buttons':[ \
      {'label': balltype_e.TOPSPIN .name.title(), 'value': 0, 'checked' : 1}, \
      {'label': balltype_e.FLAT.name.title(), 'value': 1}, \
      {'label': balltype_e.LOOP.name.title(), 'value': 2}, \
      {'label': balltype_e.CHIP.name.title(), 'value': 3}, \
      {'label': "Random", 'value': 4}, \
      {'label': "Net", 'value': 5} \
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


@blueprint_drills.route(RECENTS_URL, methods=DEFAULT_METHODS)
def recents():
   from app.main.blueprint_core import display_customization_dict  # using 'global customization_dict' did not work
   global recent_drill_list #this global is written to by reading the recents file, and then used to update the recents file after a drill is selected

   selection_list = []

   try:
      with open(f'{settings_dir}/{custom_drill_list_filename}') as f:
         recent_drill_list = json.load(f)
   except:
      try:
         with open(f'{settings_dir}/{recents_filename}') as f:
            recent_drill_list = json.load(f)
      except:
         current_app.logger.error(f"Error reading '{settings_dir}/{recents_filename}'; using defaults")
         recent_drill_list = default_recents_drill_list

   for drill_id in recent_drill_list:
      drill_id_str = f"{drill_id:03}"
      if (fetch_into_drills_dict(drill_id_str)):
         drill_item_dict = {'id': drill_id_str, 'title': drills_dict[drill_id_str]['name']}
         selection_list.append(drill_item_dict)
      else:
         current_app.logger.error(f"DRL{drill_id_str} missing from drill_dict; not including in choices")

   # current_app.logger.debug(f"drills_dict={drills_dict}")

   return render_template(SELECT_TEMPLATE, \
      home_button = my_home_button, \
      page_title = "Select Drill", \
      installation_icon = display_customization_dict['icon'], \
      footer_center = display_customization_dict['title'], \
      url_for_post = DRILL_URL, \
      choices = selection_list, \
      page_specific_js = get_drill_info_js \
   )


@blueprint_drills.route(CUSTOM_SELECTION_URL, methods=DEFAULT_METHODS)
def custom():
   from app.main.blueprint_core import display_customization_dict  # using 'global customization_dict' did not work
   custom_drill_list = []
   selection_list = []

   for file_path in os.listdir(CUSTOM_DRILL_FILES_PATH):
      if os.path.isfile(os.path.join(CUSTOM_DRILL_FILES_PATH, file_path)):
         if file_path.startswith('DRL') and file_path.endswith('.csv'):
            custom_drill_list.append(file_path)

   if len(custom_drill_list) == 0:
      os.system(f'cp {DRILL_FILES_PATH}/DRL004.csv {CUSTOM_DRILL_FILES_PATH}/{EXAMPLE_CUSTOM_DRILL_FILENAME}')
      custom_drill_list.append(EXAMPLE_CUSTOM_DRILL_FILENAME)

   for file_name in custom_drill_list:
      with open(os.path.join(settings_dir, file_name)) as f:
         try:
            title = f.readline().rstrip().strip('\"')
         except:
            current_app.logger.error(f"get_drill_info: Error reading '{file_path}'")
         drill_id_str = file_name[3:6]
         drill_item_dict = {'id': drill_id_str, 'title': title}
         # current_app.logger.debug(f"EDIT_DRILL: drill_item_dict={drill_item_dict}")
         selection_list.append(drill_item_dict)

   return render_template(SELECT_TEMPLATE, \
      home_button = my_home_button, \
      page_title = "Select Drill", \
      installation_icon = display_customization_dict['icon'], \
      footer_center = display_customization_dict['title'], \
      url_for_post = DRILL_URL, \
      enable_edit_button = True, \
      choices = selection_list, \
      # page_specific_js = get_drill_info_js \
   )


@blueprint_drills.route(DRILL_SELECT_TYPE_URL, methods=DEFAULT_METHODS)
def drill_select_type():
   from app.main.blueprint_core import display_customization_dict  # using 'global customization_dict' did not work

   # the <1,2,3>-Lines radio-buttons are disabled until the 'Group' button is pushed:
   # If a radio button in a fieldset (choice dictionary) disables a different fieldset then:
   #  add 'disables' to the fieldset dict
   #  for each button, add 'enable' to the button dictionary.
   drill_type_choices = [\
      {'name': drill_type_options.Group.name, 'legend': "Type", 'buttons':[ \
         {'label': group_options.Individual.name, 'value': group_options.Individual.value, 'checked': 1, 'disables': drill_type_options.Lines.name}, \
         {'label': group_options.Group.name, 'value': group_options.Group.value}, \
      ]}, \
      {'name': drill_type_options.Lines.name, 'legend':drill_type_options.Lines.name, 'buttons':[ \
         {'label': "1-Line", 'value': "1-line"}, \
         {'label': "2-Lines", 'value':"2-line"}, \
         {'label': "3-Lines", 'value': "3-line"}, \
         {'label': "Mini-Tennis", 'value': "mini"}, \
      ]}, \
      {'name': drill_type_options.Focus.name,'legend':drill_type_options.Focus.name, 'buttons':[ \
         {'label': focus_options.Development.name, 'value': focus_options.Development.value, 'checked': 1}, \
         {'label': focus_options.Situational.name, 'value': focus_options.Situational.value, 'disables': beep_options.Stroke.name}, \
         {'label': focus_options.Movement.name, 'value': focus_options.Movement.value,'disables': beep_options.Stroke.name}, \
      ]}, \
      {'name': beep_options.Stroke.name, 'legend':beep_options.Stroke.name, 'buttons':[ \
         {'label': stroke_category.Ground.name.title(), 'value': stroke_category.Ground.name.lower(), 'checked': 1}, \
         {'label': stroke_category.Volley.name.title(), 'value': stroke_category.Volley.name.lower()}, \
         {'label': stroke_category.Net.name.title(), 'value': stroke_category.Net.name.lower()}, \
         {'label': "Overhead", 'value': balltype_e.LOB.name.lower()}, \
      ]}, \
   ]

   return render_template(GAME_OPTIONS_TEMPLATE, \
      home_button = my_home_button, \
      page_title = "Select Type of Drill", \
      installation_icon = display_customization_dict['icon'], \
      radio_options = drill_type_choices, \
      url_for_post = SELECT_DRILL_URL, \
      footer_center = display_customization_dict['title'], \
      page_specific_js = radio_button_disable_js \
   )


@blueprint_drills.route(BEEP_SELECTION_URL, methods=DEFAULT_METHODS)
def beep_selection():
   from app.main.blueprint_core import display_customization_dict  # using 'global customization_dict' did not work

   # current_app.logger.info(f"beep_mode_choices: {beep_mode_choices}")

   return render_template(GAME_OPTIONS_TEMPLATE,
      home_button = my_home_button, \
      page_title = "Select Type of Beep Drill", \
      installation_icon = display_customization_dict['icon'], \
      radio_options = beep_mode_choices, \
      url_for_post = DRILL_URL, \
      page_specific_js = radio_button_disable_js, \
      footer_center = display_customization_dict['title'])


@blueprint_drills.route(SELECT_DRILL_URL, methods=DEFAULT_METHODS)
def select_drill():
   from app.main.blueprint_core import display_customization_dict  # using 'global customization_dict' did not work

   current_app.logger.debug(f"SELECT_DRILL_URL request_form: {request.form}")
   # DEBUG:flask.app:SELECT_URL request_form: ImmutableMultiDict([('Group', '1'), ('Lines', '4'), ('Focus', '0'), ('Stroke', '0')])

   drill_list = None
   page_title_str = "Select Drill"
   selection_list = []

   # parse drill selection criteria to make list of drills:
   if ((drill_type_options.Group.name in request.form) and (request.form[drill_type_options.Group.name] == '1')):
      if (drill_type_options.Lines.name in request.form):
         drill_list = line_drill_dict[request.form[drill_type_options.Lines.name]]
      else:
         current_app.logger.error(f"request.form missing [drill_type_options.Lines.name]: using 1-line drills")
         drill_list = line_drill_dict['1-line']
   elif (drill_type_options.Focus.name in request.form):
      current_app.logger.debug(f"request.form[drill_type_options.Focus.name]={request.form[drill_type_options.Focus.name]}")
      if (request.form[drill_type_options.Focus.name] == str(focus_options.Movement.value)):
         drill_list = movement_drill_list
      elif (request.form[drill_type_options.Focus.name] == str(focus_options.Situational.value)):
         drill_list = situational_drill_list
      elif (request.form[drill_type_options.Focus.name] == str(focus_options.Development.value)):
         drill_list = stroketype_drill_dict[request.form[beep_options.Stroke.name]]
      else:
         current_app.logger.error(f"Unrecognized Drill Select Focus: {request.form[drill_type_options.Focus.name]}; using recent_drill_list")
         drill_list = recent_drill_list

   # current_app.logger.debug(f"Group test: drill_list={drill_list}; drill_list_name={request.form[drill_type_options.Lines.name]}")
   if drill_list is None:
      current_app.logger.error(f"Drill list was None after drill selection processing; using recent_drill_list")
      drill_list = recent_drill_list
      
   # now make drill selection list (array of ID & name dicts) from drill list
   for drill_id in drill_list:
      # current_app.logger.debug(f"drill_id={drill_id} is of type {type(drill_id)}")
      if len(selection_list) > 9: #limit to 10 entries
         break
      drill_id_str = f"{drill_id:03}"
      if (fetch_into_drills_dict(drill_id_str)):
         selection_list.append({'id': drill_id_str, 'title': drills_dict[drill_id_str]['name']})
      else:
         current_app.logger.error(f"DRL{drill_id_str} missing from drill_dict; not including in choices")

   return render_template(SELECT_TEMPLATE, \
      home_button = my_home_button, \
      page_title = page_title_str, \
      installation_icon = display_customization_dict['icon'], \
      url_for_post = DRILL_URL, \
      # the following doesn't work: the query parameter is now stripped by the browser.  TODO: remove from template
      # post_param = select_post_param, \
      choices = selection_list, \
      footer_center = display_customization_dict['title'], \
      page_specific_js = get_drill_info_js \
   )
 
@blueprint_drills.route(DRILL_URL, methods=DEFAULT_METHODS)
def drill():
   from app.main.blueprint_core import display_customization_dict  # using 'global customization_dict' did not work

   global recent_drill_list
   global previous_drill_id

   '''
   There are multiple ways of getting to this page
      - select_url: the post contains the choice_id
      = thrower_calib: the post contains a drill_id  or workout ID
      - beep_select: the post contains radio buttons selections (stroke, difficulty) which are mapped to a drillID
   example from beep test:
      DRILL_URL request_form: ImmutableMultiDict([('Stroke', 'Mini-Tennis'), ('Ground Stroke Type', 'Topspin'), ('Difficulty', 'Medium')])
      DRILL_URL request_args: ImmutableMultiDict([])
   example from custom drill select, when edit button is pushed:
      DRILL_URL request_form: ImmutableMultiDict([('choice_id', '401'), ('Edit', '')])
   '''
   current_app.logger.debug(f"DRILL_URL request_form: {request.form}")
   current_app.logger.debug(f"DRILL_URL request_args: {request.args}")

   # current_app.logger.info(f"request.form is of type: {type(request.form)}")
   # for key, value in request.form.items():
   #    print(key, '->', value)

   if 'Edit' in request.form or 'Copy' in request.form:
      if 'choice_id' in request.form:
         id = int(request.form['choice_id'])
      else:
         return redirect(CUSTOM_SELECTION_URL)
      if 'Edit' in request.form:
         return redirect(f"{EDIT_DRILL_URL}?drill_id={id}")
      else:
         return redirect(f"{COPY_DRILL_URL}?drill_id={id}")
 
   id = None
   beep_type_value = None
   is_workout = False
   if 'choice_id' in request.form:
      #INFO:flask.app:DRILL_URL request_form: ImmutableMultiDict([('choice_id', '100')])
      id = int(request.form['choice_id'])
      current_app.logger.info(f"Setting drill_id= {id} from request.form")
   elif DRILL_ID in request.args:
      #DRILL_URL request_args: ImmutableMultiDict([('choice_id', '781')])
      id = int(request.args[DRILL_ID])
      current_app.logger.info(f"Setting drill_id= {id} from request.args")
   elif WORKOUT_ID in request.args:
      #DRILL_URL request_args: ImmutableMultiDict([('workout_id', '2')])
      id = int(request.args[WORKOUT_ID])
      is_workout = True
      current_app.logger.info(f"Setting workout_id= {id} from request.args")
   elif beep_options.Type.name in request.form:
      beep_type_value = int(request.form[ beep_options.Type.name])
      #request_form: ImmutableMultiDict([('Type', '2'), ('Stroke', '5'), ('Difficulty', '2')])
      # for key in request.form:
      #    current_app.logger.info(f"Beep choice {key} = {request.form[key]}")
      # example beep drill ranges - consult the drills repository for the real thing:
      #OLD: mini-tennis: 901-905; volley: 906-910; 911-915 flat, 916-920 loop, 921-925 chip, 926-930 topspin, 931-935 random
      #NEW: mini-tennis: 901-905; volley=906; flat=907 loop=908 chip=909 topspin=910 random=911
      #set defaults if missing keys in form:
      stroke_type_offset = 0 #default to mini-tennis
      difficulty_offset = 0 # only mini-tennis uses difficulty

      if beep_options.Difficulty.name in request.form:
         difficulty_offset = int(request.form[beep_options.Difficulty.name])
         # current_app.logger.info(f"beep_type={beep_type(beep_type_value).name}; Increasing id by {difficulty_offset}, e.g. {beep_difficulty(difficulty_offset).name}")
      else:
         current_app.logger.warning(f"Beep drill option: {beep_options.Difficulty.name} not in request.form")

      if beep_type_value is stroke_category.Volley.value:
         difficulty_offset = 0
         stroke_type_offset = 5

      if beep_type_value is stroke_category.Ground.value:
         difficulty_offset = 0
         if beep_options.Stroke.name in request.form:
            stroke_type = int(request.form[beep_options.Stroke.name])
         else:
            current_app.logger.warning(f"Beep drill option: {beep_options.Stroke.name} not in request.form")
            stroke_type = 1
         stroke_type_offset = stroke_type + 6
         # current_app.logger.info(f"Ground beep type, so using stroke_type={beep_stroke(stroke_type).name}")

      id = BEEP_DRILL_NUMBER_START + difficulty_offset + stroke_type_offset
      current_app.logger.info(f"drill_id={id}: {stroke_category(beep_type_value).name}, difficulty_offset={difficulty_offset}, stroke_type_offset={stroke_type_offset}")
   else:
      current_app.logger.error("DRILL_URL - no drill or workout id!")
   
   # handle case where it gets to this page without a drill ID
   if id is None:
      id = 1

   drill_stepper_options = {}
   if not is_workout and id < 600:
      # save to recents file
      if (len(recent_drill_list) < 6):
         current_app.logger.error(f"recent_drill_list only had {len(recent_drill_list)} drills; restoring with defaults.")
         recent_drill_list = default_recents_drill_list
      # move to beginning of list
      if id in recent_drill_list:
         recent_drill_list.remove(id)
      recent_drill_list.insert(0,id)
      while len(recent_drill_list) > 10:
         recent_drill_list = recent_drill_list[:-1] #remove oldest drill_id
      # re-write recents file putting drill at top
      current_app.logger.debug(f"Updating '{recents_filename}' with {len(recent_drill_list)} drill ids.")
      try:
         with open(f'{settings_dir}/{recents_filename}', 'w') as f:
            json.dump(recent_drill_list, f)
      except:
         current_app.logger.error(f"Error writing '{settings_dir}/{recents_filename}'")

   if is_workout:
      base_mode_dict = {MODE_PARAM: base_mode_e.WORKOUT.value, ID_PARAM: id}
      mode_string = f"{MODE_WORKOUT_SELECTED}{id}"
   #TODO: test BEEP enum: currently beep drills are using the DRILL enum
   # elif beep_type_value is not None:
   #    base_mode_dict = {MODE_PARAM: base_mode_e.BEEP.value, ID_PARAM: id}
   else:
      base_mode_dict = {MODE_PARAM: base_mode_e.DRILL.value, ID_PARAM: id}
      this_drill_info = get_drill_workout_info(id)
      if this_drill_info is None or 'name' not in this_drill_info:
         this_drill_info['name'] = ''
      mode_string = f"{MODE_DRILL_SELECTED}{id}: {this_drill_info['name']}"
      previous_drill_id = id

   continuous_option = [ \
      {'name': CONTINUOUS_MOD_PARAM, 'legend': "Continous Mode", 'buttons':[ \
         {'label': "Off", 'value': 0}, \
         {'label': "On", 'value': 1} \
      ] } ]

   from app.main.blueprint_core import base_settings_dict
   # if CONTINUOUS_MOD_PARAM==1 the On label (button 1) will be checked, else button 0 will be checked
   continuous_option[0]['buttons'][base_settings_dict[CONTINUOUS_MOD_PARAM]]['checked'] = 1
   # current_app.logger.debug(f"continuous_option= {continuous_option}")

   send_settings_to_base(base_settings_dict)
   send_start_to_base(base_mode_dict)

   # THROWER_CALIB_WORKOUT_ID has been disabled:
   thrower_calib_drill_number_end = THROWER_CALIB_DRILL_NUMBER_START + len(thrower_calib_drill_dict) + 1
   if (not is_workout and id not in range(THROWER_CALIB_DRILL_NUMBER_START, thrower_calib_drill_number_end)) or \
      (is_workout and id != THROWER_CALIB_WORKOUT_ID):
      # the defaults are set from what was last saved in the settings file
      drill_stepper_options = { \
         LEVEL_PARAM:{"legend":"Level", "dflt":base_settings_dict[LEVEL_PARAM]/LEVEL_UI_FACTOR, \
            "min":LEVEL_MIN/LEVEL_UI_FACTOR, "max":LEVEL_MAX/LEVEL_UI_FACTOR, "step":LEVEL_UI_STEP/LEVEL_UI_FACTOR}, \
         SPEED_MOD_PARAM:{"legend":"Speed", "dflt":base_settings_dict[SPEED_MOD_PARAM], \
            "min":SPEED_MOD_MIN, "max":SPEED_MOD_MAX, "step":SPEED_MOD_STEP}, \
         DELAY_MOD_PARAM:{"legend":"Delay", "dflt":base_settings_dict[DELAY_MOD_PARAM]/DELAY_UI_FACTOR, \
            "min":DELAY_MOD_MIN/DELAY_UI_FACTOR, "max":DELAY_MOD_MAX/DELAY_UI_FACTOR, "step":DELAY_UI_STEP/DELAY_UI_FACTOR}, \
         ELEVATION_MOD_PARAM:{"legend":"Height", "dflt":base_settings_dict[ELEVATION_MOD_PARAM], \
            "min":ELEVATION_ANGLE_MOD_MIN, "max":ELEVATION_ANGLE_MOD_MAX, "step":ELEVATION_ANGLE_MOD_STEP} \
      }
   else:
      continuous_option = []
      servo_params = get_servo_params()
      if id == 760:
         current_angle = f'{servo_params[CENTER_ANGLE_PARAM]/10.0:.1f}'
         drill_stepper_options = { \
            "ROTARY_ANGLE":{"legend":"Angle", "dflt": current_angle, \
               "min":-5, "max":+5, "step":0.1}, \
         }
      # drop and lob throws only have speed adjusted:
      elif id == 762 or id == 766:
         if id == 762:
            current_speed = servo_params[DROP_SPEED_PARAM]/10.0
         else:
            current_speed = servo_params[LOB_SPEED_PARAM]/10.0
         drill_stepper_options["SPEED"] = {"legend":"Speed", "dflt":round_to_nearest_half_int(current_speed), \
               "min":SPEED_BALL_MIN, "max":SPEED_BALL_MAX, "step":0.5}
      else:
         if id == 761:
            current_angle = servo_params[SERVE_ANGLE_PARAM]/10.0
         elif id == 763:
            current_angle = servo_params[FLAT_ANGLE_PARAM]/10.0
         elif id == 764:
            current_angle = servo_params[LOOP_ANGLE_PARAM]/10.0
         elif id == 765:
            current_angle = servo_params[CHIP_ANGLE_PARAM]/10.0
         elif id == 767:
            current_angle = servo_params[TOPSPIN_ANGLE_PARAM]/10.0
         else:
            current_angle = servo_params[PASS_ANGLE_PARAM]/10.0
         drill_stepper_options = { \
            "HEIGHT":{"legend":"Height", "dflt":round_to_nearest_half_int(current_angle), \
               "min":ELEVATION_ANGLE_BALL_MIN, "max":ELEVATION_ANGLE_BALL_MAX, "step":0.5}, \
         }
         
   return render_template(DRILL_TEMPLATE, \
      page_title = f"Running {mode_string}", \
      installation_icon = display_customization_dict['icon'], \
      stepper_options = drill_stepper_options, \
      radio_options = continuous_option, \
      footer_center = display_customization_dict['title'])


@blueprint_drills.route(EDIT_DRILL_URL, methods=DEFAULT_METHODS)
def edit_drill():
   from app.main.blueprint_core import display_customization_dict

   # current_app.logger.debug(f"EDIT_DRILL_URL request_form: {request.form}")
   current_app.logger.debug(f"EDIT_DRILL_URL request_args: {request.args}")

   if 'drill_id' in request.args:
      drill_id = request.args['drill_id']
      raw_throw_list = read_drill_csv(drill_id)
      # current_app.logger.info(f"raw_throw_list= {raw_throw_list}")
      this_drill_info = get_drill_workout_info(drill_id) #default is to get drill info
      drill_name = ""
      if ('name' in this_drill_info):
         drill_name = this_drill_info['name']
   else:
      current_app.logger.error(f"drill_id not in EDIT_DRILL_URL request_args: {request.args}")
      return redirect(CUSTOM_SELECTION_URL)

   if len(raw_throw_list) == 0:
      current_app.logger.error(f"drill {request.args['drill_id']} had no throw (shot) rows.")

   all_rows_throw_list = make_drill_options(raw_throw_list)
   # current_app.logger.info(f"all_rows_throw_list= {all_rows_throw_list}")

   return render_template('/layouts/drill_show.html', \
      page_title = "Edit Drill: " + drill_name, \
      throw_list = all_rows_throw_list, \
      home_button = my_home_button, \
      installation_icon = display_customization_dict['icon'], \
      footer_center = display_customization_dict['title'])


@blueprint_drills.route(SELECT_WORKOUT_URL, methods=DEFAULT_METHODS)
def select_workout():
   from app.main.blueprint_core import display_customization_dict  # using 'global customization_dict' did not work

   # current_app.logger.debug(f"select [drill/workout] request: {request}")
   current_app.logger.debug(f"SELECT_WORKOUT_URL request_form: {request.form}")

   page_title_str = "Select Workout"
   selection_list = []

   for workout_id in workout_list:
      # current_app.logger.debug(f"workout_id={workout_id} is of type {type(workout_id)}")
      workout_id_str = f"{workout_id:03}"
      if (fetch_into_workout_dict(workout_id_str)):
         selection_list.append({'id': workout_id_str, 'title': workouts_dict[workout_id_str]['name']})
      else:
         current_app.logger.error(f"WORK{workout_id_str} missing from workouts_dict; not including in choices")

   return render_template(SELECT_TEMPLATE, \
      home_button = my_home_button, \
      page_title = page_title_str, \
      installation_icon = display_customization_dict['icon'], \
      url_for_post = WORKOUT_URL, \
      choices = selection_list, \
      footer_center = display_customization_dict['title'], \
      # page_specific_js = get_workout_info_js \
   )


@blueprint_drills.route(WORKOUT_URL, methods=DEFAULT_METHODS)
def workout():
   from app.main.blueprint_core import display_customization_dict  # using 'global customization_dict' did not work

   current_app.logger.debug(f"DRILL_URL request_form: {request.form}")

   # current_app.logger.info(f"request.form is of type: {type(request.form)}")
   # for key, value in request.form.items():
   #    print(key, '->', value)
   id = None
   if 'choice_id' in request.form:
      #INFO:flask.app:DRILL_URL request_form: ImmutableMultiDict([('choice_id', '100')])
      id = int(request.form['choice_id'])
      current_app.logger.info(f"Setting workout_id= {id} from request.form")
   else:
      current_app.logger.error("WORKOUT_URL - no workout id!")
   
   # handle case where it gets to this page without a drill ID
   if id is None:
      id = 1

   drill_stepper_options = {}
 
   base_mode_dict = {MODE_PARAM: base_mode_e.WORKOUT.value, ID_PARAM: id}
   mode_string = f"{MODE_WORKOUT_SELECTED}{id}"

   from app.main.blueprint_core import base_settings_dict
   # turn of continous mode
   base_settings_dict['contin'] = 0
   send_settings_to_base(base_settings_dict)
   send_start_to_base(base_mode_dict)

   # the THROWER_CALIB_WORKOUT_ID has been disabled, so the following will always be true:
   if (id != THROWER_CALIB_WORKOUT_ID):
      # the defaults are set from what was last saved in the settings file
      drill_stepper_options = { \
         LEVEL_PARAM:{"legend":"Level", "dflt":base_settings_dict[LEVEL_PARAM]/LEVEL_UI_FACTOR, \
            "min":LEVEL_MIN/LEVEL_UI_FACTOR, "max":LEVEL_MAX/LEVEL_UI_FACTOR, "step":LEVEL_UI_STEP/LEVEL_UI_FACTOR}, \
         SPEED_MOD_PARAM:{"legend":"Speed", "dflt":base_settings_dict[SPEED_MOD_PARAM], \
            "min":SPEED_MOD_MIN, "max":SPEED_MOD_MAX, "step":SPEED_MOD_STEP}, \
         DELAY_MOD_PARAM:{"legend":"Delay", "dflt":base_settings_dict[DELAY_MOD_PARAM]/DELAY_UI_FACTOR, \
            "min":DELAY_MOD_MIN/DELAY_UI_FACTOR, "max":DELAY_MOD_MAX/DELAY_UI_FACTOR, "step":DELAY_UI_STEP/DELAY_UI_FACTOR}, \
         ELEVATION_MOD_PARAM:{"legend":"Height", "dflt":base_settings_dict[ELEVATION_MOD_PARAM], \
            "min":ELEVATION_ANGLE_MOD_MIN, "max":ELEVATION_ANGLE_MOD_MAX, "step":ELEVATION_ANGLE_MOD_STEP} \
      }
         
   return render_template(DRILL_TEMPLATE, \
      page_title = f"Running {mode_string}", \
      installation_icon = display_customization_dict['icon'], \
      stepper_options = drill_stepper_options, \
      footer_center = display_customization_dict['title'])


@blueprint_drills.route(THROWER_CALIB_SELECTION_URL, methods=DEFAULT_METHODS)
def thrower_calib():
   from app.main.blueprint_core import display_customization_dict  # using 'global customization_dict' did not work

   # value is the label of the button
   # !!NOTE: the label (value) is different than the param_value for ROTARY/ELEVATOR
   onclick_choice_list = [\
      {"html_before": "Motor:", \
         "value": UI_ROTARY_CALIB_NAME.title(), "onclick_url": MOTOR_CALIB_URL, "param_name": CALIB_ID,"param_value": ROTARY_CALIB_NAME}, \
      {"value": UI_ELEVATOR_CALIB_NAME.title(), "onclick_url": MOTOR_CALIB_URL, "param_name": CALIB_ID,"param_value": ELEVATOR_CALIB_NAME}, \
      {"value": UI_WHEEL_CALIB_NAME.title(), "onclick_url": MOTOR_CALIB_URL, "param_name": CALIB_ID,"param_value": UI_WHEEL_CALIB_NAME, \
          "html_after": html_horizontal_rule}, \
      # since the calibration is manual, the option to run all the thrower calib drills is removed:
      # {"value": "All", "onclick_url": DRILL_URL, "param_name": WORKOUT_ID,"param_value": THROWER_CALIB_WORKOUT_ID} \
   ]
   for parameter, drill_num in thrower_calib_drill_dict.items():
      button_label = f"{parameter.title()}"
      onclick_choice_list.append({"value": button_label, "param_name": DRILL_ID, "onclick_url": DRILL_URL, "param_value": drill_num})

   return render_template(CHOICE_INPUTS_TEMPLATE, \
      home_button = my_home_button, \
      page_title = "Select Thrower Calibration Type", \
      installation_icon = display_customization_dict['icon'], \
      onclick_choices = onclick_choice_list, \
      footer_center = display_customization_dict['title'])


@blueprint_drills.route(MOTOR_CALIB_URL, methods=DEFAULT_METHODS)
def motor_calib():
   # enter page from thrower calibration page
   # extract which button was pushed (rotary or elevator and issue command)

   from app.main.blueprint_core import display_customization_dict  # using 'global customization_dict' did not work

   # current_app.logger.debug(f"select request: {request}")
   motor_type = request.args.get(CALIB_ID)
   current_app.logger.debug(f"request for motor; type: {motor_type}")

   if motor_type is None:
      current_app.logger.error(f"request for motor; type is None")
      #TODO: do a redirect to an error page

   base_mode_dict = {MODE_PARAM: base_mode_e.CALIBRATION.value, ID_PARAM: motor_type}
   send_start_to_base(base_mode_dict)

   return render_template(CHOICE_INPUTS_TEMPLATE, \
      page_title = "Motor Calibration", \
      installation_icon = display_customization_dict['icon'], \
      message = f"{motor_type.title()} motor calibration in progress.", \
      footer_center = display_customization_dict['title'])


def fetch_into_drills_dict(drill_id_str):
   # get name from drills_dict, or read the drill file and populate the drills_dict
   if (drill_id_str not in drills_dict):
      this_drill_info = get_drill_workout_info(drill_id_str)
      if ('name' in this_drill_info):
         drills_dict[drill_id_str] = this_drill_info

   if ((drill_id_str in drills_dict) and ('name' in drills_dict[drill_id_str])):
      return True
   else:
      return False


def fetch_into_workout_dict(id_str):
   if (id_str not in workouts_dict):
      this_workout_info = get_drill_workout_info(id_str, file_type=workout_file_prefix)
      if ('name' in this_workout_info):
         workouts_dict[id_str] = this_workout_info

   if ((id_str in workouts_dict) and ('name' in workouts_dict[id_str])):
      return True
   else:
      return False


@blueprint_drills.route(EDIT_DRILL_DONE_URL, methods=DEFAULT_METHODS)
def edit_drill_done():
   from app.main.blueprint_core import display_customization_dict

   # current_app.logger.debug(f"EDIT_DRILL_DONE_URL request_form: {request.form}")
   # current_app.logger.debug(f"EDIT_DRILL_DONE_URL request_args: {request.args}")

   #EDIT_DRILL_DONE_URL request_form: ImmutableMultiDict([('1-1', 'Serve'), ('1-2', 'FH'), ('1-3', '1'), ('1-4', '2.6'), ('submit.x', '64'), ('submit.y', '48')])
   #EDIT_DRILL_DONE_URL request_args: ImmutableMultiDict([('drill_id', '403')])

   if 'drill_id' in request.args:
      saved_drill_successfully = save_drill(request.form, id=request.args['drill_id'])
      if saved_drill_successfully:
         title = f"Saved Edits for Drill {request.args['drill_id']}"
      else:
         title = f"Saving Edits failed for Drill {request.args['drill_id']}: read/write error!"
   else:
      current_app.logger.error(f"drill_id not in EDIT_DRILL_URL request_args: {request.args}")
      title = f"Saving Edits failed for Drill: no drill ID!"

   return render_template(CHOICE_INPUTS_TEMPLATE, \
      page_title = title, \
      installation_icon = display_customization_dict['icon'], \
      onclick_choices = [{"value": "OK", "onclick_url": CUSTOM_SELECTION_URL}], \
      footer_center = display_customization_dict['title'])


@blueprint_drills.route(COPY_DRILL_URL, methods=DEFAULT_METHODS)
def copy_drill():
   from app.main.blueprint_core import display_customization_dict

   # current_app.logger.debug(f"EDIT_DRILL_URL request_form: {request.form}")
   current_app.logger.debug(f"COPY_DRILL_URL request_args: {request.args}")

   new_drill_id = 410
   custom_drill_id_list = []

   if 'drill_id' in request.args:
      drill_id = request.args['drill_id']
      # figure out the next available DRL number
      all_files = os.listdir(CUSTOM_DRILL_FILES_PATH)
      # current_app.logger.debug(f"all files: {all_files}")
      for file in all_files:
         if file.startswith(drill_file_prefix) and file.endswith('.csv'):
            custom_drill_id_list.append(file[3:6])
      custom_drill_id_list.sort(reverse=True)
      new_drill_id = int(custom_drill_id_list[0]) + 1
      old_custom_number = int(drill_id) - CUSTOM_DRILL_NUMBER_START
      new_custom_number = int(new_drill_id) - CUSTOM_DRILL_NUMBER_START
      # current_app.logger.debug(f"custom files: {custom_drill_id_list}  new_drill_id= {new_drill_id}")
      os.system(f'cp {CUSTOM_DRILL_FILES_PATH}/DRL{drill_id}.csv {CUSTOM_DRILL_FILES_PATH}/DRL{new_drill_id}.csv')
      cmd = f"sed -i '1!b;s/{old_custom_number}/{new_custom_number}/' {CUSTOM_DRILL_FILES_PATH}/DRL{new_drill_id}.csv"
      current_app.logger.debug(f"sed cmd: {cmd}")
      os.system(cmd)
   else:
      current_app.logger.error(f"drill_id not in COPY_DRILL_URL request_args: {request.args}")
      
      #TODO: redirect

   return render_template(CHOICE_INPUTS_TEMPLATE, \
      page_title = f"Copied Drill {request.args['drill_id']} to Drill {new_drill_id}", \
      installation_icon = display_customization_dict['icon'], \
      onclick_choices = [{"value": "OK", "onclick_url": CUSTOM_SELECTION_URL}], \
      footer_center = display_customization_dict['title'])

def round_to_nearest_half_int(num):
    return round(num * 2) / 2
