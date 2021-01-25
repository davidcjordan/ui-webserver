// Stepper Increment Style Element, use container as class="stepper"
var inc = document.getElementsByClassName("stepper");
for (i = 0; i < inc.length; i++) {
  var incI = inc[i].querySelector("input"),
    id = incI.getAttribute("id"),
    min = incI.getAttribute("min"),
    max = incI.getAttribute("max"),
    step = incI.getAttribute("step");
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
  if (s > 0) {
    if (parseInt(el.value) < m) {
      el.value = parseInt(el.value) + s;
    }
  } else {
    if (parseInt(el.value) > m) {
      el.value = parseInt(el.value) + s;
    }
  }  
  // post data to webserver to update base
  let data = {};
  data[el.name] = el.value;
  fetch("/active", {
    method: "POST", 
    body: JSON.stringify(data)
  }).then(respns => {
    console.log("POST %s: %f -- response: %s", el.name, el.value, respns);
  });
}

