
'''
drill class definitions, and read drill files
'''
from flask import current_app
import csv

from app.main.defines import *
import sys
sys.path.append(f'{user_dir}/{repos_dir}/control_ipc_utils')
try:
   from control_ipc_defines import *
except:
   current_app.logger.error("Problems with 'control_ipc' modules, please run: git clone https://github.com/davidcjordan/control_ipc_utils")
   exit()

def get_drill_info(drill_id):
   drill_info = {}

   if isinstance(drill_id, str):
      int_drill_id = int(drill_id)
   elif isinstance(drill_id, int):
      int_drill_id = drill_id
   else:
      current_app.logger.error(f"drill_id {drill_id} is type={type(drill_id)} (not str or int)")
      return drill_info
   
   if int_drill_id >= CUSTOM_DRILL_NUMBER_START and int_drill_id <= CUSTOM_DRILL_NUMBER_END:
      file_path = f'{settings_dir}/{drill_file_prefix}{int_drill_id:03}.csv'
   else:
      file_path = f'{drills_dir}/{drill_file_prefix}{int_drill_id:03}.csv'

   try:
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

   if int_drill_id >= CUSTOM_DRILL_NUMBER_START and int_drill_id <= CUSTOM_DRILL_NUMBER_END:
      file_path = f'{settings_dir}/{drill_file_prefix}{int_drill_id:03}.csv'
   else:
      file_path = f'{drills_dir}/{drill_file_prefix}{int_drill_id:03}.csv'

   try:
      # since column titles are the 4th row, need to read them first.
      with open(file_path) as f:
         lines = f.read().splitlines()
         column_names_string = 'column0' + lines[3]
         # current_app.logger.debug(f"column_names_string: {column_names_string}")
         column_names = column_names_string.split(',')
         # current_app.logger.debug(f"column_names: {column_names}")
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

def make_drill_options(raw_throw_list):
   all_rows_throw_list = []
   for throw_row in raw_throw_list:
      this_row_throw_list = []

      # shot-type column:
      selection_list = []
      for btype in balltype_e:
         if btype.name == 'NONE' or btype.name == 'REPEAT' or btype.name == 'END':
            continue
         # current_app.logger.info(f"comparing {throw_row['SHOT_TYPE']} with {btype.name}")
         select_list_name = btype.name.replace("_", " ").title()
         select_list_name = select_list_name.replace("Ground", "Grd")
         if throw_row['SHOT_TYPE'] == btype.name:
            selection_list.append({select_list_name:1})
         else:
            selection_list.append({select_list_name:0})
      # current_app.logger.info(f"selection_list= {selection_list}")
      this_row_throw_list.append(selection_list)

      # rotary-type column: 2 pull-downs (1) which court; (2) angle if FH or BH
      # court_list = [{"FH":0}, {"BH":0},{"Center":0}, {"Inverse":0},{"Random":0},{"RandFH":0},{"RandBH":0},{"Rand4":0},{"Rand6":0}]
      court_list= [{'FH':0},{'BH':0}]
      is_FH_BH = False
      for rtype in rotary_setting_e:
         if '_FILLER' in rtype.name or '_END' in rtype.name:
            continue
         # the list was initialized with FH, BG
         if rtype.name.startswith('ROTTYPE_F') or rtype.name.startswith('ROTTYPE_B'):
            continue

         court_name_raw = rtype.name.replace("ROTTYPE_", "")
         court_name = court_name_raw.title()
         #Fix names where title does work:
         if court_name_raw == 'RANDFH':
            court_name = 'RandFH'
         elif court_name_raw == 'RANDBH':
            court_name = 'RandBH'
         elif court_name_raw == 'INV':
            court_name = 'Inverse'
         elif court_name_raw == 'R4':
            court_name = 'Rand4'
         elif court_name_raw == 'R6':
            court_name = 'Rand6'

         if throw_row['ROTARY_TYPE'].startswith('F'):
            court_list[0]['FH'] = 1
            is_FH_BH = True
         elif throw_row['ROTARY_TYPE'].startswith('B'):
            court_list[1]['BH'] = 1
            is_FH_BH = True
         
         if throw_row['ROTARY_TYPE'] == court_name_raw:
            court_list.append({court_name:1})
         else:
            court_list.append({court_name:0})
      
         # current_app.logger.debug(f"rtype={rtype.name} throw_row['ROTARY_TYPE']={throw_row['ROTARY_TYPE']} court_list={court_list}")

      this_row_throw_list.append(court_list)

      # populate the first angle selection with "-"
      if is_FH_BH:
         # angle = throw_row['ROTARY_TYPE'].name.replace("ROTTYPE_", "")
         # the number trailing F or B is the angle
         angle = int(throw_row['ROTARY_TYPE'][1:])
         angle_list = [{"-":0}]
      else:
         angle_list = [{"-":1}]

      # populate the rest of the angle_list:
      for i in range(1, 14):
         selected = 0
         if is_FH_BH and (i == angle):
            selected = 1
         angle_list.append({i:selected})

      this_row_throw_list.append(angle_list)
      # all_rows_throw_list.append(this_row_throw_list)

      # populate delay
      delay_list = [{"1.0":0},{"1.3":0},{"1.6":0},{"2.0":0},{"2.2":0},{"2.4":0},{"2.6":0},{"2.8":0}, \
                     {"3.0":0},{"3.2":0},{"3.4":0},{"3.6":0},{"3.8":0},{"4.0":0},{"4.3":0},{"4.6":0}, \
                     {"5.0":0},{"8.0":0},{"10.0":0},{"25.0":0}]
      # TODO: check ranges to match selected options
      this_row_throw_list.append(delay_list)
      all_rows_throw_list.append(this_row_throw_list)

      # inprogress
      # populate score method
     
   return all_rows_throw_list

def save_drill(request_form, id):
   # because the form button is an input type=image, then submit.x and submit.y are included in the
   # form dictionary - they can just be ignored.
   current_app.logger.debug(f"save_drill {id}: {request_form}")

   return