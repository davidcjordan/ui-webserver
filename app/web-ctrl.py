#!/usr/bin/env python3

#from flask import Flask, flash, redirect, render_template, request, session, abort
from flask import Flask, render_template, Response, request, redirect, url_for, Markup, send_from_directory
from flask_socketio import SocketIO, emit

import inspect
import os  # for sending favicon 

IP_PORT = 1111 # picked what is hopefully an unused port  (can't use 44)
DEFAULT_METHODS = ['POST', 'GET']

# note: Flask looks for following in the 'templates' directory
MAIN_URL = '/'
GAME_OPTIONS_URL = '/game_options'
ACTIVE_URL = '/active'
DRILL_SELECTION_URL = '/drill_selection'
WORKOUT_SELECTION_URL = '/workout_selection'

MAIN_TEMPLATE = 'index.html'
GAME_OPTIONS_TEMPLATE = '/layouts/game_options.html'
ACTIVE_TEMPLATE = '/layouts/active.html'
DRILL_SELECTION_TEMPLATE = '/layouts/drill_selection.html'
WORKOUT_SELECTION_TEMPLATE = '/layouts/workout_selection.html'

STATUS_IDLE = "Idle"
STATUS_ACTIVE = "Active"
MODE_NONE = " --"
MODE_GAME = "Game --"
MODE_DRILL_NOT_SELECTED = "Drills --"
MODE_WORKOUT_NOT_SELECTED = "Workout --"
MODE_WORKOUT_SELECTED = "Workout: "

previous_url = None
back_url = None


app = Flask(__name__)
app.config['SECRET_KEY'] = 'secret!'
# didn't find how to have multiple allowed origins
# socketio = SocketIO(app, cors_allowed_origins="https://cdnjs.cloudflare.com http://localhost")
# socketio = SocketIO(app, cors_allowed_origins="http://localhost")
socketio = SocketIO(app, cors_allowed_origins="*")

@app.route(MAIN_URL, methods=DEFAULT_METHODS)
def index():
    global customized_header, original_footer
    global back_url, previous_url
    back_url = previous_url = "/"
    customized_footer = original_footer.replace("{{ status }}", STATUS_IDLE)
    customized_footer = customized_footer.replace("{{ mode }}", MODE_NONE)
    return render_template(MAIN_TEMPLATE, \
        generated_header=customized_header, \
        generated_footer=customized_footer)

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

@app.route(GAME_OPTIONS_URL, methods=DEFAULT_METHODS)
def game_options():
    global customized_header, original_footer
    global back_url, previous_url
    back_url = '/'
    previous_url = "/" + inspect.currentframe().f_code.co_name
    customized_footer = original_footer.replace("{{ status }}", STATUS_IDLE)
    customized_footer = customized_footer.replace("{{ mode }}", MODE_GAME)
    return render_template(GAME_OPTIONS_TEMPLATE, \
        generated_header=customized_header, \
        generated_footer=customized_footer)

@app.route(ACTIVE_URL, methods=DEFAULT_METHODS)
def active():
    global customized_header, original_footer
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

    if request.method=='POST':
        if GAME_OPTIONS_URL in previous_url:
            if (request.form['player_count'] == "2"):
                mode_string = "Doubles "
            else:
                mode_string = "Singles "

            if (request.form['game_type'] == "tie_breaker"):
                mode_string += "Tie Breaker"
            else:
                mode_string += "Game"
        elif DRILL_SELECTION_URL in previous_url:
            mode_string = "'" + request.form['drill_id'] + "'" + " Drill"
        else:
            mode_string = "NEED TO FIX"
            
    previous_url = "/" + inspect.currentframe().f_code.co_name
    if not already_on_active_page:
        customized_footer = original_footer.replace("{{ status }}", STATUS_ACTIVE)
        customized_footer = customized_footer.replace("{{ mode }}", mode_string)
        return render_template(ACTIVE_TEMPLATE, \
        generated_header=customized_header, \
        generated_footer=customized_footer)
    else:
        return None


@app.route(DRILL_SELECTION_URL, methods=DEFAULT_METHODS)
def drill_selection():
    global customized_header, original_footer
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
        generated_header=customized_header, \
        generated_drills = drill_button_list, \
        generated_footer=customized_footer)

@app.route(WORKOUT_SELECTION_URL, methods=DEFAULT_METHODS)
def workout_selection():
    global customized_header, original_footer
    global back_url, previous_url
    back_url = '/'
    previous_url = "/" + inspect.currentframe().f_code.co_name

    customized_footer = original_footer.replace("{{ status }}", STATUS_IDLE)
    customized_footer = customized_footer.replace("{{ mode }}", MODE_WORKOUT_NOT_SELECTED)

    return render_template("WORKOUT_SELECTION_TEMPLATE.html", \
        generated_header=customized_header, \
        generated_footer=customized_footer)

@app.route('/favicon.ico')
def favicon():
    return send_from_directory(os.path.join(app.root_path, 'static'),
                               'favicon.ico', mimetype='image/vnd.microsoft.icon')


@socketio.on('message')
def handle_message(data):
    print('received message: ' + data)

@socketio.on('change_params')                          # Decorator to catch an event called "my event":
def change_params(data):                        # test_message() is the event callback function.
    print('Received data: ', data)
    # emit('my response', {'data': 'got it!'})      # Trigger a new event called "my response" 


if __name__ == '__main__':
    global customized_header, original_footer
    
    # TODO: customize header from a file
    display_title = "Red Oak Sports Club  --  Boomer 1"
    display_icon = "/static/red-oaks-icon.png"

    with open('./app/templates/includes/header.html', 'r', encoding="utf-8") as file:
        customized_header = Markup(file.read())
    customized_header = customized_header.replace("{{ installation_title }}", display_title)
    customized_header = customized_header.replace("{{ installation_icon }}", display_icon)

    my_copyright = "© tennisrobot.com"
    with open('./app/templates/includes/footer.html', 'r', encoding="utf-8") as file:
        original_footer = Markup(file.read())
    original_footer = original_footer.replace("{{ copyright }}", my_copyright)

    # app.run(host="0.0.0.0", port=IP_PORT, debug = True)
    socketio.run(app, host="0.0.0.0", port=IP_PORT, debug = True)
