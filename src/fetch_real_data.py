"""
Fetch real-world data from public APIs to overlay on World3 scenarios.

Data sources (following Herrington 2021 proxy methodology):
    - World Bank: Population, GDP per capita, life expectancy, birth/death rates
    - NOAA: CO2 concentration (Mauna Loa)
    - Our World in Data / FAO: Daily calorie supply per person (kcal/cap/day)
    - Our World in Data / PlasticsEurope: Global plastic production (tonnes)
    - Our World in Data / UNDP: Mean years of schooling

All free, no API key required.

Variable mapping follows Herrington (2021):
    World3 Variable         → Real-World Proxy                    → Source
    Population              → World population                    → World Bank SP.POP.TOTL
    Industrial Output/Cap   → GDP per capita (constant 2015$)     → World Bank NY.GDP.PCAP.KD
    Food Per Capita         → Daily calorie supply (kcal/cap/day) → FAO via OWID
    Persistent Pollution    → CO2 (ppm) + plastic production (t)  → NOAA + OWID
    Services Per Capita     → Mean years of schooling              → UNDP via OWID
    Arable Land             → Arable land (hectares)              → World Bank AG.LND.ARBL.HA
    Birth Rate              → Crude birth rate                    → World Bank SP.DYN.CBRT.IN
    Death Rate              → Crude death rate                    → World Bank SP.DYN.CDRT.IN
"""

import io
import json
from pathlib import Path
from datetime import datetime, timezone

import numpy as np
import pandas as pd
import requests

DATA_DIR = Path(__file__).parent.parent / "data"
DATA_DIR.mkdir(exist_ok=True)

REAL_DATA_CSV = DATA_DIR / "real_world_data.csv"
REAL_DATA_METADATA = DATA_DIR / "real_world_data_metadata.json"
REQUEST_TIMEOUT = 30
USER_AGENT = "world3-dashboard/0.1"
VALIDATED_VARIABLES = [
    "population",
    "industrial_output_per_capita",
    "food_per_capita",
    "pollution",
    "services_per_capita",
]


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

    with requests.Session() as session:
        session.headers.update({"User-Agent": USER_AGENT})

        while page <= total_pages:
            params["page"] = page
            r = session.get(url, params=params, timeout=REQUEST_TIMEOUT)
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
        try:
            data = fetch_world_bank(info["indicator"])
        except requests.RequestException as exc:
            print(f"    ERROR: {exc}")
            continue
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

    with requests.Session() as session:
        session.headers.update({"User-Agent": USER_AGENT})
        r = session.get(url, timeout=REQUEST_TIMEOUT)
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


# ── Our World in Data (OWID) Fetchers ────────────────────────────────────────

def _fetch_owid_csv(url, entity="World"):
    """
    Fetch a CSV from Our World in Data and filter to a specific entity.
    OWID CSVs have columns: Entity, Code, Year, <value_column>.
    Returns a dict of {year: value}.
    """
    r = requests.get(url, timeout=REQUEST_TIMEOUT,
                     headers={"User-Agent": USER_AGENT})
    r.raise_for_status()
    df = pd.read_csv(io.StringIO(r.text))

    # Filter to the target entity
    world = df[df["Entity"] == entity].copy()
    if world.empty:
        # Try common alternatives
        for alt in ["World", "OWID_WRL", "World total"]:
            world = df[df["Entity"] == alt]
            if not world.empty:
                break
        if world.empty:
            return {}

    # The value column is whichever column isn't Entity/Code/Year
    value_col = [c for c in world.columns if c not in ("Entity", "Code", "Year")][0]
    result = {}
    for _, row in world.iterrows():
        if pd.notna(row[value_col]):
            result[int(row["Year"])] = float(row[value_col])

    return result


def fetch_food_kcal_per_capita():
    """
    Fetch daily calorie supply per person (kcal/cap/day) from FAO via OWID.
    This is Herrington's food per capita proxy.
    """
    url = ("https://ourworldindata.org/grapher/daily-per-capita-caloric-supply"
           ".csv?v=1&csvType=full&useColumnShortNames=false")
    print("  Fetching FAO food supply (kcal/cap/day) via OWID...")
    try:
        data = _fetch_owid_csv(url, entity="World")
        if data:
            print(f"    Got {len(data)} years ({min(data.keys())}-{max(data.keys())})")
        else:
            print("    WARNING: No World-level data found, trying country average...")
            # OWID may not have a "World" row — fall back to computing from
            # the full dataset (not implemented here; would need population weighting)
            print("    WARNING: No food kcal data returned")
        return data
    except requests.RequestException as exc:
        print(f"    ERROR: {exc}")
        return {}


def fetch_plastic_production():
    """
    Fetch global plastic production (tonnes/year) from OWID.
    Used as part of the composite pollution proxy (Herrington 2021).
    """
    url = ("https://ourworldindata.org/grapher/global-plastics-production"
           ".csv?v=1&csvType=full&useColumnShortNames=false")
    print("  Fetching global plastic production via OWID...")
    try:
        data = _fetch_owid_csv(url, entity="World")
        if data:
            print(f"    Got {len(data)} years ({min(data.keys())}-{max(data.keys())})")
        else:
            print("    WARNING: No plastic production data returned")
        return data
    except requests.RequestException as exc:
        print(f"    ERROR: {exc}")
        return {}


def fetch_mean_years_schooling():
    """
    Fetch mean years of schooling from UNDP via OWID.
    Better services per capita proxy than life expectancy (no biological ceiling).
    """
    url = ("https://ourworldindata.org/grapher/mean-years-of-schooling-long-run"
           ".csv?v=1&csvType=full&useColumnShortNames=false")
    print("  Fetching mean years of schooling via OWID...")
    try:
        data = _fetch_owid_csv(url, entity="World")
        if data:
            print(f"    Got {len(data)} years ({min(data.keys())}-{max(data.keys())})")
        else:
            print("    WARNING: No schooling data returned")
        return data
    except requests.RequestException as exc:
        print(f"    ERROR: {exc}")
        return {}


# ── Pollution Composite ──────────────────────────────────────────────────────

def compute_pollution_composite(df):
    """
    Create a composite pollution index from CO2 ppm and plastic production,
    following Herrington (2021). Both are normalized to 1970=1.0, then averaged.
    This better approximates World3's ppol than CO2 alone.
    """
    if "co2_ppm" not in df.columns or "plastic_production" not in df.columns:
        return

    # Normalize each to 1970 = 1.0
    co2_1970 = df.loc[df["year"] == 1970, "co2_ppm"]
    plastic_1970 = df.loc[df["year"] == 1970, "plastic_production"]

    if len(co2_1970) == 0 or pd.isna(co2_1970.values[0]):
        return
    co2_base = co2_1970.values[0]

    if len(plastic_1970) == 0 or pd.isna(plastic_1970.values[0]):
        # Use earliest available plastic data as base
        valid_plastic = df.dropna(subset=["plastic_production"])
        if valid_plastic.empty:
            return
        plastic_base = valid_plastic["plastic_production"].values[0]
    else:
        plastic_base = plastic_1970.values[0]

    if co2_base == 0 or plastic_base == 0:
        return

    co2_norm = df["co2_ppm"] / co2_base

    # Forward-fill plastic production for years after the last data point.
    # Plastic data ends at 2019; real production has likely grown since,
    # so carrying 2019 forward is conservative (underestimates).
    plastic_filled = df["plastic_production"].ffill()
    plastic_norm = plastic_filled / plastic_base

    # Average the two normalized series where at least CO2 exists
    # (plastic is forward-filled so it won't gap out).
    has_co2 = co2_norm.notna()
    has_plastic = plastic_norm.notna()
    both = has_co2 & has_plastic
    df["pollution_composite"] = np.where(
        both, (co2_norm + plastic_norm) / 2,
        np.where(has_co2, co2_norm, np.nan),
    )

    print("  Computed pollution_composite (CO2 + plastic, normalized avg)")


# ── Cache Utilities ──────────────────────────────────────────────────────────

def utc_now_iso():
    """Return a stable UTC timestamp for cache metadata."""
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def load_cached_real_data():
    """Load cached real-world data and metadata if present."""
    if not REAL_DATA_CSV.exists():
        return None, None

    df = pd.read_csv(REAL_DATA_CSV)
    metadata = None
    if REAL_DATA_METADATA.exists():
        metadata = json.loads(REAL_DATA_METADATA.read_text())
    return df, metadata


def save_real_data_cache(df, metadata):
    """Persist fetched data and metadata to the local cache."""
    df.to_csv(REAL_DATA_CSV, index=False)
    REAL_DATA_METADATA.write_text(json.dumps(metadata, indent=2, sort_keys=True))


# ── Combine Everything ────────────────────────────────────────────────────────

def fetch_all_real_data():
    """Fetch all real-world data and save as CSV."""
    cached_df, cached_metadata = load_cached_real_data()
    used_cache = False

    # World Bank
    print("Fetching World Bank data...")
    wb_df = fetch_all_world_bank()

    # NOAA CO2
    print("\nFetching NOAA CO2 data...")
    try:
        co2_data = fetch_noaa_co2()
    except requests.RequestException as exc:
        print(f"  ERROR: {exc}")
        co2_data = {}
    co2_df = pd.DataFrame(list(co2_data.items()), columns=["year", "co2_ppm"])

    # OWID: Food (kcal/cap/day)
    print("\nFetching OWID data...")
    food_data = fetch_food_kcal_per_capita()
    food_df = pd.DataFrame(list(food_data.items()), columns=["year", "food_kcal_per_capita"])

    # OWID: Plastic production
    plastic_data = fetch_plastic_production()
    plastic_df = pd.DataFrame(list(plastic_data.items()), columns=["year", "plastic_production"])

    # OWID: Mean years of schooling
    schooling_data = fetch_mean_years_schooling()
    schooling_df = pd.DataFrame(list(schooling_data.items()), columns=["year", "mean_years_schooling"])

    # Merge all sources
    all_dfs = [wb_df, co2_df, food_df, plastic_df, schooling_df]
    non_empty = [d for d in all_dfs if not d.empty]

    if not non_empty:
        if cached_df is not None:
            print("Using cached dataset — all live sources unavailable.")
            return cached_df
        raise RuntimeError("No real-world data could be fetched from any source.")

    df = non_empty[0]
    for other in non_empty[1:]:
        df = df.merge(other, on="year", how="outer")
    df = df.sort_values("year").reset_index(drop=True)

    if cached_df is not None:
        # Merge with cache, preferring fresh data
        df = df.combine_first(
            cached_df.set_index("year").reindex(df["year"]).reset_index()
        ).sort_values("year").reset_index(drop=True)

    # Compute pollution composite
    compute_pollution_composite(df)

    # Save
    source_status = lambda d: "ok" if not d.empty else "unavailable"
    metadata = {
        "cached_at_utc": utc_now_iso(),
        "validated_variables": VALIDATED_VARIABLES,
        "used_cached_rows": used_cache,
        "sources": {
            "world_bank": {"status": source_status(wb_df), "rows": len(wb_df)},
            "noaa_co2": {"status": source_status(co2_df), "rows": len(co2_df)},
            "owid_food_kcal": {"status": source_status(food_df), "rows": len(food_df)},
            "owid_plastic": {"status": source_status(plastic_df), "rows": len(plastic_df)},
            "owid_schooling": {"status": source_status(schooling_df), "rows": len(schooling_df)},
        },
    }
    if cached_metadata is not None:
        metadata["previous_cache"] = cached_metadata.get("cached_at_utc")

    save_real_data_cache(df, metadata)
    print(f"\nSaved: {REAL_DATA_CSV} ({len(df)} rows, {len(df.columns)} columns)")
    print(f"Saved: {REAL_DATA_METADATA}")

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
    try:
        df = fetch_all_real_data()
    except RuntimeError as exc:
        print(f"\nERROR: {exc}")
        raise SystemExit(1)

    _, metadata = load_cached_real_data()
    if metadata is not None:
        print(f"\nValidated variables: {', '.join(metadata.get('validated_variables', [])) or 'none'}")

    print(f"\nLatest values:")
    latest = df.dropna(subset=["population"]).iloc[-1]
    print(f"  Year: {int(latest['year'])}")
    if pd.notna(latest.get("population")):
        print(f"  Population: {latest['population']/1e9:.2f} billion")
    if pd.notna(latest.get("gdp_per_capita")):
        print(f"  GDP/capita: ${latest['gdp_per_capita']:,.0f}")
    if pd.notna(latest.get("food_kcal_per_capita")):
        print(f"  Food supply: {latest['food_kcal_per_capita']:.0f} kcal/cap/day")
    if pd.notna(latest.get("mean_years_schooling")):
        print(f"  Mean years schooling: {latest['mean_years_schooling']:.1f}")

    co2_latest = df.dropna(subset=["co2_ppm"])
    if not co2_latest.empty:
        row = co2_latest.iloc[-1]
        print(f"  CO2: {row['co2_ppm']:.1f} ppm ({int(row['year'])})")
    plastic_latest = df.dropna(subset=["plastic_production"])
    if not plastic_latest.empty:
        row = plastic_latest.iloc[-1]
        print(f"  Plastic: {row['plastic_production']/1e6:.0f}M tonnes ({int(row['year'])})")
