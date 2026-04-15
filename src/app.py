"""
World3 Live Dashboard — Streamlit App

The first publicly accessible, interactive dashboard comparing World3 model
scenarios to real-world data. Shows which Limits to Growth scenario path
humanity is currently following.
"""

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import streamlit as st

# Ensure sibling modules are importable
sys.path.insert(0, str(Path(__file__).parent))

from scenarios import run_all_scenarios  # noqa: E402
from overlay import VARIABLE_MAP  # noqa: E402
from fetch_real_data import VALIDATED_VARIABLES  # noqa: E402

# -- Page config --------------------------------------------------------------

st.set_page_config(
    page_title="Where Are We on the Limits to Growth?",
    page_icon="🌍",
    layout="wide",
    initial_sidebar_state="expanded",
)

# -- Constants ----------------------------------------------------------------

DATA_DIR = Path(__file__).parent.parent / "data"

SCENARIO_COLORS = {
    "BAU": "#e74c3c",
    "BAU2": "#e67e22",
    "CT": "#27ae60",
}

SCENARIO_DESCRIPTIONS = {
    "BAU": (
        "**Business As Usual** -- no major policy changes from historical trends. "
        "Industrialization continues until resource depletion forces a decline."
    ),
    "BAU2": (
        "**Double Resources** -- assumes twice the estimated nonrenewable resource "
        "base. Delays decline by roughly 20 years, but pollution becomes the "
        "binding constraint."
    ),
    "CT": (
        "**Comprehensive Technology** -- aggressive resource efficiency, pollution "
        "controls, and agricultural yield improvements. Technology alone delays "
        "but does not prevent overshoot."
    ),
}

REAL_DATA_COLOR = "#00d4ff"  # bright cyan — visible on both light and dark themes
REAL_DATA_WIDTH = 3.5


# -- Caching ------------------------------------------------------------------

@st.cache_data(ttl=3600, show_spinner="Running World3 scenarios...")
def load_scenarios():
    """Run and cache World3 scenarios. Returns dict of World3 run objects
    serialized to plain lists (so Streamlit can hash them)."""
    raw = run_all_scenarios()
    results = {}
    for name, w in raw.items():
        entry = {"time": w.time.tolist()}
        for vk, vmap in VARIABLE_MAP.items():
            attr = vmap["world3_attr"]
            if hasattr(w, attr):
                entry[attr] = getattr(w, attr).tolist()
        results[name] = entry
    return results


@st.cache_data(ttl=3600)
def load_real_data():
    """Load cached real-world data CSV."""
    csv_path = DATA_DIR / "real_world_data.csv"
    if csv_path.exists():
        return pd.read_csv(csv_path)
    return None


@st.cache_data(ttl=3600)
def load_metadata():
    """Load data cache metadata."""
    meta_path = DATA_DIR / "real_world_data_metadata.json"
    if meta_path.exists():
        return json.loads(meta_path.read_text())
    return None


# -- Normalization (local versions for serialized data) -----------------------

def normalize_scenario_series(data_list, time_list, base_year=1970, dt=0.5, year_min=1900):
    """Normalize a World3 variable list to base_year = 1.0."""
    idx = int((base_year - year_min) / dt)
    base_val = data_list[idx]
    if base_val != 0:
        return [v / base_val for v in data_list]
    return list(data_list)


def normalize_real(df, col, base_year=1970):
    """Normalize a real-data column to base_year = 1.0.
    Returns (years_list, values_list) with NaN rows dropped."""
    valid = df.dropna(subset=[col])
    if len(valid) == 0:
        return [], []
    base_row = valid[valid["year"] == base_year]
    if len(base_row) > 0 and pd.notna(base_row[col].values[0]):
        base_val = base_row[col].values[0]
    else:
        base_val = valid[col].values[0]
    if base_val == 0:
        return valid["year"].tolist(), valid[col].tolist()
    return valid["year"].tolist(), (valid[col] / base_val).tolist()


# -- Scenario fit scoring -----------------------------------------------------

def compute_scenario_fit(scenarios, real_df, var_key):
    """RMSE between real data and each scenario for a variable."""
    vmap = VARIABLE_MAP[var_key]
    real_years, real_vals = normalize_real(real_df, vmap["real_col"], vmap["normalize_year"])
    if not real_years:
        return {}

    real_years = np.array(real_years)
    real_vals = np.array(real_vals)

    scores = {}
    for name, sdata in scenarios.items():
        attr = vmap["world3_attr"]
        if attr not in sdata:
            continue
        time_arr = np.array(sdata["time"])
        norm = np.array(normalize_scenario_series(
            sdata[attr], sdata["time"], vmap["normalize_year"]
        ))
        model_interp = np.interp(real_years, time_arr, norm)
        scores[name] = float(np.sqrt(np.mean((model_interp - real_vals) ** 2)))

    return scores


# -- Chart builders -----------------------------------------------------------

def build_single_chart(scenarios, real_df, var_key, year_range, show_scenarios,
                       show_real_data):
    """Build the main overlay Plotly chart for one variable."""
    vmap = VARIABLE_MAP[var_key]
    fig = go.Figure()

    # Scenario traces
    for name in show_scenarios:
        if name not in scenarios:
            continue
        sdata = scenarios[name]
        attr = vmap["world3_attr"]
        if attr not in sdata:
            continue
        norm = normalize_scenario_series(
            sdata[attr], sdata["time"], vmap["normalize_year"]
        )
        fig.add_trace(go.Scatter(
            x=sdata["time"],
            y=norm,
            name=name,
            line=dict(color=SCENARIO_COLORS.get(name, "#888"), width=2),
            opacity=0.8,
            hovertemplate=f"{name}<br>Year: %{{x:.0f}}<br>Value: %{{y:.3f}}<extra></extra>",
        ))

    # Real-world data
    real_max = None
    if show_real_data and real_df is not None and vmap["real_col"] in real_df.columns:
        real_years, real_vals = normalize_real(
            real_df, vmap["real_col"], vmap["normalize_year"]
        )
        if real_years:
            real_max = max(real_vals)
            fig.add_trace(go.Scatter(
                x=real_years,
                y=real_vals,
                name="Real-World Data",
                line=dict(color=REAL_DATA_COLOR, width=REAL_DATA_WIDTH),
                hovertemplate=(
                    "Real Data<br>Year: %{x:.0f}<br>Value: %{y:.3f}<extra></extra>"
                ),
            ))

            # "You Are Here" marker on latest point
            fig.add_trace(go.Scatter(
                x=[real_years[-1]],
                y=[real_vals[-1]],
                mode="markers+text",
                name="You Are Here",
                marker=dict(
                    color=REAL_DATA_COLOR, size=14,
                    line=dict(color="white", width=2),
                ),
                text=[f"  YOU ARE HERE ({int(real_years[-1])})"],
                textposition="middle right",
                textfont=dict(size=12, color="white"),
                hovertemplate=(
                    f"Latest: {int(real_years[-1])}<br>"
                    "Value: %{y:.3f}<extra></extra>"
                ),
                showlegend=False,
            ))

    # Scale y-axis so real data is clearly visible
    y_range_kwarg = {}
    if real_max is not None and real_max > 0:
        y_cap = max(real_max * 3, 3)
        y_range_kwarg["range"] = [0, y_cap]

    fig.update_layout(
        title=dict(
            text=(
                f"Limits to Growth: {vmap['label']}<br>"
                f"<span style='font-size:13px;color:gray'>"
                f"World3 Scenarios vs. Real-World Data "
                f"(normalized to {vmap['normalize_year']} = 1.0)</span>"
            ),
            font=dict(size=18),
        ),
        xaxis=dict(
            title="Year",
            range=list(year_range),
            gridcolor="rgba(128,128,128,0.15)",
        ),
        yaxis=dict(
            title=f"Normalized ({vmap['normalize_year']} = 1.0)",
            gridcolor="rgba(128,128,128,0.15)",
            **y_range_kwarg,
        ),
        legend=dict(
            orientation="h", yanchor="bottom", y=1.02,
            xanchor="left", x=0, font=dict(size=11),
        ),
        template="plotly_white",
        height=550,
        margin=dict(t=100, b=60),
        annotations=[
            dict(
                text=(
                    "Model: pyworld3 (Meadows et al.) | "
                    "Data: World Bank, NOAA | "
                    "github.com/Alzxcvb/world3-dashboard"
                ),
                xref="paper", yref="paper", x=1, y=-0.08,
                showarrow=False,
                font=dict(size=9, color="gray"),
                xanchor="right",
            ),
        ],
    )

    return fig


def build_grid_chart(scenarios, real_df, show_scenarios, show_real_data):
    """Build the 2x3 dashboard grid of all variables."""
    var_keys = list(VARIABLE_MAP.keys())
    n = len(var_keys)
    cols = 3
    rows = (n + cols - 1) // cols

    fig = make_subplots(
        rows=rows, cols=cols,
        subplot_titles=[VARIABLE_MAP[vk]["label"] for vk in var_keys],
        horizontal_spacing=0.06,
        vertical_spacing=0.12,
    )

    for idx, var_key in enumerate(var_keys):
        r = idx // cols + 1
        c = idx % cols + 1
        vmap = VARIABLE_MAP[var_key]

        real_max = None  # track max real data value for y-axis scaling

        # Scenario lines
        for name in show_scenarios:
            if name not in scenarios:
                continue
            sdata = scenarios[name]
            attr = vmap["world3_attr"]
            if attr not in sdata:
                continue
            norm = normalize_scenario_series(
                sdata[attr], sdata["time"], vmap["normalize_year"]
            )
            fig.add_trace(go.Scatter(
                x=sdata["time"], y=norm,
                name=name,
                line=dict(color=SCENARIO_COLORS.get(name, "#888"), width=1.5),
                opacity=0.7,
                showlegend=(idx == 0),
                legendgroup=name,
                hovertemplate=f"{name}<br>%{{x:.0f}}: %{{y:.3f}}<extra></extra>",
            ), row=r, col=c)

        # Real data
        if show_real_data and real_df is not None and vmap["real_col"] in real_df.columns:
            real_years, real_vals = normalize_real(
                real_df, vmap["real_col"], vmap["normalize_year"]
            )
            if real_years:
                real_max = max(real_vals)
                fig.add_trace(go.Scatter(
                    x=real_years, y=real_vals,
                    name="Real Data",
                    line=dict(color=REAL_DATA_COLOR, width=2.5),
                    showlegend=(idx == 0),
                    legendgroup="real",
                    hovertemplate="Real<br>%{x:.0f}: %{y:.3f}<extra></extra>",
                ), row=r, col=c)

                # You Are Here dot
                fig.add_trace(go.Scatter(
                    x=[real_years[-1]], y=[real_vals[-1]],
                    mode="markers",
                    marker=dict(
                        color=REAL_DATA_COLOR, size=8,
                        line=dict(color="white", width=1.5),
                    ),
                    showlegend=False,
                    hovertemplate=(
                        f"Latest ({int(real_years[-1])}): %{{y:.3f}}<extra></extra>"
                    ),
                ), row=r, col=c)

        fig.update_xaxes(range=[1960, 2100], row=r, col=c)

        # Scale y-axis so real data is visible (cap at 3x max real value).
        # Model lines going off-chart is fine — the point is to see where
        # reality is relative to predictions.
        if real_max is not None and real_max > 0:
            y_cap = max(real_max * 3, 3)
            fig.update_yaxes(range=[0, y_cap], row=r, col=c)

    # Hide empty subplots
    for idx in range(n, rows * cols):
        r = idx // cols + 1
        c = idx % cols + 1
        fig.update_xaxes(visible=False, row=r, col=c)
        fig.update_yaxes(visible=False, row=r, col=c)

    fig.update_layout(
        title=dict(
            text=(
                "Where Are We on the Limits to Growth?<br>"
                "<span style='font-size:13px;color:gray'>"
                "All Variables -- World3 Scenarios vs. Real-World Data</span>"
            ),
            font=dict(size=20),
        ),
        template="plotly_white",
        height=rows * 350,
        legend=dict(
            orientation="h", yanchor="bottom", y=1.02,
            xanchor="left", x=0,
        ),
        margin=dict(t=100),
    )

    return fig


# -- Main app -----------------------------------------------------------------

def main():
    # Load data
    scenarios = load_scenarios()
    real_df = load_real_data()
    metadata = load_metadata()

    # -- Sidebar --------------------------------------------------------------
    with st.sidebar:
        st.title("Controls")

        # View toggle
        view = st.radio(
            "View",
            ["Single Variable", "Dashboard Grid"],
            index=0,
        )

        st.divider()

        # Variable selector
        var_labels = {vk: vm["label"] for vk, vm in VARIABLE_MAP.items()}
        selected_var = st.selectbox(
            "Variable",
            options=list(var_labels.keys()),
            format_func=lambda x: var_labels[x],
            index=0,
            disabled=(view == "Dashboard Grid"),
        )

        st.divider()

        # Scenario checkboxes
        st.subheader("Scenarios")
        show_scenarios = []
        for key in SCENARIO_COLORS:
            if st.checkbox(key, value=True, key=f"show_{key}"):
                show_scenarios.append(key)

        st.divider()

        # Year range slider
        year_range = st.slider(
            "Year Range",
            min_value=1960,
            max_value=2100,
            value=(1960, 2100),
            step=10,
            disabled=(view == "Dashboard Grid"),
        )

        st.divider()

        # Show/hide real data
        show_real_data = st.toggle("Show Real-World Data", value=True)

        st.divider()

        # Live data refresh
        if st.button("Refresh Data (live fetch)", use_container_width=True):
            with st.spinner("Fetching live data from APIs..."):
                from fetch_real_data import fetch_all_real_data  # noqa: E402
                try:
                    fetch_all_real_data()
                    st.cache_data.clear()
                    st.success("Data refreshed!")
                    st.rerun()
                except Exception as e:
                    st.error(f"Fetch failed: {e}")

    # -- Title and introduction -----------------------------------------------

    st.title("Where Are We on the Limits to Growth?")
    st.markdown(
        "This dashboard overlays the World3 computer model scenarios from "
        "*The Limits to Growth* (Meadows et al., 1972) with real-world data "
        "from public sources. The goal: see which scenario path humanity is "
        "actually following, updated with the latest available data."
    )

    # -- Guard: no data -------------------------------------------------------

    if real_df is None:
        st.error(
            "No real-world data found. "
            "Run `python src/fetch_real_data.py` to fetch data first."
        )
        st.stop()

    # -- Charts ---------------------------------------------------------------

    if view == "Single Variable":
        fig = build_single_chart(
            scenarios, real_df, selected_var, year_range,
            show_scenarios, show_real_data,
        )
        st.plotly_chart(fig, use_container_width=True)

        # Scenario fit scores
        vmap = VARIABLE_MAP[selected_var]
        if vmap["real_col"] in real_df.columns:
            scores = compute_scenario_fit(scenarios, real_df, selected_var)
            if scores:
                best = min(scores, key=scores.get)
                score_cols = st.columns(len(scores))
                for i, (name, rmse) in enumerate(
                    sorted(scores.items(), key=lambda x: x[1])
                ):
                    with score_cols[i]:
                        label = "Closest fit" if name == best else ""
                        st.metric(
                            label=f"{name} {label}".strip(),
                            value=f"RMSE {rmse:.4f}",
                            help=(
                                f"Root mean square error between the {name} scenario "
                                "and real-world data. Lower means closer fit."
                            ),
                        )

    else:
        fig = build_grid_chart(scenarios, real_df, show_scenarios, show_real_data)
        st.plotly_chart(fig, use_container_width=True)

        # Fit summary table
        st.subheader("Scenario Fit Summary")
        st.caption(
            "RMSE between each scenario and real-world data (lower = closer match)"
        )
        fit_rows = []
        for var_key in VARIABLE_MAP:
            vmap = VARIABLE_MAP[var_key]
            if vmap["real_col"] not in real_df.columns:
                continue
            scores = compute_scenario_fit(scenarios, real_df, var_key)
            if scores:
                best = min(scores, key=scores.get)
                row = {"Variable": vmap["label"]}
                for name, rmse in scores.items():
                    marker = " *" if name == best else ""
                    row[name] = f"{rmse:.4f}{marker}"
                fit_rows.append(row)
        if fit_rows:
            st.table(pd.DataFrame(fit_rows).set_index("Variable"))

    # -- Scenario descriptions (expandable) -----------------------------------

    with st.expander("Scenario Descriptions"):
        for key, desc in SCENARIO_DESCRIPTIONS.items():
            st.markdown(f"**{key}:** {desc}")

    # -- Methodology note (expandable) ----------------------------------------

    with st.expander("Methodology"):
        st.markdown(
            """
World3 outputs are in abstract model units (e.g., "resource units",
"pollution units") that do not map directly to physical measurements.
To compare model output with real data, both series are **normalized**
to a common base year (1970 = 1.0). This shows relative change over
time rather than absolute levels.

Real-world proxy choices follow **Herrington (2021)**,
*"Update to limits to growth"*, Journal of Industrial Ecology:

| World3 Variable | Real-World Proxy | Source |
|---|---|---|
| Population | World population | World Bank |
| Industrial Output/Cap | GDP per capita (constant 2015 USD) | World Bank |
| Food Per Capita | Daily calorie supply (kcal/cap/day) | FAO via OWID |
| Persistent Pollution | CO2 (ppm) + plastic production (tonnes) | NOAA + OWID |
| Services Per Capita | Mean years of schooling | UNDP via OWID |

These proxies are imperfect but follow Herrington's methodology.
The normalized overlay shows **directional alignment**, not exact calibration.
See docs/METHODOLOGY.md for full proxy limitation analysis.
            """
        )

    # -- Data info footer -----------------------------------------------------

    st.divider()

    footer_cols = st.columns(3)

    with footer_cols[0]:
        st.caption("**Data Sources**")
        st.caption(
            "World Bank Open Data (population, GDP, life expectancy, "
            "birth/death rates)"
        )
        st.caption("NOAA GML (CO2, Mauna Loa)")
        st.caption("Our World in Data (FAO food supply, plastic production, schooling)")

    with footer_cols[1]:
        st.caption("**Data Freshness**")
        if metadata:
            st.caption(f"Last fetched: {metadata.get('cached_at_utc', 'unknown')}")
            for src, info in metadata.get("sources", {}).items():
                status = info.get("status", "unknown")
                rows = info.get("rows")
                row_str = f"{rows} rows" if rows else "cached"
                st.caption(f"{src}: {status} ({row_str})")
        else:
            st.caption("No metadata available. Run fetch_real_data.py.")

    with footer_cols[2]:
        st.caption("**Links**")
        st.caption(
            "[GitHub Repository]"
            "(https://github.com/Alzxcvb/world3-dashboard)"
        )
        st.caption(
            "[pyworld3 Model Library]"
            "(https://github.com/cvanwynsberghe/pyworld3)"
        )
        st.caption(
            "[Herrington (2021) Paper]"
            "(https://doi.org/10.1111/jiec.13084)"
        )


if __name__ == "__main__":
    main()
