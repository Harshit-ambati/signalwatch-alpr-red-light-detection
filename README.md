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

Upload MP4/AVI/MOV/MKV or import a public YouTube URL → choose the start time → check the suggested line, signal rectangle, and approach lane → analyze → evidence review → correct OCR and confirm/reject → export CSV. The duration limit runs from the selected start time. Manual red intervals use original video seconds.

YouTube import accepts public watch, Shorts and youtu.be links for finished recordings. It limits duration to 10 minutes and downloaded size to 100 MB, and requests a video-only MP4 stream within 854 × 854 pixels. Audio is unnecessary for traffic analysis. Import may fail if a video is unavailable, age restricted, or YouTube blocks automated access. YouTube live streams require a separate live ingestion system. Only import footage you have permission to use.

The calibration suggestion uses visible road edges and colored light candidates in the selected start frame. It can choose a lane marking, vehicle light, or the wrong traffic signal. The top strip is ignored to reduce false signal selections from title overlays. Inspect the preview and adjust the sliders as needed; the correct stop line and signal for the monitored lane are essential to a valid result. The green **approach lane** box should cover only vehicles approaching that stop line, excluding cross traffic. A moving dashcam cannot be reliably calibrated with this fixed-camera workflow.

Coordinates are normalized to video dimensions. The traffic light must control the monitored lane. Use a finite stop-line segment and approach box to exclude other lanes. The vehicle bottom-center anchor approximates its contact with the road. A crossing is flagged only if consecutive observations are red, the track was seen in the approach box before crossing, its movement was mostly toward the stop line, the trajectory intersects the finite stop-line segment, and the observation gap is at most 0.5 seconds. The same track is reported once. Green-to-red transitions at the crossing are intentionally not flagged because timing is ambiguous.

Manual timeline mode uses user-entered red intervals in video seconds; it is not automatic signal detection. Outside intervals the signal is unknown. Use this mode only with verified labels or explicitly simulated experiments.

Plate scan only mode ignores signal color and never creates violation events. Use it to demonstrate OCR on footage without a verified traffic light, such as the high-detail plate example below. Set the duration to 3 seconds for a quick presentation scan.

Vehicle detection: YOLO11n COCO vehicle classes. Tracking: ByteTrack. Signal: HSV color masks with three-frame stability. ALPR: a pretrained YOLOv8n plate detector plus EasyOCR by default, with heuristic or custom model options. The pretrained model is downloaded on first use from [Koushim's Hugging Face model](https://huggingface.co/Koushim/yolov8-license-plate-detection) at commit `83c98fbe7412fe8b3950adb5637cfd08b0f04809` and checked against SHA256 `2d95861825bb4184404344c9cf809f40fd31dba785fe54e8ba5b9a3583789822`. The model card lists an MIT license. Large tracked vehicles are sampled for plate scans at most five times, at least one second apart. OCR uses a padded plate crop so edge characters remain visible. Violation events also check recent vehicle crops. Missing readings remain blank. Plate scans and violator plate candidates are separate unverified outputs; human verification is required.

Evidence lives in `data/runs/<run>/`: configuration and events in results.json, before/crossing/vehicle images, and a plate image when recognized. Times are offsets into the video, not real-world violation times. Processing status distinguishes failures from completed runs. Review decisions persist in the JSON file. Uploads and runs remain until manually removed.

New runs include signal-frame counts, tracked line crossings, plate scan attempts, and any plate candidates found independently of violations. When zero violations are reported, the review page displays these diagnostics and plate scans. No red frames or no line crossings indicates a calibration or footage mismatch; neither is evidence that the road was violation-free.

### Reproducible public-video checks

For a positive crossing result, download `rlr_occasions.mp4` from the [Zenodo Dataset for Traffic Evaluation](https://zenodo.org/records/14041920) and upload the unmodified file. The app recognizes this sample and proposes: start **20 s**, duration **11 s**, below-to-above crossing, stop line **(2%,57%)–(82%,64%)**, signal box **(58%,1%)–(61%,7%)**, and approach lane **(35%,60%)–(72%,100%)**. With visible-signal mode, a full-resolution local check recorded one potential crossing near source second **23.23**. The pickup's plate was unreadable, so its plate field remained empty. This is a screening example, not a verified offence or accuracy measurement.

For a positive plate-scan result, use `traffic_video.mp4` from [Farzad Nekouee's public project](https://github.com/FarzadNekouee/Traffic-Violation-Detection). A local scan of the first three seconds produced candidate `KW527`, matching the visibly readable plate. This clip has an overlaid traffic-light graphic and no independently calibrated stop line, so the result demonstrates ALPR only. Third-party footage stays out of this repository.

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

Remaining validation: representative footage, a plate detector trained on the target region, calibration of signal thresholds, plate format evaluation, and measurement of tracking/occlusion errors. Red-light rules for turns are not implemented. The rectangular approach box and motion test cannot determine which signal controls every turning lane. This system produces potential violations for human review, not automatic fines.
