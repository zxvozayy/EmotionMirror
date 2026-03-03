# ai.py
import os, csv, time, math
from statistics import mean, pstdev

# ---------- Feature Engineering ----------
def _recent(items, now, window_s):
    # items are timestamps or (t, x, y); keep recent by timestamp at index 0
    if not items:
        return []
    if isinstance(items[0], tuple):
        return [m for m in items if now - m[0] <= window_s]
    else:
        return [t for t in items if now - t <= window_s]

def _safe_mean(xs):
    return mean(xs) if xs else 0.0

def _safe_pstdev(xs):
    if xs and len(xs) > 1:
        return pstdev(xs)
    return 0.0

def compute_features(keystrokes, clicks, movements, now=None, window_s=60):
    """
    Create a compact feature vector for the last `window_s` seconds.
    - keystrokes: list[timestamp]
    - clicks: list[timestamp]
    - movements: list[(timestamp, x, y)]
    """
    now = now or time.time()
    ks = _recent(keystrokes, now, window_s)
    cl = _recent(clicks, now, window_s)
    mv = _recent(movements, now, window_s)

    # typing intervals (only those inside the window)
    ks_sorted = sorted(ks)
    intervals = []
    for i in range(1, len(ks_sorted)):
        dt = ks_sorted[i] - ks_sorted[i - 1]
        # ignore huge pauses; they’re not “rhythm”
        if 0 < dt < 2.0:
            intervals.append(dt)

    # mouse distance (pixels)
    mv_sorted = sorted(mv, key=lambda m: m[0])
    total_mouse_dist = 0.0
    for i in range(1, len(mv_sorted)):
        _, x1, y1 = mv_sorted[i - 1]
        _, x2, y2 = mv_sorted[i]
        dx = x2 - x1
        dy = y2 - y1
        total_mouse_dist += math.hypot(dx, dy)

    last_activity_ts = 0.0
    for t in ks:
        last_activity_ts = max(last_activity_ts, t)
    for t in cl:
        last_activity_ts = max(last_activity_ts, t)
    for t, _, _ in mv:
        last_activity_ts = max(last_activity_ts, t)
    idle_seconds = min(window_s, (now - last_activity_ts) if last_activity_ts else window_s)

    typing_count = len(ks)
    click_count = len(cl)
    move_samples = len(mv)

    features = {
        "window_s": window_s,
        "typing_count": typing_count,
        "click_count": click_count,
        "move_samples": move_samples,
        "typing_rate_per_s": typing_count / window_s,
        "click_rate_per_s": click_count / window_s,
        "mouse_dist": round(total_mouse_dist, 2),
        "idle_seconds": round(idle_seconds, 2),
        "ks_interval_mean": round(_safe_mean(intervals), 4),
        "ks_interval_std": round(_safe_pstdev(intervals), 4),
        "ks_interval_cv": round((_safe_pstdev(intervals) / _safe_mean(intervals)) if _safe_mean(intervals) > 0 else 0.0, 4),
    }
    return features

# ---------- Weak Labeling (scaled from your 5-min rules) ----------
def weak_label_from_features(feat):
    # Scale your 5-min thresholds down to 1 min:
    # energized: typing > 180 & clicks > 120  → per-min: >36 & >24
    # tired:     typing <  60 & clicks <  36  → per-min: <12 & <7
    # focused:   typing > 144 & clicks <  36  → per-min: >29 & <7
    # restless:  typing <  60 & clicks >  96  → per-min: <12 & >19
    # bored:     typing == 0 & clicks == 0 & very low movement
    t = feat["typing_count"]
    c = feat["click_count"]
    m = feat["move_samples"]
    idle = feat["idle_seconds"]

    if t == 0 and c == 0 and m <= 2 and idle > 30:
        return "bored"
    if t > 36 and c > 24:
        return "energized"
    if t < 12 and c < 7:
        return "tired"
    if t > 29 and c < 7:
        return "focused"
    if t < 12 and c > 19:
        return "restless"
    return "neutral"

# ---------- CSV Logger ----------
class FeatureLogger:
    def __init__(self, path="ai_data.csv"):
        self.path = path
        self._ensure_header()

    def _ensure_header(self):
        if not os.path.exists(self.path):
            with open(self.path, "w", newline="", encoding="utf-8") as f:
                writer = csv.writer(f)
                writer.writerow([
                    "timestamp",
                    "label",
                    "window_s",
                    "typing_count",
                    "click_count",
                    "move_samples",
                    "typing_rate_per_s",
                    "click_rate_per_s",
                    "mouse_dist",
                    "idle_seconds",
                    "ks_interval_mean",
                    "ks_interval_std",
                    "ks_interval_cv",
                ])

    def append(self, features: dict, label: str):
        with open(self.path, "a", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow([
                time.strftime("%Y-%m-%d %H:%M:%S", time.localtime()),
                label,
                features.get("window_s", 60),
                features.get("typing_count", 0),
                features.get("click_count", 0),
                features.get("move_samples", 0),
                round(features.get("typing_rate_per_s", 0.0), 4),
                round(features.get("click_rate_per_s", 0.0), 4),
                features.get("mouse_dist", 0.0),
                features.get("idle_seconds", 0.0),
                features.get("ks_interval_mean", 0.0),
                features.get("ks_interval_std", 0.0),
                features.get("ks_interval_cv", 0.0),
            ])
