document.getElementById("pause-resume").addEventListener("click", function (e) {
  socket.emit("pause_resume");
}, false);


