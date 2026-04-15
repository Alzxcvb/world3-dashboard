"""
Generate scenario comparison charts for the implemented World3 runs.
"""

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from pathlib import Path
from scenarios import run_all_scenarios, KEY_VARIABLES

FIG_DIR = Path(__file__).parent.parent / "figures"
FIG_DIR.mkdir(exist_ok=True)


def normalize(arr, base_year_idx=140):
    """Normalize to base year = 1.0 (default: 1970, which is index 140 at dt=0.5 from 1900)."""
    base = arr[base_year_idx]
    if base == 0:
        return arr
    return arr / base


def plot_scenario_comparison(scenarios, var_key, normalize_to_1970=True):
    """Plot all scenarios for a single variable."""
    info = KEY_VARIABLES[var_key]
    colors = {
        "BAU": "#e74c3c",    # red
        "BAU2": "#e67e22",   # orange
        "CT": "#2ecc71",     # green
    }

    fig, ax = plt.subplots(figsize=(12, 6))

    for name, w in scenarios.items():
        time = w.time
        data = getattr(w, info["attr"])

        if normalize_to_1970:
            data = normalize(data)
            ylabel = f"{info['label']} (1970 = 1.0)"
        else:
            ylabel = f"{info['label']} ({info['unit']})"

        ax.plot(time, data, label=name, color=colors[name], linewidth=2, alpha=0.85)

    # Mark "now" (2026)
    ax.axvline(x=2026, color="#555", linestyle="--", alpha=0.5, linewidth=1)
    ax.text(2026.5, ax.get_ylim()[1] * 0.95, "2026", fontsize=9, color="#555")

    ax.set_title(f"Limits to Growth — {info['label']}", fontsize=14, fontweight="bold")
    ax.set_xlabel("Year")
    ax.set_ylabel(ylabel)
    ax.legend(loc="best", framealpha=0.9)
    ax.set_xlim(1900, 2100)
    ax.grid(True, alpha=0.3)

    plt.tight_layout()
    return fig


def plot_dashboard_overview(scenarios):
    """
    The classic Limits to Growth dashboard: 6 key variables in a 2x3 grid.
    This is the chart that tells the whole story at a glance.
    """
    overview_vars = [
        "population",
        "food_per_capita",
        "industrial_output_per_capita",
        "nonrenewable_resources",
        "pollution",
        "services_per_capita",
    ]

    colors = {
        "BAU": "#e74c3c",
        "BAU2": "#e67e22",
        "CT": "#2ecc71",
    }

    fig, axes = plt.subplots(2, 3, figsize=(18, 10))
    fig.suptitle(
        "Limits to Growth: World3 Model Scenarios (1900–2100)",
        fontsize=16, fontweight="bold", y=1.02
    )

    for idx, var_key in enumerate(overview_vars):
        ax = axes[idx // 3][idx % 3]
        info = KEY_VARIABLES[var_key]

        for name, w in scenarios.items():
            data = getattr(w, info["attr"])
            data_norm = normalize(data)
            ax.plot(w.time, data_norm, label=name, color=colors[name], linewidth=1.5, alpha=0.85)

        ax.axvline(x=2026, color="#555", linestyle="--", alpha=0.4, linewidth=0.8)
        ax.set_title(info["label"], fontsize=11, fontweight="bold")
        ax.set_xlim(1900, 2100)
        ax.grid(True, alpha=0.2)
        ax.tick_params(labelsize=8)

        if idx == 0:
            ax.legend(fontsize=7, loc="upper left")

    plt.tight_layout()

    out = FIG_DIR / "world3_dashboard_overview.png"
    plt.savefig(out, dpi=150, bbox_inches="tight")
    print(f"Saved: {out}")
    plt.close()
    return out


def main():
    print("Running World3 scenarios...")
    scenarios = run_all_scenarios()

    print("\nGenerating dashboard overview chart...")
    plot_dashboard_overview(scenarios)

    # Also save individual variable charts
    for var_key in KEY_VARIABLES:
        try:
            fig = plot_scenario_comparison(scenarios, var_key)
            out = FIG_DIR / f"scenario_{var_key}.png"
            fig.savefig(out, dpi=150, bbox_inches="tight")
            plt.close(fig)
            print(f"Saved: {out}")
        except Exception as e:
            print(f"Skipped {var_key}: {e}")

    print("\nDone. Check figures/ directory.")


if __name__ == "__main__":
    main()
