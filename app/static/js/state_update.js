// javascript to update base state: Idle, Active, etc
// update data format is: {"base_state": "state"}

// var socket = io();
socket.on('state_update', function(data) {
  // console.log("Data:" + JSON.stringify(data, null, 1))
  // console.log("window.location.href=" + window.location.href);
  page_id = window.location.pathname.split("/").pop();

  var game_state = {};
  Object.keys(data).forEach(function(key) {
    // console.log('Key : ' + key + ', Value : ' + data[key])
    if (key == "new_url") {
      console.log("changing page to: " + data[key])
      location.href = data[key];
    }
    else if (key === 'base_state') {
      var IdToUpdate = document.getElementById(key);

      if (IdToUpdate == null) {
        console.log("error: element=" + key + " was not found on page")
      } else {
        IdToUpdate.innerHTML = "Status: " + data[key];
        // set pause/resume icon on game/drill/workout active pages
        var IdPauseResume = document.getElementById("pause-resume");
        if (IdPauseResume != null)
        {
          var classPauseResume = document.getElementById("pause-resume").className;
          // console.log('classPauseResume:' + classPauseResume)
          if (data[key] == 'Paused') {
            if (classPauseResume.endsWith("pause")) {
              IdPauseResume.classList.toggle("pause") //removes paused
              IdPauseResume.classList.toggle("resume") //adds resume
            }
          } else {
            if (classPauseResume.endsWith("resume")) {
              IdPauseResume.classList.toggle("resume")
              IdPauseResume.classList.toggle("pause")
            }
          }
        } //IdPauseResume not null
      } //IdToUpdaet
    } else if (key === 'game_state') {
      game_state = data[key];
      // console.log('game_state: ' + JSON.stringify(game_state))
      Object.keys(game_state).forEach(function(game_key) {
        var IdToUpdate = document.getElementById(game_key);
        if (IdToUpdate) {
          if (game_key === 'server') {
            if (game_state[game_key] == 'b') {
              IdToUpdate.innerHTML = "Boomer's serve"
            } else {
              IdToUpdate.innerHTML = "Player's serve"
            }
          } else {
            IdToUpdate.innerHTML = game_state[game_key];
          }
        } else {
          if (game_key !== 'time') {
            console.log("No element with ID: " + game_key)
          }
        }
      })
    } else {
      console.log("No element with ID: " + key)
    }
  })
});