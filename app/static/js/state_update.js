// javascript:
//  invoke socketio
//  poll to get state updates
// update base state: Idle, Active, etc
// update data format is: {"base_state": "state"}

var socket = io();
var socket = io.connect('http://' + document.domain + ':' + location.port);
var data_get_update = {};
// pop takes the last element of an array/
data_get_update["page"] = window.location.pathname.split("/").pop();
// console.log("data_get_update=", data_get_update);
if (data_get_update["page"] === "") {
  data_get_update["page"] = "home"
}

socket.on('connect', function() {
  console.log("Sending client_connected from page: " + data_get_update["page"])
  socket.emit('client_connected', JSON.stringify(data_get_update));
});

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
    } else if (key === 'soft_fault') {
      // disable GAME mode button on main screen if tracking is faulted
      // console.log("soft_fault=" + data[key] + "; page_id=" + page_id)
      if (page_id.length === 0) {
        var IdToUpdate = document.getElementById("game_button");
        if (IdToUpdate) {
          if (data[key] == 1) {
            IdToUpdate.disabled = true;
          } else {
            IdToUpdate.disabled = false;
          }
        } else {
          console.log("No element with ID: game_button")
        }
      }
    } else {
      console.log("No element with ID: " + key)
    }
  })
});

// start polling for state changes after the handle_updates is defined.
var pollingVar = setInterval(pollingTimer, 350);
function pollingTimer() {
  socket.emit("get_updates", JSON.stringify(data_get_update));
}

// for faults page:
socket.on('faults_update', function(faults) {
  // console.log("received faults: " + faults)
  let table = document.getElementById("fault_table");
  // clear table before adding updated fault rows
  for (let i = (table.rows.length-1); i > 0; i--) { 
     // console.log("deleteRow: " + i)
     table.deleteRow(i);
  }
  for (let element of JSON.parse(faults)) {
     let row = table.insertRow();
     for (key in element) {
        let cell = row.insertCell();
        let text = document.createTextNode(element[key]);
        cell.appendChild(text);
        cell.className = 'Cell';
     }
  }
});