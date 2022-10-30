
// Create & insert drill description div
descriptDiv = document.createElement("DIV");
descriptDiv.setAttribute("class", "para-nomargin");
descriptDiv.id = "drill_desc"
placeHolder.parentElement.insertBefore(descriptDiv, placeHolder);
descriptDiv.innerHTML = "<p>"

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