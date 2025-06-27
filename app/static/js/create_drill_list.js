// Create a scrollable DIV for drill descriptions
const descriptDiv = document.createElement("DIV");
descriptDiv.setAttribute("class", "para-nomargin");
descriptDiv.id = "drill_list";

// Style the div to be scrollable and have a fixed height
descriptDiv.style.maxHeight = "400px";
descriptDiv.style.overflowY = "auto";
descriptDiv.style.border = "1px solid #ccc";
descriptDiv.style.padding = "10px";
descriptDiv.style.marginTop = "10px";

// Insert the div before the placeholder
const placeHolder = document.getElementById("drill_list_placeholder");
placeHolder.parentElement.insertBefore(descriptDiv, placeHolder);

socket.emit('get_drill_list'); //this triggers the get drill list function to run in events.py

 //Example: use test data instead of socket
 // handleDrillList([
   // { name: "Sample Drill 1", description: "This is the first sample drill." },
   // { name: "Sample Drill 2", description: "This is another sample drill with more detail." }
 // ]);


// Handle incoming drill description data
function handleDrillList(data) {
  if (!Array.isArray(data)) return;

  descriptDiv.innerHTML = ""; // Clear current content

  // Create a single form to wrap all entries
  const form = document.createElement("form");
  form.method = "POST";
  form.action = "/drill"; // Replace with your actual URL

  data.every(drill => {
    if(drill.number > 200) return false; //break
    const drillBlock = document.createElement("div");
    drillBlock.style.marginBottom = "15px";
    drillBlock.id = "drillblock" + drill.number;

    // Container for number and name
    const titleContainer = document.createElement("div");
    titleContainer.style.display = "flex";
    titleContainer.style.fontSize = "35px";
    titleContainer.style.alignItems = "baseline";
    titleContainer.style.gap = "10px";
    titleContainer.style.cursor = "pointer";

    // Drill number with distinct style
    const number = document.createElement("span");
    number.textContent = drill.number || "";
    number.style.fontWeight = "bold";
    number.style.color = "#555758";
    number.style.minWidth = "30px";

    // Drill name
    const title = document.createElement("span"); // Use <span> instead of <strong> to preserve font sizing
    title.textContent = drill.name;

    titleContainer.appendChild(number);
    titleContainer.appendChild(title);

    // Submit on click of number/name
    titleContainer.addEventListener("click", function () {
      // Remove any previous choice_id inputs
      form.querySelectorAll('input[name="choice_id"]').forEach(el => el.remove());

      // Add new hidden input
      const hiddenInput = document.createElement("input");
      hiddenInput.type = "hidden";
      hiddenInput.name = "choice_id";
      hiddenInput.value = drill.number;
      form.appendChild(hiddenInput);

      form.submit();
    });

    // Drill description
    const description = document.createElement("p");
    description.style.marginLeft = "30px";
    description.style.fontSize = "30px";
    description.textContent = drill.description;

    drillBlock.appendChild(titleContainer);
    drillBlock.appendChild(description);
    form.appendChild(drillBlock);
    return true; //iterate again
  });

  descriptDiv.appendChild(form);
}


socket.on('drill_list', function (data) { //this listens for the reply and calls handleDrillList below on the data
  handleDrillList(data);
});