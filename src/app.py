"""
World3 Live Dashboard — Streamlit App

The first publicly accessible, interactive dashboard comparing World3 model
scenarios to real-world data. Shows which Limits to Growth scenario path
humanity is currently following.
"""

import sys
from pathlib import Path

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

# Ensure sibling modules are importable
sys.path.insert(0, str(Path(__file__).parent))

from scenarios import run_all_scenarios, KEY_VARIABLES  # noqa: E402
from fetch_real_data import load_cached_real_data, VALIDATED_VARIABLES  # noqa: E402

# ── Page config ──────────────────────────────────────────────────────────────

st.set_page_config(
    page_title="Where Are We on the Limits to Growth?",
    page_icon="🌍",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Constants ────────────────────────────────────────────────────────────────

DATA_DIR = Path(__file__).parent.parent / "data"

SCENARIO_INFO = {
    "BAU": {
        "name": "Business As Usual (Standard Run)",
        "color": "#e74c3c",
        "desc": (
            "No major policy changes. Industrialization continues until resource "
            "depletion forces a decline. Population peaks ~2030 and falls sharply. "
            "This is the baseline — what happens if we change nothing."
        ),
    },
    "BAU2": {
        "name": "Business As Usual 2 (Double Resources)",
        "color": "#e67e22",
        "desc": (
            "Same as BAU but with double the estimated nonrenewable resources. "
            "Delays the decline by ~20 years, but pollution becomes the binding "
            "constraint instead. Collapse is slower but still occurs."
        ),
    },
    "CT": {
        "name": "Comprehensive Technology",
        "color": "#27ae60",
        "desc": (
            "Aggressive technological solutions: doubled resources, dramatically "
            "improved resource efficiency, pollution controls, and agricultural "
            "yields. Growth continues longer, but eventually overshoots carrying "
            "capacity. Technology alone doesn't prevent decline."
        ),
    },
}

VARIABLE_MAP = {
    "population": {
        "world3_attr": "pop",
        "real_col": "population",
        "label": "Population",
        "real_label": "World Population (World Bank)",
        "normalize_year": 1970,
    },
    "industrial_output_per_capita": {
        "world3_attr": "iopc",
        "real_col": "gdp_per_capita",
        "label": "Industrial Output Per Capita",
        "real_label": "GDP Per Capita, constant 2015 US$ (World Bank)",
        "normalize_year": 1970,
    },
    "food_per_capita": {
        "world3_attr": "fpc",
        "real_col": "food_production_index",
        "label": "Food Per Capita",
        "real_label": "Food Production Index (World Bank/FAO)",
        "normalize_year": 1970,
    },
    "pollution": {
        "world3_attr": "ppol",
        "real_col": "co2_ppm",
        "label": "Persistent Pollution",
        "real_label": "CO₂ Concentration, ppm (NOAA Mauna Loa)",
        "normalize_year": 1970,
    },
    "services_per_capita": {
        "world3_attr": "sopc",
        "real_col": "life_expectancy",
        "label": "Services Per Capita",
        "real_label": "Life Expectancy at Birth (World Bank)",
        "normalize_year": 1970,
    },
}


# ── Caching ──────────────────────────────────────────────────────────────────

@st.cache_data(ttl=3600)
def load_scenarios():
    """Run and cache World3 scenarios. Returns dict of extracted time series."""
    raw = run_all_scenarios()
    results = {}
    for name, w in raw.items():
        results[name] = {
            "time": w.time.tolist(),
        }
        for vk, vmap in VARIABLE_MAP.items():
            attr = vmap["world3_attr"]
            if hasattr(w, attr):
                results[name][attr] = getattr(w, attr).tolist()
    return results


@st.cache_data(ttl=3600)
def load_real_data():
    """Load cached real-world data CSV."""
    csv_path = DATA_DIR / "real_world_data.csv"
    if csv_path.exists():
        return pd.read_csv(csv_path)
    return None


# ── Normalization ────────────────────────────────────────────────────────────

def normalize_series(time_arr, data_arr, base_year=1970, dt=0.5, year_min=1900):
    """Normalize a World3 time series to base_year = 1.0."""
    idx = int((base_year - year_min) / dt)
    base_val = data_arr[idx]
    if base_val != 0:
        return [v / base_val for v in data_arr]
    return data_arr


def normalize_real(df, col, base_year=1970):
    """Normalize a real-data column to base_year = 1.0. Returns (years, values)."""
    valid = df.dropna(subset=[col])
    if len(valid) == 0:
        return [], []
    base_row = valid[valid["year"] == base_year]
    if len(base_row) > 0:
        base_val = base_row[col].values[0]
    else:
        base_val = valid[col].values[0]
    if base_val == 0:
        return valid["year"].tolist(), valid[col].tolist()
    return valid["year"].tolist(), (valid[col] / base_val).tolist()


# ── Closest scenario scoring ────────────────────────────────────────────────

def compute_scenario_fit(scenarios, real_df, var_key):
    """
    Compute least-squares distance between real data and each scenario
    for a given variable. Returns dict of {scenario_name: rmse}.
    """
    vmap = VARIABLE_MAP[var_key]
    real_years, real_vals = normalize_real(real_df, vmap["real_col"], vmap["normalize_year"])
    if not real_years:
        return {}

    real_years = np.array(real_years)
    real_vals = np.array(real_vals)

    scores = {}
    for name, sdata in scenarios.items():
        time_arr = np.array(sdata["time"])
        attr = vmap["world3_attr"]
        if attr not in sdata:
            continue
        data_arr = np.array(sdata[attr])
        norm = normalize_series(time_arr, data_arr, vmap["normalize_year"])
        norm = np.array(norm)

        # Interpolate model to real-data years
        model_interp = np.interp(real_years, time_arr, norm)
        rmse = np.sqrt(np.mean((model_interp - real_vals) ** 2))
        scores[name] = rmse

    return scores


# ── Chart builders ───────────────────────────────────────────────────────────

def build_overlay_chart(scenarios, real_df, var_key, year_range, show_scenarios):
    """Build the main 'You Are Here' Plotly chart for one variable."""
    vmap = VARIABLE_MAP[var_key]
    fig = go.Figure()

    # Scenario traces
    for name in show_scenarios:
        if name not in scenarios:
            continue
        sdata = scenarios[name]
        info = SCENARIO_INFO[name]
        time_arr = sdata["time"]
        attr = vmap["world3_attr"]
        if attr not in sdata:
            continue
        norm = normalize_series(time_arr, sdata[attr], vmap["normalize_year"])

        fig.add_trace(go.Scatter(
            x=time_arr, y=norm,
            name=f"{name} — {info['name']}",
            line=dict(color=info["color"], width=2),
            opacity=0.75,
            hovertemplate=f"{name}<br>Year: %{{x:.0f}}<br>Value: %{{y:.3f}}<extra></extra>",
        ))

    # Real-world data
    real_years, real_vals = normalize_real(real_df, vmap["real_col"], vmap["normalize_year"])
    if real_years:
        fig.add_trace(go.Scatter(
            x=real_years, y=real_vals,
            name="Real-World Data",
            line=dict(color="black", width=3),
            hovertemplate="Real Data<br>Year: %{x:.0f}<br>Value: %{y:.3f}<extra></extra>",
        ))

        # "You Are Here" marker
        fig.add_trace(go.Scatter(
            x=[real_years[-1]], y=[real_vals[-1]],
            mode="markers+text",
            name="You Are Here",
            marker=dict(color="black", size=14, line=dict(color="white", width=2)),
            text=[f"  YOU ARE HERE ({int(real_years[-1])})"],
            textposition="middle right",
            textfont=dict(size=12, color="black"),
            hovertemplate=f"Latest: {int(real_years[-1])}<br>Value: %{{y:.3f}}<extra></extra>",
            showlegend=False,
        ))

    fig.update_layout(
        title=dict(
            text=f"Limits to Growth: {vmap['label']}<br>"
                 f"<span style='font-size:13px;color:gray'>World3 Model Scenarios vs. {vmap['real_label']}</span>",
            font=dict(size=18),
        ),
        xaxis=dict(
            title="Year",
            range=year_range,
            gridcolor="rgba(0,0,0,0.08)",
        ),
        yaxis=dict(
            title=f"Normalized ({vmap['normalize_year']} = 1.0)",
            gridcolor="rgba(0,0,0,0.08)",
        ),
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="left",
            x=0,
            font=dict(size=11),
        ),
        template="plotly_white",
        height=550,
        margin=dict(t=100, b=60),
        annotations=[
            dict(
                text="Model: pyworld3 (Meadows et al.) | Data: World Bank, NOAA | "
                     "github.com/Alzxcvb/world3-dashboard",
                xref="paper", yref="paper",
                x=1, y=-0.08,
                showarrow=False,
                font=dict(size=9, color="gray"),
                xanchor="right",
            )
        ],
    )

    return fig


def build_dashboard_grid(scenarios, real_df, show_scenarios):
    """Build the multi-variable overview grid."""
    fig = go.Figure()

    var_keys = list(VARIABLE_MAP.keys())
    n = len(var_keys)
    cols = 3
    rows = (n + cols - 1) // cols

    from plotly.subplots import make_subplots
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

        # Scenarios
        for name in show_scenarios:
            if name not in scenarios:
                continue
            sdata = scenarios[name]
            info = SCENARIO_INFO[name]
            attr = vmap["world3_attr"]
            if attr not in sdata:
                continue
            norm = normalize_series(sdata["time"], sdata[attr], vmap["normalize_year"])
            fig.add_trace(go.Scatter(
                x=sdata["time"], y=norm,
                name=name,
                line=dict(color=info["color"], width=1.5),
                opacity=0.7,
                showlegend=(idx == 0),
                legendgroup=name,
                hovertemplate=f"{name}<br>%{{x:.0f}}: %{{y:.3f}}<extra></extra>",
            ), row=r, col=c)

        # Real data
        real_years, real_vals = normalize_real(real_df, vmap["real_col"], vmap["normalize_year"])
        if real_years:
            fig.add_trace(go.Scatter(
                x=real_years, y=real_vals,
                name="Real Data",
                line=dict(color="black", width=2.5),
                showlegend=(idx == 0),
                legendgroup="real",
                hovertemplate=f"Real<br>%{{x:.0f}}: %{{y:.3f}}<extra></extra>",
            ), row=r, col=c)

            # You Are Here dot
            fig.add_trace(go.Scatter(
                x=[real_years[-1]], y=[real_vals[-1]],
                mode="markers",
                marker=dict(color="black", size=8, line=dict(color="white", width=1.5)),
                showlegend=False,
                hovertemplate=f"Latest ({int(real_years[-1])}): %{{y:.3f}}<extra></extra>",
            ), row=r, col=c)

        fig.update_xaxes(range=[1960, 2100], row=r, col=c)

    fig.update_layout(
        title=dict(
            text="Where Are We on the Limits to Growth?",
            font=dict(size=20),
        ),
        template="plotly_white",
        height=rows * 350,
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="left",
            x=0,
        ),
        margin=dict(t=100),
    )

    return fig


# ── Main app ─────────────────────────────────────────────────────────────────

def main():
    # Load data
    scenarios = load_scenarios()
    real_df = load_real_data()
    _, metadata = load_cached_real_data()

    # ── Sidebar ──────────────────────────────────────────────────────────
    with st.sidebar:
        st.title("🌍 World3 Dashboard")
        st.caption("Limits to Growth — Live Comparison")

        st.divider()

        # View mode
        view = st.radio(
            "View",
            ["Single Variable", "Dashboard Overview"],
            index=0,
        )

        st.divider()

        # Variable selector
        var_options = {vk: vm["label"] for vk, vm in VARIABLE_MAP.items()}
        selected_var = st.selectbox(
            "Variable",
            options=list(var_options.keys()),
            format_func=lambda x: var_options[x],
            index=0,
            disabled=(view == "Dashboard Overview"),
        )

        st.divider()

        # Scenario toggles
        st.subheader("Scenarios")
        show_scenarios = []
        for key, info in SCENARIO_INFO.items():
            if st.checkbox(info["name"], value=True, key=f"show_{key}"):
                show_scenarios.append(key)

        st.divider()

        # Time range
        year_range = st.slider(
            "Year Range",
            min_value=1900,
            max_value=2100,
            value=(1960, 2100),
            step=10,
            disabled=(view == "Dashboard Overview"),
        )

        st.divider()

        # Data freshness
        st.subheader("Data Status")
        if metadata:
            st.caption(f"Cached: {metadata.get('cached_at_utc', 'unknown')}")
            for src, info in metadata.get("sources", {}).items():
                status = info.get("status", "unknown")
                rows = info.get("rows", "?")
                icon = "✅" if status == "ok" else "⚠️"
                st.caption(f"{icon} {src}: {rows} rows")
            validated = metadata.get("validated_variables", [])
            st.caption(f"Validated overlays: {', '.join(validated) if validated else 'none'}")
        else:
            st.caption("No cached data found. Run fetch_real_data.py first.")

    # ── Main area ────────────────────────────────────────────────────────

    if real_df is None:
        st.error(
            "No real-world data found. Run `python src/fetch_real_data.py` to fetch data first."
        )
        return

    if view == "Single Variable":
        # Main chart
        fig = build_overlay_chart(scenarios, real_df, selected_var, list(year_range), show_scenarios)
        st.plotly_chart(fig, use_container_width=True)

        # Closest scenario scoring
        vmap = VARIABLE_MAP[selected_var]
        if vmap["real_col"] in real_df.columns:
            scores = compute_scenario_fit(scenarios, real_df, selected_var)
            if scores:
                best = min(scores, key=scores.get)
                cols = st.columns(len(scores))
                for i, (name, rmse) in enumerate(sorted(scores.items(), key=lambda x: x[1])):
                    info = SCENARIO_INFO[name]
                    with cols[i]:
                        label = "🎯 Closest" if name == best else ""
                        st.metric(
                            label=f"{name} {label}",
                            value=f"{rmse:.4f}",
                            help=f"RMSE between {name} scenario and real data (lower = closer fit)",
                        )

        # Variable info
        st.divider()
        col1, col2 = st.columns(2)
        with col1:
            st.subheader("About This Variable")
            st.markdown(f"**World3 variable:** `{vmap['world3_attr']}`")
            st.markdown(f"**Real-world proxy:** {vmap['real_label']}")
            st.markdown(
                f"**Normalization:** Both series are divided by their {vmap['normalize_year']} "
                f"value so they share a common scale (1.0 = {vmap['normalize_year']} level)."
            )
            if selected_var not in VALIDATED_VARIABLES:
                st.warning(
                    "This overlay has not been fully validated. The mapping between "
                    "the World3 variable and its real-world proxy is approximate. "
                    "See Herrington (2021) for methodology."
                )
        with col2:
            st.subheader("Scenario Descriptions")
            for key in show_scenarios:
                if key in SCENARIO_INFO:
                    info = SCENARIO_INFO[key]
                    st.markdown(f"**{key} — {info['name']}**")
                    st.caption(info["desc"])

    else:
        # Dashboard overview
        fig = build_dashboard_grid(scenarios, real_df, show_scenarios)
        st.plotly_chart(fig, use_container_width=True)

        st.divider()
        st.subheader("Scenario Fit Summary")
        st.caption("RMSE between each scenario and real-world data (lower = closer match)")

        fit_data = []
        for var_key in VARIABLE_MAP:
            vmap = VARIABLE_MAP[var_key]
            if vmap["real_col"] not in real_df.columns:
                continue
            scores = compute_scenario_fit(scenarios, real_df, var_key)
            if scores:
                row = {"Variable": vmap["label"]}
                best = min(scores, key=scores.get)
                for name, rmse in scores.items():
                    marker = " 🎯" if name == best else ""
                    row[name] = f"{rmse:.4f}{marker}"
                fit_data.append(row)

        if fit_data:
            st.table(pd.DataFrame(fit_data).set_index("Variable"))

    # ── Footer ───────────────────────────────────────────────────────────
    st.divider()
    st.caption(
        "**Sources:** World Bank API, NOAA Mauna Loa | "
        "**Model:** [pyworld3](https://github.com/cvanwynsberghe/pyworld3) "
        "(Meadows et al., 1972; Nebel et al., 2024) | "
        "**Code:** [github.com/Alzxcvb/world3-dashboard]"
        "(https://github.com/Alzxcvb/world3-dashboard) | "
        "**Research:** [acoffman.substack.com](https://acoffman.substack.com)"
    )
    st.caption(
        "Variable mappings follow Herrington (2021), "
        "*\"Update to limits to growth\"*, Journal of Industrial Ecology."
    )


if __name__ == "__main__":
    main()
