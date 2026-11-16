# Verification — 22 October 2026

Story: select or upload footage → calibrate camera → run inference → save potential violations → inspect evidence and record review decisions.

## Confirmed

- 18 automated tests passed in the configured Python environment. Includes direction/segment geometry, duplicate suppression, green/unknown signal handling, stale tracking observations, signal color masks, pipeline evidence persistence with controlled tracks, corrupt-input handling, initial dashboard rendering and persisted review corrections.
- Opened the running Streamlit dashboard in the browser at http://127.0.0.1:8502.
- Selected the downloaded creator sample using the approximate built-in camera preset, with real YOLO11n/ByteTrack inference and EasyOCR enabled.
- Browser showed 100% completion and saved run `ab3796fe330f`.
- Evidence tab showed one potential violation, zero plate candidates, one pending review and complete status. Before/crossing images were available.

## Limits

The short 352 × 288 sample does not provide dependable plate detail. Its flagged event has not been independently labelled as a true violation; it remains pending review. The automated pipeline integration test uses controlled tracks and is not a detector accuracy benchmark. A trained regional plate detector and representative labelled footage are still needed to establish real-world ALPR and violation accuracy.

The current plate proposal method is experimental. Signal color thresholds and road-contact anchors are approximate. These limitations are displayed in the UI and documented in README.md.

## Public-footage check — 6 November 2026

- Source: Zenodo *Dataset for Traffic Evaluation*, record 14041920, file `rlr_occasions.mp4` (50.9 MB). The full file is a compilation with scene cuts. A stable daytime excerpt from source seconds 20–31 was resized to 960 × 540 at 10 FPS for this local check. Source footage and excerpts stay in ignored `data/` and are not redistributed in this repository.
- Calibration: near-side stop line `[[.02,.57],[.82,.64]]`, below-to-above crossing. The signal is visibly red throughout this excerpt, so the run used a **manual, visually checked** red interval of 0–11 seconds. This is not an automatic signal-recognition success.
- Result after spatial duplicate suppression: one pending candidate at excerpt 3.3 seconds (source about 23.3 seconds), showing a pickup crossing the selected line. The raw rule saw two line crossings because the tracker assigned overlapping boxes to the same pickup at that moment; the duplicate was suppressed. The OCR baseline returned no plate text. This is a candidate for human review, not a confirmed violation or measured accuracy result.
- Automatic signal check on the same excerpt: a tight box around the visible daylight signal was classified as amber on 105 frames and unknown on 5, with zero red frames. Visible-signal mode would therefore miss this event. The color threshold needs representative calibration or a trained traffic-light classifier.
- A second fixed-camera creator sample (`data/samples/youtube.mp4`, 5.16 seconds, 352 × 288) was rerun with **visible-signal mode**. It yielded one pending candidate at 2.88 seconds, 110 red frames, 19 unknown frames, one line crossing, and no readable plate. Its event has not been independently labelled.
- Automated tests and Linux import check verify behavior; no labelled ground-truth event set was available for precision or recall on these clips.

## Public-footage check — 16 November 2026

- [Zenodo Dataset for Traffic Evaluation](https://zenodo.org/records/14041920), `rlr_occasions.mp4`, original 1280 × 720 file, source seconds 20–31. Visible-signal mode with ROI `(58%,1%)–(61%,7%)`, stop line `(2%,57%)–(82%,64%)`, approach lane `(35%,60%)–(72%,100%)`, below-to-above direction: **one potential crossing at source 23.233 s**, 235 red frames, 95 unknown frames, two geometric crossings. OCR enabled: 50 bounded scan attempts, zero readable plates. The flagged pickup has no legible rear plate in the source. The app now recognizes this sample and suggests the tested calibration.
- [Farzad Nekouee's `traffic_video.mp4`](https://github.com/FarzadNekouee/Traffic-Violation-Detection/blob/master/traffic_video.mp4), original 1920 × 1012 file, first 3 seconds: plate scan candidate **KW527** on track 2, matching the clearly visible source plate, with no violation event claimed. The clip has a traffic-light graphic overlay and no independently verified stop line.
- Root causes addressed: plate reading previously ran only after a violation event, and a tight detector crop dropped enough plate border for OCR to fail on a clear example. Plate scanning now runs independently at a bounded rate; event OCR can reuse those reads; detector crops include a small margin. Start-time selection lets the user isolate a stable camera scene in a compilation.
- These two examples demonstrate separate positive crossing and plate-scan paths. Neither establishes a verified violator plate or precision/recall. The public source files remain local and excluded from the repository.
