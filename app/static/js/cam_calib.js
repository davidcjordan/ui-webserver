// display court png, draw lines, emit on button pushes
// refer to: https://stackoverflow.com/questions/807878/how-to-make-javascript-execute-after-page-load

var imgFilename;
let imgWidth = 1280; //unable to get img.naturalWidth; couldn't figure out the url

function init() {
   // console.log('Version 7');
   imgFilename = document.getElementById("image_path").value;
   // attempt to get image width from the PNG file:
   // var img = new Image;
   // img.src = window.URL.createObjectURL(image_path);  <- gets an exception
   // console.log("imgWidth=%d", img.naturalWidth);

   notZoomedDiv = document.getElementById("div_not_zoomed");
   page_id = window.location.pathname.split("/").pop();
   if ( page_id.indexOf( "verif" ) > -1 ) {
   notZoomedDiv.setAttribute("style","width:960px; height:600px");
   } else {
   notZoomedDiv.setAttribute("style","width:640px; height:480px");
   }

   notZoomedDivStyle = getComputedStyle(notZoomedDiv);
   notZoomedDivBorderTotalWidth = (parseInt(notZoomedDivStyle.borderLeftWidth) || 0) * 2;
   // console.log("notZoomedDivBorderTotalWidth=%d", notZoomedDivBorderTotalWidth);
   notZoomedDivWidth = notZoomedDiv.offsetWidth - notZoomedDivBorderTotalWidth
   notZoomedDivHeight = notZoomedDiv.offsetHeight - notZoomedDivBorderTotalWidth

   // add timestamp to not have the browser use the cached image
   var timestamp = new Date().getTime();
   notZoomedDiv.style.backgroundImage = "url('" + imgFilename + "?t=" + timestamp + "')";
   notZoomedDiv.style.backgroundSize = (notZoomedDivWidth) + "px " + (notZoomedDivHeight) + "px";

   notZoomedCanvas = document.getElementById("canvas_not_zoomed");
   notZoomedCanvas.width = notZoomedDivWidth;
   notZoomedCanvas.height = notZoomedDivHeight;
   notZoomedContext = notZoomedCanvas.getContext("2d");

   drawCourtLines();
};

init();

function drawCourtLines() {
   notZoomedContext.strokeStyle = "Chartreuse";
   notZoomedContext.lineWidth = 1;

   notZoomedContext.clearRect(0, 0, notZoomedCanvas.width, notZoomedCanvas.height);
   canvasDivisor = imgWidth/notZoomedDivWidth;
   
   // draw outer-court lines (6 of them); start by loading array of court points
   var points = 
   [[parseInt(document.getElementById("FBLX").value/canvasDivisor), 
      parseInt(document.getElementById("FBLY").value/canvasDivisor)],
      [parseInt(document.getElementById("FBRX").value/canvasDivisor),
      parseInt(document.getElementById("FBRY").value/canvasDivisor)],
      [parseInt(document.getElementById("NSRX").value/canvasDivisor),
      parseInt(document.getElementById("NSRY").value/canvasDivisor)],
      [parseInt(document.getElementById("NBRX").value/canvasDivisor),
      parseInt(document.getElementById("NBRY").value/canvasDivisor)],
      [parseInt(document.getElementById("NBLX").value/canvasDivisor),
      parseInt(document.getElementById("NBLY").value/canvasDivisor)],
      [parseInt(document.getElementById("NSLX").value/canvasDivisor),
      parseInt(document.getElementById("NSLY").value/canvasDivisor)]];

   for (var this_pt = 0; this_pt < points.length; this_pt++) {
      var next_pt = this_pt + 1;
      if (next_pt >= points.length) {next_pt = 0}
      if ((points[this_pt][0] > 0) && (points[next_pt][0] > 0))
      {
         notZoomedContext.beginPath();
         notZoomedContext.moveTo(points[this_pt][0], points[this_pt][1]);
         notZoomedContext.lineTo(points[next_pt][0], points[next_pt][1]);
         notZoomedContext.stroke();   
      }
   }

   // draw service line (2 lines);  reload points array with service line points
   points.length = 3;
   points[0] = [parseInt(document.getElementById("NSLX").value/canvasDivisor), 
      parseInt(document.getElementById("NSLY").value/canvasDivisor)];

   points[1] = [parseInt(document.getElementById("NSCX").value/canvasDivisor),
      parseInt(document.getElementById("NSCY").value/canvasDivisor)];
   
   points[2] = [parseInt(document.getElementById("NSRX").value/canvasDivisor),
      parseInt(document.getElementById("NSRY").value/canvasDivisor)];

   for (var this_pt = 0; this_pt < points.length-1; this_pt++) {
      var next_pt = this_pt + 1;
      if ((points[this_pt][0] > 0) && (points[next_pt][0] > 0))
      {
         notZoomedContext.beginPath();
         notZoomedContext.moveTo(points[this_pt][0], points[this_pt][1]);
         notZoomedContext.lineTo(points[next_pt][0], points[next_pt][1]);
         notZoomedContext.stroke();   
      }
   }
}

// used on cam_verif:
async function refreshImage(evenOdd) {
   var frame = evenOdd || "even"; //handle frame as an option
   var side = 'left';
   if (imgFilename.indexOf('ight') !== -1) {
   side = 'right';
   }
   socket.emit("refresh_image", {'side': side, 'frame': frame});
   let sleep_ms = 1500
   console.log(`Waiting ${sleep_ms} milliseconds...`);
   await new Promise(r => setTimeout(r, sleep_ms));
   var timestamp = new Date().getTime();
   notZoomedDiv.style.backgroundImage = "url('" + imgFilename + "?t=" + timestamp + "')";
   drawCourtLines();
}
