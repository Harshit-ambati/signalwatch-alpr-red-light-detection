"""Print video metadata and save frames to inspect before calibration."""
import argparse
import json
from pathlib import Path
import cv2

parser=argparse.ArgumentParser()
parser.add_argument('video')
parser.add_argument('--output',default='data/inspection')
args=parser.parse_args()
cap=cv2.VideoCapture(args.video)
fps=cap.get(cv2.CAP_PROP_FPS)
count=int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
if not cap.isOpened() or fps<=0:raise SystemExit('Unable to decode video')
destination=Path(args.output);destination.mkdir(parents=True,exist_ok=True)
print(json.dumps({'fps':fps,'frames':count,'seconds':count/fps,'width':cap.get(3),'height':cap.get(4)}))
for fraction in (0,.25,.5,.75):
    index=int(count*fraction)
    cap.set(cv2.CAP_PROP_POS_FRAMES,index)
    ok,frame=cap.read()
    if ok:cv2.imwrite(str(destination/f'frame-{index}.jpg'),frame)
cap.release()
