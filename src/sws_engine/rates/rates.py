"""Rates layer (Phase 3.4): 10Y government bond 5-year average per country,
curated ERP table, EOD FX table. All inputs are versioned CSV/JSON files;
this phase ships SYNTHETIC curated files for construction purposes."""
import csv
import json
from statistics import mean


def bond_10y_5y_average(csv_path: str, country: str, as_of: str) -> dict:
    """CSV columns: country,date,yield_10y (decimal). Uses observations in
    the 5 years up to as_of."""
    obs = []
    with open(csv_path, newline="", encoding="utf-8") as fh:
        for row in csv.DictReader(fh):
            if row["country"] != country:
                continue
            if row["date"] <= as_of and row["date"] >= _minus_years(as_of, 5):
                obs.append(float(row["yield_10y"]))
    if not obs:
        return {"value": None, "observations": 0}
    return {"value": mean(obs), "observations": len(obs),
            "country": country, "as_of": as_of,
            "definition": "mean of 10Y government bond yields, 5y window"}


def _minus_years(iso_date: str, years: int) -> str:
    y, rest = iso_date[:4], iso_date[4:]
    return f"{int(y) - years}{rest}"


def load_erp(path: str, country: str) -> dict:
    with open(path, "r", encoding="utf-8") as fh:
        table = json.load(fh)
    entry = table.get("countries", {}).get(country)
    if entry is None:
        return {"value": None}
    return {"value": entry["erp"], "as_of": table.get("as_of"),
            "source": table.get("source"), "country": country}


def fx_rate(csv_path: str, pair: str, on_date: str):
    """CSV columns: pair,date,rate. Returns EOD rate on the closest date
    <= on_date (standard EOD convention)."""
    best = None
    with open(csv_path, newline="", encoding="utf-8") as fh:
        for row in csv.DictReader(fh):
            if row["pair"] != pair or row["date"] > on_date:
                continue
            if best is None or row["date"] > best[0]:
                best = (row["date"], float(row["rate"]))
    return {"rate": best[1], "as_of": best[0], "pair": pair} if best \
        else {"rate": None, "as_of": None, "pair": pair}
