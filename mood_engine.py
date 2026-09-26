"""
Pure mood-detection logic for EmotionMirror.

Everything here is standard-library only (no Qt, pynput, pandas or
scikit-learn), so it can be unit-tested headlessly. `run_popup.py` wires
these functions to the live keyboard/mouse listeners and the GUI.
"""
from __future__ import annotations

import json
import os
import random
from dataclasses import asdict, dataclass
from typing import Dict, Iterable, List, Optional, Sequence, Tuple

# Rolling window used for every mood check (seconds).
WINDOW_SECONDS = 300

# Keystroke gaps longer than this are pauses, not typing rhythm (seconds).
MAX_RHYTHM_GAP = 2.0

MOODS: Tuple[str, ...] = ("idle", "low_energy", "deep_work", "struggling", "browsing", "steady")

# Column order shared by the CSV log, the trainer and the classifier.
FEATURE_NAMES: Tuple[str, ...] = (
    "typing_speed",
    "mouse_activity",
    "backspace_activity",
    "avg_keystroke_interval",
    "typing_rhythm_variance",
)

LOG_COLUMNS: Tuple[str, ...] = ("timestamp", "mood") + FEATURE_NAMES + ("feedback",)


# ---------------------------------------------------------------------------
# Feature extraction
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class Features:
    """Behavioural features for one rolling window. Counts, never content."""
    typing_speed: int            # non-backspace key presses in the window
    mouse_activity: int          # mouse clicks in the window
    backspace_activity: int      # backspace presses in the window
    avg_keystroke_interval: float  # mean gap between key presses (s)
    typing_rhythm_variance: float  # variance of those gaps (s^2)

    @property
    def backspace_ratio(self) -> float:
        total = self.typing_speed + self.backspace_activity
        return self.backspace_activity / total if total else 0.0

    def as_row(self) -> List[float]:
        """Values in FEATURE_NAMES order (for the classifier / CSV log)."""
        return [getattr(self, name) for name in FEATURE_NAMES]


def _in_window(timestamps: Iterable[float], now: float, window: float) -> List[float]:
    return [t for t in timestamps if 0 <= now - t <= window]


def compute_features(
        keystrokes: Sequence[float],
        clicks: Sequence[float],
        backspaces: Sequence[float],
        keystroke_intervals: Sequence[Tuple[float, float]],
        now: float,
        window: float = WINDOW_SECONDS,
) -> Features:
    """
    Build the feature vector for the last `window` seconds.

    `keystroke_intervals` is a sequence of (timestamp, gap_seconds) pairs,
    recorded when a key is pressed; only gaps inside the window and shorter
    than MAX_RHYTHM_GAP contribute to the rhythm statistics.
    """
    gaps = [dt for (t, dt) in keystroke_intervals if 0 <= now - t <= window and dt < MAX_RHYTHM_GAP]
    mean_gap = sum(gaps) / len(gaps) if gaps else 0.0
    var_gap = sum((g - mean_gap) ** 2 for g in gaps) / len(gaps) if gaps else 0.0

    return Features(
        typing_speed=len(_in_window(keystrokes, now, window)),
        mouse_activity=len(_in_window(clicks, now, window)),
        backspace_activity=len(_in_window(backspaces, now, window)),
        avg_keystroke_interval=mean_gap,
        typing_rhythm_variance=var_gap,
    )


def prune_older_than(items: list, now: float, window: float = WINDOW_SECONDS) -> None:
    """Drop entries older than `window` in place. Entries are timestamps or tuples starting with one."""
    cutoff = now - window
    items[:] = [x for x in items if (x[0] if isinstance(x, tuple) else x) >= cutoff]


# ---------------------------------------------------------------------------
# Rule-based classification (used until a trained model exists)
# ---------------------------------------------------------------------------

def rule_based_mood(f: Features) -> str:
    """Map a 5-minute feature window to one of MOODS using fixed thresholds."""
    typing, clicks, backspaces = f.typing_speed, f.mouse_activity, f.backspace_activity
    ratio = f.backspace_ratio

    if typing <= 15 and clicks <= 8:
        return "idle"
    if ratio >= 0.20 and typing >= 170:
        return "struggling"
    if typing >= 450 and clicks <= 26 and ratio <= 0.15:
        return "deep_work"
    if typing <= 120 and clicks >= 50:
        return "browsing"
    if typing <= 80 and clicks <= 20 and backspaces <= 12:
        return "low_energy"
    return "steady"


# ---------------------------------------------------------------------------
# Rolling history of recent feature snapshots (in memory only)
# ---------------------------------------------------------------------------

class BaselineTracker:
    """Keeps the most recent feature snapshots in memory (never written to disk)."""

    def __init__(self, max_items: int = 100):
        self.max_items = max_items
        self.history: List[dict] = []

    def update(self, features: dict) -> None:
        self.history.append(dict(features))
        if len(self.history) > self.max_items:
            del self.history[: len(self.history) - self.max_items]

    def averages(self) -> Dict[str, float]:
        """Mean of each numeric field across the stored snapshots."""
        if not self.history:
            return {}
        keys = self.history[0].keys()
        return {k: sum(h.get(k, 0) for h in self.history) / len(self.history) for k in keys}


# ---------------------------------------------------------------------------
# Companion messages
# ---------------------------------------------------------------------------

class NonRepeatingPicker:
    """Random choice that avoids repeating the previous pick for the same key."""

    def __init__(self, rng: Optional[random.Random] = None):
        self._rng = rng or random.Random()
        self._last: Dict[Tuple[str, str], str] = {}

    def pick(self, mood: str, kind: str, items: Sequence[str]) -> str:
        if not items:
            return ""
        last = self._last.get((mood, kind))
        candidates = [x for x in items if x != last] or list(items)
        choice = self._rng.choice(candidates)
        self._last[(mood, kind)] = choice
        return choice


# ---------------------------------------------------------------------------
# Settings (settings.json, created with defaults when missing)
# ---------------------------------------------------------------------------

@dataclass
class Settings:
    is_feedback_enabled: bool = True
    is_first_run: bool = True
    user_name: str = "User"
    is_sound_enabled: bool = True


def load_settings(path: str) -> Settings:
    """Load settings; a missing or corrupt file yields defaults (first run)."""
    defaults = Settings()
    if not os.path.exists(path):
        return defaults
    try:
        with open(path, "r", encoding="utf-8") as fh:
            data = json.load(fh)
        if not isinstance(data, dict):
            return defaults
    except (OSError, ValueError):
        return defaults
    return Settings(
        is_feedback_enabled=bool(data.get("is_feedback_enabled", True)),
        is_first_run=bool(data.get("is_first_run", False)),
        user_name=str(data.get("user_name") or "User"),
        is_sound_enabled=bool(data.get("is_sound_enabled", True)),
    )


def save_settings(settings: Settings, path: str) -> None:
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(asdict(settings), fh, ensure_ascii=False, indent=2)
