// Stepper Increment Style Element, use container as class="stepper"
var inc = document.getElementsByClassName("stepper");
for (i = 0; i < inc.length; i++) {
  var incI = inc[i].querySelector("input"),
    id = incI.getAttribute("id"),
    min = incI.getAttribute("min"),
    max = incI.getAttribute("max"),
    step = incI.getAttribute("step");
  // console.log("adding onclick to: " + incI.id)
  document
    .getElementById(id)
    .previousElementSibling.setAttribute(
      "onclick",
      "stepperInput('" + id + "', -" + step + ", " + min + ")"
    ); // Down
  document
    .getElementById(id)
    .nextElementSibling.setAttribute(
      "onclick",
      "stepperInput('" + id + "', " + step + ", " + max + ")"
    ); // Up
}

// Stepper Increment Function with Min/Max
function stepperInput(id, s, m) {
  var el = document.getElementById(id);
  // console.log("ID %s -- Step: %f  -- min/max: %f", id, s, m);
  var updated = new Boolean(false);
  var currentValue = parseFloat(el.value);
  if (s > 0) {
    if (currentValue < m) {
      el.value = currentValue + s;
      updated = true;
    }
  } else {
    if (currentValue > m) {
      el.value = currentValue + s;
      updated = true;
    }
  }  
  // emit data to webserver to update base IF the page does not have a form
  // the drill & game pages do not have forms, the cam_position page does.
  if (updated) {
    // console.log("(iteration 2) forms count: " + document.forms.length);
    if (document.forms.length === 0) {
      let data = {};
      data[el.name] = Number(el.value);
      // -- Before using websockets, then did a post, as follows:
      // fetch("/active", {
      //   method: "POST", 
      //   body: JSON.stringify(data)
      // }).then(respns => {
      //   console.log("POST %s: %f -- response: %s", el.name, el.value, respns);
      // });
      // var socket = io();
      if (typeof socket !== 'undefined') {
        socket.emit('change_params', JSON.stringify(data));
        console.log("Emitted: change_params");
      }
      else {
        console.log("Number picker: socket not defined");
      }
    }
  }
}
