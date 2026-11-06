# SignalWatch — ALPR and red-light violation review

Local final-year research prototype. Python 3.12+ recommended. This machine's configured environment uses Python 3.14 and reuses its existing system packages to avoid downloading PyTorch again.

## Run

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m streamlit run app.py --server.address 127.0.0.1
```

Set `SIGNALWATCH_PASSWORD` in your local environment, then open http://localhost:8501. First analysis downloads YOLO11n and (if enabled) EasyOCR weights. CPU supported; processing is not guaranteed real-time. Use a short clip first.

## Deploy on Streamlit Community Cloud

Connect the GitHub repository and set the entrypoint to `app.py`, branch `main`, Python 3.12. Dependencies are declared in `requirements.txt` and `packages.txt`. The first launch downloads the vehicle and OCR models, so startup and analysis can be slow. Uploaded files, model downloads, evidence, and review decisions are stored on the app instance's local filesystem; they may disappear when the instance restarts. This is a demonstration deployment, not durable evidence storage. You may need a larger host if model installation or inference exceeds Community Cloud resources.

Before opening the deployed app, set a strong `APP_PASSWORD` in Streamlit Cloud → Manage app → Settings → Secrets, using TOML syntax such as `APP_PASSWORD = "your-own-long-random-password"`. Do not put the actual password in the repository. The app stays locked until this secret exists. Everyone given this password can access the app, so treat it as a single-reviewer demo, not a multi-user account system.

Runs are visible only in the browser session that created them. Download the complete evidence bundle before closing the session. Use **Restore an evidence bundle** after a cloud restart or in a new session. This is manual persistence; cloud local storage is still temporary.

## Workflow

Upload MP4/AVI/MOV/MKV or import a public YouTube URL → check suggested line and signal rectangle → select direction → analyze → evidence review → correct OCR and confirm/reject → export CSV.

YouTube import accepts public watch, Shorts and youtu.be links for finished recordings. It limits duration to 10 minutes and downloaded size to 100 MB, and requests a video-only MP4 stream within 854 × 854 pixels. Audio is unnecessary for traffic analysis. Import may fail if a video is unavailable, age restricted, or YouTube blocks automated access. YouTube live streams require a separate live ingestion system. Only import footage you have permission to use.

The calibration suggestion uses visible road edges and colored light candidates in the first frame. It can choose a lane marking, vehicle light, or the wrong traffic signal. Inspect the preview and adjust the sliders as needed; the correct stop line and signal for the monitored lane are essential to a valid result.

Coordinates are normalized to video dimensions. The traffic light must control the monitored lane. Use a finite stop-line segment to exclude other lanes. The vehicle bottom-center anchor approximates its contact with the road. A crossing is flagged only if consecutive observations are red, the trajectory intersects the stop-line segment, and the observation gap is at most 0.5 seconds. The same track is reported once. Green-to-red transitions at the crossing are intentionally not flagged because timing is ambiguous.

Manual timeline mode uses user-entered red intervals in video seconds; it is not automatic signal detection. Outside intervals the signal is unknown. Use this mode only with verified labels or explicitly simulated experiments.

Vehicle detection: YOLO11n COCO vehicle classes. Tracking: ByteTrack. Signal: HSV color masks with three-frame stability. ALPR: experimental bright-rectangle proposals plus EasyOCR, or an optional local trained YOLO plate detector. Reads are candidates, never guaranteed registration numbers. Up to four recent crops and the crossing crop are checked. Missing readings remain blank.

Evidence lives in `data/runs/<run>/`: configuration and events in results.json, before/crossing/vehicle images, and a plate image when recognized. Times are offsets into the video, not real-world violation times. Processing status distinguishes failures from completed runs. Review decisions persist in the JSON file. Uploads and runs remain until manually removed.

## Footage

You can import a public YouTube link in the Analyze tab, though original input footage from the creators' repositories is preferable to annotated output videos:

- https://github.com/AhmadYahya97/Fully-Automated-red-light-Violation-Detection
- https://www.youtube.com/watch?v=PxHkKLUk_QM
- https://github.com/anmspro/Traffic-Signal-Violation-Detection-System

Final recorded footage requires new calibration, not code changes. Check source permissions before distributing third-party clips.

## Verification

```powershell
.\.venv\Scripts\python.exe -m pytest -q
```

The **Evaluate** tab accepts a CSV with `video_seconds,plate`, one row per true red-light crossing in the same video. Leave the plate blank if unreadable. It reports matched crossings, false alarms, missed crossings, precision, recall, and plate exact-match accuracy for readable matched plates. Match tolerance is 0.5 seconds. Split development and evaluation footage. Do not report synthetic tests as real-world accuracy.

## Architecture and remaining research

`app.py`: Streamlit upload/calibration/review UI. `alpr/pipeline.py`: inference orchestration and evidence storage. `alpr/rules.py`: direction, segment intersection, timing and deduplication. `alpr/vision.py`: signal classifier and plate OCR. `alpr/bundle.py`: evidence export and restore. `alpr/evaluate.py`: labelled event matching and metrics. The password gate protects this demo, but a multi-user deployment would need individual accounts, durable storage, database transactions and a background job queue.

Remaining validation: representative footage, a trained regional plate detector, calibration of signal thresholds, plate format evaluation, and measurement of tracking/occlusion errors. Red-light rules for turns are not implemented. This system produces potential violations for human review, not automatic fines.
