#!/usr/bin/env python3

"""
Does the following:
 - reads left/right_cam_parameters.txt
 - generates left/right_cam_location.json: [x,y,z] in mm
 - generates left/right_court_points.json: [x,y,z] in mm
 returns 0 on pass; 1 on failure
"""
import argparse
import logging
import sys
import json
import datetime
import enum

if __name__ == '__main__':
  # shell_rc = 1

  BASE_PATH = "/home/pi/boomer"
  INPUT_FILE_PREFIXES = ["left", "right"]
  INPUT_FILE_SUFFIX = "_cam_parameters.txt"
  INPUT_FILE_PATH = "/"
  OUTPUT_FILE_PATH = "/test/"
  LOCATION_FILE_SUFFIX = "_cam_location.json"
  POINTS_FILE_SUFFIX = "_court_points.json"

  dt = datetime.datetime.now()
  dt_str = dt.strftime("%Y-%m-%d_%H-%M")

  COURT_POINT_KEYS = ['FBL','FBR', 'NSL', 'NSC', 'NSR', 'NBL', 'NBR']
  court_points_dict = {}
  for key in COURT_POINT_KEYS:
    court_points_dict[key] = [0,0]

  class Axis(enum.Enum):
   x = 0
   y = 1

  for file_prefix in INPUT_FILE_PREFIXES:
    # with open(f'/home/pi/boomer/this_boomers_data/{file_prefix}{INPUT_FILE_BASE_NAME}') as infile:
    in_filename = f'{BASE_PATH}{INPUT_FILE_PATH}{file_prefix}{INPUT_FILE_SUFFIX}'
    with open(in_filename) as infile:
      line_num = 0
      for line in infile:
        line_num += 1
        # generate cam location file: get value strings, convert to floating point and write out json
        if line_num == 3:
          # read X,Y for FBL, FBR, NBR, NBL
          court_point_values = line.split()
          required_number_of_points = 4 * 2 # 4 points times 2 axis
          if len(court_point_values) != required_number_of_points:
              print(f"There are not {required_number_of_points} values in line {line_num} of file '{in_filename}' line= '{line}'")
              sys.exit(1)
          court_points_dict["FBL"][Axis.x.value] = float(court_point_values[0])
          court_points_dict["FBL"][Axis.y.value] = float(court_point_values[1])
          court_points_dict["FBR"][Axis.x.value] = float(court_point_values[2])
          court_points_dict["FBR"][Axis.y.value] = float(court_point_values[3])
          court_points_dict["NBR"][Axis.x.value] = float(court_point_values[4])
          court_points_dict["NBR"][Axis.y.value] = float(court_point_values[5])
          court_points_dict["NBL"][Axis.x.value] = float(court_point_values[6])
          court_points_dict["NBL"][Axis.y.value] = float(court_point_values[7])

        if line_num == 4:
          # read X,Y for NSL, NSL, NSR
          court_point_values = line.split()
          required_number_of_points = 3 * 2
          if len(court_point_values) != required_number_of_points:
              print(f"There are not {required_number_of_points} values in line {line_num} of file '{in_filename}' line= '{line}'")
              sys.exit(1)
          court_points_dict["NSL"][Axis.x.value] = float(court_point_values[0])
          court_points_dict["NSL"][Axis.y.value] = float(court_point_values[1])
          court_points_dict["NSC"][Axis.x.value] = float(court_point_values[2])
          court_points_dict["NSC"][Axis.y.value] = float(court_point_values[3])
          court_points_dict["NSR"][Axis.x.value] = float(court_point_values[4])
          court_points_dict["NSR"][Axis.y.value] = float(court_point_values[5])

          # have court points, so write to file:
          output_line = json.dumps(court_points_dict) + " " +  dt_str + "\n"
          # print(output_line)
          with open(f'{BASE_PATH}{OUTPUT_FILE_PATH}{file_prefix}{POINTS_FILE_SUFFIX}', 'r+') as outfile:
            lines = outfile.readlines() # read old content
            outfile.seek(0) # go back to the beginning of the file
            outfile.write(output_line) # write new content at the beginning
            for line in lines: # write old content after new
              outfile.write(line)

        if line_num == 19:
          # print("line19=" + line)
          cam_location_axis = line.split()
          for i, value in enumerate(cam_location_axis):
            cam_location_axis[i] = float(value)
          # print(f"cam_location_axis= {cam_location_axis}")
          output_line = json.dumps(cam_location_axis) + " " +  dt_str + "\n"
          with open(f'{BASE_PATH}{OUTPUT_FILE_PATH}{file_prefix}{LOCATION_FILE_SUFFIX}', 'r+') as outfile:
            lines = outfile.readlines() # read old content
            outfile.seek(0) # go back to the beginning of the file
            outfile.write(output_line) # write new content at the beginning
            for line in lines: # write old content after new
              outfile.write(line)
