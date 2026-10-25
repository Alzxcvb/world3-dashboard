# World3 Dashboard — Technical Scope

## Architecture

```
┌─────────────────────────────────────────────────────┐
│                   Streamlit Frontend                 │
│  ┌──────────┐  ┌──────────┐  ┌───────────────────┐  │
│  │ Scenario  │  │ "You Are │  │   User Controls   │  │
│  │  Charts   │  │  Here"   │  │  (view, filters)  │  │
│  └──────────┘  └──────────┘  └───────────────────┘  │
└───────────────────────┬─────────────────────────────┘
                        │
┌───────────────────────┴─────────────────────────────┐
│              Scenario Runner & Comparison             │
│  Runs World3 model → produces scenario trajectories  │
│  Maps real data onto model variables for overlay     │
└───────────────────────┬─────────────────────────────┘
                        │
          ┌─────────────┼─────────────┐
          │             │             │
   ┌──────┴──────┐ ┌───┴────┐ ┌─────┴──────┐
   │ World3 Model│ │Variable│ │ Data Fetch  │
   │ (pyworld3)  │ │Mapping │ │ (APIs)      │
   └─────────────┘ └────────┘ └─────────────┘
```

The diagram shows the Streamlit app (`src/app.py`). The deployed site is a static page built from `web/` (see README.md).

## Components

### 1. World3 Model Integration (200-400 LOC)
- Status: the code runs the 1974 pyworld3 defaults; the Nebel layer below is planned, not integrated (`src/scenarios.py:11-20`)
- Base: `cvanwynsberghe/pyworld3` (pip install pyworld3)
- Layer (planned): Nebel et al. 2024 recalibrated parameters, taken from the paper; `TimSchell98/PyWorld3-03` provides the World3-03 (2004) model
- Run standard scenarios: BAU, BAU2, CT, SW (stabilized world)
- Output: Time series for the 7 variables in `KEY_VARIABLES` (`src/scenarios.py:100-143`), 1900 to 2100

### 2. Data Pipeline (500-800 LOC)
Planned sources (implemented today: World Bank, NOAA, and Our World in Data for FAO, UNDP and plastics; IMF, the `faostat` package and UN SDG are not used by the code):

| Source | API | Variables | Auth |
|--------|-----|-----------|------|
| World Bank | `api.worldbank.org/v2/` | Population, GDP, food production, arable land | None |
| IMF | `imf.org/external/datamapper/api/v1/` | GDP growth, inflation, fiscal balance | None |
| FAO | `pip install faostat` | Food production index, cereal yield, fishery catch | None |
| NOAA | Flat file download | CO2 ppm (Mauna Loa), temperature anomalies | Free token for CDO |
| UN SDG | `unstats.un.org/sdgapi/` | Supplementary poverty/health/inequality indicators | None |

### 3. Variable Mapping (200-400 LOC) — THE HARD PART

World3 variables are abstract. Real-world data must be mapped to approximate them.
Herrington (2021) provides the blueprint. This table is the original plan; the proxies the code uses are in `docs/METHODOLOGY.md`:

| World3 Variable | Real-World Proxy | Data Source |
|----------------|-----------------|-------------|
| Population | World population | World Bank SP.POP.TOTL |
| Food per capita | Food production index per capita | FAO |
| Industrial output per capita | GDP per capita (constant $) | World Bank NY.GDP.PCAP.KD |
| Nonrenewable resources | Material footprint per capita | UN SDG 12.2.1 |
| Pollution | CO2 concentration + ecological footprint | NOAA + Global Footprint Network |
| Services per capita | Life expectancy, education index | World Bank |
| Birth/death rates | Crude birth/death rates | World Bank SP.DYN.CBRT.IN, SP.DYN.CDRT.IN |
| Arable land | Arable land (hectares per person) | World Bank AG.LND.ARBL.HA.PC |

**Key challenge:** World3 outputs are in abstract indexed units. Real data is in physical units.
Alignment requires normalization: anchor both at 1970=1.0 and compute relative changes.
This must be done carefully and documented transparently — it's the intellectual core of the project
and the basis for any future paper.

### 4. Scenario Runner (150-300 LOC)
- Run 4 standard World3 scenarios (BAU, BAU2, CT, SW)
- Cache results (scenarios don't change between runs)
- Compare against real data trajectory
- Compute "closest scenario" from RMSE per variable, ranked across the five tracked variables

### 5. Streamlit Frontend (400-700 LOC)
- Main chart: All scenarios overlaid + "You Are Here" dot for real data
- Variable selector: Choose which World3 variable to view
- Year range slider: Zoom in/out on timeline
- Scenario descriptions: What each scenario assumes
- Data freshness indicator: When data was last updated
- Charts can be saved as PNG through the default Plotly toolbar. Not implemented: a CSV data export (`src/app.py` has no download button)

### 6. Data Caching & Refresh (100-200 LOC)
- Cache real world data locally in `data/real_world_data.csv` with metadata in `data/real_world_data_metadata.json`
- Refresh schedule: monthly refresh planned; the public repo has no scheduled refresh workflow
- Data freshness caption in the Streamlit app (`src/app.py:582-584`) and a "Refresh Data (live fetch)" button (`src/app.py:467`); no stale data warning

## Existing Code to Build On

| Repo | What to Use |
|------|-------------|
| [cvanwynsberghe/pyworld3](https://github.com/cvanwynsberghe/pyworld3) | Core model, pip installable, clean API |
| [TimSchell98/PyWorld3-03](https://github.com/TimSchell98/PyWorld3-03) | World3-03 (2004) model; does not include the Nebel 2024 recalibration |
| [worlddynamics/WorldDynamics.jl](https://github.com/worlddynamics/WorldDynamics.jl) | Reference (Julia), includes Earth4All |

## Competition Analysis

Other tools found during scoping (these descriptions were not rechecked):
- world3simulator.org — domain dead
- En-ROADS (climateinteractive.org) — climate-only, not World3
- Earth4All simulator — Julia, not data-fed, different model (700 variables)
- bit-player.org/limits — 2012 JavaScript toy, no real data
- Insight Maker — generic SD tool, primitive World3 reimplementations

## Estimated Effort

| Phase | Work | Time |
|-------|------|------|
| 1. Model setup & scenarios | Install pyworld3, run standard scenarios, verify against published results | 1 week |
| 2. Data pipeline | Build fetchers (World Bank, NOAA and Our World in Data are implemented), normalize, cache | one to two weeks |
| 3. Variable mapping | Implement Herrington's proxy mappings, normalization, validation | one to two weeks |
| 4. Frontend | Streamlit app with interactive charts | 1 week |
| 5. Polish & deploy | Error handling, deployment, documentation | 1 week |
| **Total** | | **4-8 weeks** |

## Token/Cost Estimate for AI-Assisted Build

Assuming Claude Opus for architecture decisions and Claude Sonnet for implementation:
- Research & design conversations: ~200K tokens input, ~50K output = ~$4
- Implementation sessions (10-15 sessions): ~2M tokens input, ~500K output = ~$40
- Debugging & iteration: ~1M tokens input, ~250K output = ~$20
- **Total estimated AI cost: ~$60-80**

This does not include the cost of this scoping research session.

## Publication Angle

A paper could accompany the dashboard:
- **Title:** "Where Are We on the Limits to Growth? A Live Dashboard Comparing World3 Scenarios to Empirical Data"
- **Target:** Journal of Industrial Ecology (where Herrington and Nebel published)
- **Contribution:** First publicly accessible, reproducible comparison tool with a planned monthly data refresh
- **Methodology section** documents the variable mapping decisions (the academic value)
