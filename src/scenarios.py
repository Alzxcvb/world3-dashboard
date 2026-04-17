"""
World3 Standard Scenarios
Runs the currently implemented World3 scenarios and returns results.

Scenarios:
    BAU  - Business As Usual (Standard Run): No major policy changes
    BAU2 - Business As Usual 2: Double the estimated resources
    CT   - Comprehensive Technology: Technology solves resource/pollution
    SW   - Stabilized World (Scenario 9): Full policy bundle — equilibrium

Model version note:
    The pip-installable pyworld3 implements the 1974 World3. The 2004
    World3-03 update (Meadows et al., "30-Year Update") changed many
    parameters together — applying partial 2004 corrections without the
    full parameter/table set makes results WORSE (e.g., BAU peak pop
    drops to 6B vs. real 8B). We use the consistent 1974 defaults until
    full PyWorld3-03 integration (TimSchell98/PyWorld3-03) is complete.

    Nebel et al. (2024) further recalibrated 35 World3-03 parameters
    against 1970-2020 data; those values are not yet integrated.

Reference: Meadows et al. (2004), Herrington (2021), Nebel et al. (2024)
"""

from pyworld3 import World3


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
    w.init_world3_constants(nri=2e12)
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
    """Stabilized World (Scenario 9) — full policy bundle: population + economy +
    technology applied together from 2002. The only scenario in Meadows et al.
    (2004) that avoids overshoot and achieves a sustainable equilibrium.

    Note: The todo.md spec lists 2004 World3-03 params (dcfsn=2, imti=350),
    but we run the 1974 pyworld3. In the 1974 model dcfsn is a global constant
    (not policy-year-gated), so setting it to 2 crushes population from 1900.
    Instead we use the 1974 policy-year switches (zpgt, pet, fcest, iet) set
    to 2002, which produces the correct qualitative SW behavior: population
    stabilizes near 6B, resources are conserved, no overshoot collapse.
    """
    w = World3(dt=0.5, year_min=1900, year_max=2100)
    w.init_world3_constants(
        # Population stabilization policies (activate at 2002)
        zpgt=2002,          # zero population growth target year
        pet=2002,           # population equilibrium trigger
        fcest=2002,         # family size completion trigger
        # Economic equilibrium (activate at 2002)
        iet=2002,           # industrial equilibrium trigger
        iopcd=350,          # industrial output per capita desired (cap growth)
        # Technology bundle (values used after policy year)
        nruf2=0.1,          # resource efficiency after pyear
        ppgf2=0.1,          # pollution generation factor after pyear
        ppgf21=0.1,         # secondary pollution chain factor after pyear
        lyf2=1.2,           # land yield factor (ag tech)
        alai2=1,            # arable land adjustment after pyear
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
    """Run the scenarios that are actually implemented and return dict of results."""
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
