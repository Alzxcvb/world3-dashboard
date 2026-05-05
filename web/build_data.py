"""Pre-compute World3 scenarios + bundle real-world data into a single JSON
blob the static dashboard reads at runtime. Deterministic — same inputs
produce the same output, so the result can be cached + committed.

Run from the repo root:  python3 web/build_data.py
"""

from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd

REPO_ROOT = Path(__file__).resolve().parent.parent
SRC_DIR = REPO_ROOT / "src"
DATA_DIR = REPO_ROOT / "data"
OUT_PATH = Path(__file__).resolve().parent / "public" / "data.json"

sys.path.insert(0, str(SRC_DIR))

from scenarios import run_all_scenarios  # noqa: E402
from overlay import VARIABLE_MAP  # noqa: E402

SCENARIO_COLORS = {
    "BAU": "#e74c3c",
    "BAU2": "#e67e22",
    "CT": "#27ae60",
    "SW": "#3498db",
}

SCENARIO_DESCRIPTIONS = {
    "BAU": (
        "Business As Usual — no major policy changes from historical trends. "
        "Industrialization continues until resource depletion forces a decline."
    ),
    "BAU2": (
        "Double Resources — assumes twice the estimated nonrenewable resource "
        "base. Delays decline by roughly 20 years, but pollution becomes the "
        "binding constraint."
    ),
    "CT": (
        "Comprehensive Technology — aggressive resource efficiency, pollution "
        "controls, and agricultural yield improvements. Technology alone "
        "delays but does not prevent overshoot."
    ),
    "SW": (
        "Stabilized World (Scenario 9) — full policy bundle: replacement-level "
        "fertility, capped industrial output, resource efficiency, pollution "
        "controls, agricultural technology, all applied from 2002. The only "
        "scenario achieving sustainable equilibrium without overshoot."
    ),
}

DT = 0.5
YEAR_MIN = 1900


def normalize_series(values: list[float], base_index: int) -> list[float]:
    base = values[base_index]
    if base == 0:
        return [float(v) for v in values]
    return [float(v) / float(base) for v in values]


def normalize_real(df: pd.DataFrame, col: str, base_year: int) -> tuple[list[int], list[float]]:
    valid = df.dropna(subset=[col])
    if len(valid) == 0:
        return [], []
    base_row = valid[valid["year"] == base_year]
    if len(base_row) > 0 and pd.notna(base_row[col].values[0]):
        base_val = base_row[col].values[0]
    else:
        base_val = valid[col].values[0]
    if base_val == 0:
        return valid["year"].astype(int).tolist(), valid[col].astype(float).tolist()
    norm = (valid[col] / base_val).astype(float).tolist()
    return valid["year"].astype(int).tolist(), norm


def compute_rmse(model_time: list[float], model_norm: list[float],
                 real_years: list[int], real_vals: list[float]) -> float:
    if not real_years:
        return float("nan")
    interp = np.interp(np.array(real_years, dtype=float),
                       np.array(model_time, dtype=float),
                       np.array(model_norm, dtype=float))
    diff = interp - np.array(real_vals, dtype=float)
    return float(np.sqrt(np.mean(diff ** 2)))


def main() -> None:
    print("Running World3 scenarios...")
    raw = run_all_scenarios()

    # All scenarios share the same time vector
    time_arr = list(raw["BAU"].time.tolist())
    base_idx = int((1970 - YEAR_MIN) / DT)

    scenarios_out: dict[str, dict] = {}
    for name, w in raw.items():
        series: dict[str, list[float]] = {}
        for vk, vmap in VARIABLE_MAP.items():
            attr = vmap["world3_attr"]
            if not hasattr(w, attr):
                continue
            raw_vals = getattr(w, attr).tolist()
            series[attr] = normalize_series(raw_vals, base_idx)
        scenarios_out[name] = {
            "color": SCENARIO_COLORS[name],
            "description": SCENARIO_DESCRIPTIONS[name],
            "series": series,
        }

    # Real-world data
    print("Loading real-world data...")
    real_df = pd.read_csv(DATA_DIR / "real_world_data.csv")

    real_out: dict[str, dict] = {}
    for vk, vmap in VARIABLE_MAP.items():
        years, vals = normalize_real(real_df, vmap["real_col"], vmap["normalize_year"])
        real_out[vk] = {"years": years, "values": vals}

    # RMSE per (variable, scenario)
    rmse_out: dict[str, dict[str, float]] = {}
    for vk, vmap in VARIABLE_MAP.items():
        attr = vmap["world3_attr"]
        rd = real_out[vk]
        if not rd["years"]:
            continue
        rmse_out[vk] = {}
        for name, sdata in scenarios_out.items():
            if attr not in sdata["series"]:
                continue
            score = compute_rmse(time_arr, sdata["series"][attr], rd["years"], rd["values"])
            rmse_out[vk][name] = round(score, 6)

    # Variables metadata (preserve dict order from VARIABLE_MAP)
    variables_meta = []
    for vk, vmap in VARIABLE_MAP.items():
        variables_meta.append({
            "key": vk,
            "label": vmap["label"],
            "world3_attr": vmap["world3_attr"],
            "real_col": vmap["real_col"],
            "normalize_year": vmap["normalize_year"],
        })

    # Data-freshness metadata
    meta_path = DATA_DIR / "real_world_data_metadata.json"
    sources_meta = {}
    data_freshness = None
    if meta_path.exists():
        meta_blob = json.loads(meta_path.read_text())
        sources_meta = meta_blob.get("sources", {})
        data_freshness = meta_blob.get("cached_at_utc")

    payload = {
        "generated_at_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "data_freshness_utc": data_freshness,
        "sources": sources_meta,
        "variables": variables_meta,
        "time": time_arr,
        "scenarios": scenarios_out,
        "real_data": real_out,
        "rmse": rmse_out,
        "scenario_colors": SCENARIO_COLORS,
    }

    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUT_PATH.write_text(json.dumps(payload, separators=(",", ":")))
    size_kb = OUT_PATH.stat().st_size / 1024
    print(f"Wrote {OUT_PATH.relative_to(REPO_ROOT)} ({size_kb:.1f} KB)")
    print(f"  scenarios={list(scenarios_out)}  variables={[v['key'] for v in variables_meta]}")
    print(f"  time: {time_arr[0]:.0f} → {time_arr[-1]:.0f} ({len(time_arr)} steps, dt={DT})")
    print(f"  real-data freshness: {data_freshness}")


if __name__ == "__main__":
    main()
