# World3 Dashboard — Technical Scope

## Architecture

```
┌─────────────────────────────────────────────────────┐
│                   Streamlit Frontend                 │
│  ┌──────────┐  ┌──────────┐  ┌───────────────────┐  │
│  │ Scenario  │  │ "You Are │  │   User Controls   │  │
│  │  Charts   │  │  Here"   │  │  (sliders/params) │  │
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

## Components

### 1. World3 Model Integration (200-400 LOC)
- Base: `cvanwynsberghe/pyworld3` (pip install pyworld3)
- Layer: Nebel et al. 2024 recalibrated parameters from `TimSchell98/PyWorld3-03`
- Run standard scenarios: BAU, BAU2, CT, SW (stabilized world)
- Output: Time series for ~29 key variables, 1900-2100

### 2. Data Pipeline (500-800 LOC)
Five public API sources, each with a fetcher module:

| Source | API | Variables | Auth |
|--------|-----|-----------|------|
| World Bank | `api.worldbank.org/v2/` | Population, GDP, food production, arable land | None |
| IMF | `imf.org/external/datamapper/api/v1/` | GDP growth, inflation, fiscal balance | None |
| FAO | `pip install faostat` | Food production index, cereal yield, fishery catch | None |
| NOAA | Flat file download | CO2 ppm (Mauna Loa), temperature anomalies | Free token for CDO |
| UN SDG | `unstats.un.org/sdgapi/` | Supplementary poverty/health/inequality indicators | None |

### 3. Variable Mapping (200-400 LOC) — THE HARD PART

World3 variables are abstract. Real-world data must be mapped to approximate them.
Herrington (2021) provides the blueprint:

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
- Compute "closest scenario" using least-squares distance

### 5. Streamlit Frontend (400-700 LOC)
- Main chart: All scenarios overlaid + "You Are Here" dot for real data
- Variable selector: Choose which World3 variable to view
- Time range slider: Zoom in/out on timeline
- Scenario descriptions: What each scenario assumes
- Data freshness indicator: When data was last updated
- Export: Download chart as PNG, data as CSV

### 6. Data Caching & Refresh (100-200 LOC)
- Cache real-world data locally (SQLite or JSON files)
- Refresh schedule: Annual (most data is annual)
- Stale data warnings in UI

## Existing Code to Build On

| Repo | Stars | What to Use |
|------|-------|-------------|
| [cvanwynsberghe/pyworld3](https://github.com/cvanwynsberghe/pyworld3) | 339 | Core model, pip-installable, clean API |
| [TimSchell98/PyWorld3-03](https://github.com/TimSchell98/PyWorld3-03) | 42 | 2024 recalibration parameters |
| [worlddynamics/WorldDynamics.jl](https://github.com/worlddynamics/WorldDynamics.jl) | 73 | Reference (Julia), includes Earth4All |

## Competition Analysis

**There is no live World3 dashboard with real-time data.** The space is empty:
- world3simulator.org — domain dead
- En-ROADS (climateinteractive.org) — climate-only, not World3
- Earth4All simulator — Julia, not data-fed, different model (700 variables)
- bit-player.org/limits — 2012 JavaScript toy, no real data
- Insight Maker — generic SD tool, primitive World3 reimplementations

## Estimated Effort

| Phase | Work | Time |
|-------|------|------|
| 1. Model setup & scenarios | Install pyworld3, run standard scenarios, verify against published results | 1 week |
| 2. Data pipeline | Build fetchers for 5 APIs, normalize, cache | 1-2 weeks |
| 3. Variable mapping | Implement Herrington's proxy mappings, normalization, validation | 1-2 weeks |
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
- **Contribution:** First publicly accessible, reproducible, real-time comparison tool
- **Methodology section** documents the variable mapping decisions (the academic value)
