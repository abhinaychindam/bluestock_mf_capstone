"""
live_nav_fetch.py — Fetch live NAV from mfapi.in
Bluestock Mutual Fund Capstone Project

Fetches NAV for 5 key bluechip schemes + HDFC Top 100 Direct.
Saves raw JSON responses and consolidated CSV.

Usage:
    python scripts/live_nav_fetch.py
    python scripts/live_nav_fetch.py --scheme 125497   # single scheme
    python scripts/live_nav_fetch.py --latest-only     # only today's NAV
"""

import argparse
import json
import logging
import sys
import time
from datetime import date
from pathlib import Path

import pandas as pd
import requests

# ── Config ───────────────────────────────────────────────────────────────────
BASE = Path(__file__).resolve().parent.parent
RAW  = BASE / "data" / "raw"
RAW.mkdir(parents=True, exist_ok=True)

MFAPI_BASE = "https://api.mfapi.in/mf"

# Key schemes: amfi_code → friendly name
SCHEMES = {
    125497: "HDFC Top 100 Direct Growth",
    119551: "SBI Bluechip Direct Growth",
    120503: "ICICI Pru Bluechip Direct Growth",
    118632: "Nippon India Large Cap Direct Growth",
    119092: "Axis Bluechip Direct Growth",
    120841: "Kotak Bluechip Direct Growth",
}

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)
log = logging.getLogger(__name__)


# ── Fetch helpers ─────────────────────────────────────────────────────────────

def fetch_scheme(amfi_code: int, retries: int = 3, backoff: float = 2.0) -> dict:
    """
    GET https://api.mfapi.in/mf/{amfi_code}
    Returns parsed JSON dict. Raises on persistent failure.
    """
    url = f"{MFAPI_BASE}/{amfi_code}"
    for attempt in range(1, retries + 1):
        try:
            resp = requests.get(url, timeout=15, headers={"User-Agent": "BluestockMFCapstone/1.0"})
            resp.raise_for_status()
            data = resp.json()
            log.info("✓ Fetched %s (%s)  —  %d NAV records",
                     amfi_code, data["meta"].get("scheme_name", "?"), len(data["data"]))
            return data
        except requests.exceptions.HTTPError as exc:
            log.warning("HTTP %s for %s (attempt %d/%d)", exc.response.status_code, amfi_code, attempt, retries)
        except requests.exceptions.ConnectionError:
            log.warning("Connection error for %s (attempt %d/%d)", amfi_code, attempt, retries)
        except requests.exceptions.Timeout:
            log.warning("Timeout for %s (attempt %d/%d)", amfi_code, attempt, retries)
        except ValueError as exc:
            log.error("JSON decode error for %s: %s", amfi_code, exc)
            break

        if attempt < retries:
            time.sleep(backoff * attempt)

    raise RuntimeError(f"Failed to fetch NAV for AMFI code {amfi_code} after {retries} attempts")


def save_raw_json(amfi_code: int, data: dict) -> Path:
    """Save raw API response JSON for audit trail."""
    path = RAW / f"live_nav_{amfi_code}.json"
    with open(path, "w") as f:
        json.dump(data, f, indent=2)
    log.info("  Saved raw JSON → %s", path.name)
    return path


def parse_nav_records(amfi_code: int, data: dict, latest_only: bool = False) -> pd.DataFrame:
    """
    Parse mfapi.in response into a tidy DataFrame.

    mfapi.in JSON structure:
    {
      "meta": { "scheme_code": ..., "scheme_name": ..., "fund_house": ..., ... },
      "data": [ {"date": "DD-MMM-YYYY", "nav": "123.4567"}, ... ]
    }
    """
    meta = data.get("meta", {})
    records = data.get("data", [])

    if latest_only:
        records = records[:1]   # API returns latest first

    df = pd.DataFrame(records)
    if df.empty:
        log.warning("No NAV records for scheme %s", amfi_code)
        return df
    
    df["nav_date"] = pd.to_datetime(
                    df["date"],
                    format="mixed",
                    dayfirst=True,
                    errors="coerce"
                        )
    df["nav"]      = pd.to_numeric(df["nav"], errors="coerce")
    df.drop(columns=["date"], inplace=True)

    # Attach metadata columns
    df["amfi_code"]   = amfi_code
    df["scheme_name"] = meta.get("scheme_name", "")
    df["fund_house"]  = meta.get("fund_house",  "")
    df["scheme_type"] = meta.get("scheme_type", "")
    df["scheme_category"] = meta.get("scheme_category", "")

    # Sort chronologically (API sends newest-first)
    df.sort_values("nav_date", inplace=True)
    df.reset_index(drop=True, inplace=True)

    return df[["amfi_code", "scheme_name", "fund_house", "nav_date", "nav", "scheme_type", "scheme_category"]]


# ── Main ──────────────────────────────────────────────────────────────────────

def fetch_all_schemes(codes: dict[int, str], latest_only: bool = False) -> pd.DataFrame:
    """Fetch all schemes and return combined DataFrame."""
    all_dfs = []
    failed  = []

    for code, label in codes.items():
        log.info("Fetching: [%s] %s", code, label)
        try:
            raw_data = fetch_scheme(code)
            save_raw_json(code, raw_data)
            df = parse_nav_records(code, raw_data, latest_only=latest_only)
            if not df.empty:
                all_dfs.append(df)
        except RuntimeError as exc:
            log.error("FAILED %s — %s", code, exc)
            failed.append(code)
        time.sleep(0.3)   # polite rate limiting

    if failed:
        log.warning("Could not fetch %d scheme(s): %s", len(failed), failed)

    if not all_dfs:
        log.error("No data fetched. Check internet connection or AMFI codes.")
        return pd.DataFrame()

    combined = pd.concat(all_dfs, ignore_index=True)
    return combined


def main() -> None:
    parser = argparse.ArgumentParser(description="Fetch live NAV from mfapi.in")
    parser.add_argument("--scheme", type=int, help="Fetch single AMFI scheme code")
    parser.add_argument("--latest-only", action="store_true",
                        help="Fetch only the latest NAV (not full history)")
    args = parser.parse_args()

    codes = SCHEMES
    if args.scheme:
        if args.scheme not in SCHEMES:
            log.warning("Code %s not in default list — fetching anyway", args.scheme)
        codes = {args.scheme: f"Scheme {args.scheme}"}

    log.info("=" * 60)
    log.info("Live NAV Fetch — %s", date.today())
    log.info("Schemes to fetch: %d", len(codes))
    log.info("=" * 60)

    nav_df = fetch_all_schemes(codes, latest_only=args.latest_only)

    if nav_df.empty:
        sys.exit(1)

    # Save consolidated CSV
    suffix = "_latest" if args.latest_only else "_history"
    out_path = RAW / f"live_nav_all{suffix}.csv"
    nav_df.to_csv(out_path, index=False)
    log.info("Saved → %s  (%d rows)", out_path.name, len(nav_df))

    # Print summary
    print("\n" + "═"*70)
    print("  LIVE NAV FETCH SUMMARY")
    print("═"*70)
    summary = (
        nav_df.groupby(["amfi_code", "scheme_name"])
        .agg(
            records=("nav", "count"),
            latest_date=("nav_date", "max"),
            latest_nav=("nav", "last"),
        )
        .reset_index()
    )
    print(summary.to_string(index=False))
    print("═"*70)
    log.info("Live NAV fetch complete.")


if __name__ == "__main__":
    main()
