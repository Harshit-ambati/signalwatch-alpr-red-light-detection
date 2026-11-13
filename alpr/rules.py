"""Geometry and conservative crossing rules, independent of inference libraries."""
from dataclasses import dataclass
from math import hypot


@dataclass
class Observation:
    point: tuple
    time: float
    signal: str


class CrossingDetector:
    def __init__(self, start, end, direction=1, max_gap=0.5, approach_zone=None):
        self.start, self.end = start, end
        self.direction, self.max_gap = direction, max_gap
        if hypot(end[0]-start[0], end[1]-start[1]) < 0.01:
            raise ValueError('Stop line endpoints must be different.')
        if approach_zone is not None:
            x1, y1, x2, y2 = approach_zone
            if not (0 <= x1 < x2 <= 1 and 0 <= y1 < y2 <= 1):
                raise ValueError('Approach lane must be a rectangle inside the frame.')
        self.approach_zone = approach_zone
        self.approach_hits = {}
        self.approach_entry = {}
        self.approach_last_time = {}
        self.previous = {}
        self.reported = set()
        self.geometry_crossings = 0

    def side(self, p):
        a, b = self.start, self.end
        return ((b[0]-a[0])*(p[1]-a[1])-(b[1]-a[1])*(p[0]-a[0])) * self.direction

    def update(self, track, point, time, signal):
        old = self.previous.get(track)
        prior_approach_hits = self.approach_hits.get(track, 0)
        self.previous[track] = Observation(point, time, signal)
        if self.approach_zone is not None:
            x1, y1, x2, y2 = self.approach_zone
            in_approach = x1 <= point[0] <= x2 and y1 <= point[1] <= y2
            last_approach = self.approach_last_time.get(track, float('-inf'))
            if in_approach:
                if time - last_approach > self.max_gap:
                    self.approach_entry[track] = point
                    prior_approach_hits = 0
                self.approach_hits[track] = prior_approach_hits + 1
                self.approach_last_time[track] = time
            elif time - last_approach > self.max_gap:
                self.approach_hits[track] = 0
        if old is None or track in self.reported or not 0 < time-old.time <= self.max_gap:
            return False
        before, after = self.side(old.point), self.side(point)
        if not before < 0 <= after:
            return False
        # Check intersection with the finite stop-line segment, not its extension.
        ratio = -before / (after-before)
        hit = tuple(old.point[i]+ratio*(point[i]-old.point[i]) for i in (0, 1))
        a, b = self.start, self.end
        along = sum((hit[i]-a[i])*(b[i]-a[i]) for i in (0, 1))
        length2 = sum((b[i]-a[i])**2 for i in (0, 1))
        if not 0 <= along <= length2:
            return False
        self.geometry_crossings += 1
        if self.approach_zone is not None:
            if not self.approach_zone[0] <= hit[0] <= self.approach_zone[2]:
                return False
            if prior_approach_hits < 2 or time - self.approach_last_time.get(track, float('-inf')) > self.max_gap:
                return False
            origin = self.approach_entry[track]
            dx, dy = point[0] - origin[0], point[1] - origin[1]
            lx, ly = b[0] - a[0], b[1] - a[1]
            normal = abs(lx * dy - ly * dx)
            lateral = abs(lx * dx + ly * dy)
            if normal < 0.5 * lateral:
                return False
        # Require red on BOTH sides of crossing; ambiguous transitions need review.
        if old.signal != 'red' or signal != 'red':
            return False
        self.reported.add(track)
        return True


def parse_intervals(text):
    intervals = []
    for item in text.split(','):
        if not item.strip():
            continue
        start, end = map(float, item.strip().split('-'))
        if not 0 <= start < end:
            raise ValueError('Intervals require 0 <= start < end.')
        intervals.append((start, end))
    return intervals
