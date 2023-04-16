// const radios = document.querySelectorAll('[data-disables_field]');
const radios = document.getElementsByTagName('input');
// console.log(radios);
const f_sets = document.getElementsByTagName('fieldset');
// console.log(f_sets);

window.onload = function() {
   disable_fieldsets();
   for(var k = 0; k < radios.length; k++) {
      radios[k].onclick = function() {
         disable_fieldsets();
      }
   }   
 };

function disable_fieldsets() {
   // re-enable all fieldsets:
   for(var j = 0; j < f_sets.length; j++) {
      f_sets[j].disabled = 0;
   }
   //then disable the ones based on buttons that are checked:
   for(var i = 0; i < radios.length; i++) {
      // console.log("iteration=" + i + " of " + radios.length +": " + radios[i].id);
      if ((radios[i].checked) && (radios[i].dataset.disables_field)) {
         // console.log(radios[i].id + " checked: disabling " + radios[i].dataset.disables_field);
         for(var j = 0; j < f_sets.length; j++) {
            if (f_sets[j]['id'] == radios[i].dataset.disables_field) {
               f_sets[j].disabled = 1;
            }
         }
      }
   }
}
