"""Project folders. Import these names instead of typing paths by hand.

Src/ sits directly inside the project folder, so the project root is one
level above this file. Python paths are case-sensitive.
"""
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
assert ROOT.name == "Sunspot detection with ML", f"Wrong project root: {ROOT}"

DATA      = ROOT / "Data"
RAW_HMI   = DATA / "Raw" / "HMI"
REF_DEB   = DATA / "Reference" / "Debrecen"
REF_NOAA  = DATA / "Reference" / "NOAA"
PROCESSED = DATA / "Processed"

for _folder in [RAW_HMI, REF_DEB, REF_NOAA, PROCESSED]:
    _folder.mkdir(parents=True, exist_ok=True)
