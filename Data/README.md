# Data README: Sunspot detection with ML

## Purpose
Records what data this project uses, where it came from, how it is split,
and why. Update it whenever a decision changes.

## Folder map
- `Raw/HMI/`               downloaded HMI FITS files (never edited)
- `Reference/Debrecen/`    Debrecen HMIDD catalogue tables
- `Reference/NOAA/`        NOAA Solar Region Summary tables
- `Processed/`             anything produced by my own code

## Primary images
- JSOC series `hmi.Ic_720s` (HMI continuum intensity), full disk
  4096x4096, 0.504 arcsec/pixel, one image per 12 minutes.

## Time split (v2 draft)
| Split      | Months                              |
|------------|-------------------------------------|
| Train      | 2012-03 to 2012-06; 2013-06 to 2013-09 |
| Validation | 2013-01 to 2013-03                  |
| Test       | 2014-02; 2014-06                    |
| Case study | 2014-10 (AR 12192)                  |

### Why split by time
HMI images 12 minutes apart are almost identical. Putting neighbours in
different splits would leak the test answer into training and inflate
the Dice score silently.

### Why gaps between splits
Sunspot groups survive several solar rotations (about 27 days). Leaving
at least 2 to 3 months between splits stops the same region appearing
on both sides.

### Why these months
- Test months fall inside Debrecen HMIDD hourly coverage (2010-2014), so
  I can compare against a reference.
- Training months do not need a reference, only my own pipeline masks,
  so they can be extended later (including after 2014) if the data
  scaling check shows more data helps.
- AR 12192 is held out as a standalone extreme case.

### Rules
- The test set is used only for the final evaluation, never for tuning.
- A hand-corrected test subset (15 to 30 masks) is kept separate.

## Sampling rule
TO DECIDE in Stage 4 (current idea: one image per day at a fixed time).

## Reference data and required citations
- Debrecen HMIDD (SDO/HMI Debrecen Sunspot Data). If used, cite:
  - Baranyi, Gyori & Ludmany (2016), Solar Physics 291, 3081-3102,
    DOI 10.1007/s11207-016-0930-1
  - Gyori, Ludmany & Baranyi (2017), MNRAS 465(2), 1259-1273,
    DOI 10.1093/mnras/stw2667
- NOAA SWPC Solar Region Summary (SRS): daily; classes can be slightly
  stale near class transitions.
- Note: HMIDD is itself an automatic algorithm, so it is a reference,
  not ground truth.

## Decision log
- v1: initial draft (train 2012-03 to 06, val 2013-03, test 2014-02)
- v2: widened train/val/test after realising the Debrecen date limit
  applies only to evaluation, not training