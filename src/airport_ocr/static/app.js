"use strict";

const MAX_PDF_BYTES = 5 * 1024 * 1024;
const $ = (id) => document.getElementById(id);
const form = $("upload-form");
const fileInput = $("pdf-file");
const permission = $("permission-confirmed");
const button = $("extract-button");
const resetButton = $("reset-button");
const statusNode = $("request-status");
const errorPanel = $("error-panel");
const resultPanel = $("result-panel");
const output = $("json-output");
const viewSelect = $("result-view");
const dropZone = $("drop-zone");
let responseData = null;
let selectedFile = null;

function formatBytes(bytes) {
  return bytes < 1024 * 1024
    ? `${(bytes / 1024).toFixed(1)} KiB`
    : `${(bytes / (1024 * 1024)).toFixed(2)} MiB`;
}

function selectedFileError(file) {
  if (!file) return "Choose one PDF file.";
  if (!file.name.toLowerCase().endsWith(".pdf")) return "The filename must end in .pdf.";
  if (file.type && file.type !== "application/pdf") return "The browser media type must be application/pdf.";
  if (file.size === 0) return "The selected PDF is empty.";
  if (file.size > MAX_PDF_BYTES) return "The selected PDF exceeds the 5 MiB limit.";
  return null;
}

function showError(message) {
  errorPanel.textContent = message;
  errorPanel.hidden = false;
}

function clearError() {
  errorPanel.textContent = "";
  errorPanel.hidden = true;
}

function activeView() {
  if (!responseData) return null;
  return viewSelect.value === "full" ? responseData : responseData[viewSelect.value];
}

function renderJson() {
  const value = activeView();
  output.textContent = value == null ? "" : JSON.stringify(value, null, 2);
}

function renderSummary(data) {
  const airport = data.normalized?.airport || {};
  const extraction = data.normalized?.extraction || {};
  const validation = data.validation || {};
  const items = [
    ["Airport", airport.icao || "n/a"],
    ["Name", airport.name || "not extracted"],
    ["Extraction", extraction.status || "n/a"],
    ["Validation", validation.status || "n/a"],
  ];
  $("summary-grid").replaceChildren(...items.map(([label, value]) => {
    const card = document.createElement("div");
    card.className = "summary-card";
    const labelNode = document.createElement("span");
    labelNode.className = "label";
    labelNode.textContent = label;
    const valueNode = document.createElement("span");
    valueNode.className = "value";
    valueNode.textContent = String(value);
    card.append(labelNode, valueNode);
    return card;
  }));
}

async function problemMessage(response) {
  try {
    const problem = await response.json();
    const violations = (problem.violations || []).map((v) => `${v.field}: ${v.message}`).join("\n");
    return `${problem.code || "REQUEST_FAILED"}: ${problem.detail || response.statusText}${violations ? `\n${violations}` : ""}`;
  } catch (_) {
    return `Request failed with HTTP ${response.status}.`;
  }
}

function updateSelectedFile(file) {
  selectedFile = file || null;
  $("file-label").textContent = selectedFile
    ? `${selectedFile.name} · ${formatBytes(selectedFile.size)}`
    : "No file selected";
  clearError();
  const error = selectedFileError(selectedFile);
  if (selectedFile && error) showError(error);
}

fileInput.addEventListener("change", () => {
  updateSelectedFile(fileInput.files[0]);
});

for (const eventName of ["dragenter", "dragover"]) {
  dropZone.addEventListener(eventName, (event) => {
    event.preventDefault();
    dropZone.classList.add("dragging");
  });
}
dropZone.addEventListener("dragleave", () => dropZone.classList.remove("dragging"));
dropZone.addEventListener("drop", (event) => {
  event.preventDefault();
  dropZone.classList.remove("dragging");
  const files = event.dataTransfer?.files || [];
  if (files.length !== 1) {
    updateSelectedFile(null);
    showError("Drop exactly one PDF file.");
    return;
  }
  updateSelectedFile(files[0]);
});

viewSelect.addEventListener("change", renderJson);

form.addEventListener("submit", async (event) => {
  event.preventDefault();
  clearError();
  const file = selectedFile;
  const clientError = selectedFileError(file);
  if (clientError) return showError(clientError);
  if (!permission.checked) return showError("Confirm permission before processing the file.");

  const body = new FormData();
  body.append("file", file);
  body.append("permission_confirmed", "true");
  body.append("profile", "auto");
  button.disabled = true;
  statusNode.textContent = "Uploading and extracting locally…";
  resultPanel.hidden = true;

  try {
    const response = await fetch("/api/v1/extractions", { method: "POST", body });
    if (!response.ok) throw new Error(await problemMessage(response));
    responseData = await response.json();
    renderSummary(responseData);
    viewSelect.value = "full";
    renderJson();
    resultPanel.hidden = false;
    statusNode.textContent = "Extraction completed. Review partial and blocker statuses before using the data.";
    resultPanel.scrollIntoView({ behavior: "smooth", block: "start" });
  } catch (error) {
    statusNode.textContent = "Extraction did not complete.";
    showError(error.message || String(error));
  } finally {
    button.disabled = false;
  }
});

resetButton.addEventListener("click", () => {
  form.reset();
  responseData = null;
  selectedFile = null;
  $("file-label").textContent = "No file selected";
  statusNode.textContent = "";
  resultPanel.hidden = true;
  clearError();
});

$("copy-button").addEventListener("click", async () => {
  await navigator.clipboard.writeText(output.textContent);
  statusNode.textContent = "Current JSON view copied to the clipboard.";
});

$("download-button").addEventListener("click", () => {
  const value = activeView();
  if (value == null) return;
  const blob = new Blob([JSON.stringify(value, null, 2) + "\n"], { type: "application/json" });
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = `airport-ocr-${viewSelect.value}.json`;
  link.click();
  URL.revokeObjectURL(url);
});

(async () => {
  try {
    const response = await fetch("/api/v1/health");
    if (!response.ok) throw new Error();
    const health = await response.json();
    $("health-status").textContent = `${health.status.toUpperCase()} · v${health.version} · 5 MiB max`;
    $("health-status").classList.add("ok");
  } catch (_) {
    $("health-status").textContent = "Service unavailable";
  }
})();
