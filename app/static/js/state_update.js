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

// The faults page is not opened automatically when the base is faulted.  Instead the status in the
// footer shows a warning icon after "Faulted", and tapping the status opens the faults page.
var FAULTED_STATE = 'Faulted';
var FAULTS_PAGE_URL = '/faults';
var FAULT_ICON_HTML = '<img class="fault-icon" src="/static/warning.svg" alt="Warning">';
// the status is only rewritten when it changes, so that a tap on it isn't lost by replacing it mid-tap
var displayed_base_state = null;

var base_state_element = document.getElementById('base_state');
if (base_state_element != null) {
  base_state_element.addEventListener('click', function() {
    if (base_state_element.classList.contains('faulted') && (window.location.pathname !== FAULTS_PAGE_URL)) {
      location.href = FAULTS_PAGE_URL;
    }
  });
}

// Play buttons with the class 'disable-when-faulted' are disabled while the base is faulted (hard fault).
// A page that also disables its play button for its own reasons (drill_list.html) doesn't use the class:
// it includes base_faulted in its own check, and re-checks on the 'base_faulted_change' event.
var base_faulted = false;
function set_base_faulted(faulted) {
  if (faulted === base_faulted) {
    return;
  }
  base_faulted = faulted;
  document.querySelectorAll('.disable-when-faulted').forEach(function(button) {
    button.disabled = faulted;
  });
  document.dispatchEvent(new Event('base_faulted_change'));
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
      // var Idmessage = document.getElementById("header-mess"); //!! TODO - renable

      if (IdToUpdate == null) {
        console.log("error: element=" + key + " was not found on page")
      } else {
        if (data[key] !== displayed_base_state) {
          displayed_base_state = data[key];
          if (data[key] == 'Outofballs') {
            IdToUpdate.innerHTML = "Status: Out Of Balls";
            // if (Idmessage != null) {
            //   Idmessage.innerHTML = "Add balls to hopper";
            // } else {
            //   console.log("No header-message element")
            // }
          } else if (data[key] == FAULTED_STATE) {
            IdToUpdate.innerHTML = "Status: " + data[key] + FAULT_ICON_HTML;
          } else {
            IdToUpdate.innerHTML = "Status: " + data[key];
          }
          // the 'faulted' class makes the status tappable (see the click listener above)
          IdToUpdate.classList.toggle("faulted", data[key] == FAULTED_STATE);
          set_base_faulted(data[key] == FAULTED_STATE);
        }
        // set pause/resume icon on game/drill/workout active pages
        var IdPauseResume = document.getElementById("pause-resume");
        if (IdPauseResume != null)
        {
          var classPauseResume = document.getElementById("pause-resume").className;
          // console.log('classPauseResume:' + classPauseResume)
          if ((data[key] == 'Paused') || (data[key] == 'Outofballs')) {
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
      // disable the GAME mode Play button if tracking is faulted: the ID game_button is on the
      // main screen's Play button and on the Game Settings start button (other pages don't have it)
      // console.log("soft_fault=" + data[key] + "; page_id=" + page_id)
      var IdToUpdate = document.getElementById("game_button");
      if (IdToUpdate) {
        if (data[key] == 1) {
          IdToUpdate.disabled = true;
        } else {
          IdToUpdate.disabled = false;
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