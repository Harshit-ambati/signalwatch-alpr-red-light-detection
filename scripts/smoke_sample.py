"""Exercise real inference with approximate sample calibration; not an accuracy evaluation."""
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from alpr.pipeline import process

config={'line':[[.05,.64],[.90,.54]],'direction':-1,'ocr':False,'signal_mode':'Visible traffic light',
        'roi':[.04,.14,.10,.20],'red_intervals':[],'max_seconds':0}
print(process('data/samples/youtube.mp4',config))
