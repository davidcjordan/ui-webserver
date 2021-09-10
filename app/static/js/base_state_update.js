// javascript to update base state: Idle, Active, etc
// update data format is: {"base_state": "state"}

// var socket = io();
socket.on('base_state_update', function(data) {
  Object.keys(data).forEach(function(key) {
    console.log('Key : ' + key + ', Value : ' + data[key])
    var IdToUpdate = document.getElementById(key);
    if (IdToUpdate) {
      IdToUpdate.innerHTML = "Status: " + data[key];
    }
    else {
      console.log("No element with ID: " + key)
    }
  })
});