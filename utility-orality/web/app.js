// orality analyzer — frontend logic

const FLAG = {
  long: { bg: "rgba(251,191,36,0.25)", border: "#f59e0b", label: "Long" },
  dense: { bg: "rgba(239,68,68,0.2)", border: "#ef4444", label: "Dense" },
  hard: { bg: "rgba(168,85,247,0.2)", border: "#a855f7", label: "Hard words" },
  subord: {
    bg: "rgba(59,130,246,0.2)",
    border: "#3b82f6",
    label: "Subordination",
  },
};

let data = null;
let activeFilters = new Set();

const SAMPLE =
  "He was an old man who fished alone in a skiff in the Gulf Stream and he " +
  "had gone eighty-four days now without taking a fish. In the first forty " +
  "days a boy had been with him. But after forty days without a fish the " +
  "boy's parents had told him that the old man was now definitely and finally " +
  "salao, which is the worst form of unlucky, and the boy had gone at their " +
  "orders in another boat which caught three good fish the first week. It " +
  "made the boy sad to see the old man come in each day with his skiff empty " +
  "and he always went down to help him carry either the coiled lines or the " +
  "gaff and harpoon and the sail that was furled around the mast. The sail " +
  "was patched with flour sacks and, furled, it looked like the flag of " +
  "permanent defeat.";

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

function esc(s) {
  const d = document.createElement("div");
  d.textContent = s;
  return d.innerHTML;
}

function scoreColor(s) {
  return s >= 65 ? "#22c55e" : s >= 45 ? "#eab308" : "#ef4444";
}

function barGrad(pct) {
  const end = pct > 60 ? "#22c55e" : pct > 35 ? "#eab308" : "#ef4444";
  return `linear-gradient(90deg, #475569 0%, ${end} 100%)`;
}

// ---------------------------------------------------------------------------
// API
// ---------------------------------------------------------------------------

async function run() {
  const text = document.getElementById("input").value.trim();
  if (!text) return;
  const spinner = document.getElementById("spinner");
  spinner.classList.add("show");
  try {
    const res = await fetch("/analyse", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ text }),
    });
    data = await res.json();
    if (data.error) {
      alert(data.error);
      return;
    }
    activeFilters.clear();
    render();
  } catch (e) {
    alert("Request failed: " + e.message);
  } finally {
    spinner.classList.remove("show");
  }
}

function trySample() {
  document.getElementById("input").value = SAMPLE;
  run();
}

// ---------------------------------------------------------------------------
// Rendering
// ---------------------------------------------------------------------------

function render() {
  if (!data) return;

  // Banner
  const col = scoreColor(data.score);
  document.getElementById("banner").classList.add("show");
  const arc = document.getElementById("ring-arc");
  arc.setAttribute("stroke", col);
  arc.setAttribute("stroke-dasharray", `${(data.score / 100) * 264} 264`);
  const rv = document.getElementById("ring-val");
  rv.textContent = Math.round(data.score);
  rv.style.color = col;
  document.getElementById("banner-label").textContent = data.label;
  const flagged = data.details.filter((s) => s.flags.length > 0).length;
  document.getElementById("banner-sub").textContent =
    `${data.metrics.sentences} sentences · ${data.metrics.words} words · ${flagged} flagged`;

  document.getElementById("tabs").classList.add("show");

  renderLegend();
  renderProse();
  renderBars();
  renderTable();
}

// --- Legend filters ---

function renderLegend() {
  const el = document.getElementById("legend");

  // Count how many sentences have each flag type
  const counts = {};
  for (const type of Object.keys(FLAG)) counts[type] = 0;
  counts["clean"] = 0;
  data.details.forEach((s) => {
    if (s.flags.length === 0) {
      counts["clean"]++;
    } else {
      s.flags.forEach((f) => counts[f.type]++);
    }
  });

  let html = "";
  for (const [type, meta] of Object.entries(FLAG)) {
    const n = counts[type];
    const on = activeFilters.size === 0 || activeFilters.has(type);
    const dim = n === 0;
    const style =
      on && !dim
        ? `background:${meta.bg};border-color:${meta.border}`
        : dim
          ? "opacity:0.4"
          : "";
    html +=
      `<button class="legend-btn ${on && !dim ? "on" : ""}" data-flag="${type}" style="${style}" ${dim ? "disabled" : ""}>` +
      `<span class="dot" style="background:${meta.border}"></span>${meta.label}` +
      `<span style="font-size:11px;opacity:0.7;margin-left:2px">${n}</span></button>`;
  }
  const cleanN = counts["clean"];
  const cleanOn = activeFilters.size === 0 || activeFilters.has("clean");
  const cleanDim = cleanN === 0;
  const cleanStyle =
    cleanOn && !cleanDim
      ? "background:rgba(255,255,255,.05);border-color:#64748b"
      : cleanDim
        ? "opacity:0.4"
        : "";
  html +=
    `<button class="legend-btn ${cleanOn && !cleanDim ? "on" : ""}" data-flag="clean" style="${cleanStyle}" ${cleanDim ? "disabled" : ""}>` +
    `<span class="dot" style="background:#475569"></span>Clean` +
    `<span style="font-size:11px;opacity:0.7;margin-left:2px">${cleanN}</span></button>`;

  el.innerHTML = html;

  el.querySelectorAll(".legend-btn").forEach((btn) => {
    btn.addEventListener("click", () => {
      const f = btn.dataset.flag;
      if (activeFilters.has(f)) {
        activeFilters.delete(f);
      } else {
        activeFilters.add(f);
      }
      renderLegend();
      renderProse();
    });
  });
}

function sentMatchesFilter(info) {
  if (activeFilters.size === 0) return true;
  const types = info.flags.map((f) => f.type);
  if (types.length === 0) return activeFilters.has("clean");
  return types.some((t) => activeFilters.has(t));
}

// --- Highlighted prose ---

function renderProse() {
  const el = document.getElementById("prose");
  const orig = data.originalText;
  let html = "";
  let cursor = 0;

  data.details.forEach((s) => {
    // Render any gap (newlines, bullets, whitespace) before this sentence
    if (s.startChar > cursor) {
      html += esc(orig.slice(cursor, s.startChar));
    }
    cursor = s.endChar;

    const hasFl = s.flags.length > 0;
    const dimmed = activeFilters.size > 0 && !sentMatchesFilter(s);
    const meta = hasFl ? FLAG[s.flags[0].type] : null;

    let cls = "sent";
    if (hasFl) cls += " flagged";
    if (dimmed) cls += " dimmed";

    let style = "";
    if (hasFl && !dimmed) {
      style =
        `background:${meta.bg};border-bottom:2px solid ${meta.border};` +
        `--flag-border:${meta.border};`;
    }

    let tip = "";
    if (hasFl) {
      tip = '<span class="tip">';
      s.flags.forEach((f) => {
        const fm = FLAG[f.type];
        tip +=
          `<span class="tip-row">` +
          `<span class="tip-dot" style="background:${fm.border}"></span>` +
          `${esc(f.label)}</span>`;
      });
      tip += "</span>";
    }

    html += `<span class="${cls}" style="${style}">${tip}${esc(s.text)}</span>`;
  });

  // Render any trailing text after the last sentence
  if (cursor < orig.length) {
    html += esc(orig.slice(cursor));
  }

  el.innerHTML = html;
}

// --- Component bars ---

function renderBars() {
  const c = data.components;
  const items = [
    ["Readability (Flesch)", c.flesch, "Dense", "Easy"],
    ["Sentence length", c.sent_length, "Long", "Short"],
    ["Length variety", c.sent_variety, "Uniform", "Varied"],
    ["Lexical density", c.lexical_density, "High", "Low"],
    ["Coordination ratio", c.coordination, "Subordinated", "Coordinated"],
    ["Long sentence ratio", c.long_sents, "Many", "Few"],
    ["Contractions", c.contractions, "None", "Frequent"],
  ];
  let html = "";
  items.forEach(([label, val, lo, hi]) => {
    const pct = Math.max(0, Math.min(100, val * 100));
    html +=
      `<div class="bar-group">` +
      `<div class="bar-label"><span>${label}</span><span class="pct">${pct.toFixed(0)}%</span></div>` +
      `<div class="bar-wrap">` +
      `<span class="bar-lo">${lo}</span>` +
      `<div class="bar-track"><div class="bar-fill" style="width:${pct}%;background:${barGrad(pct)}"></div></div>` +
      `<span class="bar-hi">${hi}</span>` +
      `</div></div>`;
  });
  document.getElementById("bars").innerHTML = html;
}

// --- Sentence table ---

function renderTable() {
  let html =
    "<thead><tr>" +
    "<th>#</th><th>Sentence</th><th class='num'>Words</th><th class='num'>Syl/w</th>" +
    "<th class='num'>Density</th><th class='num'>Flesch</th><th>Flags</th>" +
    "</tr></thead><tbody>";

  data.details.forEach((d, i) => {
    const meta = d.flags.length ? FLAG[d.flags[0].type] : null;
    const rowCls = d.flags.length ? "flagged-row" : "";
    const rowStyle = meta ? `--row-bg:${meta.bg}` : "";
    html +=
      `<tr class="${rowCls}" style="${rowStyle}">` +
      `<td class="num" style="color:#64748b">${i + 1}</td>` +
      `<td class="sent-text">${esc(d.text)}</td>` +
      `<td class="num">${d.words}</td>` +
      `<td class="num">${d.sylPerWord.toFixed(2)}</td>` +
      `<td class="num">${(d.lexDensity * 100).toFixed(0)}%</td>` +
      `<td class="num">${d.flesch.toFixed(0)}</td>` +
      `<td class="flags-cell">${d.flags.map((f) => esc(f.label)).join(", ") || "—"}</td>` +
      `</tr>`;
  });
  html += "</tbody>";
  document.getElementById("tbl").innerHTML = html;
}

// ---------------------------------------------------------------------------
// Tab switching
// ---------------------------------------------------------------------------

document.getElementById("tabs").addEventListener("click", (e) => {
  const btn = e.target.closest(".tab-btn");
  if (!btn) return;
  document
    .querySelectorAll(".tab-btn")
    .forEach((b) => b.classList.remove("active"));
  btn.classList.add("active");
  document
    .querySelectorAll(".panel")
    .forEach((p) => p.classList.remove("active"));
  document.getElementById("panel-" + btn.dataset.tab).classList.add("active");
});
