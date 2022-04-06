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
python3 -m pip install waitress
```
jquery.js is already installed on Raspbian, but a symbolic link needs to be made.  Run the following script which is the app directory.
```
./make_links.sh
```
# Other dependencies:

git clone https://github.com/davidcjordan/drills to ~/boomer should have already been performed. The file *ui_drill_selection_lists.py* in the drills directory is used by the UI to present a subset of drills to select.

# Implementation notes:

## templates
The base template has a section for page specific javascript.  This is used on the following pages:
* select.html: whether to enable filtrify (or not); NOT include
* game and drill.html: enable pause_resume, number-picker
* choice_inputs: enable emits per radio button

## Flow
###
* Main (POST)-> drill_select_type (POST with form)-> select (POST on start button) -> drill
* Main (POST-with-mode=workout)-> select
* Main (POST)-> game_options

## Drill selection
Refer to [Drill Categorization and Filtering](https://docs.google.com/document/d/1V0n3HToN0-XzfUT8dVTWYwKsZZYaLfdsvD9uuKcMHIQ)

### Lists of Drills/Workflows
Without filtering a drill list is as follows:
```
drill_list_test = [\
   {'id': '100', 'name': 'Test 100'},\
   {'id': '800', 'name': 'Test servoing'},\
...]
```

### Filters
Filters are used to reduce the number of buttons (drills or workflows) the user can select from - to shrink the list of drills from an overwhelming number.

To use filters on the select.html page, a filter list needs to be provided, e.g.
```
drill_filter_list = ['data-Type', 'data-Stroke', 'data-Difficulty']
```
The 'data-' prefix is used by the filtrify javascript to filter the items.  So the example filters are Type, Stroke and Difficulty.

Additionally, each drill in the drill list needs to have a  key 'filter_values' containing a list of values to assign for each filter, e.g.:
```
{'id': '005', 'name': 'Groundstrokes Random 20 balls', 'filter_values': ['Development', 'Ground', 'Medium']}

```
When a filter_list is provided, and the drill_list includes filter_values, the select.html buttons will have extra attribute for each filter, e.g. 
```
data-Type="Development"
```
