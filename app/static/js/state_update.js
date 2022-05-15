// javascript to update base state: Idle, Active, etc
// update data format is: {"base_state": "state"}

// var socket = io();
socket.on('state_update', function(data) {
  // console.log("Data:" + JSON.stringify(data, null, 1))
  Object.keys(data).forEach(function(key) {
    // console.log('Key : ' + key + ', Value : ' + data[key])
    var IdToUpdate = document.getElementById(key);
    if (IdToUpdate) {
      if (key === 'base_state') {
        if ((data[key] === 'Faulted') && !window.location.href.includes("faults")) {
          console.log("Faulted status detected; switching to /faults")
          location.href = '/faults';
        } else if ((data[key] !== 'Faulted') && window.location.href.includes("faults")) {
          console.log("NON-Faulted status detected; switching to /")
          location.href = '/';
        } else if (window.location.href.includes("creep") && (data[key] !== 'Active')) {
          console.log("creep calibration done; switching to /")
          location.href = '/';
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
          }
        }
      } else if (key === 'server') {
        if (data[key] == 'b') {
          IdToUpdate.innerHTML = "Boomer's serve"
        } else {
          IdToUpdate.innerHTML = "Player's serve"
        }
      } else {
        IdToUpdate.innerHTML = data[key];
      }
    } else {
      console.log("No element with ID: " + key)
    }
  })
});