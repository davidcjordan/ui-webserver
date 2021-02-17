#!/usr/bin/env python3

#from flask import ? session, abort
from flask import Flask, render_template, Response, request, redirect, url_for, Markup, send_from_directory
from flask_socketio import SocketIO, emit

import inspect
import os  # for sending favicon 

# the following requires: export PYTHONPATH='/Users/tom/Documents/Projects/Boomer/control_ipc_utils'
import sys
sys.path.append('/Users/tom/Documents/Projects/Boomer/control_ipc_utils')
from ctrl_messaging_routines import send_msg #, is_active
from control_ipc_defines import *
import json
from random import randint


IP_PORT = 1111 # picked what is hopefully an unused port  (can't use 44)
DEFAULT_METHODS = ['POST', 'GET']

# Flask looks for following in the 'templates' directory
MAIN_URL = '/'
GAME_OPTIONS_URL = '/game_options'
GAME_URL = '/game'
DRILL_SELECTION_URL = '/drill_selection'
DRILL_URL = '/drill'
# WORKOUT_SELECTION_URL = '/workout_selection'
SETTINGS_URL = '/settings'

MAIN_TEMPLATE = 'index.html'
GAME_OPTIONS_TEMPLATE = '/layouts/game_options.html'
GAME_TEMPLATE = '/layouts/game.html'
DRILL_SELECTION_TEMPLATE = '/layouts/drill_selection.html'
DRILL_TEMPLATE = '/layouts/drill.html'
# WORKOUT_SELECTION_TEMPLATE = '/layouts/workout_selection.html'
SETTINGS_TEMPLATE = '/layouts/settings.html'

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

@app.route('/test')
def test_io_send():
    return render_template('test.html')
 
@app.route(MAIN_URL, methods=DEFAULT_METHODS)
def index():
    global back_url, previous_url
    back_url = previous_url = "/"
    
    customized_footer = original_footer.replace("{{ status }}", STATUS_IDLE)
    customized_footer = customized_footer.replace("{{ mode }}", MODE_NONE)
    return render_template(MAIN_TEMPLATE, \
        generated_header=customized_header_wo_home, \
        generated_footer=customized_footer)

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
    customized_footer = original_footer.replace("{{ status }}", STATUS_IDLE)
    customized_footer = customized_footer.replace("{{ mode }}", MODE_GAME)
    return render_template(GAME_OPTIONS_TEMPLATE, \
        generated_header=customized_header_w_home, \
        generated_footer=customized_footer)

@app.route(GAME_URL, methods=DEFAULT_METHODS)
def game():
    global back_url, previous_url
    back_url = previous_url

    if ("/" + inspect.currentframe().f_code.co_name == previous_url):
        already_on_active_page = True
        print("post when on active page; request: {}".format(request.data))
        # multi_dict = request.args
        # for key in multi_dict:
            # print(multi_dict.get(key))
            # print(multi_dict.getlist(key))
    else:
        already_on_active_page = False
    already_on_active_page = False

    mode_string = "FIX ME"

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
        
    previous_url = "/" + inspect.currentframe().f_code.co_name
    if not already_on_active_page:
        customized_footer = original_footer.replace("{{ status }}", STATUS_ACTIVE)
        customized_footer = customized_footer.replace("{{ mode }}", mode_string)
        return render_template(GAME_TEMPLATE, \
        generated_header=customized_header_wo_home, \
        generated_footer=customized_footer)
    else:
        return None


@app.route(DRILL_SELECTION_URL, methods=DEFAULT_METHODS)
def drill_selection():
    global back_url, previous_url
    back_url = '/'
    previous_url = "/" + inspect.currentframe().f_code.co_name

    drill_names = ["Side to Side", "Backhand", "The Dribble"]

    button_def = \
        Markup('<div>\n\
            <input type="radio" id="{{drill_id}}" name="drill_id" value="{{value}}" {{checked}}>\n\
            <label for="{{drill_id}}">{{drill_text}}</label>\n\
            </div>')

    drill_button_list = Markup("<fieldset>\n")
    for id, drill_text in enumerate(drill_names):
        this_drill_selection = button_def.replace("{{value}}", drill_text)
        this_drill_selection = this_drill_selection.replace("{{drill_text}}", drill_text)
        this_drill_selection = this_drill_selection.replace("{{drill_id}}", "drill_"+str(id+1))
        if id == 0:
            this_drill_selection = this_drill_selection.replace("{{checked}}", "checked")
        else:
            this_drill_selection = this_drill_selection.replace("{{checked}}", "")
        drill_button_list += this_drill_selection
    drill_button_list += Markup("</fieldset>\n")

    customized_footer = original_footer.replace("{{ status }}", STATUS_IDLE)
    customized_footer = customized_footer.replace("{{ mode }}", MODE_DRILL_NOT_SELECTED)

    return render_template(DRILL_SELECTION_TEMPLATE, \
        generated_header=customized_header_w_home, \
        generated_drills = drill_button_list, \
        generated_footer=customized_footer)

@app.route(DRILL_URL, methods=DEFAULT_METHODS)
def drill():
    global back_url, previous_url
    back_url = previous_url

    if request.method=='POST':
        mode_string = "'" + request.form['drill_id'] + "'" + " Drill"
            
    previous_url = "/" + inspect.currentframe().f_code.co_name
    customized_footer = original_footer.replace("{{ status }}", STATUS_ACTIVE)
    customized_footer = customized_footer.replace("{{ mode }}", mode_string)
    return render_template(DRILL_TEMPLATE, \
        generated_header=customized_header_wo_home, \
        generated_footer=customized_footer)


@app.route(SETTINGS_URL, methods=DEFAULT_METHODS)
def settings():
    global customized_header, original_footer
    global back_url, previous_url
    back_url = '/'
    previous_url = "/" + inspect.currentframe().f_code.co_name

    customized_footer = original_footer.replace("{{ status }}", STATUS_IDLE)
    customized_footer = customized_footer.replace("{{ mode }}", MODE_SETTINGS)

    return render_template(SETTINGS_TEMPLATE, \
        generated_header=customized_header_w_home, \
        generated_footer=customized_footer)

@app.route('/favicon.ico')
def favicon():
    return send_from_directory(os.path.join(app.root_path, 'static'),
                               'favicon.ico', mimetype='image/vnd.microsoft.icon')


@socketio.on('message')
def handle_message(data):
    print('received message: ' + data)

@socketio.on('change_params')     # Decorator to catch an event named change_params
def change_params(data):          # change_params() is the event callback function.
    print('change_params data: ', data)      # data is a json string: {"speed":102}
    item_to_change = json.loads(data)
    print('change opts: {}'.format(item_to_change))
    # send_msg(PUT_METHOD, OPTS_RSRC, item_to_change)

@socketio.on('pause')
def pause():
    print('received pause.')

@socketio.on('resume')
def resume():
    print('received resume.')

@socketio.on('test')
def test():
    emit('score_update', {"pp": randint(0,3), \
        "bp": 1, "pg": 3, "bg": 2, "ps": 5, "bs": 4, "pt": 6, "bt": 7, "server": "b"})


if __name__ == '__main__':
    global customized_header, original_footer
    
    # TODO: customize header from a file
    display_title = "Red Oak Sports Club  --  Boomer 1"
    display_icon = "/static/red-oaks-icon.png"
    home_button = Markup('          <button type="submit" onclick="window.location.href=\'/\';"> \
            <img src="/static/home.png" style="height:64px;"> \
          </button>')


    with open('./app/templates/includes/header.html', 'r', encoding="utf-8") as file:
        customized_header = Markup(file.read())
    customized_header = customized_header.replace("{{ installation_title }}", display_title)
    customized_header = customized_header.replace("{{ installation_icon }}", display_icon)
    customized_header_w_home = customized_header.replace("{{ home_button }}", home_button)
    customized_header_wo_home = customized_header.replace("{{ home_button }}", "")
    

    my_copyright = "© tennisrobot.com"
    with open('./app/templates/includes/footer.html', 'r', encoding="utf-8") as file:
        original_footer = Markup(file.read())
    original_footer = original_footer.replace("{{ copyright }}", my_copyright)

    # app.run(host="0.0.0.0", port=IP_PORT, debug = True)
    socketio.run(app, host="0.0.0.0", port=IP_PORT, debug = True)
