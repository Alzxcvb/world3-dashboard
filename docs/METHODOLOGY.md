# Methodology: Variable Mapping and Proxy Selection

This document describes how real-world empirical data is mapped to World3 model
variables for the overlay comparison. The approach follows **Herrington (2021)**,
with modifications noted below.

## References

- Herrington, G. (2021). "Update to limits to growth: Comparing the World3
  model with empirical data." *Journal of Industrial Ecology*, 25(3), 614-626.
  DOI: [10.1111/jiec.13084](https://doi.org/10.1111/jiec.13084)
- Nebel, A., Nebel, A., Moutarde, R., & Sciarretta, A. (2024). "Recalibration
  of limits to growth: An update of the World3 model." *Journal of Industrial
  Ecology*, 28(1), 87-99. DOI: [10.1111/jiec.13442](https://doi.org/10.1111/jiec.13442)
- Turner, G. (2008, 2012, 2014). Validation studies comparing World3 to empirical data.

## Normalization Method

World3 outputs are in abstract model units (e.g., "pollution units", "resource
units") that have no direct physical equivalent. Real-world data is in physical
units (ppm, people, dollars, years). Direct comparison is meaningless.

**Solution**: Both model and real data are normalized to a common base year:

    normalized_value = raw_value / value_at_base_year

- **Base year**: 1970 for all variables (the year the original model was calibrated)
- **Result**: Both series equal 1.0 at the base year; subsequent values show
  relative change

This follows Herrington (2021), who normalized to 1990 scenario values and
applied scaling factors for some variables. We normalize to 1970 for consistency
with the model's calibration epoch. The trade-off is that pre-1970 real data
deviates more from model output (the model was tuned to match up to ~1970).

## Variable Mapping Table

| World3 Variable | Model Attr | Real-World Proxy | Source | Indicator Code | Quality |
|---|---|---|---|---|---|
| Population | `pop` | World population | World Bank | SP.POP.TOTL | Excellent |
| Industrial Output/Cap | `iopc` | GDP per capita (constant 2015 USD) | World Bank | NY.GDP.PCAP.KD | Good |
| Food Per Capita | `fpc` | Food production index / population growth index | World Bank (computed) | AG.PRD.FOOD.XD / SP.POP.TOTL | Moderate |
| Persistent Pollution | `ppol` | CO2 concentration (ppm) | NOAA Mauna Loa | -- | Weak |
| Services Per Capita | `sopc` | Life expectancy at birth | World Bank | SP.DYN.LE00.IN | Weak |
| Nonrenewable Resources | `nr` | (not yet implemented) | -- | -- | -- |
| Arable Land | `al` | Arable land (hectares) | World Bank | AG.LND.ARBL.HA | Good |
| Birth Rate | (cbr) | Crude birth rate | World Bank | SP.DYN.CBRT.IN | Excellent |
| Death Rate | (cdr) | Crude death rate | World Bank | SP.DYN.CDRT.IN | Excellent |

### Herrington's Original Proxies (for comparison)

| World3 Variable | Herrington's Proxy | Herrington's Source |
|---|---|---|
| Population | World population | UN DESA, World Bank |
| Food Per Capita | Total energy available per person per day (kcal) | FAO Food Balance Sheets |
| Industrial Output/Cap | Index of Industrial Production + GFCF per capita | UNIDO, World Bank |
| Services Per Capita | Education Index + health/education spending (% GDP) | UNDP, World Bank |
| Persistent Pollution | CO2 concentration + plastic production | NOAA, academic sources |
| Nonrenewable Resources | Fossil fuels + 21 metals remaining fraction | BP Statistical Review, USGS |
| Human Welfare | Human Development Index (x1.106 scaling) | UNDP |
| Ecological Footprint | Ecological footprint (x1.17 scaling) | Global Footprint Network |

## Proxy Limitations by Variable

### Population -- Excellent Match

Direct measurement. World Bank and UN sources agree. The only World3 variable
with a 1:1 mapping to observable reality. No proxy issues.

### Industrial Output Per Capita -- Good Match

GDP per capita is the standard proxy but conflates services with industry.
World3's `iopc` specifically measures industrial goods output. In modern
economies, services dominate GDP (~70% in OECD countries), inflating the proxy
relative to what World3 models. Herrington used UNIDO's Index of Industrial
Production for more precision; we use GDP/capita for data availability.

**Known divergence**: GDP/capita grows faster than industrial output alone,
making real data appear to outperform the model.

### Food Per Capita -- Moderate Match (Corrected)

**Original bug**: We initially used World Bank's food production index
(AG.PRD.FOOD.XD), which is total food production -- not per capita. This
overstated growth because it included population increase.

**Current fix**: We compute `food_per_capita_index = food_production_index /
(population / population_1970)`, dividing by a population growth index to
convert total production to per-capita.

**Remaining limitations**:
- The World Bank index is indexed to 2014-2016 = 100, not a physical unit
- Herrington used FAO Food Balance Sheets (kcal/person/day), which is more
  directly comparable to World3's `fpc` (vegetal-equivalent kg/person/year)
- The Green Revolution (synthetic fertilizers, high-yield varieties, irrigation)
  produced yield gains that World3's agriculture sector underestimated

**Why real data diverges upward from BAU**: World3 assumes diminishing returns
from agricultural investment. The Green Revolution effectively reset those
curves. Real food per capita has grown steadily; BAU predicts a peak and decline.

### Persistent Pollution -- Weak Match

**The proxy**: CO2 concentration at Mauna Loa (NOAA). This is the weakest
mapping in the dashboard.

**Why it underestimates World3's `ppol`**:

1. **Baseline effect**: CO2 was already 325 ppm in 1970 (elevated from
   pre-industrial ~280 ppm). Normalized to 1970=1.0, the subsequent rise looks
   modest (~1.30x by 2024). World3's `ppol` starts near 0 in 1900 and grows
   multiplicatively from a low base.

2. **Shape mismatch**: CO2 ppm grows roughly linearly (2-3 ppm/year). World3
   `ppol` grows exponentially. After normalization, the model shoots upward
   while the real data barely bends.

3. **Scope mismatch**: `ppol` represents ALL persistent pollutants (DDT, PCBs,
   heavy metals, radioactive waste, plastics). Many of these were regulated
   after 1970 (Clean Air Act, Montreal Protocol, Stockholm Convention) and
   actually declined. CO2 is the one that wasn't effectively regulated.

4. **Regulatory response**: World3 does not model policy feedback. In reality,
   societies banned the worst pollutants when damage became visible.

**Herrington's approach**: Used CO2 + plastic production as a composite. We
currently use CO2 only. Adding ecological footprint data (Global Footprint
Network) would improve coverage.

### Services Per Capita -- Weak Match

**The proxy**: Life expectancy at birth (World Bank).

**Why it saturates relative to World3's `sopc`**:

1. **Ceiling effect**: Life expectancy has a biological ceiling (~85-90 years
   for most populations). Wealthy countries plateau around 80-85. Normalized to
   1970=1.0, the maximum possible value is ~1.46 (85/58). World3's `sopc` is an
   economic flow ($/person/year on services) with no ceiling.

2. **Nonlinear return**: Adding $10,000/person/year in healthcare spending lifts
   life expectancy from 60 to 75 years in developing countries, but from 80 to
   81 in rich ones. The relationship is deeply concave.

3. **Cheap wins**: Much of the post-1970 life expectancy gain came from
   low-cost interventions (oral rehydration therapy, vaccines, mosquito nets)
   that are decoupled from the service spending World3 models.

**Herrington's approach**: Used Education Index (UNDP) + government spending on
education and health as % of GDP. This is closer to an economic input measure
and avoids the saturation problem.

**Our mitigation**: We also fetch education expenditure (% GDP) as a secondary
indicator (`SE.XPD.TOTL.GD.ZS`), though it is not yet used in the overlay.

## Model Version Note

The pip-installable `pyworld3` package implements the **1974 version** of World3
(from *Dynamics of Growth in a Finite World*). This differs from the **2004
World3-03 version** used in *Limits to Growth: The 30-Year Update* (Meadows et
al., 2005) and by both Herrington (2021) and Nebel et al. (2024).

Key differences between 1974 and 2004 versions:
- `dcfsn` (desired completed family size): 4.0 (1974) vs. 3.8 (2004)
- `alln` (average life of land normal): 6000 (1974) vs. 1000 (2004)
- 2004 version adds separate policy year parameters for resource technology,
  pollution technology, and agricultural yield technology
- 2004 version adds Human Welfare Index (`hwi`) and Ecological Footprint (`ef`)
  output variables

The PyWorld3-03 implementation by Tim Schell (GitHub: TimSchell98/PyWorld3-03)
provides the 2004 version. Nebel et al. (2024) further recalibrated 35
parameters of the 2004 version against 1970-2020 empirical data, shifting peaks
a few years into the future and raising their heights. The parameters with the
largest changes were industrial capital lifetime, pollution transmission delay,
and urban-industrial land development time.

Integration of Nebel 2024 recalibrated parameters is planned but not yet
implemented. The specific parameter values require extraction from the published
paper (DOI: 10.1111/jiec.13442).

## Scenario Definitions

| Scenario | Name | Key Assumption | pyworld3 Config |
|---|---|---|---|
| BAU | Business As Usual | No policy changes | Default constants |
| BAU2 | Double Resources | 2x nonrenewable resources | `nri=2e12` |
| CT | Comprehensive Technology | Resource efficiency + pollution control | `nri=2e12, nruf2=0.125` |
| SW | Stabilized World | Population + industrial output control | Not yet implemented |

## Data Sources

| Source | URL | Auth Required | Variables |
|---|---|---|---|
| World Bank Open Data | api.worldbank.org/v2/ | No | Population, GDP, food, life expectancy, education, birth/death rates, arable land |
| NOAA GML | gml.noaa.gov | No | CO2 concentration (Mauna Loa annual mean) |

All data is cached locally in `data/real_world_data.csv` with metadata in
`data/real_world_data_metadata.json`. The cache is refreshed by running
`python src/fetch_real_data.py`.
