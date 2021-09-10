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

# Other dependencies:

There are 3 files (drill_titles_player.py, drill_titles_instructor.py, drill_titles_test.py) which need to be included in the /app directory.  It hasn't been decided how those will get installed.
