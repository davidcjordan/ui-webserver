from flask import Blueprint, current_app, request, render_template

blueprint_camera = Blueprint('blueprint_camera', __name__)
import enum
import json
import datetime
import os.path #for file exists

from app.main.defines import *
from app.func_base import send_gen_vectors_to_base

import sys
sys.path.append(f'{user_dir}/{repos_dir}/control_ipc_utils')
try:
   from control_ipc_defines import *
except:
   current_app.logger.error("Problems with 'control_ipc' modules, please run: git clone https://github.com/davidcjordan/control_ipc_utils")
   exit()

cam_side = None  # a global on which camera is being calibrated
class cam_e(enum.Enum):
  LEFT = 0
  RIGHT = 1

CAM_LABEL = [cam_e.LEFT.name,cam_e.RIGHT.name]

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

class scp_status(enum.Enum):
   OK = 0
   PING_FAILED = 1
   SCP_FAILED = 2

page_styles = []
page_styles.append(Markup('<link rel="stylesheet" href="/static/css/cam-calib.css">'))


@blueprint_camera.route(CAM_LOCATION_URL, methods=DEFAULT_METHODS)
def cam_location():
   from app.main.blueprint_core import display_customization_dict  # using 'global display_customization_dict' did not work

   global cam_side, Units, unit_lengths
 
   current_app.logger.debug(f"CAM_LOCATION_URL request_args: {request.args}")
   cam_side = request.args.get(CAM_SIDE_ID)
   # current_app.logger.debug(f"request for CAM_LOCATION_URL; {CAM_SIDE_ID}={cam_side}")
   if cam_side is None:
      current_app.logger.error(f"request for CAM_LOCATION_URL is missing {CAM_SIDE_ID} arg")
      cam_side = CAM_LABEL[cam_e.LEFT.value]

   # restore measurements, which are A (camera to left doubles), B (cam to right doubles), and Z (cam height)
   cam_measurements_filepath = f'{settings_dir}/{cam_side.lower()}_cam_measurements.json'
   try:
      with open(cam_measurements_filepath) as infile:
         full_line = infile.readline()
         bracket_index = full_line.find(']')
         previous_cam_measurement_mm = json.loads(full_line[0:bracket_index+1])
         # previous_cam_measurement_mm = json.load(infile)
   except:
      current_app.logger.warning(f"using default values for cam_location; couldn't read {cam_measurements_filepath}")
      if cam_side.upper() == CAM_LABEL[cam_e.LEFT.value]:
         previous_cam_measurement_mm = [6402, 12700, 2440]
      else:
         previous_cam_measurement_mm = [12700, 6402, 2440]

   for measurement, value in enumerate(previous_cam_measurement_mm):
      # need the following 8-digit precision in order to maintain the measurements
      inches = 0.03937008 * value
      unit_lengths[measurement][Units.quar.value] = 0
      unit_lengths[measurement][Units.feet.value] = int(inches / 12)
      unit_lengths[measurement][Units.inch.value] = int(inches % 12)
      if ((inches % 12) > (11+ 7/8)):
         unit_lengths[measurement][Units.inch.value] = 0
         unit_lengths[measurement][Units.feet.value] += 1
      else:
         remaining_inches_remainder = inches % 12 % 1
         unit_lengths[measurement][Units.quar.value] = 0
         if (remaining_inches_remainder < 1/8):
            continue
         if (remaining_inches_remainder < 3/8):
            unit_lengths[measurement][Units.quar.value] = 1
         elif (remaining_inches_remainder < 5/8):
            unit_lengths[measurement][Units.quar.value] = 2
         elif (remaining_inches_remainder < 7/8):
            unit_lengths[measurement][Units.quar.value] = 3
         else:
            unit_lengths[measurement][Units.inch.value] += 1
  
   position_options = {}
   for i in Measurement:
      for j in Units:
         main_key = f"{Measurement(i).name}_{Units(j).name}"
         position_options[main_key] = {"dflt":unit_lengths[Measurement(i).value][Units(j).value], "step":1}
         # customize min, max and row title
         if j == Units(0):
            if i == Measurement(0):
               position_options[main_key]["start_div"] = "A"
               # the fence should be 21 ft from the baseline, but allowing smaller
               if cam_side.upper() == CAM_LABEL[cam_e.LEFT.value]:
                  # A should be short; B should be long for on LEFT side
                  position_options[main_key]["min"] = 0
                  position_options[main_key]["max"] = 70
               else:
                  position_options[main_key]["min"] = 0
                  position_options[main_key]["max"] = 80
            if i == Measurement(1):
               position_options[main_key]["start_div"] = "B"
               if cam_side.upper() == CAM_LABEL[cam_e.RIGHT.value]:
                  # A should be short; B should be long for on RIGHT side
                  position_options[main_key]["min"] = 0
                  position_options[main_key]["max"] = 75
               else:
                  position_options[main_key]["min"] = 0
                  position_options[main_key]["max"] = 80
            if i == Measurement(2):
               position_options[main_key]["start_div"] = "Height"
               position_options[main_key]["min"] = 6
               position_options[main_key]["max"] = 20
         if j == Units(1):
               position_options[main_key]["min"] = 0
               position_options[main_key]["max"] = 11
         if j == Units(2):
            position_options[main_key]["min"] = 0
            position_options[main_key]["max"] = 3
            position_options[main_key]["end_div"] = "Y"
   # print(f"position_options={position_options}")

   return render_template(CAM_LOCATION_TEMPLATE, \
      home_button = my_home_button, \
      page_title = f"Enter {cam_side} Camera Location", \
      installation_icon = display_customization_dict['icon'], \
      options = position_options, \
      footer_center = display_customization_dict['title'])


@blueprint_camera.route(CAM_CALIB_URL, methods=DEFAULT_METHODS)
def cam_calib():
   from app.main.blueprint_core import display_customization_dict  # using 'global display_customization_dict' did not work

   global cam_side, Units, unit_lengths

   new_cam_measurement_mm = [0]*3
   new_cam_location_mm = [0]*3

   change_from_persisted_measurement = False

   if request.method=='POST':
      current_app.logger.debug(f"POST to CALIB (location) request.form: {request.form}")
      # example: 
      # POST to CALIB (location) request.form: ImmutableMultiDict([('x_feet', '6'), ('x_inch', '6'), ('x_quar', '2'), ('y_feet', '54'), ('y_inch', '6'), ('y_quar', '3'), ('z_feet', '13'), ('z_inch', '8'), ('z_quar', '3')])
      for i in Measurement:
         for j in Units:
            key = f"{Measurement(i).name}_{Units(j).name}"
            if key in request.form:
               # if the measurement differs, set that there was a change
               new_value = int(request.form[key])
               if ((new_value != unit_lengths[Measurement(i).value][Units(j).value]) and not change_from_persisted_measurement):
                  change_from_persisted_measurement = True
               current_app.logger.debug(f"key={key} prev={unit_lengths[Measurement(i).value][Units(j).value]} new={new_value} change={change_from_persisted_measurement}")
               if j == Units['feet']:
                  new_cam_measurement_mm[Measurement(i).value] += new_value * 12 * INCHES_TO_MM
               if j == Units['inch']:
                  new_cam_measurement_mm[Measurement(i).value] += new_value * INCHES_TO_MM
               if j == Units['quar']:
                  new_cam_measurement_mm[Measurement(i).value] += new_value * (INCHES_TO_MM/4)
            else:
               current_app.logger.error("Unknown key '{key}' in POST of camera location measurement")

      if change_from_persisted_measurement:
         #TODO: move persist values to func_base

         current_app.logger.debug(f"Updating {cam_side} cam_measurements and cam_location")
         #persist new A,B, Z measurements and cam_location for base to use to generate correction vectors
         dt = datetime.datetime.now()
         dt_str = dt.strftime("%Y-%m-%d_%H-%M")

         # convert from floating point to integer:
         for i in Measurement:
            new_cam_measurement_mm[Measurement(i).value] = int(new_cam_measurement_mm[Measurement(i).value])
         
         output_line = json.dumps(new_cam_measurement_mm) + " " +  dt_str + "\n"
         with open(f'{settings_dir}/{cam_side.lower()}_cam_measurements.json', 'r+') as outfile:
            lines = outfile.readlines() # read old content
            outfile.seek(0) # go back to the beginning of the file
            outfile.write(output_line) # write new content at the beginning
            for line in lines: # write old content after new
               outfile.write(line)

         # convert measurements (A & B) to camera_location X and Y and save in file
         court_width_mm = 36 * 12 * INCHES_TO_MM
         doubles_width_mm = 4.5 * 12 * INCHES_TO_MM
         court_depth_mm = 78/2 * 12 * INCHES_TO_MM
         
         # Dave's code: (in C)
         # 		x1 = (1296 + A*A - B*B)/72;
			# 		y1 = sqrt(A*A - x1*x1);
			# 		Xworld = x1 - 4.5;	// in feet
			# 		Yworld = y1 + 39;	// in feet
         # A=20.00 B=20.00 x1=18.00 y1=8.72 Xworld=4114.8 Yworld=14544.4
         # A=25.45 B=25.45 x1=18.00 y1=17.99 Xworld=4114.8 Yworld=17371.1

         cam_to_left_doubles = new_cam_measurement_mm[Measurement.a.value]
         cam_to_right_doubles = new_cam_measurement_mm[Measurement.b.value]

         # pow(number, 2) is the same as squaring;  pow(number, 0.5) is squareroot
         x1 = (pow(court_width_mm, 2) + pow(cam_to_left_doubles, 2) - pow(cam_to_right_doubles, 2)) / (court_width_mm*2)
         if not isinstance(x1,float):
            current_app.logger.error(f"x1 distance calculation error; x1={x1}")
            x1 = 0
         new_cam_location_mm[Axis.x.value] = int(x1 - doubles_width_mm)

         Y = pow((pow(cam_to_left_doubles, 2) - pow(x1, 2)), 0.5) + court_depth_mm
         if not isinstance(Y,float):
            current_app.logger.error(f"Y distance calculation error; y={Y}")
            Y = 0
         new_cam_location_mm[Axis.y.value] = int(Y)
         new_cam_location_mm[Axis.z.value] = new_cam_measurement_mm[Measurement.z.value]

         #TODO: move persist values to func_base
         output_line = json.dumps(new_cam_location_mm) + " " +  dt_str + "\n"
         with open(f'{settings_dir}/{cam_side.lower()}_cam_location.json', 'r+') as outfile:
            lines = outfile.readlines() # read old content
            outfile.seek(0) # go back to the beginning of the file
            outfile.write(output_line) # write new content at the beginning
            for line in lines: # write old content after new
               outfile.write(line)
         # with open(f"{settings_dir}/{cam_side.lower()}_cam_location.json", "w") as outfile:
         #    json.dump(new_cam_location_mm, outfile)
      else:
         current_app.logger.debug(f"No change in {cam_side} cam measurements, not updating cam_measurements or cam_location")


   # copy the lastest PNG from the camera to the base 
   scp_rc = scp_court_png(side_name = cam_side.lower())
   if (scp_rc == scp_status.PING_FAILED.value):
      this_page_title = f"ERROR: cannot connect to the {cam_side.title()} camera"
   elif (scp_rc == scp_status.SCP_FAILED.value):
      this_page_title = f"ERROR: image transfer from {cam_side.title()} camera failed"
   else:
      this_page_title = "Enter Court Coordinates"

   court_point_dict_index = 0
   if cam_side.upper() == CAM_LABEL[cam_e.RIGHT.value]:
      court_point_dict_index = 1

   read_ok, temp_dict = read_court_points_file(cam_side)
   if read_ok:
      court_points_dict_list[court_point_dict_index] = temp_dict

   # mode_str = f"Court Points"
   return render_template(CAM_CALIBRATION_TEMPLATE, \
      home_button = my_home_button, \
      page_title = this_page_title, \
      installation_icon = display_customization_dict['icon'], \
      image_path = "/static/" + cam_side.lower() + "_court.png", \
      court_point_coords = court_points_dict_list[court_point_dict_index], \
      # court_point_coords = COURT_POINT_KEYS_W_AXIS, \
      footer_center = display_customization_dict['title'])



@blueprint_camera.route(CAM_CALIB_DONE_URL, methods=DEFAULT_METHODS)
def cam_calib_done():
   global cam_side, new_cam_location_mm
   from app.main.blueprint_core import display_customization_dict  # using 'global display_customization_dict' did not work

   # current_app.logger.debug(f"POST to CALIB_DONE request: {request}")
   # current_app.logger.debug(f"POST to CALIB_DONE request.content_type: {request.content_type}")

   result = ""
   received_court_points_invalid = False

   if request.method=='POST':
      if cam_side == None:
         # this happens during debug, when using the browser 'back' to navigate to CAM_CALIB_URL
         cam_side = CAM_LABEL[cam_e.LEFT.value]
         current_app.logger.warning("cam_side was None in cam_calib_done")

      if (request.content_type.startswith('application/json')):
         # >> not supporting a javascript POST of json; left for reference
         # print(f"request to calib: {request.json}")
         # request.json example: {'fblx': 883, 'fbly': 77, 'fbrx': 1193, 'fbry': 91,\
         #  'nslx': 503, 'nsly': 253, 'nscx': 747, 'nscy': 289, 'nsrx': 1065, 'nsry': 347,\
         #  'nblx': 187, 'nbly': 397, 'nbrx': 933, 'nbry': 653}
         c = request.json
         coord_args = (f"--fblx {c['fblx']} --fbly {c['fbly']}"
            f" --fbrx {c['fbrx']} --fbry {c['fbry']} --nblx {c['nblx']} --nbly {c['nbly']}"
            f" --nbrx {c['nbrx']} --nbry {c['nbry']} --nslx {c['nslx']} --nsly {c['nsly']}"
            f" --nscx {c['nscx']} --nscy {c['nscy']} --nsrx {c['nsrx']} --nsry {c['nsry']}"
            f" --camx {new_cam_location_mm[Axis.x.value]} --camy {new_cam_location_mm[Axis.y.value]} --camz {new_cam_location_mm[Axis.z.value]}" )
      else:
         current_app.logger.debug(f"POST to CALIB_DONE request.form: {request.form}")
         # example: ImmutableMultiDict([('FBLX', '322'), ('FBLY', '72'), ('FBRX', '612'), ('FBRY', '54'), ('NSLX', '248'), ('NSLY', '328'), ('NSCX', '602'), ('NSCY', '292'), ('NSRX', '904'), ('NSRY', '262'), ('NBLX', '146'), ('NBLY', '686'), ('NBRX', '1244'), ('NBRY', '482')])
         court_point_dict_index = 0
         if cam_side.upper() == CAM_LABEL[cam_e.RIGHT.value]:
            court_point_dict_index = 1

         if len(request.form) > 0:
            for coordinate_id in COURT_POINT_KEYS_W_AXIS:
               if coordinate_id in request.form:
                  this_coord_point = coordinate_id[0:3]
                  this_coord_axis = Axis[coordinate_id[3:4].lower()].value
                  # current_app.logger.info(f"Before: court_point_dict_index={court_point_dict_index} this_coord_point={this_coord_point} this_coord_axis={this_coord_axis}")
                  court_points_dict_list[court_point_dict_index][this_coord_point][this_coord_axis] = int(request.form[coordinate_id])
               else:
                  current_app.logger.error(f"Missing {coordinate_id} in cam_calib_done post.")
                  received_court_points_invalid = True
         else:
            current_app.logger.debug("POST to CALIB_DONE request.form is zero length; using emit data instead")

         # do some sanity checking:
         if (received_court_points_invalid or (court_points_dict_list[court_point_dict_index]["NBR"][1] < 1)):
            current_app.logger.error(f"Invalid court_point values: {court_points_dict_list[court_point_dict_index]}")
            result = f"FAILED: {cam_side.title()} camera court points are invalid."
         else:
            #TODO: move persist values to func_base
            #persist values for base to use to generate correction vectors
            dt = datetime.datetime.now()
            dt_str = dt.strftime("%Y-%m-%d_%H-%M")
            output_line = json.dumps(court_points_dict_list[court_point_dict_index]) + " " +  dt_str + "\n"
            court_points_filename = f'{settings_dir}/{cam_side.lower()}_court_points.json'
            if not os.path.exists(court_points_filename):
               open(court_points_filename, 'a').close()
            with open(court_points_filename, 'r+') as outfile:
               lines = outfile.readlines() # read old content
               outfile.seek(0) # go back to the beginning of the file
               outfile.write(output_line) # write new content at the beginning
               for line in lines: # write old content after new
                  outfile.write(line)

            # tell the bbase to regenerate correction vectors; the '1' in the value is not used and is there for completeness
            vec_gen_ok = send_gen_vectors_to_base(court_point_dict_index)
            # current_app.logger.error(f"send_gen_vectors_to_base() returned: {vec_gen_ok}")
            if (not vec_gen_ok):
               result = f"FAILED: {cam_side.title()} camera correction vector generation failed."

   page_js = []
   page_js.append(Markup('<script src="/static/js/timed-redirect.js" defer></script>'))
 
   button_label = "Camera Calibration"
   return render_template(CHOICE_INPUTS_TEMPLATE, \
      home_button = my_home_button, \
      page_title = f"{cam_side} Camera Calibration Finished.", \
      installation_icon = display_customization_dict['icon'], \
      message = result, \
      # UI decision: redirect after seconds  -or-  have user click 'OK'
      page_specific_js = page_js, \
      # onclick_choices = [{"value": "OK", "onclick_url": MAIN_URL}], \
      footer_center = display_customization_dict['title'])


@blueprint_camera.route(CAM_VERIF_URL, methods=DEFAULT_METHODS)
def cam_verif():

   from app.main.blueprint_core import display_customization_dict  # using 'global display_customization_dict' did not work
   
   court_point_dict_index = 0
   # not using global cam_side:
   cam_side = CAM_SIDE_LEFT_LABEL.lower()

   if request.method=='POST':
      current_app.logger.debug(f"POST to CAM_VERIF_URL request.form: {request.form}")
      # POST to CAM_LOCATION request.form: ImmutableMultiDict([('choice', 'Left Cam Calib')])
      if ('image_path' in request.form) and 'left' in request.form['image_path']:
         court_point_dict_index = 1
         cam_side = CAM_SIDE_RIGHT_LABEL.lower()
 
   read_ok, temp_dict = read_court_points_file(cam_side)
   if read_ok:
      court_points_dict_list[court_point_dict_index] = temp_dict
      # current_app.logger.debug(f"cam_verif; court_points={court_points_dict_list}")
   else:
      this_page_title = f"ERROR: reading the {CAM_SIDE_LEFT_LABEL.title()} court point location file failed"
      # if read failed, then the court_points_dict_list should be what it was initialized to - all zeros

   scp_rc = scp_court_png(side_name = cam_side)
   if (scp_rc == scp_status.PING_FAILED.value):
      this_page_title = f"ERROR: cannot connect to the {cam_side.title()} camera"
   elif (scp_rc == scp_status.SCP_FAILED.value):
      this_page_title = f"ERROR: transferring image from the {cam_side.title()} camera failed"
   else:
      this_page_title = "Check court point locations"

   return render_template(CAM_VERIFICATION_TEMPLATE, \
      home_button = my_home_button, \
      installation_icon = display_customization_dict['icon'], \
      footer_center = display_customization_dict['title'], \
      page_title = this_page_title, \
      image_path = "/static/" + cam_side + "_court.png", \
      court_point_coords = court_points_dict_list[court_point_dict_index])


def scp_court_png(side_name='Left', frame='even'):
   from subprocess import Popen

   scp_return_code = scp_status.OK.value

   # current_app.logger.debug(f"scp_court_png: side_name={side} frame={frame}")
   source_path = f"{side_name.lower()}:/run/shm/frame_{frame}.png"
   destination_path = f"{user_dir}/{boomer_dir}/{side_name.lower()}_court.png"
   # current_app.logger.info(f"BEFORE: scp {source_path} {destination_path}")

   p = Popen(["ping", "-c1", "-W1",f"{side_name.lower()}"], shell=False)
   p.wait()
   if p.returncode != 0:
      current_app.logger.error(f"FAILED: ping {side_name.lower()}")
      scp_return_code = scp_status.PING_FAILED.value
   else:
      # the q is for quiet
      p = Popen(["scp", "-q", "-o ConnectTimeout=3",source_path, destination_path], shell=False)
      rc = p.wait()
      stdoutdata, stderrdata = p.communicate()
      if p.returncode != 0:
         current_app.logger.error(f"FAILED: scp {source_path} {destination_path}; error_code={p.returncode}")
         scp_return_code = scp_status.SCP_FAILED.value
      else:
         current_app.logger.info(f"OK: scp {source_path} {destination_path}")

   return scp_return_code


def read_court_points_file(side_name = 'Left'):
   court_points_dict = {}
   read_ok = True
   import json
   try:
      with open(f'{settings_dir}/{side_name.lower()}_court_points.json') as f:
         file_lines = f.readlines()
         first_line_json = file_lines[0].split("}")[0] + "}"
         # current_app.logger.debug(f"first_line_json={first_line_json}")
         court_points_dict = json.loads(first_line_json)
         current_app.logger.debug(f"{side_name.lower()} court_points={court_points_dict}")
   except:
      current_app.logger.warning(f"read failed: {settings_dir}/{side_name.lower()}_court_points.json")
      read_ok = False

   return read_ok, court_points_dict
