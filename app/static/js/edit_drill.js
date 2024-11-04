document.getElementById("add_row").addEventListener("click", function (event) {
  event.preventDefault();
  console.log("add_row_button clicked");
  const table = document.getElementById('drill_table');

  // const lastRow = table.rows[table.rows.length - 1];
  const newRowNumber = table.rows.length;
  // console.log({newRowNumber});

  const cellDict = {};
  for (let i = 0; i < 7; i++) {
    cellName = newRowNumber + '-' + i
    if (i > 0) {
      cellContent = newRowNumber + '-' + i
    } else {
      cellContent = newRowNumber
    }
    
    cellDict[cellName] = cellContent;
  }
  // console.log({cellDict});

  const row = table.insertRow();
  // first column:
  var cell = row.insertCell();
  cell.textContent = newRowNumber;
  cell.className = "Cell";

  cell = row.insertCell();
  cell.innerHTML = '<select name="3-1">\n' +
      '<option value="Serve">Serve</option>\n' +
      '<option value="Drop">Drop</option>\n' +
      '<option value="Flat">Flat</option>\n' +
      '<option value="Loop">Loop</option>\n' +
      '<option value="Chip">Chip</option>\n' +
      '<option value="Lob">Lob</option>\n' +
      '<option value="Topspin">Topspin</option>\n' +
      '<option value="Pass">Pass</option>\n' +
      '<option value="Custom">Custom</option>\n' +
      '<option value="Rand Grd">Rand Grd</option>\n' +
      '<option value="Rand Net">Rand Net</option>\n' +
    '</select>'

  // for (const [key, value] of Object.entries(cellDict)) {
  //   // console.log(key, value);
  //   const cell = row.insertCell();
  //   cell.name = key;
  //   cell.textContent = value;
  //   cell.className = "Cell";
  // }
}, false);