# Overview
![Block Diagram](./UI_Software_Block_Diagram.svg)

The User Interface uses a touchscreen interfaced by Raspian/Linux drivers (the screen uses HDMI, the touch function uses USB).

The components in the diagram are:
* Boomer base: controls the ball throwing motors and performs ball tracking.  A real-time program written in C
* Web server: serves HTML pages including javascript and css files.  It uses [Flask](https://en.wikipedia.org/wiki/Flask_\(web_framework\)) to serve the pages.  The framework and pages served is written in Python.  The web-server also uses [Flask-SocketIO](https://flask-socketio.readthedocs.io/en/latest/) to send scoring updates to the browser and receive events, like level changes, from the browser.
* The Chromium browser that comes pre-installed with Raspbian.  It is launched on startup and configured to run full-screen so that browser controls (address bar, back button, refresh) are not visible.

A mouse and keyboard will not be available - the only input will be the touchscreen.  This is significant for the following reasons:
* numeric entry is not simple - a touchscreen style keypad would have to be implemented.  Hence numeric controls (like tennis skill level) should use +/- buttons instead of number input
* browser features like hover (tool tips) and focus are not available

# Installation Instructions

For development using VS Code, install the Microsoft Python Extension in order to run under VScode control.

git clone https://github.com/manningt/ui-webserver  (this will be moved to Dave's repo)

Currently another repository has to be cloned: https://github.com/manningt/control_ipc_utils should be cloned to /home/pi/repos.  web-ctrl.py uses python scripts in this repository to send messages to the base in order to set/get information.

The following python packages have to be installed:
```
python3 -m pip install flask-socketio
python3 -m pip install eventlet
```
jquery.js is already installed on Raspbian, but a symbolic link needs to be made.  Run the following script which is the app directory.
```
./make_links.sh
```
# Other dependencies:

git clone https://github.com/davidcjordan/drills to ~/boomer should have already been performed. The file *ui_drill_selection_lists.py* in the drills directory is used by the UI to present a subset of drills to select.

# Implementation notes:
## Drill selection
A file 'ui_drill_selection_lists.py' has lists of drills as follows, where the player list has extra key/value pairs
used to filter drills during the selection process. The test ```len(drill_list[0]) > 2``` tells whether there are filter keys.
```
drill_list_test = [\
   {'id': '100', 'name': 'Test 100'},\
   {'id': '800', 'name': 'Test servoing'},\
...]

drill_list_player = [\
   {'id': '005', 'name': 'Groundstrokes Random 20 balls', 'type': 'Development', 'stroke': 'Ground', 'difficulty': 'Medium'},\
...]
```

The drill_select.html page generates drill buttons as in the following example, although this only has one filter key (speed)
```
<div class="selections">
  <div id="placeHolder"> </div>
  <fieldset id="container" class="radio-text-buttons">
    <input type="radio" id="DRL001" name="drill_id" value="DRL001" data-Type="speed">
    <label for="DRL001" data-Type="speed">speed test</label>
    <input type="radio" id="DRL002" name="drill_id" value="DRL002" data-Type="groundstroke">
    <label for="DRL002" data-Type="groundstroke">2-line groundstroke footwork</label>
    <input type="radio" id="DRL003" name="drill_id" value="DRL003" data-Type="suicide">
    <label for="DRL003" data-Type="suicide">2-line suicide</label>
  </fieldset>
</div>
```