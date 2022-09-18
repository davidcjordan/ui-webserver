
'''
drill class definitions, and read drill files
'''
from flask import current_app

# global user_dir, boomer_dir
# drills_dir = f'{user_dir}/{boomer_dir}/drills'
drills_dir = "/home/pi/boomer/drills"
drill_file_prefix = "DRL"
workout_file_prefix = "WORK"

drills_dict = {} # holds copies of drills read in from DRLxxx.csv files; keys are the drill numbers
workouts_dict = {} #as above, but using WORKxxx.csv files

def fetch_into_drills_dict(drill_id_str):
   global drills_dict
   # get name from drills_dict, or read the drill file and populate the drills_dict
   if (drill_id_str not in drills_dict):
      this_drill_info = get_drill_info(drill_id_str)
      if ('name' in this_drill_info):
         drills_dict[drill_id_str] = this_drill_info

   if ((drill_id_str in drills_dict) and ('name' in drills_dict[drill_id_str])):
      return True
   else:
      return False


def fetch_into_workout_dict(id_str):
   global workouts_dict
   # get name from drills_dict, or read the drill file and populate the drills_dict
   if (id_str not in workouts_dict):
      this_workout_info = get_workout_info(id_str)
      if ('name' in this_workout_info):
         workouts_dict[id_str] = this_workout_info

   if ((id_str in workouts_dict) and ('name' in workouts_dict[id_str])):
      return True
   else:
      return False

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
