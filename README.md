# World3 Live Dashboard

A live, interactive dashboard that runs the World3 system dynamics model (the "Limits to Growth" model) and overlays real-time data from public APIs to show which scenario path humanity is currently following.

## Why This Exists

In 1972, the Club of Rome published *The Limits to Growth*, using the World3 computer model to simulate interactions between population, industrial growth, food production, resource depletion, and pollution. The model projected several scenarios — some leading to overshoot and collapse, others to stabilization.

In 2021, Gaya Herrington (then at KPMG) updated the comparison with 40+ years of real data and found we're tracking the "BAU2" and "CT" (comprehensive technology) scenarios — both of which lead to decline around 2030-2040.

**Nobody has built a live, publicly accessible dashboard that shows this in real time.** This project fills that gap.

## What It Does

- Runs the World3 model (using the 2024 Nebel et al. recalibration)
- Pulls real-world data from World Bank, IMF, FAO, and NOAA APIs
- Maps empirical data to World3 variables (following Herrington's methodology)
- Shows an interactive chart: "Here are the model's scenarios. Here's where we actually are."
- Lets users explore: What happens if resource efficiency improves? What if pollution doubles?

## Project Status

**Phase: Scoping & Design**

See [docs/SCOPE.md](docs/SCOPE.md) for technical scope and architecture.

## Tech Stack

- **Model:** [pyworld3](https://github.com/cvanwynsberghe/pyworld3) (339 stars, pip-installable) + [Nebel 2024 recalibration params](https://github.com/TimSchell98/PyWorld3-03)
- **Data:** World Bank API, IMF DataMapper API, NOAA CO2 data, FAO Python package
- **Frontend:** Streamlit (MVP) → Plotly Dash or React (later)
- **Hosting:** TBD (Railway, Render, or Fly.io)

## Key References

- Meadows et al. (1972) — *The Limits to Growth*
- Meadows et al. (2004) — *Limits to Growth: The 30-Year Update*
- Turner (2008, 2012, 2014) — Validation studies comparing World3 to real data
- Herrington (2021) — "Update to Limits to Growth" (*Journal of Industrial Ecology*)
- Nebel et al. (2024) — "Recalibration of Limits to Growth" (*Journal of Industrial Ecology*)

## Related Work

- [polycrisis-research](https://github.com/Alzxcvb/polycrisis-research) — Bibliometric analysis of polycrisis and LtG literature
- [acoffman.substack.com](https://acoffman.substack.com/) — Research updates and analysis
