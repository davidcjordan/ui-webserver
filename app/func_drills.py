
'''
drill class definitions, and read drill files
'''
from flask import current_app

#TODO: use defines.py:
drills_dir = "/home/pi/boomer/drills"
drill_file_prefix = "DRL"
workout_file_prefix = "WORK"

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
