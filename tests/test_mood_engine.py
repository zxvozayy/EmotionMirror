"""Headless tests for EmotionMirror's pure mood logic (stdlib only)."""
import json
import random

import pytest

from mood_engine import (
    FEATURE_NAMES,
    LOG_COLUMNS,
    MOODS,
    BaselineTracker,
    Features,
    NonRepeatingPicker,
    Settings,
    compute_features,
    load_settings,
    prune_older_than,
    rule_based_mood,
    save_settings,
)

NOW = 10_000.0


def feats(typing=0, clicks=0, backspaces=0):
    return Features(typing, clicks, backspaces, 0.0, 0.0)


# ---------------------------------------------------------------------------
# Feature extraction
# ---------------------------------------------------------------------------

class TestComputeFeatures:
    def test_counts_only_events_inside_window(self):
        keys = [NOW - 400, NOW - 299, NOW - 10, NOW]
        clicks = [NOW - 301, NOW - 5]
        backs = [NOW - 1000, NOW - 1]
        f = compute_features(keys, clicks, backs, [], NOW, window=300)
        assert (f.typing_speed, f.mouse_activity, f.backspace_activity) == (3, 1, 1)

    def test_future_timestamps_are_ignored(self):
        f = compute_features([NOW + 5], [], [], [], NOW)
        assert f.typing_speed == 0

    def test_rhythm_statistics(self):
        intervals = [(NOW - 3, 0.2), (NOW - 2, 0.4), (NOW - 1, 0.6)]
        f = compute_features([], [], [], intervals, NOW)
        assert f.avg_keystroke_interval == pytest.approx(0.4)
        assert f.typing_rhythm_variance == pytest.approx(((0.2 - 0.4) ** 2 + 0 + (0.6 - 0.4) ** 2) / 3)

    def test_long_pauses_and_old_gaps_are_excluded(self):
        intervals = [(NOW - 1, 5.0), (NOW - 999, 0.1), (NOW - 2, 0.3)]
        f = compute_features([], [], [], intervals, NOW, window=300)
        assert f.avg_keystroke_interval == pytest.approx(0.3)
        assert f.typing_rhythm_variance == pytest.approx(0.0)

    def test_empty_input(self):
        f = compute_features([], [], [], [], NOW)
        assert f.as_row() == [0, 0, 0, 0.0, 0.0]

    def test_backspace_ratio(self):
        assert Features(80, 0, 20, 0, 0).backspace_ratio == pytest.approx(0.2)
        assert feats().backspace_ratio == 0.0

    def test_row_order_matches_log_columns(self):
        f = Features(1, 2, 3, 4.0, 5.0)
        assert f.as_row() == [1, 2, 3, 4.0, 5.0]
        assert LOG_COLUMNS == ("timestamp", "mood", *FEATURE_NAMES, "feedback")


def test_prune_older_than_handles_plain_and_tuple_entries():
    stamps = [NOW - 500, NOW - 100, NOW]
    pairs = [(NOW - 500, 0.1), (NOW - 1, 0.2)]
    prune_older_than(stamps, NOW, 300)
    prune_older_than(pairs, NOW, 300)
    assert stamps == [NOW - 100, NOW]
    assert pairs == [(NOW - 1, 0.2)]


# ---------------------------------------------------------------------------
# Rule-based classification
# ---------------------------------------------------------------------------

class TestRuleBasedMood:
    @pytest.mark.parametrize(
        "f, mood",
        [
            (feats(typing=10, clicks=5), "idle"),
            (feats(typing=200, clicks=10, backspaces=60), "struggling"),
            (feats(typing=500, clicks=20, backspaces=20), "deep_work"),
            (feats(typing=100, clicks=60), "browsing"),
            (feats(typing=60, clicks=15, backspaces=5), "low_energy"),
            (feats(typing=300, clicks=40, backspaces=10), "steady"),
        ],
    )
    def test_each_mood_is_reachable(self, f, mood):
        assert rule_based_mood(f) == mood

    def test_idle_boundary(self):
        assert rule_based_mood(feats(typing=15, clicks=8)) == "idle"
        assert rule_based_mood(feats(typing=16, clicks=8)) == "low_energy"

    def test_deep_work_requires_few_corrections(self):
        assert rule_based_mood(feats(typing=500, clicks=20, backspaces=150)) == "struggling"

    def test_all_outputs_are_known_moods(self):
        rng = random.Random(0)
        for _ in range(500):
            f = feats(rng.randint(0, 800), rng.randint(0, 120), rng.randint(0, 200))
            assert rule_based_mood(f) in MOODS


# ---------------------------------------------------------------------------
# Rolling history
# ---------------------------------------------------------------------------

class TestBaselineTracker:
    def test_keeps_only_most_recent_items(self):
        b = BaselineTracker(max_items=3)
        for i in range(5):
            b.update({"typing_speed": i})
        assert [h["typing_speed"] for h in b.history] == [2, 3, 4]

    def test_averages(self):
        b = BaselineTracker()
        assert b.averages() == {}
        b.update({"typing_speed": 10, "mouse_activity": 4})
        b.update({"typing_speed": 20, "mouse_activity": 0})
        assert b.averages() == {"typing_speed": 15, "mouse_activity": 2}

    def test_update_copies_input(self):
        b = BaselineTracker()
        snap = {"typing_speed": 1}
        b.update(snap)
        snap["typing_speed"] = 99
        assert b.history[0]["typing_speed"] == 1


# ---------------------------------------------------------------------------
# Message picking
# ---------------------------------------------------------------------------

def test_picker_never_repeats_consecutively():
    picker = NonRepeatingPicker(random.Random(42))
    items = ["a", "b", "c"]
    last = None
    for _ in range(200):
        choice = picker.pick("idle", "comments", items)
        assert choice in items and choice != last
        last = choice


def test_picker_single_and_empty():
    picker = NonRepeatingPicker()
    assert picker.pick("idle", "tips", ["only"]) == "only"
    assert picker.pick("idle", "tips", ["only"]) == "only"
    assert picker.pick("idle", "tips", []) == ""


# ---------------------------------------------------------------------------
# Settings
# ---------------------------------------------------------------------------

class TestSettings:
    def test_missing_file_gives_first_run_defaults(self, tmp_path):
        s = load_settings(str(tmp_path / "settings.json"))
        assert s == Settings(is_feedback_enabled=True, is_first_run=True, user_name="User", is_sound_enabled=True)

    def test_round_trip_preserves_unicode(self, tmp_path):
        path = str(tmp_path / "settings.json")
        save_settings(Settings(is_first_run=False, user_name="Zoë", is_sound_enabled=False), path)
        assert load_settings(path) == Settings(is_first_run=False, user_name="Zoë", is_sound_enabled=False)

    def test_corrupt_file_falls_back_to_defaults(self, tmp_path):
        path = tmp_path / "settings.json"
        path.write_text("{not json", encoding="utf-8")
        assert load_settings(str(path)) == Settings()

    def test_existing_file_without_first_run_flag_is_not_first_run(self, tmp_path):
        path = tmp_path / "settings.json"
        path.write_text(json.dumps({"user_name": ""}), encoding="utf-8")
        s = load_settings(str(path))
        assert s.is_first_run is False
        assert s.user_name == "User"
