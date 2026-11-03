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
