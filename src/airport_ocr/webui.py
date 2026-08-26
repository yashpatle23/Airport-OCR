"""Static browser UI for the Airport-OCR web application.

The page is fully self-contained: no external scripts, styles, fonts, tiles, or
network calls beyond this application's own JSON API. That keeps it runnable in
restricted/offline environments and avoids leaking data to third parties.
"""

from __future__ import annotations

INDEX_HTML = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8" />
<meta name="viewport" content="width=device-width, initial-scale=1" />
<title>Airport-OCR &mdash; VOBL (non-operational)</title>
<style>
  :root {
    --bg: #0f172a; --panel: #1e293b; --panel2: #273449; --ink: #e2e8f0;
    --muted: #94a3b8; --line: #334155; --accent: #38bdf8; --warn: #f59e0b;
    --bad: #f87171; --ok: #34d399;
  }
  * { box-sizing: border-box; }
  body { margin: 0; font: 14px/1.5 system-ui, sans-serif; background: var(--bg); color: var(--ink); }
  header { padding: 16px 20px; border-bottom: 1px solid var(--line); background: var(--panel); }
  header h1 { margin: 0; font-size: 18px; }
  header .sub { color: var(--muted); font-size: 12px; margin-top: 4px; }
  .banner { background: #78350f; color: #fde68a; padding: 8px 20px; font-size: 12px; border-bottom: 1px solid var(--line); }
  main { display: grid; grid-template-columns: 360px 1fr; gap: 0; min-height: calc(100vh - 92px); }
  .side { border-right: 1px solid var(--line); padding: 16px 20px; overflow: auto; }
  .content { padding: 16px 20px; overflow: auto; }
  h2 { font-size: 13px; text-transform: uppercase; letter-spacing: .06em; color: var(--muted); margin: 20px 0 8px; }
  .card { background: var(--panel); border: 1px solid var(--line); border-radius: 8px; padding: 12px 14px; margin-bottom: 10px; }
  .kv { display: flex; justify-content: space-between; gap: 12px; padding: 3px 0; }
  .kv .k { color: var(--muted); }
  .kv .v { font-variant-numeric: tabular-nums; text-align: right; }
  table { width: 100%; border-collapse: collapse; font-size: 13px; }
  th, td { text-align: left; padding: 6px 8px; border-bottom: 1px solid var(--line); font-variant-numeric: tabular-nums; }
  th { color: var(--muted); font-weight: 600; }
  .pill { display: inline-block; padding: 1px 8px; border-radius: 999px; font-size: 11px; border: 1px solid var(--line); }
  .pill.warn { background: #78350f; color: #fde68a; border-color: #b45309; }
  .pill.bad { background: #7f1d1d; color: #fecaca; border-color: #b91c1c; }
  .pill.ok { background: #064e3b; color: #a7f3d0; border-color: #059669; }
  .conflict { border-left: 3px solid var(--warn); }
  .blocked { border-left: 3px solid var(--bad); }
  svg { width: 100%; height: auto; background: var(--panel2); border: 1px solid var(--line); border-radius: 8px; }
  .dot-arp { fill: var(--accent); }
  .dot-thr { fill: var(--ok); }
  .runway-line { stroke: #64748b; stroke-width: 1.5; stroke-dasharray: 4 3; }
  .lbl { fill: var(--ink); font-size: 9px; }
  input, select, button { font: inherit; background: var(--panel2); color: var(--ink); border: 1px solid var(--line); border-radius: 6px; padding: 6px 8px; }
  button { cursor: pointer; }
  button:hover { border-color: var(--accent); }
  .row { display: flex; gap: 8px; flex-wrap: wrap; align-items: center; margin-bottom: 8px; }
  .muted { color: var(--muted); }
  pre { background: #0b1220; border: 1px solid var(--line); border-radius: 8px; padding: 12px; overflow: auto; font-size: 12px; }
  .checks { font-size: 12px; }
  .checks .c { display: flex; gap: 8px; padding: 2px 0; }
  .status-PASS { color: var(--ok); }
  .status-FAIL { color: var(--bad); }
  .status-EXPECTED_BLOCKER { color: var(--warn); }
  .status-INFO { color: var(--muted); }
  a { color: var(--accent); }
</style>
</head>
<body>
<header>
  <h1>Airport-OCR &mdash; VOBL <span id="chart" class="muted"></span></h1>
  <div class="sub">Kempegowda International Airport Bengaluru &middot; provisional, research-only view</div>
</header>
<div class="banner" id="banner">Non-operational. Not authoritative aeronautical data. Do not use for navigation.</div>
<main>
  <section class="side">
    <h2>Airport</h2>
    <div class="card" id="airport-card">Loading&hellip;</div>

    <h2>Elevation</h2>
    <div class="card conflict" id="elev-card">Loading&hellip;</div>

    <h2>Collections</h2>
    <div class="card blocked" id="coll-card">Loading&hellip;</div>

    <h2>Validation</h2>
    <div class="card" id="val-card">Loading&hellip;</div>
  </section>

  <section class="content">
    <h2>Feature map <span class="muted">(threshold connectors are not surveyed runway extents)</span></h2>
    <svg id="map" viewBox="0 0 800 460" role="img" aria-label="Feature map"></svg>

    <h2>Search features</h2>
    <div class="row">
      <select id="ftype">
        <option value="">any type</option>
        <option value="aerodrome_reference_point">aerodrome_reference_point</option>
        <option value="runway_threshold">runway_threshold</option>
        <option value="runway_threshold_connector">runway_threshold_connector</option>
      </select>
      <input id="designator" placeholder="designator e.g. 09L" size="12" />
      <input id="bbox" placeholder="bbox minLon,minLat,maxLon,maxLat" size="30" />
      <button id="search-btn">Search</button>
      <span class="muted" id="search-count"></span>
    </div>
    <div id="results"></div>

    <h2>Runways</h2>
    <div id="runways"></div>

    <h2>Validation report</h2>
    <div class="checks card" id="checks"></div>
  </section>
</main>
<script>
const $ = (id) => document.getElementById(id);

async function getJSON(url) {
  const res = await fetch(url);
  if (!res.ok) throw new Error(url + " -> " + res.status);
  return res.json();
}

function esc(s) {
  return String(s).replace(/[&<>"]/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]));
}

function kv(k, v) {
  return `<div class="kv"><span class="k">${esc(k)}</span><span class="v">${esc(v)}</span></div>`;
}

let FEATURES = null;

async function loadAirport() {
  const a = (await getJSON("/api/airport")).airport;
  $("chart").textContent = "";
  const arp = a.arp.coordinates;
  $("airport-card").innerHTML =
    kv("ICAO", a.icao) +
    kv("Name", a.name) +
    kv("ARP (lon, lat)", arp[0].toFixed(6) + ", " + arp[1].toFixed(6)) +
    kv("ARP source", a.arp.source.latitude + " " + a.arp.source.longitude) +
    kv("CRS", a.arp.crs + " (" + a.arp.axis_order + ")");

  const e = a.elevation;
  let claims = e.claims.map((c) =>
    `<div class="kv"><span class="k">${esc(c.source_text)}</span><span class="v">${esc(c.value)} ${esc(c.unit)}</span></div>`
  ).join("");
  $("elev-card").innerHTML =
    `<div class="row"><span class="pill warn">CONFLICT</span> <span class="muted">selected: none</span></div>` +
    claims +
    `<div class="muted" style="margin-top:6px">${esc(e.conflict_status)}</div>`;
}

function collBadge(node, label) {
  const blocked = node.completeness_status && node.completeness_status.indexOf("BLOCKED") === 0;
  const cls = blocked ? "bad" : "ok";
  const semantics = node.empty_array_semantics ? ` <span class="muted">(${esc(node.empty_array_semantics)})</span>` : "";
  return `<div class="kv"><span class="k">${esc(label)}</span>` +
    `<span class="v"><span class="pill ${cls}">${esc(node.completeness_status)}</span></span></div>` +
    (blocked ? `<div class="muted" style="margin-top:2px">${node.features.length} extracted${semantics}</div>` : "");
}

async function loadCollections() {
  const n = await getJSON("/api/airport");
  $("coll-card").innerHTML =
    collBadge(n.taxiways, "Taxiways") +
    collBadge(n.runway_holding_positions, "Runway holding positions");
}

async function loadRunways() {
  const n = await getJSON("/api/airport");
  let rows = "";
  for (const r of n.runways) {
    for (const d of r.directions) {
      const t = d.threshold;
      rows += `<tr><td>${esc(d.designator)}</td>` +
        `<td>${esc(r.designator_pair)}</td>` +
        `<td>${t.position.coordinates[1].toFixed(6)}, ${t.position.coordinates[0].toFixed(6)}</td>` +
        `<td>${esc(t.elevation.value)} ${esc(t.elevation.unit)}</td>` +
        `<td>${esc(t.tdz_elevation.value)} ${esc(t.tdz_elevation.unit)}</td>` +
        `<td>${esc(r.declared_length.value)}&times;${esc(r.declared_width.value)} ${esc(r.declared_width.unit)}</td></tr>`;
    }
  }
  $("runways").innerHTML =
    `<table><thead><tr><th>RWY</th><th>Pair</th><th>Threshold (lat, lon)</th>` +
    `<th>THR elev</th><th>TDZ elev</th><th>Declared</th></tr></thead><tbody>${rows}</tbody></table>`;
}

async function loadValidation() {
  const r = await getJSON("/api/validation");
  const c = r.counts || {};
  const statusCls = r.status === "FAIL" ? "bad" : "ok";
  $("val-card").innerHTML =
    `<div class="row"><span class="pill ${statusCls}">${esc(r.status)}</span></div>` +
    kv("PASS", c.PASS || 0) +
    kv("EXPECTED_BLOCKER", c.EXPECTED_BLOCKER || 0) +
    kv("INFO", c.INFO || 0) +
    kv("FAIL", c.FAIL || 0);
  $("checks").innerHTML = r.checks.map((c) =>
    `<div class="c"><span class="status-${esc(c.status)}">[${esc(c.status)}]</span>` +
    `<span><b>${esc(c.id)}</b> &mdash; ${esc(c.detail)}</span></div>`
  ).join("");
}

function drawMap(fc) {
  const pts = [];
  for (const f of fc.features) {
    const g = f.geometry;
    if (g.type === "Point") pts.push(g.coordinates);
    if (g.type === "LineString") for (const p of g.coordinates) pts.push(p);
  }
  if (!pts.length) return;
  const lons = pts.map((p) => p[0]), lats = pts.map((p) => p[1]);
  let minLon = Math.min(...lons), maxLon = Math.max(...lons);
  let minLat = Math.min(...lats), maxLat = Math.max(...lats);
  const padX = (maxLon - minLon) * 0.15 || 0.01;
  const padY = (maxLat - minLat) * 0.25 || 0.01;
  minLon -= padX; maxLon += padX; minLat -= padY; maxLat += padY;
  const W = 800, H = 460, M = 30;
  const sx = (lon) => M + (lon - minLon) / (maxLon - minLon) * (W - 2 * M);
  const sy = (lat) => H - M - (lat - minLat) / (maxLat - minLat) * (H - 2 * M);

  let svg = "";
  for (const f of fc.features) {
    if (f.geometry.type === "LineString") {
      const cs = f.geometry.coordinates.map((p) => sx(p[0]) + "," + sy(p[1])).join(" ");
      svg += `<polyline class="runway-line" fill="none" points="${cs}" />`;
    }
  }
  for (const f of fc.features) {
    const g = f.geometry;
    if (g.type !== "Point") continue;
    const x = sx(g.coordinates[0]), y = sy(g.coordinates[1]);
    const isArp = f.properties.feature_type === "aerodrome_reference_point";
    svg += `<circle class="${isArp ? "dot-arp" : "dot-thr"}" cx="${x}" cy="${y}" r="${isArp ? 6 : 4}" />`;
    const label = isArp ? "ARP" : (f.properties.designator || "");
    svg += `<text class="lbl" x="${x + 6}" y="${y - 6}">${esc(label)}</text>`;
  }
  $("map").innerHTML = svg;
}

function renderResults(fc) {
  $("search-count").textContent = fc.properties.match_count + " match(es)";
  if (!fc.features.length) { $("results").innerHTML = '<div class="muted">No matches.</div>'; return; }
  const rows = fc.features.map((f) => {
    const p = f.properties;
    const coords = f.geometry.type === "Point"
      ? f.geometry.coordinates[1].toFixed(5) + ", " + f.geometry.coordinates[0].toFixed(5)
      : f.geometry.type;
    return `<tr><td>${esc(p.feature_type)}</td><td>${esc(p.designator || p.designator_pair || "")}</td><td>${esc(coords)}</td></tr>`;
  }).join("");
  $("results").innerHTML =
    `<table><thead><tr><th>Type</th><th>Designator</th><th>Geometry</th></tr></thead><tbody>${rows}</tbody></table>`;
}

async function doSearch() {
  const params = new URLSearchParams();
  const ft = $("ftype").value.trim();
  const des = $("designator").value.trim();
  const bbox = $("bbox").value.trim();
  if (ft) params.set("feature_type", ft);
  if (des) params.set("designator", des);
  if (bbox) params.set("bbox", bbox);
  const fc = await getJSON("/api/search?" + params.toString());
  renderResults(fc);
}

async function main() {
  try {
    await loadAirport();
    await loadCollections();
    await loadRunways();
    await loadValidation();
    FEATURES = await getJSON("/api/features");
    drawMap(FEATURES);
    renderResults({ properties: { match_count: FEATURES.features.length }, features: FEATURES.features });
    $("search-btn").addEventListener("click", () => doSearch().catch((e) => alert(e.message)));
  } catch (e) {
    document.body.insertAdjacentHTML("beforeend", '<pre style="margin:20px">' + esc(e.message) + "</pre>");
  }
}
main();
</script>
</body>
</html>
"""
