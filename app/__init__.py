from flask import Flask
from flask_socketio import SocketIO

socketio = SocketIO()

def create_app(debug=False):
   """Create an application."""
   app = Flask(__name__)
   app.debug = debug
   app.config['SECRET_KEY'] = 'gjr39dkjn344_!67#'

   from .main import main as main_blueprint
   app.register_blueprint(main_blueprint)

   # refer to: https://github.com/miguelgrinberg/python-engineio/issues/142
   # the following magically fixed socketio failures logged on the browser console
   from engineio.payload import Payload
   Payload.max_decode_packets = 64

   if (0):
      #TODO: fix logging to file
      import logging
      log_level = logging.DEBUG
      for handler in app.logger.handlers:
         app.logger.removeHandler(handler)
      # https://betterstack.com/community/guides/logging/how-to-start-logging-with-flask/
         #  root = os.path.dirname(os.path.abspath(__file__))
         #  logdir = os.path.join(root, 'logs')
         #  if not os.path.exists(logdir):
         #      os.mkdir(logdir)
         #  log_file = os.path.join(logdir, 'app.log')
      handler = logging.FileHandler('/run/shm/ui.log')
      defaultFormatter = logging.Formatter('[%(asctime)s]%(levelname)s: %(message)s')
      handler.setFormatter(defaultFormatter)
      handler.setLevel(log_level)
      app.logger.addHandler(handler)
      app.logger.setLevel(log_level)

   socketio.init_app(app)

   # from waitress import serve
   # import sys
   # try:
   #    serve(app, host="0.0.0.0", port="1111")
   #    app.logger.info("started server")
   # except Exception as e:
   #    print(e)
   #    sys.exit(1)

   return app
