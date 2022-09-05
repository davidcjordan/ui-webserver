var radios = document.querySelectorAll('input[type=radio]')
for(var i = 0, max = radios.length; i < max; i++) {
   radios[i].onclick = function() {
      // console.log("this.name=" + this.name + "  this.value=" + this.value)
      if (this.name.includes("Type")) {
         if (this.value !== '0') {
            disable_button = true;
            // console.log("disabling stroketype");
         } else {
            // console.log("enabling stroketype");
            disable_button = false;
         }
         var IdsToToggle = document.getElementsByName("beep_options.Stroke");
         // console.log("IdsToToggle= ", IdsToToggle);
         for (let i = 0; i < IdsToToggle.length; i++) {
            IdsToToggle[i].disabled = disable_button;
            // console.log("Setting ", IdsToToggle[i]);
         }
      }
   }
}