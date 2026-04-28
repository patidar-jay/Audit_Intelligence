// ── Utility helpers ───────────────────────────────────────────────────────────

// Session storage helpers
const Session = {
  set: (k, v) => sessionStorage.setItem(k, JSON.stringify(v)),
  get: (k)    => { try { return JSON.parse(sessionStorage.getItem(k)); } catch { return null; } },
  del: (k)    => sessionStorage.removeItem(k),
  clear:()    => sessionStorage.clear()
};

// Auth guard - redirect to login if not logged in
function requireAuth() {
  const user = Session.get("user");
  if (!user) { window.location.href = "/"; return null; }
  return user;
}

// Fill sidebar user info
function fillSidebarUser() {
  const user = Session.get("user");
  if (!user) return;
  const nameEl = document.getElementById("sidebar-name");
  const roleEl = document.getElementById("sidebar-role");
  if (nameEl) nameEl.textContent = user.full_name || user.username;
  if (roleEl) roleEl.textContent = "Role: " + (user.role || "auditor").charAt(0).toUpperCase() + (user.role || "auditor").slice(1);
}

// Logout
function logout() {
  Session.clear();
  window.location.href = "/";
}

// Toast notification
function toast(msg, type = "info") {
  const el = document.getElementById("toast");
  if (!el) return;
  el.textContent = msg;
  el.className = "show " + type;
  setTimeout(() => { el.className = ""; }, 3000);
}

// Show/hide loading overlay
function setLoading(show, msg = "Processing...") {
  const el = document.getElementById("loading-overlay");
  if (!el) return;
  el.classList.toggle("show", show);
  const p = el.querySelector("p");
  if (p) p.textContent = msg;
}

// Format Indian Rupee
function fmtINR(n) {
  n = parseFloat(n) || 0;
  if (n >= 1e7)  return "Rs " + (n/1e7).toFixed(2) + " Cr";
  if (n >= 1e5)  return "Rs " + (n/1e5).toFixed(2) + " L";
  if (n >= 1000) return "Rs " + (n/1000).toFixed(1) + "K";
  return "Rs " + n.toFixed(2);
}

// Format number with commas
function fmtNum(n) {
  return parseInt(n || 0).toLocaleString("en-IN");
}

// Tab switching
function initTabs() {
  document.querySelectorAll(".tab-btn").forEach(btn => {
    btn.addEventListener("click", () => {
      const group = btn.dataset.tabGroup || "default";
      const target = btn.dataset.tab;
      document.querySelectorAll(`[data-tab-group="${group}"].tab-btn`).forEach(b => b.classList.remove("active"));
      document.querySelectorAll(`[data-tab-group="${group}"].tab-content`).forEach(c => c.classList.remove("active"));
      btn.classList.add("active");
      const content = document.getElementById(target);
      if (content) content.classList.add("active");
    });
  });
}

// Table sort
function sortTable(table, col, asc) {
  const tbody = table.querySelector("tbody");
  const rows  = Array.from(tbody.querySelectorAll("tr"));
  rows.sort((a, b) => {
    const av = a.cells[col]?.textContent.trim() || "";
    const bv = b.cells[col]?.textContent.trim() || "";
    const an = parseFloat(av.replace(/[^0-9.-]/g,""));
    const bn = parseFloat(bv.replace(/[^0-9.-]/g,""));
    if (!isNaN(an) && !isNaN(bn)) return asc ? an-bn : bn-an;
    return asc ? av.localeCompare(bv) : bv.localeCompare(av);
  });
  rows.forEach(r => tbody.appendChild(r));
}

function initSortableTable(tableId) {
  const table = document.getElementById(tableId);
  if (!table) return;
  let sortCol = -1, sortAsc = true;
  table.querySelectorAll("th").forEach((th, i) => {
    th.addEventListener("click", () => {
      sortAsc = sortCol === i ? !sortAsc : true;
      sortCol = i;
      sortTable(table, i, sortAsc);
      table.querySelectorAll("th").forEach(h => h.textContent = h.textContent.replace(" ▲","").replace(" ▼",""));
      th.textContent += sortAsc ? " ▲" : " ▼";
    });
  });
}

// Export table to CSV
function exportTableCSV(tableId, filename) {
  const table = document.getElementById(tableId);
  if (!table) return;
  const rows = Array.from(table.querySelectorAll("tr"));
  const csv  = rows.map(r =>
    Array.from(r.querySelectorAll("th,td"))
      .map(c => '"' + c.textContent.trim().replace(/"/g,'""') + '"')
      .join(",")
  ).join("\n");
  const blob = new Blob([csv], {type: "text/csv"});
  const a = document.createElement("a");
  a.href = URL.createObjectURL(blob);
  a.download = filename;
  a.click();
}

// Risk badge HTML
function riskBadge(level) {
  const map = { High: "badge-danger", Medium: "badge-warning", Low: "badge-success" };
  return `<span class="badge ${map[level] || ''}">${level}</span>`;
}

// Score color
function scoreColor(score) {
  if (score >= 60) return "#ef4444";
  if (score >= 30) return "#f59e0b";
  return "#10b981";
}

// Flag badge
function flagBadge(reason) {
  const map = {
    "Duplicate Invoice":  "badge-warning",
    "Cash Limit Breach":  "badge-danger",
    "Structured Payment": "badge-purple",
    "AI Anomaly":         "badge-cyan",
  };
  return `<span class="badge ${map[reason] || 'badge-cyan'}">${reason}</span>`;
}

// Draw simple bar chart using Canvas
function drawBarChart(canvasId, labels, values, color = "#00d4ff") {
  const canvas = document.getElementById(canvasId);
  if (!canvas) return;
  const ctx    = canvas.getContext("2d");
  const W = canvas.width, H = canvas.height;
  const pad = { top: 20, right: 10, bottom: 50, left: 60 };
  const cW = W - pad.left - pad.right;
  const cH = H - pad.top  - pad.bottom;
  ctx.clearRect(0, 0, W, H);

  if (!values.length) return;
  const max   = Math.max(...values) * 1.1 || 1;
  const barW  = cW / values.length * 0.7;
  const gap   = cW / values.length;

  // Grid lines
  ctx.strokeStyle = "#1e2d45"; ctx.lineWidth = 1;
  for (let i = 0; i <= 4; i++) {
    const y = pad.top + cH - (i / 4) * cH;
    ctx.beginPath(); ctx.moveTo(pad.left, y); ctx.lineTo(pad.left + cW, y); ctx.stroke();
    ctx.fillStyle = "#64748b"; ctx.font = "10px Arial"; ctx.textAlign = "right";
    ctx.fillText(fmtNum((max * i / 4).toFixed(0)), pad.left - 6, y + 4);
  }

  // Bars
  values.forEach((v, i) => {
    const x   = pad.left + i * gap + (gap - barW) / 2;
    const bH  = (v / max) * cH;
    const y   = pad.top + cH - bH;
    ctx.fillStyle = color;
    ctx.beginPath();
    ctx.roundRect ? ctx.roundRect(x, y, barW, bH, 3) : ctx.rect(x, y, barW, bH);
    ctx.fill();
    // Label
    ctx.fillStyle = "#64748b"; ctx.font = "9px Arial"; ctx.textAlign = "center";
    const lbl = String(labels[i]).length > 8 ? String(labels[i]).slice(0,8)+"…" : String(labels[i]);
    ctx.fillText(lbl, x + barW/2, pad.top + cH + 14);
  });
}

// Draw simple line chart
function drawLineChart(canvasId, labels, values, color = "#00d4ff") {
  const canvas = document.getElementById(canvasId);
  if (!canvas) return;
  const ctx    = canvas.getContext("2d");
  const W = canvas.width, H = canvas.height;
  const pad = { top: 20, right: 10, bottom: 50, left: 70 };
  const cW = W - pad.left - pad.right;
  const cH = H - pad.top  - pad.bottom;
  ctx.clearRect(0, 0, W, H);

  if (!values.length) return;
  const max = Math.max(...values) * 1.1 || 1;
  const min = 0;

  // Grid
  ctx.strokeStyle = "#1e2d45"; ctx.lineWidth = 1;
  for (let i = 0; i <= 4; i++) {
    const y = pad.top + cH - (i / 4) * cH;
    ctx.beginPath(); ctx.moveTo(pad.left, y); ctx.lineTo(pad.left + cW, y); ctx.stroke();
    ctx.fillStyle = "#64748b"; ctx.font = "10px Arial"; ctx.textAlign = "right";
    ctx.fillText(fmtINR(max * i / 4), pad.left - 6, y + 4);
  }

  // Line
  const pts = values.map((v, i) => ({
    x: pad.left + (i / (values.length - 1 || 1)) * cW,
    y: pad.top  + cH - ((v - min) / (max - min)) * cH
  }));

  // Fill
  ctx.beginPath();
  ctx.moveTo(pts[0].x, pad.top + cH);
  pts.forEach(p => ctx.lineTo(p.x, p.y));
  ctx.lineTo(pts[pts.length-1].x, pad.top + cH);
  ctx.closePath();
  ctx.fillStyle = color + "22"; ctx.fill();

  // Stroke
  ctx.beginPath();
  ctx.strokeStyle = color; ctx.lineWidth = 2.5;
  pts.forEach((p, i) => i === 0 ? ctx.moveTo(p.x, p.y) : ctx.lineTo(p.x, p.y));
  ctx.stroke();

  // Dots
  pts.forEach(p => {
    ctx.beginPath(); ctx.arc(p.x, p.y, 4, 0, Math.PI*2);
    ctx.fillStyle = color; ctx.fill();
  });

  // X labels
  ctx.fillStyle = "#64748b"; ctx.font = "9px Arial"; ctx.textAlign = "center";
  labels.forEach((l, i) => {
    const x = pad.left + (i / (labels.length - 1 || 1)) * cW;
    const lbl = String(l).length > 6 ? String(l).slice(-5) : String(l);
    ctx.fillText(lbl, x, pad.top + cH + 14);
  });
}

// API helper
async function api(endpoint, method = "GET", body = null, isForm = false) {
  const opts = { method, headers: {} };
  if (body && !isForm) {
    opts.headers["Content-Type"] = "application/json";
    opts.body = JSON.stringify(body);
  } else if (body && isForm) {
    opts.body = body;
  }
  const res  = await fetch(endpoint, opts);
  const data = await res.json();
  if (!res.ok) throw new Error(data.detail || "Request failed");
  return data;
}
