"""Conservative visual suggestions for a fixed traffic camera."""

import cv2
import numpy as np

DEFAULT_LINE = [[0.1, 0.6], [0.9, 0.6]]
DEFAULT_ROI = [0.8, 0.05, 0.95, 0.3]


def suggest_geometry(frame):
    height, width = frame.shape[:2]
    if height < 40 or width < 40:
        return {'line': DEFAULT_LINE, 'roi': DEFAULT_ROI, 'line_found': False, 'signal_found': False}

    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    edges = cv2.Canny(cv2.GaussianBlur(gray, (5, 5), 0), 60, 150)
    edges[:int(height * 0.35)] = 0
    edges[int(height * 0.9):] = 0
    lines = cv2.HoughLinesP(edges, 1, np.pi / 180, threshold=max(25, width // 10),
                            minLineLength=max(25, width // 4), maxLineGap=max(8, width // 25))
    choices = []
    if lines is not None:
        for x1, y1, x2, y2 in lines.reshape(-1, 4):
            if x1 > x2:
                x1, x2, y1, y2 = x2, x1, y2, y1
            length = x2 - x1
            if length >= width * 0.25 and abs(y2 - y1) <= length * 0.35:
                middle = (y1 + y2) / (2 * height)
                score = length / width - abs(middle - 0.62) * 0.5
                choices.append((score, [[x1 / width, y1 / height], [x2 / width, y2 / height]]))
    line = max(choices, default=(None, DEFAULT_LINE), key=lambda item: -1 if item[0] is None else item[0])[1]

    hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
    color = (cv2.inRange(hsv, (0, 120, 150), (10, 255, 255)) |
             cv2.inRange(hsv, (170, 120, 150), (179, 255, 255)) |
             cv2.inRange(hsv, (40, 100, 130), (95, 255, 255)) |
             cv2.inRange(hsv, (15, 120, 150), (35, 255, 255)))
    # Titles and channel watermarks commonly occupy the top strip.
    color[:int(height * 0.08)] = 0
    color[int(height * 0.55):] = 0
    count, _, stats, centers = cv2.connectedComponentsWithStats(color)
    candidates = []
    for index in range(1, count):
        x, y, w, h, area = stats[index]
        if 3 <= w <= width * 0.12 and 3 <= h <= height * 0.12 and 6 <= area <= width * height * 0.002:
            aspect = w / h
            if 0.5 <= aspect <= 2:
                candidates.append((area, centers[index]))
    roi = DEFAULT_ROI
    if candidates:
        _, (cx, cy) = max(candidates, key=lambda item: item[0])
        pad_x, pad_y = max(8, int(width * 0.025)), max(12, int(height * 0.055))
        roi = [max(0, (cx - pad_x) / width), max(0, (cy - pad_y) / height),
               min(1, (cx + pad_x) / width), min(1, (cy + pad_y) / height)]
    return {'line': line, 'roi': roi, 'line_found': bool(choices), 'signal_found': bool(candidates)}
