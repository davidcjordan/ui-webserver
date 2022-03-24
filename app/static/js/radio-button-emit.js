var radios = document.querySelectorAll('input[type=radio]')
for(var i = 0, max = radios.length; i < max; i++) {
   radios[i].onclick = function() {
      socket.emit('change_params', {[this.name] : Number(this.value)});
   }
}