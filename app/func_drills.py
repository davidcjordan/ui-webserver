
'''
drill class definitions, and read drill files
'''
from flask import current_app
import csv

from app.main.defines import *

def get_drill_info(drill_id):
   drill_info = {}

   if isinstance(drill_id, str):
      int_drill_id = int(drill_id)
   elif isinstance(drill_id, int):
      int_drill_id = drill_id
   else:
      current_app.logger.error(f"drill_id {drill_id} is type={type(drill_id)} (not str or int)")
      return drill_info

   try:
      file_path = f'{drills_dir}/{drill_file_prefix}{int_drill_id:03}.csv'
      with open(file_path) as f:
         lines = f.read().splitlines()
         # remove quotes from name, description and audio strings, if they exist
         drill_info['name'] = lines[0].replace('"','')
         drill_info['desc'] = lines[1].replace('"','')
         drill_info['audio'] = lines[2].replace('"','')
   except:
      current_app.logger.error(f"get_drill_info: Error reading '{file_path}'")
   return drill_info

def get_workout_info(workout_id):
   workout_info = {}

   if isinstance(workout_id, str):
      int_drill_id = int(workout_id)
   elif isinstance(workout_id, int):
      int_drill_id = workout_id
   else:
      current_app.logger.error(f"workout_id {workout_id} is type={type(workout_id)} (not str or int)")
      return workout_info

   try:
      file_path = f'{drills_dir}/{workout_file_prefix}{int_drill_id:03}.csv'
      with open(file_path) as f:
         lines = f.read().splitlines()
         # remove quotes from name, description and audio strings, if they exist
         workout_info['name'] = lines[0].replace('"','')
         workout_info['desc'] = lines[1].replace('"','')
         workout_info['audio'] = lines[2].replace('"','')
   except:
      current_app.logger.error(f"get_drill_info: Error reading '{file_path}'")
   return workout_info

def read_drill_csv(drill_id):
   drill_info = {}

   if isinstance(drill_id, str):
      int_drill_id = int(drill_id)
   elif isinstance(drill_id, int):
      int_drill_id = drill_id
   else:
      current_app.logger.error(f"drill_id {drill_id} is type={type(drill_id)} (not str or int)")
      return drill_info

   # if int_drill_id >= CUSTOM_DRILL_NUMBER_START and <= CUSTOM_DRILL_NUMBER_END:
   if int_drill_id >= 400 and int_drill_id <= 499:
      file_path = f'{settings_dir}/{drill_file_prefix}{int_drill_id:03}.csv'
   else:
      file_path = f'{drills_dir}/{drill_file_prefix}{int_drill_id:03}.csv'

   try:
      # since column titles are the 4th row, need to read them first.
      with open(file_path) as f:
         lines = f.read().splitlines()
         column_names_string = 'column0' + lines[3]
         current_app.logger.info(f"column_names_string: {column_names_string}")
         column_names = column_names_string.split(',')
         # current_app.logger.info(f"column_names: {column_names}")
   except:
      current_app.logger.error(f"read_drill_csv: Error reading '{file_path}'")

   throw_list = []
   if 'SHOT_TYPE' in column_names and 'ROTARY_TYPE' in column_names:
      try:
         with open(file_path) as csvfile:
            reader = csv.DictReader(csvfile, fieldnames=column_names)
            i = 0
            for row in reader:
               if i > 3:
                  del row['column0']
                  throw_list.append(row)
                  # current_app.logger.info(f"row={i} contents={row}")
               i += 1 
      except:
         current_app.logger.error(f"read_drill_csv: Error parsing '{file_path}'")
   else:
      current_app.logger.error(f"read_drill_csv: SHOT_TYPE and ROTARY_TYPE not on '{file_path}'")
   return throw_list
