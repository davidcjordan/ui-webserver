// display court png, draw lines, emit on button pushes
// refer to: https://stackoverflow.com/questions/807878/how-to-make-javascript-execute-after-page-load

var imgFilename;
let imgWidth = 1280; //unable to get img.naturalWidth; couldn't figure out the url
let imgHeight = 800; //unable to get img.naturalWidth; couldn't figure out the url
let verifDivSizeMultiplier = 3/4; //scales image to 3/4 size
let calibDivSizeMultiplier = 1/2;
let zoomDivSize = 256; //px
let lensDivSize = 16;

// the image zoom box was taken &  modified from: https://www.w3schools.com/howto/tryit.asp?filename=tryhow_js_image_zoom
// the following variables are used by cam_calib, to draw the zoomed image canvas
var zoomed8Div;      //where the zoomed canvas is displayed; the canvas has the image zoomed as a background, plus a cursor
var zoomed8Canvas;   //used in moveLensBoundaryCheck()
var zoomed8Context;  //used in drawCursorInZoom8()
var notZoomedDivWidth; //set in init; used in drawLines
var notZoomedDivHeight; //used in imageZoom
var currentCoordinate;
var coordinateArray;

var lensDiv; //this is the square drawn on the image to indicate the zoomed area
var lensDivBorderTotalWidth;  //set in imageZoom(), used in moveLensByTouch() to not have the lens go outside the image

var zoomRatio;       //since zooming a square, the zoom ratio is the same for both x & y
var backgroundMax = {}; //the max pixel values for the nonZoomed canvas; used to make sure zoom box is within the canvas
var background = {top: 0, left: 0}; //the current position of the zoom box in the nonZoomed canvas; used when moving the zoom image, aka move...() functions
var centerOfZoomed = {x: 16, y: 16}; //nonZoomed pixel coordinates of the cursor in the zoomed canvas

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
      notZoomedDiv.style.width = Math.trunc(imgWidth * verifDivSizeMultiplier) + 'px';
      notZoomedDiv.style.height = Math.trunc(imgHeight * verifDivSizeMultiplier) + 'px';
   } else {
      notZoomedDiv.style.width = Math.trunc(imgWidth * calibDivSizeMultiplier) + 'px';
      notZoomedDiv.style.height = Math.trunc(imgHeight * calibDivSizeMultiplier) + 'px';
   }

   notZoomedDivStyle = getComputedStyle(notZoomedDiv);
   notZoomedDivBorderTotalWidth = (parseInt(notZoomedDivStyle.borderLeftWidth) || 0) * 2;
   // console.log("notZoomedDivBorderTotalWidth=%d", notZoomedDivBorderTotalWidth);
   notZoomedDivWidth = notZoomedDiv.offsetWidth - notZoomedDivBorderTotalWidth
   notZoomedDivHeight = notZoomedDiv.offsetHeight - notZoomedDivBorderTotalWidth

   notZoomedCanvas = document.getElementById("canvas_not_zoomed");
   notZoomedCanvas.width = notZoomedDivWidth;
   notZoomedCanvas.height = notZoomedDivHeight;
   notZoomedContext = notZoomedCanvas.getContext("2d");

   // add timestamp to not have the browser use the cached image
   var timestamp = new Date().getTime();
   notZoomedDiv.style.backgroundImage = "url('" + imgFilename + "?t=" + timestamp + "')";
   notZoomedDiv.style.backgroundSize = (notZoomedDivWidth) + "px " + (notZoomedDivHeight) + "px";

   drawCourtLines();

   if ( page_id.indexOf( "calib" ) > -1 ) {
      imageZoom("div_zoomed_8")
      drawCursorInZoom8();

      coordinateArray = document.getElementById("court_coordinates").elements;
      // console.log(coordinateArray)
      // the following is the output of the console log:
      // HTMLFormControlsCollection(15) [input#FBLX, input#FBLY, input#FBRX, input#FBRY, input#NSLX, input#NSLY, input#NSCX, input#NSCY, input#NSRX, input#NSRY, input#NBLX, input#NBLY, input#NBRX, input#NBRY, input#submitButton, FBLX: input#FBLX, FBLY: input#FBLY, FBRX: input#FBRX, FBRY: input#FBRY, NSLX: input#NSLX, …]
      currentCoordinate = 0;
      setPointLabel();
   }
};

init();

function drawCourtLines() {
   notZoomedContext.strokeStyle = "Chartreuse";
   notZoomedContext.lineWidth = 1;

   notZoomedContext.clearRect(0, 0, notZoomedCanvas.width, notZoomedCanvas.height);
   canvasDivisor = imgWidth/notZoomedDivWidth;
   // console.log('canvasDivisor=%f', canvasDivisor);

   // ? could change this to use the coordinateArray to get the coordinate names
   // and iterate through the pairs of coordinates, but skip certain pairs: FBR to NSL & NSR to NBL
   // And add other pairs: FBL to NSL, FBR to NSR, NSL to NBL and NSR to NBL
   
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
   // console.table(points);
   
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

// the following are used on cam_calib:

function imageZoom(targetDivID) {
   // Create & insert lens
   lensDiv = document.createElement("DIV");
   lensDiv.className = "lens_class";
   lensDiv.style.width = lensDivSize + 'px';
   lensDiv.style.height = lensDivSize + 'px';
   lensDiv.id = "LENS"
   notZoomedDiv.parentElement.insertBefore(lensDiv, notZoomedDiv);

   lensDivStyle = getComputedStyle(lensDiv);
   lensDivBorderTotalWidth = (parseInt(lensDivStyle.borderLeftWidth) || 0) * 2;

   zoomed8Div = document.getElementById(targetDivID);
   zoomed8Div.style.width = zoomDivSize + 'px';
   zoomed8Div.style.height = zoomDivSize + 'px';
   zoomed8DivStyle = getComputedStyle(zoomed8Div);
   let zoomed8DivBorderTotalWidth = (parseInt(zoomed8DivStyle.borderLeftWidth) || 0) *2;
   // console.log("lensDivBorderTotalWidth: %d   zoomed8DivBorderTotalWidth: %d", lensDivBorderTotalWidth, zoomed8DivBorderTotalWidth);
 
   zoomed8Canvas = document.getElementById("canvas_id_zoomed_8");
   zoomed8Canvas.width = zoomed8Div.offsetWidth - zoomed8DivBorderTotalWidth;
   zoomed8Canvas.height = zoomed8Div.offsetHeight - zoomed8DivBorderTotalWidth;
   zoomed8Context = zoomed8Canvas.getContext("2d");

   // zoomRatio is the ratio of the zoomed8Div and the lens; since the lens is square, only calculate based on width
   zoomRatio = (zoomed8Div.offsetWidth - zoomed8DivBorderTotalWidth) / (lensDiv.offsetWidth - lensDivBorderTotalWidth);
   // console.log("zoomed8Div.offsetWidth & Height: %d x %d   lensDiv.offsetWidth & Height: %d x %d",
   //   zoomed8Div.offsetWidth, zoomed8Div.offsetHeight, lensDiv.offsetWidth, lensDiv.offsetHeight);
   // console.log("zoomRatio=%d", zoomRatio);

   // Set background properties for the zoomed8Div !! add timestamp to not have the browser use the cached image
   var timestamp = new Date().getTime();
   zoomed8Div.style.backgroundImage = "url('" + imgFilename + "?t=" + timestamp + "')";
   // NOTE: the notZoomedDivWidth.width (image.width) and height is 1/2 the full size image, since the div height is set to 400 in the html
   zoomed8Div.style.backgroundSize = (notZoomedDivWidth * zoomRatio) + "px " + (notZoomedDivHeight * zoomRatio) + "px";
   // console.log("img: width=%d height=%d zoomed8Div.backgroundSize=%s", notZoomedDivWidth, notZoomedDivHeight, zoomed8Div.style.backgroundSize);

   //The max is doubled in order to be able to move the center pixel by pixel
   backgroundMax = {
     left: 2*(notZoomedDivWidth - lensDiv.offsetWidth + lensDivBorderTotalWidth),
     top:  2*(notZoomedDivHeight - lensDiv.offsetHeight + lensDivBorderTotalWidth)
   };
   // console.log("backgroundMax left=%d top=%s ", backgroundMax.left, backgroundMax.top);

   let current_x_y_element = document.getElementById('current_x_y');
   current_x_y_element.innerText = `Current X: ${centerOfZoomed.x} Y: ${centerOfZoomed.y}`;

   /* Execute a function when someone moves the cursor over the image: */
   lensDiv.addEventListener("mousedown", moveLensByTouch);
   notZoomedDiv.addEventListener("mousedown", moveLensByTouch);
   /* And also for touch screens: */
   lensDiv.addEventListener("touchmove", moveLensByTouch);
   notZoomedDiv.addEventListener("touchmove", moveLensByTouch);
 }

 function drawCursorInZoom8() {
   zoomed8Context.clearRect(0, 0, zoomed8Canvas.width, zoomed8Canvas.height);
   // zoomed8Context.beginPath();
   // // x, y, radius, starting angle, ending angle
   // zoomed8Context.arc((x_px_selector-3), (y_px_selector-3), 6, 0, 2 * Math.PI);
   // zoomed8Context.lineWidth = 3;
   // zoomed8Context.strokeStyle = "Chartreuse";
   // zoomed8Context.setLineDash([2]);
   // zoomed8Context.stroke();
   let len_half_line = 8;
   zoomed8Context.beginPath();
   // zoomed8Context.setLineDash([2]);

   /*
     with a square 'lens' of 256x256, and the cursor always being in the middle, then there is no 'x/y_px_selector'
     Instead the one can use center.x and center.y, where these are locals = 'zoomed8Canvas.width/2'
   */
   cursorPosition = {x: zoomed8Canvas.width/2, y: zoomed8Canvas.height/2}
   zoomed8Context.strokeStyle = "Chartreuse";
   zoomed8Context.lineWidth = 1;
   zoomed8Context.moveTo(cursorPosition.x-len_half_line, cursorPosition.y);
   zoomed8Context.lineTo(cursorPosition.x+len_half_line, cursorPosition.y);
   zoomed8Context.moveTo(cursorPosition.x, cursorPosition.y-len_half_line);
   zoomed8Context.lineTo(cursorPosition.x, cursorPosition.y+len_half_line);
   zoomed8Context.stroke();   

   zoomed8Context.beginPath();
   zoomed8Context.strokeStyle = "DarkGreen";
   zoomed8Context.lineWidth = 1;
   zoomed8Context.moveTo(cursorPosition.x-len_half_line, cursorPosition.y-len_half_line);
   zoomed8Context.lineTo(cursorPosition.x+len_half_line, cursorPosition.y+len_half_line);
   zoomed8Context.moveTo(cursorPosition.x-len_half_line, cursorPosition.y+len_half_line);
   zoomed8Context.lineTo(cursorPosition.x+len_half_line, cursorPosition.y-len_half_line);
   zoomed8Context.stroke();   
 }

 function goToNextPoint() {
   currentCoordinate += 2;
   if (currentCoordinate >= 13) {
     currentCoordinate = 0;
     let submitButton = document.getElementById("submitButton");
     submitButton.disabled = false;
   }
   setPointLabel();
 }

 function setPoint() {
   // the point's X/Y is equal to the center of the zoomed image which is set in moveLensBoundaryCheck()
   // console.log("background left=%d top=%d  centerOfZoomed x=%d y=%d  canvas.width=%d", 
   //   background.left, background.top, centerOfZoomed.x, centerOfZoomed.y, zoomed8Canvas.width);

   // console.dir(coordinateArray, {'maxArrayLength': null});
   var coordinateId = coordinateArray[currentCoordinate].id
   document.getElementById(coordinateId).value = centerOfZoomed.x;
   coordinateId = coordinateArray[currentCoordinate+1].id
   document.getElementById(coordinateId).value = centerOfZoomed.y;

   goToNextPoint();    
   drawCourtLines()
 }

 function setPointLabel() {
   let coordinateId = coordinateArray[currentCoordinate].id
   var name = [];
   if (coordinateId[0] === 'F') {
     name[0] = "Far"
   } else {
     name[0] = "Near"
   }
   if (coordinateId[1] === 'B') {
     name[1] = "Baseline"
   } else {
     name[1] = "Service Line"
   }
   if (coordinateId[2] === 'L') {
     name[2] = "Left"
   } else if (coordinateId[2] === 'R'){
     name[2] = "Right"
   } else {
     name[2] = "Center"
   }
   // console.log("coordinateId=%s  label= %s %s %s", coordinateId, name[0], name[1], name[2])
   let label = document.getElementById("current_point_label");
   label.innerHTML = `${name[0]} ${name[1]} ${name[2]}: `;
 }

 // cursor move functions
 function move_down() {
   background.top += 1;
   moveLensBoundaryCheck();
 }
 function move_up() {
   background.top -= 1;
   moveLensBoundaryCheck();
 }
 function move_right() {
   background.left += 1;
   moveLensBoundaryCheck();
 }
 function move_left() {
   background.left -= 1;
   moveLensBoundaryCheck();
 }

 // zoomed image (lens) displays the rectangle that has been touched
 function moveLensByTouch(e) {
   var pos, x, y;
   /* Prevent any other actions that may occur when moving over the image */
   e.preventDefault();
   /* Get the cursor's x and y positions: */
   pos = getCursorPos(e);
   console.log("touch cursor x=%d  y=%d", pos.x, pos.y);

   /* Calculate the top & left of the lens - placing the cursor at the center of the lens
      x -> horizontal left to right, e.g. Width.
     img.width & height do NOT include the border
     lensDiv.offsetHeight & Width DO include the border
     Double the pos.x/y to achieve pixel granularity when moving the zoom center using the buttons
   */
   background.top = (2*pos.y) - (lensDiv.offsetWidth);
   background.left = (2*pos.x) - (lensDiv.offsetHeight);
   moveLensBoundaryCheck();
 }

 function moveLensBoundaryCheck() {
     /* Prevent the lens from being positioned outside the image:  (BUT: OK to have lens border outside the image
      on the zero sides, allow the lens to overlap the image border - hence limit to -1
      on the other side, have the lens be inside the img.height/widht - the lens size not including the border
   */
   if (background.top < 0) {
     background.top = 0;
   }
   if (background.top > backgroundMax.top) {
     background.top = backgroundMax.top;
   }
   if (background.left < 0) {
     background.left = 0;
   }
   if (background.left > backgroundMax.left) {
     background.left = backgroundMax.left;
   }

   //halve the background to position the lens
   // the lensBorderOffset was determined by experimentation on what looked good; lensDivBorderTotalWidth=4 defined in lens_class
   let lensBorderOffset = lensDivBorderTotalWidth/4 - 1;
   lens_top = background.top/2 + lensBorderOffset;
   lens_left = background.left/2 + lensBorderOffset;
   // reposition the lens:
   lensDiv.style.left = lens_left + "px";
   lensDiv.style.top = lens_top + "px";

   // Display what the lens "sees" by positioning the image position in the background of the DIV
   // console.log("previous background position=%s", zoomed8Div.style.backgroundPosition);
   //In order to move 1 pixel at time, the zoomRatio needs to be halved since the background.x/y doubled
   var backgroundCoords = {x: (background.left * zoomRatio/2), y: (background.top * zoomRatio/2)};
   zoomed8Div.style.backgroundPosition = "-" + backgroundCoords.x + "px -" + backgroundCoords.y + "px";
   // console.log("background left=%d  top=%d    lens left: %d  top: %d", background.left, background.top, lens_left, lens_top);
   // console.log(" updated background position=%s", zoomed8Div.style.backgroundPosition);

   // the 1280x800 image is displayed at 640x400, which is what the background.left/top range is
   // The divide by 16 is to get 1/2 the width/height, and then divide by 8, which is the amount the image is zoomed
   centerOfZoomed.x = background.left + (zoomed8Canvas.width/16);
   centerOfZoomed.y = background.top + (zoomed8Canvas.height/16);
   // console.log('background.left=', background.left, ' zoomed8Canvas.width=', zoomed8Canvas.width, ' centerOfZoomed.x=', centerOfZoomed.x);
   let current_x_y_element = document.getElementById('current_x_y');
   current_x_y_element.innerText = `Cursor Position:  X: ${centerOfZoomed.x} Y: ${centerOfZoomed.y}`;
 }

 // get the rectangle that's been touched coordinates
 function getCursorPos(e) {
   var a, x = 0, y = 0;
   e = e || window.event;
   /* Get the x and y positions of the image: */
   a = notZoomedDiv.getBoundingClientRect();

   // console.log("getBoundingClientRect: %s", JSON.stringify(a));
   // "{\"x\":16,\"y\":106,\"width\":642,\"height\":402,\"top\":106,\"right\":658,\"bottom\":508,\"left\":16}"
   // console.log("e.page X=%d Y=%d  a left=%d top=%d  window.pageOffset X=%d Y=%d", e.pageX, e.pageY, a.left, a.top, window.pageXOffset, window.pageYOffset);
   // Calculate the cursor's x and y current_x_y, relative to the image:
   x = e.pageX - a.left;
   y = e.pageY - a.top;
   // Consider any page scrolling: for Boomer, these should always be zero
   x = x - window.pageXOffset;
   y = y - window.pageYOffset;
   return {x : x, y : y};
 }
