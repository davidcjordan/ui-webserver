document.getElementById("add_row").addEventListener("click", function (event) {
  event.preventDefault();
  console.log("add_row_button clicked");
  const table = document.getElementById('drill_table');
  const newRowNumber = table.rows.length;

  const rowLimit = 10;
  if (newRowNumber > rowLimit) {
    console.log("Not adding row; limit is " + rowLimit + "rows.")
    return;
  }

  const row = table.insertRow();
  // first column:
  var cell = row.insertCell();
  cell.textContent = newRowNumber;
  cell.className = "Cell";

  for (let i = 1; i < 11; i++) {
    const select_list = document.getElementById('column-' + i); 
    if (select_list == null) {
      console.log("select_list is null")
      alert("Missing data on webpage, so editing drills is broken. Redirecting to the home page.");
      window.location.replace("/");
    }
    cell = row.insertCell();
    cell.innerHTML = '<select name="' + newRowNumber + '-' + i +'">\n' + 
      select_list.innerHTML +
      '</select>' 
  }
  initEventListeners();
}, false);

document.getElementById("del_row").addEventListener("click", function (event) {
  event.preventDefault();
  const table = document.getElementById('drill_table');
  const lastRowNumber = table.rows.length - 1;
  console.log("del_row_button clicked: delete row=" + lastRowNumber);
  if (lastRowNumber > 1) {
    table.deleteRow(lastRowNumber);
  }
}, false);

// window.addEventListener('load', (event) => {
//   console.log('edit_drill: The page has fully loaded');
//   const form_elements = document.getElementsByTagName('form')[0].elements;
//   console.log(form_elements);
// });

window.onload = function() {
  initEventListeners();
};

function initEventListeners() {
  console.log('initEventListeners called');
  const selectors = document.querySelectorAll("select");
  // console.log(selectors[0].name, selectors[0].value);
  // the above log yields: 1-1 Serve
  // console.log(selectors[0][0]);
  for (let i = 0; i < selectors.length; i++) {
    var column = selectors[i].name.split('-')[1];
    // console.log(fields[0], fields[1]);
    // only do value checking on shot-type, court and angle;
    if (column < 4) {
      selectors[i].addEventListener("change", dropDownChanged);
    }
  }

  // for (let i = 0; i < selectors.length; i++) {
  //     for (let j = 0; j < selectors[i].length; j++) {
  //       var selected = selectors[i][j].attributes.getNamedItem("selected").value;
  //       console.log("selector=" + i + " option=" + j +  " selected=" + selected);
  //   }
  // }
}

function dropDownChanged(event) {
  const name = event.currentTarget.name;
  const value = event.currentTarget.value;
  // const value = event.target.options[event.target.selectedIndex].getAttribute('value');
  console.log("dropDownChanged for ", name, value);
  const fields = name.split('-');
  const event_selector_row = fields[0];
  const event_selector_column = fields[1];
  // target_selector_column is the column that will change based on the event_selector_column
  // e.g. if event_selector_column is 2 (court), then target_selector_column is 3 (angle)
  let target_selector_columns = ['3']; // assume will change angle
  if (event_selector_column === '1') {
    target_selector_columns = ['7','8','9','10']; // otherwise change speed, loft, spin
  }

  const selectors = document.querySelectorAll("select");
  for (let i = 0; i < selectors.length; i++) {
    // if (i < 2) {
    //   console.log("Selector ", i, " = ", selectors[i]);
    // }
    if ((selectors[i].name.split('-')[0] === event_selector_row) &&
        target_selector_columns.includes(selectors[i].name.split('-')[1])) {
        // console.log('matched ', event_selector_row, target_selector_columns, event_selector_column);
      if (event_selector_column === '2') {
        if (value === 'FH' || value === 'BH') {
          if (selectors[i].value === '-') {
            selectors[i].value = '6';
          } //else leave the current value
        } else {
          selectors[i].value = '-';
        }
        } else if (event_selector_column === '1') {
          // change from Custom to something else should set to '-----'
          // change from something else to Custom should set to a value based on the column
          if (value !== 'Custom') {
            // console.log("value is not Custom, so setting to -----");
            selectors[i].value = '------';
          } else {
            // console.log("should set column ", selectors[i].name.split('-')[1], "to a value");
            if (selectors[i].name.split('-')[1] === '7') {
              selectors[i].value = '40'; // speed
            } else if (selectors[i].name.split('-')[1] === '8') {
              selectors[i].value = '20'; // loft
            } else if (selectors[i].name.split('-')[1] === '9') {
              selectors[i].value = '1000'; // spin
            } else if (selectors[i].name.split('-')[1] === '10') {
              selectors[i].value = 'Plus'; // spin type
            }
          }
        }
     }
  }

}
