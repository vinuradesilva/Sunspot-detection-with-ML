"""Loader for the Debrecen HMIDD catalogue (SDO/HMI Debrecen Sunspot Data).

Column meanings are in HMIDDformat.txt on the Debrecen site. Citations required
if the data are used: Baranyi, Gyori & Ludmany (2016), Solar Physics 291, 3081;
Gyori, Ludmany & Baranyi (2017), MNRAS 465, 1259.
"""
import io

import numpy as np
import pandas as pd

from paths import REF_DEB

# Names for the 20 whitespace-separated values on every row
COLS = ["code", "year", "month", "day", "hour", "minute", "second", "grp", "n",
        "c10", "c11", "c12", "c13", "c14", "c15", "c16", "c17", "c18", "c19", "c20"]


def load_hmidd(year, verbose=True):
    """Read HMIDD<year>.txt and return two tables: (h, g).

    h: one row per image (whole-disc summary: number of groups, summed areas, P, B0, L0).
    g: one row per sunspot group per image (NOAA number as TEXT, areas, position).
    Spot ('s') rows are skipped: they are 93% of the file and not needed yet.
    999999 (missing) becomes NaN. Areas: 'proj_*' are in millionths of the DISC,
    'corr_*' in millionths of the HEMISPHERE.
    """
    src = REF_DEB / f"HMIDD{year}.txt"

    keep, n_bad_rows = [], 0
    with open(src) as fh:
        for line in fh:
            if line[0] in "hg":
                if len(line.split()) != 20:
                    n_bad_rows += 1
                keep.append(line)
    if verbose:
        print(f"{src.name}: kept {len(keep)} h/g rows | malformed: {n_bad_rows}")
    if n_bad_rows > 0:
        raise ValueError(f"{n_bad_rows} rows in {src.name} do not have 20 values")

    df = pd.read_csv(io.StringIO("".join(keep)), sep=r"\s+", header=None,
                     names=COLS, dtype={"code": str, "grp": str})
    df = df.replace(999999, np.nan)
    df["time"] = (pd.to_datetime(df[["year", "month", "day", "hour", "minute"]])
                  + pd.to_timedelta(df["second"], unit="s"))

    h = df[df["code"] == "h"].rename(columns={
        "n": "n_groups", "c10": "proj_U", "c11": "proj_UP", "c12": "corr_U",
        "c13": "corr_UP", "c14": "jd", "c15": "P", "c16": "B0", "c17": "L0"})
    h = h[["time", "n_groups", "proj_U", "proj_UP", "corr_U", "corr_UP",
           "jd", "P", "B0", "L0"]]

    g = df[df["code"] == "g"].rename(columns={
        "grp": "noaa", "n": "n_spots", "c10": "proj_U", "c11": "proj_UP",
        "c12": "corr_U", "c13": "corr_UP", "c14": "lat", "c15": "lon",
        "c16": "lcm", "c18": "r"})
    g = g[["time", "noaa", "n_spots", "proj_U", "proj_UP", "corr_U", "corr_UP",
           "lat", "lon", "lcm", "r"]]

    # Safety check: the full-disk file (fdHMIDD) has ONE pseudo-group per hour,
    # labelled with the year. Real group numbers give many distinct labels.
    if g["noaa"].nunique() <= 1:
        raise ValueError(f"Only one group label in {src.name}: is this the full-disk file?")

    if verbose:
        print(f"h rows: {len(h)} | g rows: {len(g)} | distinct group labels: {g['noaa'].nunique()}")
    return h, g
