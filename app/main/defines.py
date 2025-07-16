MAIN_URL = '/'
GAME_OPTIONS_URL = '/game_options'
GAME_URL = '/game'
DRILL_SELECT_TYPE_URL = '/drill_select_type'
SELECT_DRILL_URL = '/select_drill'
SELECT_WORKOUT_URL = '/select_workout'
DRILL_URL = '/drill'
WORKOUT_URL = '/workout'
CAM_CALIB_URL = '/cam_calib'
CAM_LOCATION_URL = '/cam_location'
CAM_CALIB_DONE_URL = '/cam_calib_done'
SETTINGS_URL = '/settings'
FAULTS_URL = '/faults'
THROWER_CALIB_SELECTION_URL = '/thrower_calibration'
MOTOR_CALIB_URL = '/motor_calib'
BEEP_SELECTION_URL = '/beep_selection'
CUSTOM_SELECTION_URL = '/custom_selection'
CAM_VERIF_URL = '/cam_verif'
DONE_URL = '/done'
RECENTS_URL = '/recent_drills'
EDIT_DRILL_URL = '/edit_drill'
EDIT_DRILL_DONE_URL = '/edit_drill_done'
COPY_DRILL_URL = '/copy_drill'
TEST_SCREEN_URL = '/test_screen'
DRILL_LIST_URL = '/drill_list'
WORKOUT_RESULT_URL = '/workout_result'
DESTINATION_SELECT_URL = '/destination_select'

from flask import Markup
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
SELECT_TEMPLATE = '/layouts' + '/select' + '.html'
DRILL_TEMPLATE = '/layouts' + DRILL_URL + '.html'
EDIT_DRILL_TEMPLATE = '/layouts' + 'drill_show' + '.html'
CAM_CALIBRATION_TEMPLATE = '/layouts' + CAM_CALIB_URL + '.html'
CAM_LOCATION_TEMPLATE = '/layouts' + CAM_LOCATION_URL + '.html'
CAM_VERIFICATION_TEMPLATE = '/layouts' + CAM_VERIF_URL + '.html'
FAULTS_TEMPLATE = '/layouts' + FAULTS_URL + '.html'
DRILL_LIST_TEMPLATE = '/layouts' + DRILL_LIST_URL + '.html'
WORKOUT_RESULT_TEMPLATE = '/layouts' + WORKOUT_RESULT_URL + '.html'
DESTINATION_SELECT_TEMPLATE = '/layouts/destination_select.html'

ONCLICK_MODE_KEY = 'mode'
ONCLICK_MODE_WORKOUT_VALUE = 'workouts'
CAM_SIDE_ID = "cam_side"
CAM_SIDE_LEFT_LABEL = 'Left'
CAM_SIDE_RIGHT_LABEL = 'Right'

#ELEVATOR & ROTARY_CALIB_NAME are defined in calc_ball
UI_WHEEL_CALIB_NAME = "WHEELS"
UI_ROTARY_CALIB_NAME = "ROTARY"
UI_ELEVATOR_CALIB_NAME = "ELEVATOR"

user_dir = '/home/pi'
boomer_dir = 'boomer'
repos_dir = 'repos'
site_data_dir = 'this_boomers_data'
settings_dir = f'{user_dir}/{boomer_dir}/{site_data_dir}'
execs_dir = f"{user_dir}/{boomer_dir}/execs"
recents_filename = "recents.json"
custom_drill_list_filename = "custom_drill_list.json"
settings_filename = "drill_game_settings.json"

drills_dir = f'{user_dir}/{boomer_dir}/drills'
drill_file_prefix = "DRL"
workout_file_prefix = "WORK"
