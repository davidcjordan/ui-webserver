document.getElementById("add_row").addEventListener("click", function (event) {
  event.preventDefault();
  console.log("add_row_button clicked");
  const table = document.getElementById('drill_table');
  const newRowNumber = table.rows.length;

  const rowLimit = 9;
  if (newRowNumber > rowLimit) {
    console.log("Not adding row; limit is " + rowLimit + "rows.")
    return;
  }

  const row = table.insertRow();
  // first column:
  var cell = row.insertCell();
  cell.textContent = newRowNumber;
  cell.className = "Cell";

  for (let i = 1; i < 7; i++) {
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
  // console.log(selectors[0][0]);
  for (let i = 0; i < selectors.length; i++) {
    selectors[i].addEventListener("change", dropDownChanged);
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
}
