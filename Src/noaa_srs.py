"""NOAA Solar Region Summary (SRS): build addresses, download, parse.

One text file per day, issued 00:30 UTC, describing 24:00Z of the previous day.
The archive's robots.txt asks for a 60-second pause between automated requests.
"""
import re
import time

import pandas as pd
import requests

from paths import REF_NOAA

BASE = "https://www.ngdc.noaa.gov/stp/space-weather/swpc-products/daily_reports/solar_region_summaries"


def srs_url(date):
    """Address of the SRS file issued on `date` (a pandas Timestamp)."""
    year = date.strftime("%Y")
    month = date.strftime("%m")
    stamp = date.strftime("%Y%m%d")
    return f"{BASE}/{year}/{month}/{stamp}SRS.txt"


def download_srs(days, pause=60):
    """Download the SRS file for each day into REF_NOAA, politely.

    Skips files already on disk (no request, no pause). Saves a file only if the
    status is 200 AND the text contains "Solar Region Summary". Waits `pause`
    seconds after every real request. Returns the list of days that failed.
    """
    saved, skipped, failed = [], [], []
    for day in days:
        url = srs_url(day)
        path = REF_NOAA / url.split("/")[-1]      # file name = last part of the address

        if path.exists():                         # already downloaded?
            skipped.append(day.date())
            continue

        try:
            r = requests.get(url, timeout=30)
            got_file = (r.status_code == 200) and ("Solar Region Summary" in r.text)
        except requests.RequestException as e:
            got_file = False
            print("request problem:", day.date(), e)

        if got_file:
            path.write_text(r.text)
            saved.append(day.date())
        else:
            failed.append(day.date())

        print(day.date(), "ok" if got_file else "FAILED")
        time.sleep(pause)

    print(f"saved {len(saved)} | skipped {len(skipped)} | failed {len(failed)}")
    return failed


def read_srs(path, verbose=False):
    """Parse one SRS file into a table of regions with spots (Part I of the report).

    'valid' is 00:00 of the file's issue date (the report describes 24:00Z of the
    previous day). 'noaa' is the region number + 10000 as TEXT, to match Debrecen
    (NOAA prints 2192, Debrecen writes 12192). 'area' is in millionths of the
    hemisphere, rounded to the nearest 10; 0 means too small to measure.
    """
    with open(path) as fh:
        lines = fh.readlines()
    issued = next(l for l in lines if l.startswith(":Issued:"))
    issued = pd.to_datetime(issued.split(":Issued:")[1].replace("UTC", "").strip(),
                            format="%Y %b %d %H%M")
    valid = issued.normalize()

    rows, short, on = [], 0, False
    for l in lines:
        if l.startswith("I.  Regions with Sunspots"):
            on = True
            continue
        if on and (l.startswith("IA.") or l.startswith("II.")):
            break
        if on and re.match(r"^\d{4}\s", l):
            p = l.split()
            if len(p) != 8:
                short += 1
            rows.append((p + [None] * 8)[:8])
    d = pd.DataFrame(rows, columns=["nmbr", "location", "lo", "area", "z", "ll", "nn", "mag"])
    for c in ["area", "ll", "nn"]:
        d[c] = pd.to_numeric(d[c])
    d["noaa"] = (d["nmbr"].astype(int) + 10000).astype(str)
    d["valid"] = valid
    if verbose:
        print(f"{path.name}: {len(d)} regions, valid {valid}, rows without 8 fields: {short}")
    return d


def load_srs_folder():
    """Parse every *SRS.txt file in REF_NOAA and stack them into one table."""
    tables = [read_srs(f) for f in sorted(REF_NOAA.glob("*SRS.txt"))]
    return pd.concat(tables, ignore_index=True)
