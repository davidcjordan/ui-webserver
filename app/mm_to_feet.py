
def mm_to_feet(mm_value):
   inches = mm_value * 0.03937008
   print(f'total_inches={inches}') # feet={lengths[English_units.feet.value]} inches={lengths[English_units.inch.value]}')
   lengths = [0]*3

   import enum
   class English_units(enum.Enum):
      feet = 0
      inch = 1
      quar = 2 #quarter

   lengths[English_units.quar.value] = 0
   lengths[English_units.feet.value] = int(inches / 12)
   lengths[English_units.inch.value] = int(inches % 12)

   if ((inches % 12) > (11+ 7/8)):
      lengths[English_units.inch.value] = 0
      lengths[English_units.feet.value] += 1
   else:
      remaining_inches_remainder = inches % 12 % 1
      lengths[English_units.quar.value] = 0
      if (remaining_inches_remainder < 1/8):
         lengths[English_units.quar.value] = 0
      elif (remaining_inches_remainder < 3/8):
         lengths[English_units.quar.value] = 1
      elif (remaining_inches_remainder < 5/8):
         lengths[English_units.quar.value] = 2
      elif (remaining_inches_remainder < 7/8):
         lengths[English_units.quar.value] = 3
      else:
         lengths[English_units.inch.value] += 1
      
   return lengths