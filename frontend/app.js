// Global state
let fields = [];
let machines = [];
let editingMachineId = null;

// ---------- Helpers ----------
function $(id) {
  return document.getElementById(id);
}

// escape text before putting it inside innerHTML
function escapeHtml(text) {
  const div = document.createElement("div");
  div.textContent = text === undefined || text === null ? "" : text;
  return div.innerHTML;
}

function showMessage(text, type) {
  const box = $("message");
  box.textContent = text;
  box.className = "message " + type;
  setTimeout(() => box.classList.add("hidden"), 3000);
}

async function api(url, method = "GET", body = null) {
  const options = { method: method, headers: { "Content-Type": "application/json" } };
  if (body) {
    options.body = JSON.stringify(body);
  }

  const response = await fetch("/api" + url, options);
  if (response.status === 204) {
    return null;
  }

  const data = await response.json();
  if (!response.ok) {
    throw new Error(data.detail || "Something went wrong");
  }
  return data;
}

async function loadData() {
  fields = await api("/fields");
  machines = await api("/machines");
  renderFields();
  renderMachines();
  renderMachineForm({});
  renderPredictOptions();
}

// ---------- Tabs ----------
document.querySelectorAll(".tab").forEach((button) => {
  button.addEventListener("click", () => {
    document.querySelectorAll(".tab").forEach((b) => b.classList.remove("active"));
    button.classList.add("active");

    ["fields", "machines", "predict"].forEach((name) => {
      $("tab-" + name).classList.toggle("hidden", name !== button.dataset.tab);
    });
  });
});

// ---------- Fields ----------
function renderFields() {
  let html = "<tr><th>Name</th><th>Type</th><th>Required</th><th>Options</th><th></th></tr>";

  fields.forEach((field) => {
    html += `<tr>
      <td>${escapeHtml(field.name)}</td>
      <td><span class="badge">${field.type}</span></td>
      <td>${field.required ? "Yes" : "No"}</td>
      <td>${escapeHtml(field.options.join(", "))}</td>
      <td>
        <button class="btn small secondary" onclick="editField(${field.id})">Edit</button>
        <button class="btn small danger" onclick="deleteField(${field.id})">Delete</button>
      </td>
    </tr>`;
  });
  $("fields-table").innerHTML = html;
}

$("field-type").addEventListener("change", () => {
  $("options-box").classList.toggle("hidden", $("field-type").value !== "dropdown");
});

$("add-field-btn").addEventListener("click", async () => {
  const type = $("field-type").value;
  const newField = {
    name: $("field-name").value,
    type: type,
    required: $("field-required").checked,
    options: type === "dropdown" ? $("field-options").value.split(",") : [],
  };

  try {
    await api("/fields", "POST", newField);
    $("field-name").value = "";
    $("field-options").value = "";
    $("field-required").checked = false;
    showMessage("Field added", "success");
    await loadData();
  } catch (error) {
    showMessage(error.message, "error");
  }
});

async function editField(id) {
  const field = fields.find((f) => f.id === id);

  const name = prompt("Field name:", field.name);
  if (name === null) return;
  const required = confirm("Is this field required? (OK = yes, Cancel = no)");

  let options = field.options;
  if (field.type === "dropdown") {
    const input = prompt("Options (comma separated):", field.options.join(", "));
    if (input === null) return;
    options = input.split(",");
  }

  try {
    await api("/fields/" + id, "PUT", { name: name, type: field.type, required: required, options: options });
    showMessage("Field updated", "success");
    await loadData();
  } catch (error) {
    showMessage(error.message, "error");
  }
}

async function deleteField(id) {
  if (!confirm("Delete this field? Its values will be removed from all machines.")) return;

  try {
    await api("/fields/" + id, "DELETE");
    showMessage("Field deleted", "success");
    await loadData();
  } catch (error) {
    showMessage(error.message, "error");
  }
}

// ---------- Machines ----------
function renderMachines() {
  let html = "<tr><th>ID</th>";
  fields.forEach((field) => {
    html += `<th>${escapeHtml(field.name)}</th>`;
  });
  html += "<th></th></tr>";

  if (machines.length === 0) {
    html += `<tr><td colspan="${fields.length + 2}" class="muted">No machines yet.</td></tr>`;
  }

  machines.forEach((machine) => {
    html += `<tr><td>${machine.id}</td>`;
    fields.forEach((field) => {
      const value = machine.values[field.id];
      html += `<td>${value === undefined ? "-" : escapeHtml(value)}</td>`;
    });
    html += `<td>
      <button class="btn small secondary" onclick="editMachine(${machine.id})">Edit</button>
      <button class="btn small danger" onclick="deleteMachine(${machine.id})">Delete</button>
    </td></tr>`;
  });
  $("machines-table").innerHTML = html;
}

// build the form from the configured fields
function renderMachineForm(values) {
  let html = '<div class="row">';

  fields.forEach((field) => {
    const current = values[field.id] === undefined ? "" : values[field.id];
    const star = field.required ? " *" : "";
    html += `<div><label>${escapeHtml(field.name)}${star}</label>`;

    if (field.type === "dropdown") {
      html += `<select data-field-id="${field.id}"><option value="">-- select --</option>`;
      field.options.forEach((option) => {
        const selected = option === current ? "selected" : "";
        html += `<option value="${escapeHtml(option)}" ${selected}>${escapeHtml(option)}</option>`;
      });
      html += "</select>";
    } else {
      const inputType = field.type === "number" ? "number" : "text";
      html += `<input type="${inputType}" step="any" data-field-id="${field.id}" value="${escapeHtml(current)}">`;
    }
    html += "</div>";
  });

  html += "</div>";
  $("machine-form").innerHTML = html;
}

function resetMachineForm() {
  editingMachineId = null;
  $("form-title").textContent = "New Machine";
  renderMachineForm({});
}

function editMachine(id) {
  const machine = machines.find((m) => m.id === id);
  editingMachineId = id;
  $("form-title").textContent = "Edit Machine #" + id;
  renderMachineForm(machine.values);
  $("machine-form").scrollIntoView({ behavior: "smooth" });
}

$("save-machine-btn").addEventListener("click", async () => {
  const values = {};
  document.querySelectorAll("#machine-form [data-field-id]").forEach((input) => {
    values[input.dataset.fieldId] = input.value;
  });

  try {
    if (editingMachineId === null) {
      await api("/machines", "POST", { values: values });
    } else {
      await api("/machines/" + editingMachineId, "PUT", { values: values });
    }
    showMessage("Machine saved", "success");
    editingMachineId = null;
    $("form-title").textContent = "New Machine";
    await loadData();
  } catch (error) {
    showMessage(error.message, "error");
  }
});

$("clear-form-btn").addEventListener("click", resetMachineForm);

async function deleteMachine(id) {
  if (!confirm("Delete this machine?")) return;

  try {
    await api("/machines/" + id, "DELETE");
    showMessage("Machine deleted", "success");
    await loadData();
  } catch (error) {
    showMessage(error.message, "error");
  }
}

// ---------- Prediction ----------
function renderPredictOptions() {
  const nameField = fields.find((f) => f.name.toLowerCase() === "machine name");
  let html = "";

  machines.forEach((machine) => {
    let label = "Machine #" + machine.id;
    if (nameField && machine.values[nameField.id]) {
      label += " - " + machine.values[nameField.id];
    }
    html += `<option value="${machine.id}">${escapeHtml(label)}</option>`;
  });

  $("predict-machine").innerHTML = html || '<option value="">No machines available</option>';
}

$("predict-btn").addEventListener("click", async () => {
  const id = $("predict-machine").value;
  if (!id) {
    showMessage("Select a machine first", "error");
    return;
  }

  try {
    const result = await api(`/machines/${id}/predict`, "POST");
    let html = `<div class="result ${result.risk_level}">
      <div class="muted">Risk Level</div>
      <h3>${result.risk_level}</h3>
      <div class="muted">Confidence: ${Math.round(result.confidence * 100)}%</div>
    </div>
    <p class="muted">Inputs used by the model: ${escapeHtml(result.features_used.join(", "))}.</p>`;

    if (result.features_ignored.length > 0) {
      html += `<p class="muted">Not used by the current model: ${escapeHtml(result.features_ignored.join(", "))}.</p>`;
    }
    $("predict-result").innerHTML = html;
  } catch (error) {
    showMessage(error.message, "error");
  }
});

// start
loadData().catch((error) => showMessage(error.message, "error"));
