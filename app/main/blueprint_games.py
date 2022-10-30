from flask import Blueprint, current_app, request, render_template

blueprint_games = Blueprint('blueprint_games', __name__)
'''
'''

from app.main.defines import *
from app.func_base import send_start_to_base, send_settings_to_base

import sys
sys.path.append(f'{user_dir}/{repos_dir}/control_ipc_utils')
try:
   from control_ipc_defines import *
except:
   current_app.logger.error("Problems with 'control_ipc' modules, please run: git clone https://github.com/davidcjordan/control_ipc_utils")
   exit()


@blueprint_games.route(GAME_OPTIONS_URL, methods=DEFAULT_METHODS)
def game_options():
   from app.main.blueprint_core import display_customization_dict

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

   from app.main.blueprint_core import base_settings_dict
   game_radio_options[0]['buttons'][base_settings_dict[SERVE_MODE_PARAM]]['checked'] = 1
   # app.logger.debug(f"base_settings_dict[SERVE_MODE_PARAM]= {base_settings_dict[SERVE_MODE_PARAM]}")
   # if (base_settings_dict[TIEBREAKER_PARAM] == 1):
   # app.logger.debug(f"base_settings_dict[TIEBREAKER_PARAM]= {base_settings_dict[TIEBREAKER_PARAM]}")
   game_radio_options[1]['buttons'][base_settings_dict[TIEBREAKER_PARAM]]['checked'] = 1
   # app.logger.debug(f"game_radio_options= {game_radio_options}")

   page_js = [Markup('<script src="/static/js/radio-button-emit.js" defer></script>')]

   return render_template(GAME_OPTIONS_TEMPLATE, \
      home_button = my_home_button, \
      page_title = "Select Game Mode Options", \
      installation_icon = display_customization_dict['icon'], \
      url_for_post = GAME_URL, \
      # optional_form_begin = Markup('<form action ="' + GAME_URL + '" method="post">'), \
      # optional_form_end = Markup('</form>'), \

      radio_options = game_radio_options, \
      # point_delay_dflt = GAME_POINT_DELAY_DEFAULT, \
      # point_delay_min = GAME_POINT_DELAY_MIN, \
      # point_delay_max = GAME_POINT_DELAY_MAX, \
      # point_delay_step = GAME_POINT_DELAY_STEP, \
      page_specific_js = page_js, \
      footer_center = display_customization_dict['title'])

@blueprint_games.route(GAME_URL, methods=DEFAULT_METHODS)
def game():
   from app.main.blueprint_core import display_customization_dict

   # ignore the POST data: wServes & tiebreaker are set using emit(change_params)
   # app.logger.debug(f"GAME_URL request_form: {request.form}")
   #ImmutableMultiDict([('wServes', '0'), ('tiebreaker', '0')])

   base_mode_dict = {MODE_PARAM: base_mode_e.GAME.value}
   from app.main.blueprint_core import base_settings_dict
   send_settings_to_base(base_settings_dict)
   send_start_to_base(base_mode_dict)

   return render_template(GAME_TEMPLATE, \
      page_title = "Game Mode", \
      installation_icon = display_customization_dict['icon'], \
      level_dflt = base_settings_dict[LEVEL_PARAM]/LEVEL_UI_FACTOR, \
      level_min = LEVEL_MIN/LEVEL_UI_FACTOR, \
      level_max = LEVEL_MAX/LEVEL_UI_FACTOR, \
      level_step = LEVEL_UI_STEP/LEVEL_UI_FACTOR, \
      footer_center = display_customization_dict['title'])
