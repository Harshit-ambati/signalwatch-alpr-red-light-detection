from pathlib import Path
import re
import cv2
import numpy as np


def signal_state(frame, roi):
    h, w = frame.shape[:2]
    x1, y1, x2, y2 = roi
    crop = frame[int(y1*h):int(y2*h), int(x1*w):int(x2*w)]
    if crop.size == 0:
        return 'unknown'
    hsv = cv2.cvtColor(crop, cv2.COLOR_BGR2HSV)
    masks = {
        'red': cv2.inRange(hsv, (0, 100, 120), (10, 255, 255)) | cv2.inRange(hsv, (170, 100, 120), (179, 255, 255)),
        'green': cv2.inRange(hsv, (40, 90, 100), (95, 255, 255)),
        'amber': cv2.inRange(hsv, (15, 100, 120), (35, 255, 255)),
    }
    scores = sorted(((np.count_nonzero(mask)/mask.size, name) for name, mask in masks.items()), reverse=True)
    if scores[0][0] < 0.015 or scores[0][0] < scores[1][0]*1.5:
        return 'unknown'
    return scores[0][1]


class PlateReader:
    def __init__(self, model_path=None):
        import easyocr
        self.reader = easyocr.Reader(['en'], gpu=False, model_storage_directory='models/ocr', verbose=False)
        self.detector = None
        if model_path:
            from ultralytics import YOLO
            self.detector = YOLO(model_path)

    def read(self, vehicle):
        if vehicle.size == 0:
            return None
        candidates = []
        if self.detector:
            result = self.detector(vehicle, verbose=False)[0]
            for box in result.boxes.xyxy.cpu().tolist():
                x1,y1,x2,y2 = map(int,box)
                candidates.append(vehicle[max(0,y1):y2,max(0,x1):x2])
        else:
            # Baseline only: bright rectangular regions. A trained plate model is preferable.
            gray = cv2.cvtColor(vehicle, cv2.COLOR_BGR2GRAY)
            mask = cv2.threshold(gray, 160, 255, cv2.THRESH_BINARY)[1]
            contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            for contour in sorted(contours, key=cv2.contourArea, reverse=True)[:30]:
                x,y,w,h = cv2.boundingRect(contour)
                if 1.8 < w/max(h,1) < 6.5 and w >= 35 and h >= 10:
                    candidates.append(vehicle[y:y+h,x:x+w])
        best = None
        for crop in candidates[:8]:
            if crop.size == 0:
                continue
            enlarged = cv2.resize(crop, None, fx=3, fy=3, interpolation=cv2.INTER_CUBIC)
            reads = self.reader.readtext(enlarged, allowlist='ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789', paragraph=False)
            for _, text, confidence in reads:
                text = re.sub('[^A-Z0-9]', '', text.upper())
                if 5 <= len(text) <= 12 and confidence >= 0.4 and (best is None or confidence > best[1]):
                    best = (text, float(confidence), crop.copy())
        return best
