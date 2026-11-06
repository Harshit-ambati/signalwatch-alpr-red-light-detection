# Temporary footage sources

Historical reference video: https://www.youtube.com/watch?v=7UjyifjnzJg (currently private; use the creator repository's sample instead).

Creator repository: https://github.com/AhmadYahya97/Fully-Automated-red-light-Violation-Detection

Candidate input file: `videos/youtube.mp4` on the repository's master branch.

Download URL: https://raw.githubusercontent.com/AhmadYahya97/Fully-Automated-red-light-Violation-Detection/master/videos/youtube.mp4

Local destination: `data/samples/youtube.mp4`. This is third-party sample footage, not footage collected by this project. No redistribution license has been established. Keep it out of the source repository and check permissions before publishing it. Recordings supplied later will replace this development sample.

Reference videos do not establish plate readability, correctness of violations, or measured model accuracy. Calibration and frame inspection are required for each clip.

Additional research footage: [Zenodo Dataset for Traffic Evaluation](https://zenodo.org/records/14041920), file `rlr_occasions.mp4`. It is a compilation of several traffic-camera scenes. A local excerpt of source seconds 20–31 was used for the 6 November 2026 check in VERIFICATION.md. The dataset page does not display a specific license in its Rights section, so the media is kept local and excluded from GitHub.

Inspected metadata: 129 frames at 25 FPS, 352 × 288 pixels, 5.16 seconds. Fixed camera with a visible signal and road markings; plates are small. Dashboard preset: line (0.05,0.64) to (0.90,0.54), below-to-above direction, signal ROI (0.04,0.14) to (0.10,0.20). Geometry is approximate and needs review.
