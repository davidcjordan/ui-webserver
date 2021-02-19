// javascript to update score table
// update data format is: {"pp": 1, "bp": 1, "pg": 3, "bg": 2, "ps": 5, "bs": 4, "pt": 6, "bt": 7, "server": "b"}
// where: p = player, b = boomer, 
//        2nd char: p = point, g = game, s = set, t = tiebreak points

// var socket = io();
socket.on('score_update', function(data) {
  Object.keys(data).forEach(function(key) {
    // console.log('Key : ' + key + ', Value : ' + data[key])
    var IdToUpdate = document.getElementById(key);
    if (IdToUpdate) {
      if (key !== 'server') {
        IdToUpdate.innerHTML = data[key];
      }
      else {
        if (data[key] == 'b') {
          IdToUpdate.innerHTML = "Boomer's serve"
        } else {
          IdToUpdate.innerHTML = "Player's serve"
        }
      }
    }
    else {
      console.log("No element with ID: " + key)
    }
  })
});