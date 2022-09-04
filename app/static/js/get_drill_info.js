
// Create & insert drill description div
descriptDiv = document.createElement("DIV");
// lens_class defines the pixel height/width of the lens
descriptDiv.setAttribute("class", "para-nomargin");
descriptDiv.id = "drill_desc"
placeHolder.parentElement.insertBefore(descriptDiv, placeHolder);
descriptDiv.innerHTML = "<p>"
// lensDivStyle = getComputedStyle(lensDiv);
// lensDivBorderTotalWidth = (parseInt(lensDivStyle.borderLeftWidth) || 0) * 2;


var radios = document.querySelectorAll('input[type=radio]')
for(var i = 0, max = radios.length; i < max; i++) {
   radios[i].onclick = function() {
      socket.emit('get_drill_desc', {'page': page_id, 'drill_id' : this.id});
   }
}

socket.on('drill_desc', function(data) {
   // console.log("drill_desc data:" + JSON.stringify(data, null, 1))
   descriptDiv.innerHTML = data.replaceAll('"', '')
});