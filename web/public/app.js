(() => {
  "use strict";

  const REAL_DATA_COLOR = "#00d4ff";
  const REAL_DATA_WIDTH = 3.5;
  const PLOT_TEMPLATE = "plotly_dark";

  const state = {
    data: null,
    view: "single",
    variable: null,
    scenarios: new Set(),
    yearMin: 1960,
    yearMax: 2100,
    showReal: true,
  };

  const els = {
    chart: document.getElementById("chart"),
    variableSelect: document.getElementById("variable-select"),
    scenarioToggles: document.getElementById("scenario-toggles"),
    yearMin: document.getElementById("year-min"),
    yearMax: document.getElementById("year-max"),
    showReal: document.getElementById("show-real"),
    rmseSection: document.getElementById("rmse-section"),
    rmseContent: document.getElementById("rmse-content"),
    headline: document.getElementById("headline"),
    freshness: document.getElementById("freshness-line"),
    scenarioDescriptions: document.getElementById("scenario-descriptions"),
    viewRadios: document.querySelectorAll("input[name='view']"),
  };

  init().catch((err) => {
    console.error(err);
    els.chart.innerHTML =
      '<p style="padding:24px;color:#e74c3c">Failed to load dashboard data: ' +
      escapeHtml(String(err && err.message ? err.message : err)) +
      "</p>";
  });

  async function init() {
    const res = await fetch("./data.json", { cache: "no-cache" });
    if (!res.ok) throw new Error("HTTP " + res.status + " loading data.json");
    state.data = await res.json();

    populateVariables();
    populateScenarios();
    populateScenarioDescriptions();
    bindControls();
    renderFreshness();
    renderHeadline();
    render();
  }

  function populateVariables() {
    const opts = state.data.variables
      .map(
        (v) =>
          `<option value="${v.key}">${escapeHtml(v.label)}</option>`
      )
      .join("");
    els.variableSelect.innerHTML = opts;
    state.variable = state.data.variables[0].key;
    els.variableSelect.value = state.variable;
  }

  function populateScenarios() {
    const names = Object.keys(state.data.scenarios);
    state.scenarios = new Set(names);
    els.scenarioToggles.innerHTML = names
      .map((name) => {
        const color = state.data.scenarios[name].color;
        return `<label class="checkbox">
          <input type="checkbox" data-scenario="${name}" checked />
          <span style="display:inline-block;width:10px;height:10px;border-radius:50%;background:${color};"></span>
          ${name}
        </label>`;
      })
      .join("");
  }

  function populateScenarioDescriptions() {
    els.scenarioDescriptions.innerHTML = Object.entries(state.data.scenarios)
      .map(
        ([name, s]) =>
          `<p><strong>${name}.</strong> ${escapeHtml(s.description)}</p>`
      )
      .join("");
  }

  function bindControls() {
    els.variableSelect.addEventListener("change", () => {
      state.variable = els.variableSelect.value;
      render();
    });
    els.scenarioToggles.addEventListener("change", (e) => {
      const t = e.target;
      if (!(t instanceof HTMLInputElement)) return;
      const name = t.dataset.scenario;
      if (t.checked) state.scenarios.add(name);
      else state.scenarios.delete(name);
      render();
    });
    els.yearMin.addEventListener("change", () => {
      state.yearMin = clampYear(els.yearMin.value, 1900, state.yearMax - 1);
      els.yearMin.value = state.yearMin;
      render();
    });
    els.yearMax.addEventListener("change", () => {
      state.yearMax = clampYear(els.yearMax.value, state.yearMin + 1, 2100);
      els.yearMax.value = state.yearMax;
      render();
    });
    els.showReal.addEventListener("change", () => {
      state.showReal = els.showReal.checked;
      render();
    });
    els.viewRadios.forEach((r) => {
      r.addEventListener("change", () => {
        if (r.checked) {
          state.view = r.value;
          render();
        }
      });
    });
    window.addEventListener("resize", () => Plotly.Plots.resize(els.chart));
  }

  function clampYear(raw, lo, hi) {
    let n = parseInt(raw, 10);
    if (!Number.isFinite(n)) n = lo;
    return Math.max(lo, Math.min(hi, n));
  }

  function renderFreshness() {
    const fresh = state.data.data_freshness_utc;
    const generated = state.data.generated_at_utc;
    const parts = [];
    if (fresh)
      parts.push(
        `Real-world data fetched ${fresh.slice(0, 10)} · Model rebuilt ${generated.slice(0, 10)}`
      );
    else parts.push(`Model rebuilt ${generated.slice(0, 10)}`);
    els.freshness.textContent = parts.join(" ");
  }

  function renderHeadline() {
    // Aggregate RMSE rank across all variables. Lowest sum-of-ranks wins.
    const rmse = state.data.rmse;
    const variables = Object.keys(rmse);
    if (variables.length === 0) return;

    const scenarioNames = Object.keys(state.data.scenarios);
    const rankSums = Object.fromEntries(scenarioNames.map((n) => [n, 0]));
    const counted = Object.fromEntries(scenarioNames.map((n) => [n, 0]));

    variables.forEach((v) => {
      const scores = rmse[v];
      const sorted = Object.entries(scores).sort((a, b) => a[1] - b[1]);
      sorted.forEach(([name], idx) => {
        rankSums[name] += idx;
        counted[name] += 1;
      });
    });

    const ranked = scenarioNames
      .filter((n) => counted[n] > 0)
      .map((n) => ({ name: n, score: rankSums[n] / counted[n] }))
      .sort((a, b) => a.score - b.score);

    if (!ranked.length) return;
    const best = ranked[0].name;
    const desc = state.data.scenarios[best].description.split(" — ")[0];

    els.headline.innerHTML =
      `Across the five tracked variables, real-world data is currently closest to <strong>${best}</strong> (${escapeHtml(desc)}).`;
    els.headline.hidden = false;
  }

  function render() {
    if (!state.data) return;
    if (state.view === "single") renderSingle();
    else renderGrid();
    renderRmse();
  }

  function findVariable(key) {
    return state.data.variables.find((v) => v.key === key);
  }

  function realCappedYRange(realVals) {
    if (!realVals || !realVals.length) return null;
    const max = Math.max(...realVals);
    if (!(max > 0)) return null;
    const cap = Math.max(max * 3, 3);
    return [0, cap];
  }

  function renderSingle() {
    const v = findVariable(state.variable);
    const traces = [];
    const time = state.data.time;

    Object.entries(state.data.scenarios).forEach(([name, s]) => {
      if (!state.scenarios.has(name)) return;
      const series = s.series[v.world3_attr];
      if (!series) return;
      traces.push({
        type: "scatter",
        mode: "lines",
        name: name,
        x: time,
        y: series,
        line: { color: s.color, width: 2 },
        opacity: 0.85,
        hovertemplate: `${name}<br>Year: %{x:.0f}<br>Value: %{y:.3f}<extra></extra>`,
      });
    });

    let yRange = null;
    if (state.showReal && state.data.real_data[v.key]) {
      const rd = state.data.real_data[v.key];
      if (rd.years.length) {
        traces.push({
          type: "scatter",
          mode: "lines",
          name: "Real-world data",
          x: rd.years,
          y: rd.values,
          line: { color: REAL_DATA_COLOR, width: REAL_DATA_WIDTH },
          hovertemplate: "Real<br>Year: %{x:.0f}<br>Value: %{y:.3f}<extra></extra>",
        });
        const lastYear = rd.years[rd.years.length - 1];
        const lastVal = rd.values[rd.values.length - 1];
        traces.push({
          type: "scatter",
          mode: "markers+text",
          name: "You are here",
          x: [lastYear],
          y: [lastVal],
          marker: {
            color: REAL_DATA_COLOR,
            size: 14,
            line: { color: "white", width: 2 },
          },
          text: [`  YOU ARE HERE (${lastYear})`],
          textposition: "middle right",
          textfont: { size: 12, color: "#e6edf3" },
          showlegend: false,
          hovertemplate: `Latest: ${lastYear}<br>Value: %{y:.3f}<extra></extra>`,
        });
        yRange = realCappedYRange(rd.values);
      }
    }

    const layout = {
      template: PLOT_TEMPLATE,
      paper_bgcolor: "rgba(0,0,0,0)",
      plot_bgcolor: "rgba(0,0,0,0)",
      font: { color: "#e6edf3" },
      title: {
        text: `${v.label}<br><span style="font-size:12px;color:#8b98a9">World3 scenarios vs real-world data (normalized to ${v.normalize_year} = 1.0)</span>`,
        font: { size: 18 },
      },
      xaxis: {
        title: "Year",
        range: [state.yearMin, state.yearMax],
        gridcolor: "rgba(128,128,128,0.18)",
        zerolinecolor: "rgba(128,128,128,0.4)",
      },
      yaxis: {
        title: `Normalized (${v.normalize_year} = 1.0)`,
        gridcolor: "rgba(128,128,128,0.18)",
        zerolinecolor: "rgba(128,128,128,0.4)",
        range: yRange || undefined,
      },
      legend: {
        orientation: "h",
        yanchor: "bottom",
        y: 1.04,
        xanchor: "left",
        x: 0,
      },
      margin: { t: 90, r: 30, b: 60, l: 60 },
      height: 560,
    };

    Plotly.react(els.chart, traces, layout, {
      responsive: true,
      displaylogo: false,
      modeBarButtonsToRemove: ["select2d", "lasso2d"],
    });
  }

  function renderGrid() {
    const variables = state.data.variables;
    const cols = 3;
    const rows = Math.ceil(variables.length / cols);
    const traces = [];
    const layout = {
      template: PLOT_TEMPLATE,
      paper_bgcolor: "rgba(0,0,0,0)",
      plot_bgcolor: "rgba(0,0,0,0)",
      font: { color: "#e6edf3" },
      grid: { rows, columns: cols, pattern: "independent" },
      height: rows * 320 + 80,
      margin: { t: 70, r: 20, b: 40, l: 50 },
      showlegend: true,
      legend: {
        orientation: "h",
        yanchor: "bottom",
        y: 1.04,
        xanchor: "left",
        x: 0,
      },
      annotations: [],
    };

    variables.forEach((v, idx) => {
      const r = Math.floor(idx / cols) + 1;
      const c = (idx % cols) + 1;
      const axisSuffix = idx === 0 ? "" : String(idx + 1);
      const xKey = "xaxis" + axisSuffix;
      const yKey = "yaxis" + axisSuffix;
      layout[xKey] = {
        range: [state.yearMin, state.yearMax],
        gridcolor: "rgba(128,128,128,0.18)",
        anchor: "y" + axisSuffix,
        domain: [
          (c - 1) / cols + 0.02,
          c / cols - 0.02,
        ],
      };
      layout[yKey] = {
        gridcolor: "rgba(128,128,128,0.18)",
        anchor: "x" + axisSuffix,
        domain: [
          1 - r / rows + 0.08,
          1 - (r - 1) / rows - 0.04,
        ],
      };

      // Subplot title
      layout.annotations.push({
        text: v.label,
        showarrow: false,
        x: (layout[xKey].domain[0] + layout[xKey].domain[1]) / 2,
        y: layout[yKey].domain[1] + 0.02,
        xref: "paper",
        yref: "paper",
        xanchor: "center",
        yanchor: "bottom",
        font: { size: 13, color: "#e6edf3" },
      });

      let realMax = null;

      Object.entries(state.data.scenarios).forEach(([name, s]) => {
        if (!state.scenarios.has(name)) return;
        const series = s.series[v.world3_attr];
        if (!series) return;
        traces.push({
          type: "scatter",
          mode: "lines",
          name: name,
          x: state.data.time,
          y: series,
          line: { color: s.color, width: 1.5 },
          opacity: 0.7,
          xaxis: "x" + axisSuffix,
          yaxis: "y" + axisSuffix,
          showlegend: idx === 0,
          legendgroup: name,
          hovertemplate: `${name}<br>%{x:.0f}: %{y:.3f}<extra></extra>`,
        });
      });

      if (state.showReal && state.data.real_data[v.key]) {
        const rd = state.data.real_data[v.key];
        if (rd.years.length) {
          realMax = Math.max(...rd.values);
          traces.push({
            type: "scatter",
            mode: "lines",
            name: "Real-world data",
            x: rd.years,
            y: rd.values,
            line: { color: REAL_DATA_COLOR, width: 2.5 },
            xaxis: "x" + axisSuffix,
            yaxis: "y" + axisSuffix,
            showlegend: idx === 0,
            legendgroup: "real",
            hovertemplate: "Real<br>%{x:.0f}: %{y:.3f}<extra></extra>",
          });
          const lastYear = rd.years[rd.years.length - 1];
          const lastVal = rd.values[rd.values.length - 1];
          traces.push({
            type: "scatter",
            mode: "markers",
            x: [lastYear],
            y: [lastVal],
            marker: {
              color: REAL_DATA_COLOR,
              size: 9,
              line: { color: "white", width: 1.5 },
            },
            xaxis: "x" + axisSuffix,
            yaxis: "y" + axisSuffix,
            showlegend: false,
            hovertemplate: `Latest (${lastYear}): %{y:.3f}<extra></extra>`,
          });
        }
      }

      if (realMax !== null && realMax > 0) {
        const cap = Math.max(realMax * 3, 3);
        layout[yKey].range = [0, cap];
      }
    });

    Plotly.react(els.chart, traces, layout, {
      responsive: true,
      displaylogo: false,
      modeBarButtonsToRemove: ["select2d", "lasso2d"],
    });
  }

  function renderRmse() {
    if (state.view === "single") {
      const v = findVariable(state.variable);
      const scores = state.data.rmse[v.key];
      if (!scores) {
        els.rmseSection.hidden = true;
        return;
      }
      const sorted = Object.entries(scores).sort((a, b) => a[1] - b[1]);
      const best = sorted[0][0];
      els.rmseContent.innerHTML = `<div class="rmse-cards">${sorted
        .map(([name, val]) => {
          const isBest = name === best;
          return `<div class="rmse-card${isBest ? " best" : ""}">
            <div class="label">${name}${isBest ? ' <span class="star">★</span>' : ""}</div>
            <div class="value">RMSE ${val.toFixed(4)}</div>
          </div>`;
        })
        .join("")}</div>`;
      els.rmseSection.hidden = false;
      return;
    }

    // Grid view: full table
    const variables = state.data.variables.filter((v) => state.data.rmse[v.key]);
    if (!variables.length) {
      els.rmseSection.hidden = true;
      return;
    }
    const scenarioNames = Object.keys(state.data.scenarios);
    const rows = variables.map((v) => {
      const scores = state.data.rmse[v.key];
      const present = scenarioNames.filter((n) => n in scores);
      const best = present
        .slice()
        .sort((a, b) => scores[a] - scores[b])[0];
      return { v, scores, best, present };
    });

    const head =
      "<tr><th>Variable</th>" +
      scenarioNames.map((n) => `<th>${n}</th>`).join("") +
      "</tr>";
    const body = rows
      .map((row) => {
        const cells = scenarioNames
          .map((n) => {
            if (!(n in row.scores)) return "<td>—</td>";
            const cls = n === row.best ? "best" : "";
            const star = n === row.best ? " ★" : "";
            return `<td class="${cls}">${row.scores[n].toFixed(4)}${star}</td>`;
          })
          .join("");
        return `<tr><td>${escapeHtml(row.v.label)}</td>${cells}</tr>`;
      })
      .join("");
    els.rmseContent.innerHTML = `<table class="rmse"><thead>${head}</thead><tbody>${body}</tbody></table>`;
    els.rmseSection.hidden = false;
  }

  function escapeHtml(str) {
    return String(str).replace(/[&<>"']/g, (c) => ({
      "&": "&amp;",
      "<": "&lt;",
      ">": "&gt;",
      '"': "&quot;",
      "'": "&#39;",
    }[c]));
  }
})();
