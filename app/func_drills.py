
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

def get_drill_workout_info(id, file_type=drill_file_prefix):
   info = {}

   if isinstance(id, str):
      int_id = int(id)
   elif isinstance(id, int):
      int_id = id
   else:
      current_app.logger.error(f"id {id} is type={type(id)} (not str or int)")
      return info
   
   if int_id >= CUSTOM_DRILL_NUMBER_START and int_id <= CUSTOM_DRILL_NUMBER_END:
      file_path = f'{settings_dir}/{file_type}{int_id:03}.csv'
   else:
      file_path = f'{drills_dir}/{file_type}{int_id:03}.csv'

   try:
       with open(file_path) as f:
         lines = f.read().splitlines()
         # remove quotes from name, description and audio strings, if they exist
         info['name'] = lines[0].replace('"','')
         info['desc'] = lines[1].replace('"','')
         info['audio'] = lines[2].replace('"','')
   except:
      current_app.logger.error(f"get_drill_workout_info: Error reading '{file_path}'")
   return info


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
      # compare file's delay to list to select the proper option.
      try:
         original_delay_float = float(throw_row['DELAY'])
      except:
         original_delay_float = None
         current_app.logger.debug(f"make_drill_options exception on delay {throw_row['DELAY']} float: {original_delay_float}")
      
      if original_delay_float is not None:
         for idx, delay in enumerate(delay_list):
            delay_key = list(delay.keys())[0]
            if float(delay_key) >= original_delay_float:
               delay_list[idx][delay_key] = 1
               break

      this_row_throw_list.append(delay_list)
      all_rows_throw_list.append(this_row_throw_list)

      # inprogress
      # populate score method
     
   return all_rows_throw_list

def save_drill(request_form, id):
   # because the form button is an input type=image, then submit.x and submit.y are included in the
   # form dictionary - they can just be ignored.
   current_app.logger.debug(f"save_drill {id}: {request_form}")

   '''[func_drills186]: save_drill 402: ImmutableMultiDict([('1-1', 'Serve'), ('1-2', 'FH'), ('1-3', '1'), ('1-4', '1.0'), 
      ('2-1', 'Lob'), ('2-2', 'FH'), ('2-3', '13'), ('2-4', '1.0'), 
      ('3-1', 'Pass'), ('3-2', 'BH'), ('3-3', '2'), ('3-4', '1.0'),
      ('4-1', 'Chip'), ('4-2', 'BH'), ('4-3', '12'), ('4-4', '1.0'), 
      ('5-1', 'Rand Net'), ('5-2', 'Center'),
      ('5-3', '-'), ('5-4', '1.0'), ('6-1', 'Rand Grd'),
      ('6-2', 'RandFH'), ('6-3', '-'), ('6-4', '1.0'), ('7-1', 'Rand Grd'),
      ('7-2', 'RandBH'), ('7-3', '-'), ('7-4', '1.0'), ('8-1', 'Rand Grd'),
      ('8-2', 'Rand4'), ('8-3', '-'), ('8-4', '1.0'), ('9-1', 'Rand Grd'),
      ('9-2', 'Rand6'), ('9-3', '-'), ('9-4', '1.0'), ('10-1', 'Rand Grd'),
      ('10-2', 'Inverse'), ('10-3', '-'), ('10-4', '1.0'), 
      ('submit.x', '36'),('submit.y', '52')])
   '''
   row_string_list = []
   current_row = 0
   column_list = []
   for key, value in request_form.items():
      if "-" not in key:
         continue
      item = key.split('-')
      row_num = int(item[0])
      col_num = int(item[1])
      if row_num != current_row:
         #start a new row_string
         if len(column_list) > 0:
            # current_app.logger.debug(f"current_row={current_row} column_list= {column_list}")
            row_string = "," + ",".join(column_list)
            row_string_list.append(row_string)
         current_row += 1
         column_list = []
      upper_value = value.upper().replace(' ','_')
      # decode specific columns: combine court+angle into ROTTYPE
      if col_num == 1 and upper_value == "RAND_GRD":
            column_list.append('RAND_GROUND')
      elif col_num == 2:
         if upper_value == "INVERSE":
            column_list.append('INV')
         elif upper_value == 'Rand4':
            column_list.append('R4')
         elif upper_value == 'Rand6':
            column_list.append('R4')
         else:
            column_list.append(upper_value)

      elif col_num == 3:
         if column_list[-1] == 'FH' or column_list[-1] == 'BH':
            column_list[-1] = column_list[-1] + value
      else:
         column_list.append(upper_value)
 
      # current_app.logger.debug(f"key={key}  item[0]={int(item[0])} item[1]={item[1]} current_row={current_row}  column_list={column_list}")

   # append last row:
   if len(column_list) > 0:
      row_string = "," + ",".join(column_list)
      row_string_list.append(row_string)
   current_app.logger.debug(f"row_string_list= {row_string_list}")
         
   # write file
   if 1:
      if isinstance(id, str):
         int_drill_id = int(id)
      elif isinstance(id, int):
         int_drill_id = id
      else:
         current_app.logger.error(f"drill_id {id} is type={type(id)} (not str or int)")
         return False

      file_path = f'{settings_dir}/{drill_file_prefix}{int_drill_id:03}.csv'

      # read info lines (the first 3)
      try:
       with open(file_path) as f:
         lines = f.read().splitlines()
      except:
         current_app.logger.error(f"get_drill_workout_info: Error reading '{file_path}'")

      if len(lines) < 3:
         return False #bad file read
      
      file_path = f'{settings_dir}/tmp_{drill_file_prefix}{int_drill_id:03}.csv'
      try:
         with open(file_path, "w") as f:
            for idx, line in enumerate(lines):
               f.write(line + '\n')
               if idx > 2:
                  break
            for row in row_string_list:
               f.write(row + '\n')
      except:
         current_app.logger.error(f"save_drill: Error writing '{file_path}'")

   return True