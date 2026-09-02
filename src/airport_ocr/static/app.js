"use strict";

const MAX_PDF_BYTES = 5 * 1024 * 1024;
const SVG_NS = "http://www.w3.org/2000/svg";
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
let requestActive = false;

function formatBytes(bytes) {
  return bytes < 1024 * 1024
    ? `${(bytes / 1024).toFixed(1)} KiB`
    : `${(bytes / (1024 * 1024)).toFixed(2)} MiB`;
}

function selectedFileError(file) {
  if (!file) return "Choose or drop one PDF file.";
  if (!file.name.toLowerCase().endsWith(".pdf")) return "The filename must end in .pdf.";
  if (file.type && file.type !== "application/pdf") return "The browser media type must be application/pdf.";
  if (file.size === 0) return "The selected PDF is empty.";
  if (file.size > MAX_PDF_BYTES) return "The selected PDF exceeds the fixed 5 MiB limit.";
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

function setBusy(busy) {
  requestActive = busy;
  button.disabled = busy;
  resetButton.disabled = busy;
  fileInput.disabled = busy;
  permission.disabled = busy;
  dropZone.classList.toggle("busy", busy);
}

function syncNativeFile(file) {
  try {
    const transfer = new DataTransfer();
    if (file) transfer.items.add(file);
    fileInput.files = transfer.files;
  } catch (_) {
    // selectedFile remains the authoritative state on browsers without DataTransfer construction.
  }
}

function updateSelectedFile(file, syncInput = false) {
  selectedFile = file || null;
  if (syncInput) syncNativeFile(selectedFile);
  $("file-label").textContent = selectedFile
    ? `${selectedFile.name} · ${formatBytes(selectedFile.size)}`
    : "No file selected";
  dropZone.classList.toggle("has-file", Boolean(selectedFile));
  clearError();
  const error = selectedFileError(selectedFile);
  if (selectedFile && error) showError(error);
}

function multipartFile(file) {
  if (file.type === "application/pdf") return file;
  return new File([file], file.name, {
    type: "application/pdf",
    lastModified: file.lastModified,
  });
}

function activeView() {
  if (!responseData) return null;
  const results = responseData.results || {};
  const views = {
    full: responseData,
    package: results.package,
    normalized: results.normalized,
    geojson: results.geojson,
    validation: results.validation,
    observations: results.observations,
    holding_candidates: results.holding_candidates,
    words: responseData.evidence?.positioned_words,
    intake: responseData.intake,
    research: responseData.research,
    manifest: responseData.manifest,
  };
  return views[viewSelect.value];
}

function renderJson() {
  const value = activeView();
  output.textContent = value == null ? "" : JSON.stringify(value, null, 2);
}

function makeSummaryCard(label, value) {
  const card = document.createElement("div");
  card.className = "summary-card";
  const labelNode = document.createElement("span");
  labelNode.className = "label";
  labelNode.textContent = label;
  const valueNode = document.createElement("span");
  valueNode.className = "value";
  valueNode.textContent = String(value ?? "n/a");
  card.append(labelNode, valueNode);
  return card;
}

function renderOverview(data) {
  const packageData = data.results?.package || {};
  const airport = packageData.airport || {};
  const validation = data.results?.validation || {};
  const items = [
    ["Airport", airport.icao || "n/a"],
    ["Name", airport.name || "not extracted"],
    ["Pipeline", data.pipeline?.status || "n/a"],
    ["Validation", `${validation.status || "n/a"} · ${validation.failure_count || 0} failures`],
    ["Pages", data.run?.page_count || 0],
    ["Native words", data.run?.native_word_count || 0],
    ["Runways", packageData.runways?.length || 0],
    ["Artifacts", data.artifacts?.length || 0],
  ];
  $("summary-grid").replaceChildren(...items.map(([label, value]) => makeSummaryCard(label, value)));
  $("run-id").textContent = data.run?.run_id || "";
}

function renderPipeline(data) {
  const nodes = (data.pipeline?.stages || []).map((stage, index) => {
    const item = document.createElement("li");
    item.className = "pipeline-stage";
    const number = document.createElement("span");
    number.className = "stage-number";
    number.textContent = String(index + 1).padStart(2, "0");
    const body = document.createElement("div");
    const label = document.createElement("strong");
    label.textContent = stage.label;
    const status = document.createElement("span");
    status.className = "stage-status";
    status.textContent = stage.status;
    body.append(label, status);
    item.append(number, body);
    return item;
  });
  $("pipeline-list").replaceChildren(...nodes);
}

function makeResearchCard(title, content) {
  const card = document.createElement("article");
  card.className = "research-card";
  const heading = document.createElement("h3");
  heading.textContent = title;
  card.append(heading, content);
  return card;
}

function renderResearch(data) {
  const research = data.research || {};
  const findings = document.createElement("dl");
  for (const [key, value] of Object.entries(research.document_findings || {})) {
    const term = document.createElement("dt");
    term.textContent = key.replaceAll("_", " ");
    const detail = document.createElement("dd");
    detail.textContent = Array.isArray(value) ? value.join(", ") || "none" : String(value ?? "n/a");
    findings.append(term, detail);
  }

  const boundary = document.createElement("ul");
  for (const value of research.supported_input_boundary || []) {
    const item = document.createElement("li");
    item.textContent = value;
    boundary.append(item);
  }

  const limitations = document.createElement("ul");
  for (const value of research.limitations || []) {
    const item = document.createElement("li");
    item.textContent = value;
    limitations.append(item);
  }

  const diagnostics = document.createElement("pre");
  diagnostics.className = "compact-output";
  diagnostics.textContent = JSON.stringify(research.extraction_diagnostics || {}, null, 2);

  $("research-content").replaceChildren(
    makeResearchCard("Document findings", findings),
    makeResearchCard("Supported-input boundary", boundary),
    makeResearchCard("Limitations and review gates", limitations),
    makeResearchCard("Extraction diagnostics", diagnostics),
  );
}

function geometryPositions(geometry) {
  if (!geometry) return [];
  if (geometry.type === "Point") return [geometry.coordinates];
  if (geometry.type === "LineString") return geometry.coordinates || [];
  return [];
}

function renderMap(collection) {
  const frame = $("map-frame");
  const features = collection?.features || [];
  const allPositions = features.flatMap((feature) => geometryPositions(feature.geometry));
  if (!allPositions.length) {
    frame.textContent = "No point or line geometry is available for this result.";
    return;
  }

  let minLon = Math.min(...allPositions.map((p) => Number(p[0])));
  let maxLon = Math.max(...allPositions.map((p) => Number(p[0])));
  let minLat = Math.min(...allPositions.map((p) => Number(p[1])));
  let maxLat = Math.max(...allPositions.map((p) => Number(p[1])));
  if (minLon === maxLon) { minLon -= 0.001; maxLon += 0.001; }
  if (minLat === maxLat) { minLat -= 0.001; maxLat += 0.001; }

  const width = 900;
  const height = 360;
  const padding = 34;
  const x = (lon) => padding + ((Number(lon) - minLon) / (maxLon - minLon)) * (width - padding * 2);
  const y = (lat) => height - padding - ((Number(lat) - minLat) / (maxLat - minLat)) * (height - padding * 2);
  const svg = document.createElementNS(SVG_NS, "svg");
  svg.setAttribute("viewBox", `0 0 ${width} ${height}`);
  svg.setAttribute("aria-hidden", "true");

  for (const feature of features) {
    const geometry = feature.geometry || {};
    const properties = feature.properties || {};
    if (geometry.type === "LineString") {
      const line = document.createElementNS(SVG_NS, "polyline");
      line.setAttribute("points", geometry.coordinates.map((p) => `${x(p[0])},${y(p[1])}`).join(" "));
      line.setAttribute("class", "map-line");
      svg.append(line);
    } else if (geometry.type === "Point") {
      const [lon, lat] = geometry.coordinates;
      const point = document.createElementNS(SVG_NS, "circle");
      point.setAttribute("cx", String(x(lon)));
      point.setAttribute("cy", String(y(lat)));
      point.setAttribute("r", properties.feature_type === "aerodrome_reference_point" ? "7" : "5");
      point.setAttribute("class", properties.feature_type === "aerodrome_reference_point" ? "map-arp" : "map-point");
      const title = document.createElementNS(SVG_NS, "title");
      title.textContent = properties.designator || properties.feature_type || "feature";
      point.append(title);
      svg.append(point);

      const label = document.createElementNS(SVG_NS, "text");
      label.setAttribute("x", String(x(lon) + 9));
      label.setAttribute("y", String(y(lat) - 7));
      label.textContent = properties.feature_type === "aerodrome_reference_point"
        ? "ARP"
        : properties.designator || "";
      svg.append(label);
    }
  }
  frame.replaceChildren(svg);
}

function searchGeoJson(collection, featureType, designator) {
  const matches = (collection?.features || []).filter((feature) => {
    const properties = feature.properties || {};
    if (featureType && properties.feature_type !== featureType) return false;
    if (designator && ![properties.designator, properties.designator_pair].includes(designator)) return false;
    return true;
  });
  return {
    type: "FeatureCollection",
    name: "airport-ocr browser search result",
    properties: {
      operational_use: false,
      query: { feature_type: featureType || null, designator: designator || null },
      match_count: matches.length,
    },
    features: matches,
  };
}

function runSearch() {
  if (!responseData) return;
  const featureType = $("search-feature-type").value.trim() || null;
  const designator = $("search-designator").value.trim().toUpperCase() || null;
  const result = searchGeoJson(responseData.results?.geojson, featureType, designator);
  $("search-status").textContent = `${result.properties.match_count} feature(s) matched.`;
  $("search-output").textContent = JSON.stringify(result, null, 2);
  renderMap(result);
}

function artifactValue(key) {
  if (!responseData) return null;
  const results = responseData.results || {};
  const values = {
    intake: responseData.intake,
    words: responseData.evidence?.positioned_words,
    observations: results.observations,
    holding_candidates: results.holding_candidates,
    normalized: results.normalized,
    geojson: results.geojson,
    validation: results.validation,
    package: results.package,
    summary: responseData.summary?.markdown,
    report: responseData.summary?.report_html,
    manifest: responseData.manifest,
  };
  return values[key];
}

function artifactBytes(descriptor) {
  const value = artifactValue(descriptor.key);
  const text = typeof value === "string" ? value : `${JSON.stringify(value, null, 2)}\n`;
  return new TextEncoder().encode(text);
}

function downloadBlob(blob, filename) {
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = filename;
  link.click();
  setTimeout(() => URL.revokeObjectURL(url), 0);
}

function downloadArtifact(descriptor) {
  const bytes = artifactBytes(descriptor);
  downloadBlob(new Blob([bytes], { type: descriptor.media_type }), descriptor.filename);
}

function renderArtifacts(data) {
  const rows = (data.artifacts || []).map((artifact) => {
    const row = document.createElement("tr");
    const name = document.createElement("td");
    name.textContent = artifact.filename;
    const type = document.createElement("td");
    type.textContent = artifact.media_type;
    const size = document.createElement("td");
    size.textContent = "Generated on download";
    const action = document.createElement("td");
    const download = document.createElement("button");
    download.type = "button";
    download.className = "secondary compact";
    download.textContent = "Download";
    download.addEventListener("click", () => downloadArtifact(artifact));
    action.append(download);
    row.append(name, type, size, action);
    return row;
  });
  $("artifact-list").replaceChildren(...rows);
}

const CRC_TABLE = (() => {
  const table = new Uint32Array(256);
  for (let n = 0; n < 256; n += 1) {
    let value = n;
    for (let k = 0; k < 8; k += 1) value = (value & 1) ? (0xedb88320 ^ (value >>> 1)) : (value >>> 1);
    table[n] = value >>> 0;
  }
  return table;
})();

function crc32(bytes) {
  let crc = 0xffffffff;
  for (const byte of bytes) crc = CRC_TABLE[(crc ^ byte) & 0xff] ^ (crc >>> 8);
  return (crc ^ 0xffffffff) >>> 0;
}

function write16(bytes, offset, value) {
  new DataView(bytes.buffer).setUint16(offset, value, true);
}

function write32(bytes, offset, value) {
  new DataView(bytes.buffer).setUint32(offset, value >>> 0, true);
}

function buildZip(descriptors) {
  const encoder = new TextEncoder();
  const localParts = [];
  const centralParts = [];
  let localOffset = 0;
  let centralSize = 0;
  const utf8Flag = 0x0800;
  const dosDate = 33;

  for (const descriptor of descriptors) {
    const name = encoder.encode(descriptor.filename);
    const content = artifactBytes(descriptor);
    const checksum = crc32(content);
    const local = new Uint8Array(30);
    write32(local, 0, 0x04034b50);
    write16(local, 4, 20);
    write16(local, 6, utf8Flag);
    write16(local, 8, 0);
    write16(local, 10, 0);
    write16(local, 12, dosDate);
    write32(local, 14, checksum);
    write32(local, 18, content.length);
    write32(local, 22, content.length);
    write16(local, 26, name.length);
    write16(local, 28, 0);
    localParts.push(local, name, content);

    const central = new Uint8Array(46);
    write32(central, 0, 0x02014b50);
    write16(central, 4, 20);
    write16(central, 6, 20);
    write16(central, 8, utf8Flag);
    write16(central, 10, 0);
    write16(central, 12, 0);
    write16(central, 14, dosDate);
    write32(central, 16, checksum);
    write32(central, 20, content.length);
    write32(central, 24, content.length);
    write16(central, 28, name.length);
    write16(central, 30, 0);
    write16(central, 32, 0);
    write16(central, 34, 0);
    write16(central, 36, 0);
    write32(central, 38, 0);
    write32(central, 42, localOffset);
    centralParts.push(central, name);
    localOffset += local.length + name.length + content.length;
    centralSize += central.length + name.length;
  }

  const end = new Uint8Array(22);
  write32(end, 0, 0x06054b50);
  write16(end, 4, 0);
  write16(end, 6, 0);
  write16(end, 8, descriptors.length);
  write16(end, 10, descriptors.length);
  write32(end, 12, centralSize);
  write32(end, 16, localOffset);
  write16(end, 20, 0);
  return new Blob([...localParts, ...centralParts, end], { type: "application/zip" });
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

function renderRun(data) {
  responseData = data;
  renderOverview(data);
  renderPipeline(data);
  $("summary-output").textContent = data.summary?.markdown || "No summary was generated.";
  renderResearch(data);
  renderArtifacts(data);
  viewSelect.value = "package";
  renderJson();
  $("search-feature-type").value = "";
  $("search-designator").value = "";
  runSearch();
  resultPanel.hidden = false;
}

fileInput.addEventListener("change", () => updateSelectedFile(fileInput.files[0]));

for (const eventName of ["dragenter", "dragover"]) {
  dropZone.addEventListener(eventName, (event) => {
    event.preventDefault();
    if (!requestActive) dropZone.classList.add("dragging");
  });
}
dropZone.addEventListener("dragleave", () => dropZone.classList.remove("dragging"));
dropZone.addEventListener("drop", (event) => {
  event.preventDefault();
  dropZone.classList.remove("dragging");
  if (requestActive) return;
  const files = event.dataTransfer?.files || [];
  if (files.length !== 1) {
    updateSelectedFile(null, true);
    showError("Drop exactly one PDF file.");
    return;
  }
  updateSelectedFile(files[0], true);
});

viewSelect.addEventListener("change", renderJson);

form.addEventListener("submit", async (event) => {
  event.preventDefault();
  clearError();
  const clientError = selectedFileError(selectedFile);
  if (clientError) return showError(clientError);
  if (!permission.checked) return showError("Confirm permission before processing the file.");

  const body = new FormData();
  body.append("file", multipartFile(selectedFile), selectedFile.name);
  body.append("permission_confirmed", "true");
  body.append("profile", "auto");
  setBusy(true);
  statusNode.textContent = "Running intake, all-page extraction, validation, search, summary, report, and artifact generation locally…";
  resultPanel.hidden = true;

  try {
    const response = await fetch("/api/v1/pipeline-runs", { method: "POST", body });
    if (!response.ok) throw new Error(await problemMessage(response));
    renderRun(await response.json());
    statusNode.textContent = "Full pipeline completed. Review validation, blockers, candidate states, and source rights before using the research output.";
    resultPanel.scrollIntoView({ behavior: "smooth", block: "start" });
  } catch (error) {
    statusNode.textContent = "The full pipeline did not complete. Your selected file is still available for retry.";
    showError(error.message || String(error));
  } finally {
    setBusy(false);
  }
});

resetButton.addEventListener("click", () => {
  form.reset();
  syncNativeFile(null);
  responseData = null;
  selectedFile = null;
  $("file-label").textContent = "No file selected";
  dropZone.classList.remove("has-file", "dragging");
  statusNode.textContent = "";
  resultPanel.hidden = true;
  clearError();
});

$("search-form").addEventListener("submit", (event) => {
  event.preventDefault();
  runSearch();
});
$("clear-search-button").addEventListener("click", () => {
  $("search-feature-type").value = "";
  $("search-designator").value = "";
  runSearch();
});

$("copy-button").addEventListener("click", async () => {
  try {
    await navigator.clipboard.writeText(output.textContent);
    statusNode.textContent = "Current JSON view copied to the clipboard.";
  } catch (_) {
    showError("Clipboard access was not available; use the download button instead.");
  }
});

$("download-button").addEventListener("click", () => {
  const value = activeView();
  if (value == null || !responseData) return;
  const text = `${JSON.stringify(value, null, 2)}\n`;
  const filename = `${responseData.run.run_id}-${viewSelect.value}.json`;
  downloadBlob(new Blob([text], { type: "application/json" }), filename);
});

$("download-report-button").addEventListener("click", () => {
  const descriptor = responseData?.artifacts?.find((artifact) => artifact.key === "report");
  if (descriptor) downloadArtifact(descriptor);
});

$("download-all-button").addEventListener("click", () => {
  if (!responseData) return;
  statusNode.textContent = "Building the complete ZIP in browser memory…";
  const zip = buildZip(responseData.artifacts || []);
  downloadBlob(zip, `${responseData.run.run_id}-airport-ocr-results.zip`);
  statusNode.textContent = "Complete result ZIP prepared. No artifacts were persisted by the service.";
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
