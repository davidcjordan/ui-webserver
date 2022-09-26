from flask import Blueprint, current_app, request, render_template

blueprint_camera = Blueprint('blueprint_camera', __name__)

import os, sys
current_dir = os.path.dirname(os.path.realpath(__file__))
parent_dir = os.path.dirname(current_dir)

sys.path.append(current_dir)
from defines import *

cam_side = None  # a global on which camera is being calibrated

import enum
class Measurement(enum.Enum):
   a = 0
   b = 1
   z = 2
class Axis(enum.Enum):
   x = 0
   y = 1
   z = 2
class English_units(enum.Enum):
   feet = 0
   inch = 1
   quar = 2 #quarter
class Metric_units(enum.Enum):
   meter = 0
   cm = 1
   mm = 2

Units = English_units
INCHES_TO_MM = 25.4

COURT_POINT_KEYS = ['FBL','FBR', 'NSL', 'NSC', 'NSR', 'NBL', 'NBR']
court_points_dict_list = [{}, {}]
for key in COURT_POINT_KEYS:
   court_points_dict_list[0][key] = [0,0]
   court_points_dict_list[1][key] = [0,0]

COURT_POINT_KEYS_W_AXIS = []
for court_point_id in COURT_POINT_KEYS:
   for axis in Axis:
      if (axis.name == 'z'):
         continue
      else:
         COURT_POINT_KEYS_W_AXIS.append(f"{court_point_id}{axis.name.upper()}")

# unit_lengths are the measurements (A,B,Z) converted to feet, inches and quarter inches
unit_lengths = [[0 for _ in range(len(Measurement))] for _ in range(len(Units))]



@blueprint_camera.route(CAM_VERIF_URL, methods=DEFAULT_METHODS)
def cam_verif():
   global customization_dict
   court_point_dict_index = 0
   cam_name = CAM_SIDE_LEFT_LABEL.lower()

   if request.method=='POST':
      current_app.logger.debug(f"POST to CAM_VERIF_URL request.form: {request.form}")
      # POST to CAM_LOCATION request.form: ImmutableMultiDict([('choice', 'Left Cam Calib')])
      if ('image_path' in request.form) and 'left' in request.form['image_path']:
         court_point_dict_index = 1
         cam_name = CAM_SIDE_RIGHT_LABEL.lower()
 
   read_ok, temp_dict = read_court_points_file(cam_name)
   if read_ok:
      court_points_dict_list[court_point_dict_index] = temp_dict
   # current_app.logger.debug(f"cam_verif; court_points={court_points_dict_list}")

   scp_court_png(side = cam_name)

   #TODO: handle scp or court_points failure

   return render_template(CAM_VERIFICATION_TEMPLATE, \
      home_button = my_home_button, \
      page_title = "Check court point locations.", \
      installation_icon = customization_dict['icon'], \
      image_path = "/static/" + cam_name + "_court.png", \
      court_point_coords = court_points_dict_list[court_point_dict_index], \
      footer_center = customization_dict['title'])


def scp_court_png(side='Left', frame='even'):
   # current_app.logger.debug(f"scp_court_png: side={side} frame={frame}")
   source_path = f"{side.lower()}:/run/shm/frame_{frame}.png"
   destination_path = f"{user_dir}/{boomer_dir}/{side.lower()}_court.png"
   # current_app.logger.info(f"BEFORE: scp {source_path} {destination_path}")
   from subprocess import Popen
   # the q is for quiet
   p = Popen(["scp", "-q", source_path, destination_path], shell=False)
   rc = p.wait()
   stdoutdata, stderrdata = p.communicate()
   if p.returncode != 0:
      current_app.logger.error(f"FAILED: scp {source_path} {destination_path}; error_code={p.returncode}")
   else:
      current_app.logger.info(f"OK: scp {source_path} {destination_path}")


def read_court_points_file(side_name = 'left'):
   court_points_dict = {}
   read_ok = True
   import json
   try:
      with open(f'{settings_dir}/{side_name}_court_points.json') as f:
         file_lines = f.readlines()
         first_line_json = file_lines[0].split("}")[0] + "}"
         # current_app.logger.debug(f"first_line_json={first_line_json}")
         court_points_dict = json.loads(first_line_json)
         current_app.logger.debug(f"{side_name} court_points={court_points_dict}")
   except:
      current_app.logger.warning(f"read failed: {settings_dir}/{side_name}_court_points.json")
      read_ok = False

   return read_ok, court_points_dict
