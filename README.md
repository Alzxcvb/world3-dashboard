# World3 Live Dashboard

A live, interactive dashboard that runs the World3 system dynamics model (the "Limits to Growth" model) and overlays cached real world data from public APIs (refreshed monthly) to show which scenario path humanity is currently following.

## Why This Exists

In 1972, the Club of Rome published *The Limits to Growth*, using the World3 computer model to simulate interactions between population, industrial growth, food production, resource depletion, and pollution. The model projected several scenarios — some leading to overshoot and collapse, others to stabilization.

In 2021, Gaya Herrington (then at KPMG) updated the comparison with 40+ years of real data and found we're tracking the "BAU2" and "CT" (comprehensive technology) scenarios — both of which lead to decline around 2030-2040.

**Nobody has built a live, publicly accessible dashboard that shows this in real time.** This project fills that gap.

## What It Does

- Runs the World3 model with 1974 defaults as the base via pyworld3, and per scenario overrides for BAU2, CT and SW (the Nebel et al. 2024 recalibration is not yet integrated), for four scenarios: BAU, BAU2, CT, and SW
- Pulls real world data from the World Bank and NOAA APIs, plus Our World in Data (FAO food supply, UNDP mean years of schooling, plastic production)
- Maps empirical data to World3 variables (following Herrington's methodology)
- Shows an interactive chart: "Here are the model's scenarios. Here's where we actually are."
- Lets users pick a variable, toggle scenarios, and set the year range. It does not have sliders for changing model parameters
- Scores fit per variable by RMSE between each scenario and the real data, both normalized to 1970 = 1.0, and names the closest scenario by lowest average rank across the five tracked variables

## Project Status

**Phase: Working prototype**

Currently implemented:
- Cached real world data ingestion for five variables (population, GDP per capita, food supply, pollution composite, years of schooling)
- Four World3 scenarios: BAU, BAU2, CT, SW
- Overlay charts and RMSE fit scoring for all five variables
- A static dashboard deployed on Vercel, plus a Streamlit app for local use

See [docs/SCOPE.md](docs/SCOPE.md) for technical scope and architecture.

## Run Locally

```bash
pip install -r requirements.txt
streamlit run src/app.py        # interactive Streamlit app (local use)
```

For the static build (what's deployed):

```bash
python3 web/build_data.py
cd web/public && python3 -m http.server 8000
```

## Deployments

- **Live URL:** https://world3-dashboard.vercel.app
- **Static dashboard** (always-on, no auth, no cold start) — `web/` deploys to Vercel as a pure static site. Pre-computed scenarios + bundled real-world data ship in `web/public/data.json`; the page is plain HTML + Plotly.js. A monthly GitHub Action (`.github/workflows/refresh-data.yml`) re-runs the data fetcher and rebuilds the JSON. See [`web/README.md`](web/README.md).
- **Streamlit app** (local use) — `src/app.py` is an interactive Streamlit app for quick iteration. The static build is the canonical public URL.

## Tech Stack

- **Model:** [pyworld3](https://github.com/cvanwynsberghe/pyworld3) (339 stars, pip installable) + 1974 defaults as the base with per scenario overrides (Nebel 2024 recalibration via [PyWorld3-03](https://github.com/TimSchell98/PyWorld3-03) is planned, not integrated)
- **Data:** World Bank API, NOAA CO2 data, Our World in Data CSVs (FAO, UNDP, plastics)
- **Frontend:** Static HTML + Plotly.js (`web/public/`), plus a Streamlit app for local use (`src/app.py`)
- **Hosting:** Vercel (static site from `web/`)

## Key References

- Meadows et al. (1972) — *The Limits to Growth*
- Meadows et al. (2004) — *Limits to Growth: The 30-Year Update*
- Turner (2008, 2012, 2014) — Validation studies comparing World3 to real data
- Herrington (2021) — "Update to Limits to Growth" (*Journal of Industrial Ecology*)
- Nebel et al. (2024) — "Recalibration of Limits to Growth" (*Journal of Industrial Ecology*)

## Related Work

- [polycrisis-research](https://github.com/Alzxcvb/polycrisis-research) — Bibliometric analysis of polycrisis and LtG literature
- [acoffman.substack.com](https://acoffman.substack.com/) — Research updates and analysis
