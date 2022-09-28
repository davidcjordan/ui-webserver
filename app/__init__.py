from flask import Flask
from flask_socketio import SocketIO

import logging
gunicorn_logger = logging.getLogger('gunicorn.warning')
log_level = logging.DEBUG
# https://betterstack.com/community/guides/logging/how-to-start-logging-with-flask/
   #  root = os.path.dirname(os.path.abspath(__file__))
   #  logdir = os.path.join(root, 'logs')
   #  if not os.path.exists(logdir):
   #      os.mkdir(logdir)
   #  log_file = os.path.join(logdir, 'app.log')
file_handler = logging.FileHandler('/run/shm/ui.log')
defaultFormatter = logging.Formatter('[%(asctime)s]%(levelname)s in %(module)s: %(message)s')
file_handler.setFormatter(defaultFormatter)
file_handler.setLevel(log_level)

import eventlet
eventlet.monkey_patch()
# without the following, the following error occurs: RuntimeError: Second simultaneous read on fileno N detected
# occurs because of the FIFO read.  Look into threading control to control access to the FIFO?  Use eventlet semaphore?
import eventlet.debug
eventlet.debug.hub_prevent_multiple_readers(False)

socketio = SocketIO() # logger=True)

def create_app(debug=False):
   from app.main.blueprint_core import blueprint_core
   from app.main.blueprint_camera import blueprint_camera
   from app.main.blueprint_drills import blueprint_drills

   app = Flask(__name__)
   app.debug = debug
   app.config['SECRET_KEY'] = 'gjr39dkjn344_!67#'

   app.register_blueprint(blueprint_core)
   app.register_blueprint(blueprint_camera)
   app.register_blueprint(blueprint_drills)

   # refer to: https://github.com/miguelgrinberg/python-engineio/issues/142
   # the following magically fixed socketio failures logged on the browser console
   from engineio.payload import Payload
   Payload.max_decode_packets = 64

   # for handler in app.logger.handlers:
   #    # removes: <StreamHandler <stderr> (NOTSET)>
   #    app.logger.removeHandler(handler)
   # from flask.logging import default_handler
   # app.logger.removeHandler(default_handler)

   app.logger.addHandler(file_handler)
   app.logger.setLevel(log_level)

   # app.logger.addHandler(gunicorn_logger.handlers)
   # app.logger.handlers = gunicorn_logger.handlers
   # app.logger.setLevel(gunicorn_logger.level)

   socketio.init_app(app)
   from app.main import events

   return app
