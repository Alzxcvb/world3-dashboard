"""
Fetch real-world data from public APIs to overlay on World3 scenarios.

Data sources:
    - World Bank: Population, GDP per capita, food production, arable land, birth/death rates
    - NOAA: CO2 concentration (Mauna Loa)

All free, no API key required.

Variable mapping follows Herrington (2021):
    World3 Variable         → Real-World Proxy              → Source
    Population              → World population              → World Bank SP.POP.TOTL
    Industrial Output/Cap   → GDP per capita (constant 2015$) → World Bank NY.GDP.PCAP.KD
    Food Per Capita         → Food production index          → World Bank AG.PRD.FOOD.XD
    Nonrenewable Resources  → Material footprint/cap (proxy) → UN SDG 12.2.1 (limited)
    Persistent Pollution    → CO2 concentration              → NOAA Mauna Loa
    Services Per Capita     → Life expectancy                → World Bank SP.DYN.LE00.IN
    Arable Land             → Arable land (hectares)         → World Bank AG.LND.ARBL.HA
    Birth Rate              → Crude birth rate               → World Bank SP.DYN.CBRT.IN
    Death Rate              → Crude death rate               → World Bank SP.DYN.CDRT.IN
"""

import requests
import json
import pandas as pd
from pathlib import Path

DATA_DIR = Path(__file__).parent.parent / "data"
DATA_DIR.mkdir(exist_ok=True)


# ── World Bank API ────────────────────────────────────────────────────────────

WORLD_BANK_INDICATORS = {
    "population": {
        "indicator": "SP.POP.TOTL",
        "label": "World Population",
        "unit": "people",
    },
    "gdp_per_capita": {
        "indicator": "NY.GDP.PCAP.KD",
        "label": "GDP Per Capita (constant 2015 US$)",
        "unit": "$/person/year",
    },
    "food_production_index": {
        "indicator": "AG.PRD.FOOD.XD",
        "label": "Food Production Index (2014-2016 = 100)",
        "unit": "index",
    },
    "arable_land": {
        "indicator": "AG.LND.ARBL.HA",
        "label": "Arable Land",
        "unit": "hectares",
    },
    "life_expectancy": {
        "indicator": "SP.DYN.LE00.IN",
        "label": "Life Expectancy at Birth",
        "unit": "years",
    },
    "birth_rate": {
        "indicator": "SP.DYN.CBRT.IN",
        "label": "Crude Birth Rate",
        "unit": "per 1,000 people",
    },
    "death_rate": {
        "indicator": "SP.DYN.CDRT.IN",
        "label": "Crude Death Rate",
        "unit": "per 1,000 people",
    },
}


def fetch_world_bank(indicator_code, country="WLD", date_range="1960:2025"):
    """
    Fetch a single indicator from World Bank API for the world aggregate.
    Returns a dict of {year: value}.
    """
    url = f"https://api.worldbank.org/v2/country/{country}/indicator/{indicator_code}"
    params = {
        "date": date_range,
        "format": "json",
        "per_page": 100,
    }

    all_data = {}
    page = 1
    total_pages = 1

    while page <= total_pages:
        params["page"] = page
        r = requests.get(url, params=params)
        r.raise_for_status()
        result = r.json()

        if len(result) < 2:
            break

        meta = result[0]
        total_pages = meta.get("pages", 1)
        records = result[1]

        for record in records:
            year = int(record["date"])
            value = record["value"]
            if value is not None:
                all_data[year] = float(value)

        page += 1

    return all_data


def fetch_all_world_bank():
    """Fetch all World Bank indicators and return a combined DataFrame."""
    frames = {}

    for key, info in WORLD_BANK_INDICATORS.items():
        print(f"  Fetching {info['label']}...")
        data = fetch_world_bank(info["indicator"])
        if data:
            frames[key] = data
            print(f"    Got {len(data)} years ({min(data.keys())}-{max(data.keys())})")
        else:
            print(f"    WARNING: No data returned")

    # Combine into DataFrame
    all_years = set()
    for d in frames.values():
        all_years.update(d.keys())

    rows = []
    for year in sorted(all_years):
        row = {"year": year}
        for key, data in frames.items():
            row[key] = data.get(year)
        rows.append(row)

    df = pd.DataFrame(rows)
    return df


# ── NOAA CO2 Data ─────────────────────────────────────────────────────────────

def fetch_noaa_co2():
    """
    Fetch annual mean CO2 from Mauna Loa.
    Source: NOAA GML (flat text file, no auth needed).
    """
    url = "https://gml.noaa.gov/webdata/ccgg/trends/co2/co2_annmean_mlo.txt"
    print(f"  Fetching NOAA CO2 data...")

    r = requests.get(url)
    r.raise_for_status()

    data = {}
    for line in r.text.strip().split("\n"):
        if line.startswith("#"):
            continue
        parts = line.split()
        if len(parts) >= 2:
            try:
                year = int(parts[0])
                co2 = float(parts[1])
                data[year] = co2
            except ValueError:
                continue

    print(f"    Got {len(data)} years ({min(data.keys())}-{max(data.keys())})")
    return data


# ── Combine Everything ────────────────────────────────────────────────────────

def fetch_all_real_data():
    """Fetch all real-world data and save as CSV."""
    print("Fetching World Bank data...")
    wb_df = fetch_all_world_bank()

    print("\nFetching NOAA CO2 data...")
    co2_data = fetch_noaa_co2()
    co2_df = pd.DataFrame(list(co2_data.items()), columns=["year", "co2_ppm"])

    # Merge
    df = wb_df.merge(co2_df, on="year", how="outer").sort_values("year").reset_index(drop=True)

    # Save
    csv_path = DATA_DIR / "real_world_data.csv"
    df.to_csv(csv_path, index=False)
    print(f"\nSaved: {csv_path} ({len(df)} rows, {len(df.columns)} columns)")

    # Summary
    print(f"\nData coverage:")
    for col in df.columns:
        if col == "year":
            continue
        valid = df[col].notna().sum()
        years = df.loc[df[col].notna(), "year"]
        if len(years) > 0:
            print(f"  {col}: {valid} years ({years.min()}-{years.max()})")

    return df


if __name__ == "__main__":
    df = fetch_all_real_data()

    print(f"\nLatest values:")
    latest = df.dropna(subset=["population"]).iloc[-1]
    print(f"  Year: {int(latest['year'])}")
    if pd.notna(latest.get("population")):
        print(f"  Population: {latest['population']/1e9:.2f} billion")
    if pd.notna(latest.get("gdp_per_capita")):
        print(f"  GDP/capita: ${latest['gdp_per_capita']:,.0f}")
    if pd.notna(latest.get("life_expectancy")):
        print(f"  Life expectancy: {latest['life_expectancy']:.1f} years")

    co2_latest = df.dropna(subset=["co2_ppm"]).iloc[-1]
    if pd.notna(co2_latest.get("co2_ppm")):
        print(f"  CO2: {co2_latest['co2_ppm']:.1f} ppm ({int(co2_latest['year'])})")
