const radios = document.querySelectorAll('[data-disables_field]');
for(var i = 0, max = radios.length; i < max; i++) {
   radios[i].onclick = function() {
      // console.log(this)
      if (this.dataset.disables_field) {
         // console.log("fieldset= " + this.dataset.disables_field);
         if (this.dataset.enable) {
            // console.log("enable=" + this.dataset.enable);
            var FieldsetId = document.getElementById(this.dataset.disables_field);
            //invert enable to become disable
            FieldsetId.disabled = !Number(this.dataset.enable);
         } else {
            console.log("WARN: this.data-enable is undefined for ", this);
         }
      } else {
        console.log("WARN: this.data-disables_field is undefined for ", this);
      }
   }
}