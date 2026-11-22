from flask import Blueprint, render_template, Markup

blueprint_wifi = Blueprint('blueprint_wifi', __name__)
'''
WiFi page: scan for networks, connect (with an on-screen keyboard for the password) and show
connection status & link details.  The page talks to the server with the wifi_* socketio events
in events.py; the wpa_supplicant interaction is in func_wifi.py.
'''

from app.main.defines import *


@blueprint_wifi.route(WIFI_URL, methods=DEFAULT_METHODS)
def wifi():
   from app.main.blueprint_core import display_customization_dict

   page_js = [Markup('<script src="/static/js/wifi.js" defer></script>')]
   page_styles = [Markup('<link rel="stylesheet" href="/static/css/wifi.css">')]

   return render_template(WIFI_TEMPLATE, \
      home_button = my_home_button, \
      page_title = "WiFi", \
      installation_icon = display_customization_dict.get('icon', '/static/favicon.ico'), \
      page_specific_js = page_js, \
      page_specific_styles = page_styles, \
      footer_center = display_customization_dict.get('title', ''))
