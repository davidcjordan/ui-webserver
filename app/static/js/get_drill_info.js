
// Create & insert drill description div
descriptDiv = document.getElementById("drill_desc");

const urlParams = new URLSearchParams(location.search);
// for (const [key, value] of urlParams) {
//     console.log(`${key}:${value}`);
// }

var mode;
if (urlParams.has('mode')) {
   mode = urlParams.get('mode');
}
else {mode = "drills"}

var radios = document.querySelectorAll('input[type=radio]')
for(var i = 0, max = radios.length; i < max; i++) {
   radios[i].onclick = function() {
      // console.log("mode=%s", mode);
      socket.emit('get_drill_desc', {'page': page_id, 'mode': mode, 'drill_id' : this.id});
   }
}

socket.on('drill_desc', function(data) {
   // console.log("drill_desc data:" + JSON.stringify(data, null, 1))
   descriptDiv.innerHTML = data.replaceAll('"', '')
});
