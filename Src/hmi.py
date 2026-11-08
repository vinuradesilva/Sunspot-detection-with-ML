"""Small helpers for HMI continuum images from JSOC (series hmi.ic_720s)."""
import numpy as np


def hex_to_int(s):
    """Turn JSOC's hex text (e.g. '0x00010400') into a number; anything else becomes NaN.

    drms 0.9.0 converts QUALITY to NaN by default (and NaN == 0 is False), so query
    with skip_conversion=["QUALITY"] and convert here. QUALITY == 0 means no known issue.
    """
    if isinstance(s, str) and s.startswith("0x"):
        return int(s, 16)
    return np.nan


def fits_name(t_rec):
    """File name JSOC gives an exported image, from its T_REC string.

    '2014.10.23_00:00:00_TAI' -> 'hmi.ic_720s.20141023_000000_TAI.1.continuum.fits'
    """
    stamp = t_rec.replace(".", "").replace(":", "")
    return f"hmi.ic_720s.{stamp}.1.continuum.fits"
