// javascript to emit pause/resume and flip the pause/resume icon

// var socket = io();
document.getElementById("pause-resume").addEventListener("click", function (e) {
  var target = e.target;
  //the full classlist is: 
  //      {0: "pause-resume-button", 1: "resume", length: 2, value: "pause-resume-button resume", ...
  // console.log(document.getElementById("pause-resume").classList);
  // the following gets pause/resume before changing the icon
  var action = document.getElementById("pause-resume").classList.item(1);
  socket.emit(action);
  target.classList.toggle("pause");
  target.classList.toggle("resume");
}, false);


