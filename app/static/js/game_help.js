document.getElementById("game_help_button").addEventListener("click", function (e) {
  console.log("game_help_button clicked");
  socket.emit("game_help");
}, false);