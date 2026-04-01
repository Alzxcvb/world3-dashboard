"""
The core "You Are Here" chart: World3 scenarios overlaid with real-world data.

This is the visualization that makes the dashboard novel — no one has built
a live version of this. Herrington (2021) did it as a static figure in a paper.
We do it dynamically with fresh data from public APIs.
"""

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from pathlib import Path
from scenarios import run_all_scenarios, KEY_VARIABLES

DATA_DIR = Path(__file__).parent.parent / "data"
FIG_DIR = Path(__file__).parent.parent / "figures"
FIG_DIR.mkdir(exist_ok=True)

# Map from World3 variable names to real-data column names
VARIABLE_MAP = {
    "population": {
        "world3_attr": "pop",
        "real_col": "population",
        "label": "Population",
        "normalize_year": 1970,
    },
    "industrial_output_per_capita": {
        "world3_attr": "iopc",
        "real_col": "gdp_per_capita",
        "label": "Industrial Output / GDP Per Capita",
        "normalize_year": 1970,
    },
    "food_per_capita": {
        "world3_attr": "fpc",
        "real_col": "food_production_index",
        "label": "Food Per Capita / Food Production Index",
        "normalize_year": 1970,
    },
    "pollution": {
        "world3_attr": "ppol",
        "real_col": "co2_ppm",
        "label": "Persistent Pollution / CO2",
        "normalize_year": 1970,
    },
    "services_per_capita": {
        "world3_attr": "sopc",
        "real_col": "life_expectancy",
        "label": "Services Per Capita / Life Expectancy",
        "normalize_year": 1970,
    },
}


def normalize_series(values, years, base_year):
    """Normalize a series so that base_year = 1.0."""
    if base_year in years:
        idx = list(years).index(base_year)
        base_val = values[idx]
        if base_val != 0:
            return values / base_val
    # Fallback: normalize to first value
    if values[0] != 0:
        return values / values[0]
    return values


def normalize_world3(world3_run, attr, base_year=1970):
    """Normalize a World3 variable to base_year = 1.0."""
    data = getattr(world3_run, attr)
    time = world3_run.time
    # Find index for base year (time steps are 0.5yr from 1900)
    idx = int((base_year - 1900) / 0.5)
    base_val = data[idx]
    if base_val != 0:
        return data / base_val
    return data


def normalize_real_data(df, col, base_year=1970):
    """Normalize real data column to base_year = 1.0."""
    base_row = df[df["year"] == base_year]
    if len(base_row) == 0 or pd.isna(base_row[col].values[0]):
        # Use earliest available value
        valid = df.dropna(subset=[col])
        if len(valid) == 0:
            return df["year"].values, np.full(len(df), np.nan)
        base_val = valid[col].values[0]
    else:
        base_val = base_row[col].values[0]

    if base_val == 0:
        return df["year"].values, df[col].values

    return df["year"].values, (df[col] / base_val).values


def plot_overlay(scenarios, real_df, var_key):
    """
    Plot World3 scenarios + real-world data for a single variable.
    The signature "You Are Here" chart.
    """
    vmap = VARIABLE_MAP[var_key]
    colors = {
        "BAU": "#e74c3c",
        "BAU2": "#e67e22",
        "CT": "#2ecc71",
        "SW": "#3498db",
    }

    fig, ax = plt.subplots(figsize=(14, 7))

    # Plot World3 scenarios
    for name, w in scenarios.items():
        data_norm = normalize_world3(w, vmap["world3_attr"], vmap["normalize_year"])
        ax.plot(w.time, data_norm, label=f"{name} (model)", color=colors[name],
                linewidth=1.8, alpha=0.7)

    # Plot real-world data
    years, real_norm = normalize_real_data(real_df, vmap["real_col"], vmap["normalize_year"])
    valid_mask = ~np.isnan(real_norm)
    ax.plot(years[valid_mask], real_norm[valid_mask],
            color="black", linewidth=2.5, label="Real-World Data",
            marker="", linestyle="-", zorder=10)

    # "You Are Here" dot — latest data point
    valid_years = years[valid_mask]
    valid_vals = real_norm[valid_mask]
    if len(valid_years) > 0:
        latest_year = valid_years[-1]
        latest_val = valid_vals[-1]
        ax.scatter([latest_year], [latest_val], color="black", s=120, zorder=11,
                   edgecolors="white", linewidth=2)
        ax.annotate(f"  YOU ARE HERE ({int(latest_year)})",
                    xy=(latest_year, latest_val),
                    fontsize=10, fontweight="bold", color="black",
                    ha="left", va="center")

    ax.set_title(f"Limits to Growth: {vmap['label']}\nWorld3 Scenarios vs. Real-World Data",
                 fontsize=14, fontweight="bold")
    ax.set_xlabel("Year", fontsize=12)
    ax.set_ylabel(f"Normalized ({vmap['normalize_year']} = 1.0)", fontsize=12)
    ax.legend(loc="upper left", framealpha=0.9, fontsize=9)
    ax.set_xlim(1960, 2100)
    ax.grid(True, alpha=0.3)

    # Add subtitle
    ax.text(0.99, 0.01,
            "Model: pyworld3 (Meadows et al.) | Data: World Bank, NOAA | github.com/Alzxcvb/world3-dashboard",
            transform=ax.transAxes, fontsize=7, color="#888",
            ha="right", va="bottom")

    plt.tight_layout()
    return fig


def plot_all_overlays(scenarios, real_df):
    """Generate overlay charts for all mapped variables."""
    for var_key in VARIABLE_MAP:
        vmap = VARIABLE_MAP[var_key]
        if vmap["real_col"] not in real_df.columns:
            print(f"Skipping {var_key}: no real data column '{vmap['real_col']}'")
            continue

        fig = plot_overlay(scenarios, real_df, var_key)
        out = FIG_DIR / f"overlay_{var_key}.png"
        fig.savefig(out, dpi=150, bbox_inches="tight")
        plt.close(fig)
        print(f"Saved: {out}")


def plot_dashboard_with_overlay(scenarios, real_df):
    """
    The hero image: 2x3 grid with all key variables, scenarios + real data.
    """
    colors = {
        "BAU": "#e74c3c",
        "BAU2": "#e67e22",
        "CT": "#2ecc71",
        "SW": "#3498db",
    }

    var_keys = list(VARIABLE_MAP.keys())
    n = len(var_keys)
    cols = 3
    rows = (n + cols - 1) // cols

    fig, axes = plt.subplots(rows, cols, figsize=(18, rows * 5))
    fig.suptitle(
        "Where Are We on the Limits to Growth?\nWorld3 Model Scenarios vs. Real-World Data",
        fontsize=16, fontweight="bold", y=1.02
    )

    for idx, var_key in enumerate(var_keys):
        ax = axes[idx // cols][idx % cols] if rows > 1 else axes[idx % cols]
        vmap = VARIABLE_MAP[var_key]

        # Plot scenarios
        for name, w in scenarios.items():
            data_norm = normalize_world3(w, vmap["world3_attr"], vmap["normalize_year"])
            ax.plot(w.time, data_norm, label=name, color=colors[name],
                    linewidth=1.3, alpha=0.7)

        # Plot real data
        if vmap["real_col"] in real_df.columns:
            years, real_norm = normalize_real_data(real_df, vmap["real_col"], vmap["normalize_year"])
            valid_mask = ~np.isnan(real_norm)
            ax.plot(years[valid_mask], real_norm[valid_mask],
                    color="black", linewidth=2, label="Real Data", zorder=10)

            # You Are Here dot
            valid_years = years[valid_mask]
            valid_vals = real_norm[valid_mask]
            if len(valid_years) > 0:
                ax.scatter([valid_years[-1]], [valid_vals[-1]], color="black", s=60,
                           zorder=11, edgecolors="white", linewidth=1.5)

        ax.set_title(vmap["label"], fontsize=10, fontweight="bold")
        ax.set_xlim(1960, 2100)
        ax.grid(True, alpha=0.2)
        ax.tick_params(labelsize=8)

        if idx == 0:
            ax.legend(fontsize=7, loc="upper left")

    # Hide empty subplots
    for idx in range(n, rows * cols):
        axes[idx // cols][idx % cols].set_visible(False)

    plt.tight_layout()
    out = FIG_DIR / "dashboard_with_real_data.png"
    fig.savefig(out, dpi=150, bbox_inches="tight")
    print(f"Saved: {out}")
    plt.close()
    return out


def main():
    print("Loading real-world data...")
    real_df = pd.read_csv(DATA_DIR / "real_world_data.csv")
    print(f"  {len(real_df)} years of data loaded")

    print("\nRunning World3 scenarios...")
    scenarios = run_all_scenarios()

    print("\nGenerating overlay charts...")
    plot_all_overlays(scenarios, real_df)

    print("\nGenerating dashboard with real data overlay...")
    plot_dashboard_with_overlay(scenarios, real_df)

    print("\nDone!")


if __name__ == "__main__":
    main()
