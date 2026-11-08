# Data README: Sunspot detection with ML

Last updated: end of Step 1 (Data Acquisition). Update this file whenever a
decision changes, and add a line to the decision log at the bottom.

## 1. Folder map and what is in each folder

| Folder | Contents |
|---|---|
| `Raw/HMI/` | 421 HMI continuum FITS files, about 15 MB each, 6.31 GB in total. Never edited. |
| `Reference/Debrecen/` | `HMIDD2014.txt` (used) and `fdHMIDD2014.txt` (not used, see section 4) |
| `Reference/NOAA/` | 89 daily SRS files: Feb 2014, Jun 2014, Oct 2014 |
| `Processed/` | `debrecen_h_2014.csv`, `debrecen_g_2014.csv`, `noaa_srs_test_case.csv`, `hmi_manifest.csv`, `hmi_headers.csv` |

Reloading any CSV: read the group-number columns as text, for example
`pd.read_csv(path, dtype={"noaa": str, "nmbr": str})`. Group numbers can contain
letters (for example `11934m`).

## 2. Time split (v2, split by time, never randomly)

| Split | Months | Images |
|---|---|---|
| Train | 2012-03 to 2012-06; 2013-06 to 2013-09 | 243 |
| Validation | 2013-01 to 2013-03 | 90 |
| Test | 2014-02; 2014-06 | 58 |
| Case study | 2014-10 (AR 12192) | 30 |

Why split by time: HMI images 12 minutes apart are almost identical, so neighbours
in different splits would leak the answer and inflate the Dice score silently.

Why gaps between splits: sunspot groups can survive several solar rotations
(about 27 days), so a gap of several months stops the same region appearing on
both sides.

Rules:
- The test set is used only for the final evaluation, never for tuning.
- A hand-corrected subset of test masks (15 to 30) is kept separate.
- The Debrecen date limit (2010 to 2014 hourly) applies only to evaluation.
  Training months can be extended later, including after 2014.
- During training, validation compares against masks from my own classical
  pipeline, so validation months need no reference table. Reference tables for
  2013 were deliberately not downloaded; add them only if I decide to tune
  thresholds against Debrecen or NOAA.

## 3. HMI images (JSOC series `hmi.ic_720s`)

### Sampling rule (one image per day)
1. Take the 00:00:00 TAI record of the day.
2. Keep it only if QUALITY == 0.
3. If it is flagged, use the nearest QUALITY == 0 record within 30 minutes.
4. If none exists, skip the day.

Result for the 423 days in the plan: 406 first choice, 15 fallback (offsets of
12 or 24 minutes), 2 skipped (2012-06-06 in train, 2014-10-09 in the case study).
That leaves 421 images. The full list is in `Processed/hmi_manifest.csv`.

TAI ran 34 to 35 seconds ahead of UTC in these years, so the 00:00:00 TAI record
is almost exactly 00:00 UT. Debrecen's hourly rows are stamped about 00:00:30,
and NOAA's morning report describes 24:00Z of the previous day, so all three line
up. The time stamps in a FITS header (`T_REC`, `T_OBS`, `DATE-OBS`) differ
slightly; everything is keyed on `T_REC`.

### How the data were obtained
- Queries: `drms` client, no registration needed. Exports need a registered email.
- Export protocol `fits`, so keywords are written into the header (the
  `as-is` protocol would leave them out).
- JSOC allows one pending export at a time. Exports were done in batches of 30.
  One batch of 27 to 30 images took about 8 minutes.
- File names follow `hmi.ic_720s.YYYYMMDD_HHMMSS_TAI.1.continuum.fits`.
- All 421 files were opened and checked: shape 4096 x 4096, `T_REC` matches the
  manifest, QUALITY == 0, no truncated files.

### QUALITY keyword (silent error)
JSOC returns QUALITY as hex text such as `0x00000000`. With `drms` 0.9.0 the
default conversion turned all values into NaN, and `NaN == 0` is False, so a
naive count of good records gave 0. Fix: pass `skip_conversion=["QUALITY"]` and
convert with `int(s, 16)`. On 2014-10-23, 113 of 120 records had QUALITY 0.
What each flag bit means is described on JSOC's wiki page `Lev1qualBits`
(not yet read). Rule used for now: keep only QUALITY == 0.

### Facts from the 421 headers
| Quantity | Value |
|---|---|
| Solar radius in pixels (`RSUN_OBS / CDELT1`) | 1871.6 to 1935.5, mean 1897 |
| Disc centre (`CRPIX1 - 1`, `CRPIX2 - 1`) | x 2032.1 to 2037.8, y 2046.0 to 2053.4 |
| `CROTA2` | 180.013 or 180.014 in every file |
| Pixel scale `CDELT1`, `CDELT2` | 0.504 arcsec/pixel, equal in every file |
| B0 (`CRLT_OBS`) | -7.26 to +7.26 degrees |
| Missing header keywords | none |

Image format: compressed int16 on disk, 4096 x 4096, converted by astropy to
float32 (the Apple GPU cannot use float64).

### What Step 2 must do (do not forget)
1. Read the radius and centre from each file's header. Never hard-code them
   (the radius varies by about 3.4% over the year, about 7% in area).
2. Rotate every image by 180 degrees (lossless). Rotate the centre too:
   after the flip the centre becomes (4095 - cx, 4095 - cy). Forgetting this
   shifts the disc mask by about 24 pixels with no error message.
3. FITS counts pixels from 1, Python from 0: subtract 1 from `CRPIX1`, `CRPIX2`.
4. NaN is not the only "off the Sun" marker. Pixels out to r about 1.047
   (1.1 million pixels in the test image) hold low real values (191 to 15,824),
   not NaN. Never use `np.nanmin`, `np.nanmax` or `np.nanmean` on a whole image.
   Build a disc mask from the header radius and centre.
5. Even just inside r = 1 the values are very low (minimum 2789 on the test
   image, against a limb value of about 27,000 at r = 0.99). Use a smaller disc
   for normalisation statistics; the cut-off is to be chosen in Step 2.
6. Limb darkening is clearly visible (about 39,600 at r = 0.90 down to about
   27,200 at r = 0.99 on the test image). It must be corrected before any
   threshold.

## 4. Debrecen HMIDD (SDO/HMI Debrecen Sunspot Data)

Page: http://fenyi.solarobs.epss.hun-ren.hu/en/databases/SDO/
(not `/SOHO`, which is the older MDI instrument). The site asks automated
programs to stay out, so the files were downloaded by hand.

- Hourly data cover 2010 to 2014. A daily quick-look product covers 2014 to
  2017 and is preliminary and incomplete.
- Tables of measurements, not pixel masks. Compare area, count and position only.
- `HMIDD2014.txt` (283 MB) is whitespace-separated, 20 values on every row.
  Rows: `h` (hour, 8,662), `g` (group, 141,014), `s` (spot, 1,961,470).
- `fdHMIDD2014.txt` holds the same spots without grouping (the group column is
  the year). Not used.
- Projected areas are in millionths of the solar DISC. Corrected areas are in
  millionths of the solar HEMISPHERE.
- Negative area values in `s` rows are pointers ("shares an umbra with spot N").
  Use `g` rows for totals.
- `999999` means missing; converted to NaN.
- Debrecen counts every intensity minimum inside an umbra as a separate spot
  (about 400 "spots" in AR 12192), so spot counts differ from connected-component
  counts by definition. Compare counts at group level.
- No daily summary row (build it from `h` rows) and no radius in pixels.
- Positions are heliographic, not pixels.
- Check: corrected area = projected U+P / (2 cos theta), with
  cos theta = sqrt(1 - r^2) and r the distance from disc centre in solar radii.
  Tested on 19,764 groups (r < 0.6, projected U+P > 50): ratio 0.991, std 0.002.
  The constant 0.9% offset is unexplained.
- Debrecen's processed images are north-up (P is near 0), while raw HMI images
  are upside down (`CROTA2` = 180).
- Required citations: Baranyi, Gyori & Ludmany (2016), Solar Physics 291, 3081,
  DOI 10.1007/s11207-016-0930-1; Gyori, Ludmany & Baranyi (2017), MNRAS 465,
  1259, DOI 10.1093/mnras/stw2667.
- HMIDD is itself an algorithm: a reference, not ground truth.

## 5. NOAA Solar Region Summary (SRS)

Archive: https://www.ngdc.noaa.gov/stp/space-weather/swpc-products/daily_reports/solar_region_summaries/YYYY/MM/YYYYMMDDSRS.txt
The site's robots.txt asks for a 60-second pause between automated requests
(`Crawl-delay: 60`); the `/stp/space-weather/...` folder is not disallowed.

- One file per day, issued 00:30 UTC, describing the previous day: "Locations
  Valid at 23/2400Z" in the file dated the 24th. Valid time = 00:00 of the file date.
- Columns: Nmbr, Location, Lo, Area, Z, LL, NN, Mag Type.
- NOAA region numbers are written with four digits, 10000 lower than Debrecen's.
  Add 10000 (2192 becomes 12192).
- Area is reported to the nearest 10 millionths; an area of 0 means too small to
  measure. Z is the McIntosh class (first letter = Zurich class).
- Classes can be slightly stale near class changes (one update per day).
- 89 files downloaded (Feb, Jun, Oct 2014); all passed a check that the date in
  the file name matches the `:Issued:` date inside.

## 6. NOAA compared with Debrecen (2014 test and case-study months)

- 544 NOAA region rows; 520 matched to a Debrecen group (same region number,
  within 30 minutes).
- The 24 unmatched rows are all on the west side, and 20 of them are 77 degrees
  or more from the central meridian. For these, NOAA's location appears to be
  at or beyond the limb. Not explained for the 4 unmatched rows away from the limb.
- NOAA area / Debrecen area (matched, NOAA area > 0, r < 0.8, 345 rows), by Debrecen group size: 
  under 50: 118 rows, median 0.80 (IQR 0.52 to 1.53); 50 to 100: 41, 0.57; 100 to 200: 65, 0.58; 200 to 500: 82, 0.63; over 500: 39, 0.67. NOAA is about 0.6 of Debrecen for groups of 50 or more, for a reason not yet known. Small groups are unreliable: 7 of the 8 largest ratios have NOAA at 10 and Debrecen at 1 to 3.
- AR 12192 at 2014-10-24 00:00: NOAA area 2740, 58 spots, class Fkc; Debrecen
  corrected U+P 3688, about 407 spots.
- How the references will be used: Debrecen is the main ruler for area and
  position (it measures the same HMI images). NOAA is a coarser check and the
  source of class labels for the MPhil. Compare spot counts at group level only.
- Near the limb cos theta is small, so corrected areas are unreliable in both
  catalogues. Evaluation should exclude or report separately groups beyond a
  chosen r (cut-offs tested: 0.6, 0.8, 0.9, 0.95; to be fixed in Step 5).

## 7. Decision log
- v1: initial draft (train 2012-03 to 06, val 2013-03, test 2014-02).
- v2: widened train, val and test after realising the Debrecen date limit applies
  only to evaluation.
- v3: sampling rule fixed (00:00 TAI, QUALITY 0, fallback within 30 minutes).
  Reference tables for the 2013 validation months not downloaded (not needed
  unless thresholds are tuned against references).

## 8. Open issues
- A first query for 2014-10-23 returned 91 records instead of 120. Later queries
  returned 120. Cause unknown.
- QUALITY bit meanings not read yet (JSOC wiki page `Lev1qualBits`).
- Largest NOAA/Debrecen area ratio (9.9) not yet examined.
- `DATE-OBS` differs from `T_OBS` by about a minute (not explained, not needed).
- NOAA reports an area of 10 for groups Debrecen measures at 1 to 3 (possibly a floor in 
  NOAA's reporting; not tested). One group (12093 on 2014-06-21, NOAA 60 vs Debrecen 15.5) is unexplained.
- Why NOAA's areas are about 40% lower than Debrecen's for groups of 50 or more is unknown.