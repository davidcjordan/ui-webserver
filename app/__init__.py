from flask import Flask
from flask_socketio import SocketIO

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
   from app.main.blueprint_games import blueprint_games

   app = Flask(__name__)
   # secret key configured un gunicorn.conf.py
   # app.config['SECRET_KEY'] = 'gjr39dkjn344_!67#'
   
   import logging
   # the following attempts were replaced by gunicorn_log.conf:

   # gunicorn_logger = logging.getLogger('gunicorn')
   # gunicorn_logger.setLevel(logging.DEBUG)
   # app.logger.handlers = gunicorn_logger.handlers

   # gunicorn_access_logger = logging.getLogger('gunicorn.access')
   # gunicorn_access_logger.setLevel(logging.DEBUG)
   # app.logger.handlers = gunicorn_err_logger.handlers
   #? app.logger.addHandler(gunicorn_logger.handlers)

   # gunicorn_err_logger = logging.getLogger('gunicorn.error')
   # gunicorn_err_logger.setLevel(logging.INFO)
   # for handler in gunicorn_err_logger.handlers:
   #    # removes: <StreamHandler <stderr> (NOTSET)>
   #    gunicorn_err_logger.removeHandler(handler)
   # gunicorn_err_file_handler = logging.FileHandler('/run/shm/ui-gunicorn.log')
   # gunicorn_err_file_handler.setFormatter(defaultFormatter)

   # logger = logging.getLogger() 
   # # https://betterstack.com/community/guides/logging/how-to-start-logging-with-flask/
   # app_file_handler = logging.FileHandler('/run/shm/ui.log')
   # defaultFormatter = logging.Formatter('[%(asctime)s] %(levelname)5s [%(module)17s.%(lineno)3s]: %(message)s', datefmt='%Y-%m-%d %H:%M:%S')
   # app_file_handler.setFormatter(defaultFormatter)
   # for handler in app.logger.handlers:
   #    app.logger.removeHandler(handler)
   # app.logger.addHandler(app_file_handler)

   # ?? the following removes flask logging to stderr:
   # from flask.logging import default_handler
   # app.logger.removeHandler(default_handler)

   output_logging_tree = False
   if output_logging_tree:
      import logging_tree
      with open('/tmp/log_cfg_tree.txt', 'w') as f:
         f.write(logging_tree.format.build_description())

   app.logger.setLevel(logging.DEBUG)
   app.debug = debug

   app.register_blueprint(blueprint_core)
   app.register_blueprint(blueprint_camera)
   app.register_blueprint(blueprint_drills)
   app.register_blueprint(blueprint_games)

   # refer to: https://github.com/miguelgrinberg/python-engineio/issues/142
   # the following magically fixed socketio failures logged on the browser console
   ## UPDATE: this problem happens when the browser is running (making socketio calls) and the server is not:
   # from engineio.payload import Payload
   # Payload.max_decode_packets = 64

   socketio.init_app(app)
   from app.main import events

   return app
