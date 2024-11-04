document.getElementById("add_row").addEventListener("click", function (event) {
  event.preventDefault();
  console.log("add_row_button clicked");
  const table = document.getElementById('drill_table');
  const newRowNumber = table.rows.length;

  const row = table.insertRow();
  // first column:
  var cell = row.insertCell();
  cell.textContent = newRowNumber;
  cell.className = "Cell";

  for (let i = 1; i < 7; i++) {
    const select_list = document.getElementById('column-' + i); 
    if (select_list == null) {
      console.log("select_list is null")
      // how to handle error ?
    }
    //  else {
    //   console.log(select_list.innerHTML)
    // }
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
  table.deleteRow(lastRowNumber);
}, false);
