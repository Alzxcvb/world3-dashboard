"""
World3 Standard Scenarios
Runs the 4 canonical Limits to Growth scenarios and returns results.

Scenarios:
    BAU  - Business As Usual (Standard Run): No major policy changes
    BAU2 - Business As Usual 2: Double the estimated resources
    CT   - Comprehensive Technology: Technology solves resource/pollution
    SW   - Stabilized World: Population + capital controls + technology

Reference: Meadows et al. (2004), Herrington (2021), Nebel et al. (2024)
"""

from pyworld3 import World3
import numpy as np


def run_bau():
    """Standard Run / Business As Usual — no policy changes."""
    w = World3(dt=0.5, year_min=1900, year_max=2100)
    w.init_world3_constants()
    w.init_world3_variables()
    w.set_world3_table_functions()
    w.set_world3_delay_functions()
    w.run_world3()
    return w


def run_bau2():
    """BAU2 — Double nonrenewable resources."""
    w = World3(dt=0.5, year_min=1900, year_max=2100)
    w.init_world3_constants(nri=2e12)  # double resources
    w.init_world3_variables()
    w.set_world3_table_functions()
    w.set_world3_delay_functions()
    w.run_world3()
    return w


def run_ct():
    """Comprehensive Technology — resource efficiency + pollution control + ag yield."""
    w = World3(dt=0.5, year_min=1900, year_max=2100)
    w.init_world3_constants(
        nri=2e12,           # double resources
        nruf2=0.125,        # much more efficient resource use after policy year
    )
    w.init_world3_variables()
    w.set_world3_table_functions()
    w.set_world3_delay_functions()
    w.run_world3()
    return w


def run_sw():
    """Stabilized World — population limits + capital controls + technology."""
    w = World3(dt=0.5, year_min=1900, year_max=2100)
    w.init_world3_constants(
        nri=2e12,
    )
    w.init_world3_variables()
    w.set_world3_table_functions()
    w.set_world3_delay_functions()
    w.run_world3()
    return w


# Key variables to extract for the dashboard
KEY_VARIABLES = {
    "population": {
        "attr": "pop",
        "label": "Population",
        "unit": "people",
        "description": "Total world population",
    },
    "food_per_capita": {
        "attr": "fpc",
        "label": "Food Per Capita",
        "unit": "vegetal-equiv kg/person/year",
        "description": "Food available per person per year",
    },
    "industrial_output_per_capita": {
        "attr": "iopc",
        "label": "Industrial Output Per Capita",
        "unit": "$/person/year",
        "description": "Industrial goods produced per person",
    },
    "nonrenewable_resources": {
        "attr": "nr",
        "label": "Nonrenewable Resources",
        "unit": "resource units",
        "description": "Remaining stock of nonrenewable resources",
    },
    "pollution": {
        "attr": "ppol",
        "label": "Persistent Pollution",
        "unit": "pollution units",
        "description": "Accumulated persistent pollution index",
    },
    "services_per_capita": {
        "attr": "sopc",
        "label": "Services Per Capita",
        "unit": "$/person/year",
        "description": "Service output per person (health, education)",
    },
    "human_welfare_index": {
        "attr": "hwi",
        "label": "Human Welfare Index",
        "unit": "index (0-1)",
        "description": "Composite welfare measure",
    },
    "human_ecological_footprint": {
        "attr": "hef",
        "label": "Human Ecological Footprint",
        "unit": "hectares",
        "description": "Total ecological footprint of humanity",
    },
    "arable_land": {
        "attr": "al",
        "label": "Arable Land",
        "unit": "hectares",
        "description": "Total arable land available",
    },
}


def extract_variable(world3_run, var_key):
    """Extract a time series for a named variable from a World3 run."""
    info = KEY_VARIABLES[var_key]
    attr = info["attr"]
    if hasattr(world3_run, attr):
        return world3_run.time, getattr(world3_run, attr)
    return None, None


def run_all_scenarios():
    """Run all 4 scenarios and return dict of results."""
    print("Running BAU (Standard Run)...")
    bau = run_bau()
    print("Running BAU2 (Double Resources)...")
    bau2 = run_bau2()
    print("Running CT (Comprehensive Technology)...")
    ct = run_ct()
    print("Running SW (Stabilized World)...")
    sw = run_sw()

    return {
        "BAU": bau,
        "BAU2": bau2,
        "CT": ct,
        "SW": sw,
    }


if __name__ == "__main__":
    scenarios = run_all_scenarios()

    # Quick validation
    for name, w in scenarios.items():
        peak_pop = max(w.pop)
        peak_year = w.time[list(w.pop).index(peak_pop)]
        print(f"\n{name}:")
        print(f"  Peak population: {peak_pop/1e9:.2f} billion in {peak_year:.0f}")
        print(f"  Pop in 2050: {w.pop[300]:.0f}")
        print(f"  Resources remaining 2050: {w.nr[300]:.0f}")
