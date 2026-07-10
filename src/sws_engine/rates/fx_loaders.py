"""ECB/BNR FX loaders: official reference rates -> curated FX rows (P2.3).

Completes the P1.5 plan item: until now the curated FX file was populated by
one manual session; refreshing it meant hand-editing CSV rows. This module
parses the two official sources per the plan (ECB euro foreign exchange
reference rates; BNR reference rates for RON) and emits rows in the
established curated format with the full review lifecycle.

Provenance semantics (unchanged doctrine):
- pairs read directly from an official publication are exact / E0
  (EURUSD, EURRON from ECB; USDRON, EURRON from BNR — BNR quotes RON per
  unit of foreign currency, so USDRON is a DIRECT official rate there);
- pairs derived as crosses (e.g. USDRON from ECB EURRON/EURUSD) are
  approximation / E1 and say so in their note;
- every generated row carries review_status=operator_review_required —
  the operator approves before the registry status may claim real_curated
  freshness (stop condition 7);
- BNR is the preferred primary for RON pairs per the plan; when both
  sources are supplied, BNR wins RON pairs and ECB wins the rest. The two
  sources are also cross-checked: a divergence above the tolerance on a
  common pair is reported as a warning (seed data for the conflict
  detector), never silently averaged.

Live fetching is optional and stdlib-only (mirrors the SEC adapter): the
official endpoints are public, but tests are fixture-first and never touch
the network.
"""
from __future__ import annotations

import csv
import urllib.request
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Any

ECB_DAILY_URL = "https://www.ecb.europa.eu/stats/eurofxref/eurofxref-daily.xml"
BNR_DAILY_URL = "https://www.bnr.ro/nbrfxrates.xml"
CROSS_TOLERANCE = 0.005  # 0.5% divergence between ECB-derived and BNR direct

CURATED_FX_COLUMNS = [
    "pair", "date", "rate", "source", "source_id", "source_tier",
    "source_quality", "source_class", "source_as_of", "review_status",
    "source_url_reference", "note",
]


def parse_ecb_eurofxref_xml(xml_text: str) -> dict[str, Any]:
    """Parse the ECB daily reference XML -> {"date", "base": "EUR", "rates"}."""
    root = ET.fromstring(xml_text)
    ns = {"e": "http://www.ecb.int/vocabulary/2002-08-01/eurofxref"}
    day = root.find(".//e:Cube/e:Cube[@time]", ns)
    if day is None:
        raise ValueError("ECB XML: no dated Cube element found")
    rates: dict[str, float] = {}
    for cube in day.findall("e:Cube", ns):
        currency = cube.get("currency")
        rate = cube.get("rate")
        if currency and rate:
            rates[currency.upper()] = float(rate)
    return {"date": day.get("time"), "base": "EUR", "rates": rates}


def parse_bnr_nbrfxrates_xml(xml_text: str) -> dict[str, Any]:
    """Parse the BNR daily XML -> {"date", "base": "RON", "rates"}.

    BNR quotes RON per unit of foreign currency; a ``multiplier`` attribute
    (e.g. HUF per 100) is normalized to per-unit.
    """
    root = ET.fromstring(xml_text)
    ns = {"b": "http://www.bnr.ro/xsd"}
    cube = root.find(".//b:Body/b:Cube[@date]", ns)
    if cube is None:
        raise ValueError("BNR XML: no dated Cube element found")
    rates: dict[str, float] = {}
    for node in cube.findall("b:Rate", ns):
        currency = node.get("currency")
        if not currency or node.text in (None, ""):
            continue
        multiplier = float(node.get("multiplier") or 1)
        rates[currency.upper()] = float(node.text) / multiplier
    return {"date": cube.get("date"), "base": "RON", "rates": rates}


def fetch_ecb_daily_live(*, timeout: int = 30) -> str:
    with urllib.request.urlopen(ECB_DAILY_URL, timeout=timeout) as resp:  # nosec - official public endpoint
        return resp.read().decode("utf-8")


def fetch_bnr_daily_live(*, timeout: int = 30) -> str:
    with urllib.request.urlopen(BNR_DAILY_URL, timeout=timeout) as resp:  # nosec - official public endpoint
        return resp.read().decode("utf-8")


def _row(pair: str, date: str, rate: float, *, source: str, quality: str,
         source_class: str, url: str, note: str, fetched_as_of: str) -> dict[str, str]:
    return {
        "pair": pair, "date": date, "rate": f"{rate:.6f}".rstrip("0").rstrip("."),
        "source": source, "source_id": source,
        "source_tier": "curated", "source_quality": quality,
        "source_class": source_class, "source_as_of": fetched_as_of,
        "review_status": "operator_review_required",
        "source_url_reference": url, "note": note,
    }


def build_fx_curated_rows(
    *,
    ecb: dict[str, Any] | None = None,
    bnr: dict[str, Any] | None = None,
    pairs: list[str] | None = None,
    fetched_as_of: str,
    cross_tolerance: float = CROSS_TOLERANCE,
) -> dict[str, Any]:
    """Build curated FX rows for the requested pairs from official parses.

    Returns {"rows", "warnings", "skipped"}. Unresolvable pairs are skipped
    with a warning (honest MISSING), never estimated.
    """
    wanted = [p.upper() for p in (pairs or ["EURUSD", "EURRON", "USDRON"])]
    rows: list[dict[str, str]] = []
    warnings: list[str] = []
    skipped: list[str] = []
    ecb_rates = (ecb or {}).get("rates") or {}
    bnr_rates = (bnr or {}).get("rates") or {}

    def ecb_direct(quote: str) -> float | None:
        return ecb_rates.get(quote)

    for pair in wanted:
        base, quote = pair[:3], pair[3:]
        made = False
        # 1. BNR direct for RON-quoted pairs (preferred RON primary per plan)
        if bnr and quote == "RON" and base in bnr_rates:
            rows.append(_row(pair, bnr["date"], bnr_rates[base],
                             source="BNR_reference_rate", quality="exact", source_class="E0",
                             url=BNR_DAILY_URL,
                             note=f"BNR daily reference rate ({base} in RON), official publication.",
                             fetched_as_of=fetched_as_of))
            made = True
            # cross-check vs ECB-derived when possible
            if ecb and base != "EUR" and ecb_direct("RON") and ecb_direct(base):
                derived = ecb_rates["RON"] / ecb_rates[base]
                rel = abs(derived - bnr_rates[base]) / max(bnr_rates[base], 1e-12)
                if rel > cross_tolerance:
                    warnings.append(
                        f"FX_SOURCE_DIVERGENCE: {pair} BNR direct {bnr_rates[base]:.4f} vs "
                        f"ECB-derived cross {derived:.4f} ({rel:.2%} > {cross_tolerance:.2%}); "
                        "BNR direct kept per RON-primary rule, divergence left visible")
        # 2. ECB direct for EUR-based pairs
        if not made and ecb and base == "EUR" and ecb_direct(quote) is not None:
            rows.append(_row(pair, ecb["date"], ecb_rates[quote],
                             source="ECB_reference_rate", quality="exact", source_class="E0",
                             url=ECB_DAILY_URL,
                             note=f"ECB euro foreign exchange reference rate (EUR{quote}), official publication.",
                             fetched_as_of=fetched_as_of))
            made = True
        # 3. ECB cross for non-EUR pairs (approximation/E1, honestly labeled)
        if not made and ecb and base != "EUR" and quote != "EUR" \
                and ecb_direct(base) is not None and ecb_direct(quote) is not None:
            derived = ecb_rates[quote] / ecb_rates[base]
            rows.append(_row(pair, ecb["date"], derived,
                             source="ECB_cross_derived", quality="approximation", source_class="E1",
                             url=ECB_DAILY_URL,
                             note=f"Derived cross EUR{quote}/EUR{base} from ECB reference rates of the "
                                  "same date; not a directly published pair, marked approximation/E1.",
                             fetched_as_of=fetched_as_of))
            made = True
        if not made:
            skipped.append(pair)
            warnings.append(
                f"FX_PAIR_UNRESOLVABLE: {pair} cannot be built from the supplied official "
                "parses; the pair stays MISSING rather than estimated")
    return {"rows": rows, "warnings": warnings, "skipped": skipped}


def write_fx_curated_csv(rows: list[dict[str, str]], output_path: str | Path) -> str:
    out = Path(output_path)
    out.parent.mkdir(parents=True, exist_ok=True)
    with out.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=CURATED_FX_COLUMNS)
        writer.writeheader()
        writer.writerows(rows)
    return str(out)
