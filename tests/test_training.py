"""Training-data loader tests (skipped when pandas / scikit-learn are not installed)."""
import csv

import pytest

pytest.importorskip("pandas")
pytest.importorskip("sklearn")

from mood_engine import FEATURE_NAMES, LOG_COLUMNS  # noqa: E402
import train_ai  # noqa: E402


def _write_log(path, rows):
    with open(path, "w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(LOG_COLUMNS)
        w.writerows(rows)


def _row(mood, typing, feedback=""):
    return ["2026-01-01 10:00:00", mood, typing, 5, 1, 0.2, 0.01, feedback]


def test_load_mood_log_aligns_columns_and_drops_bad_rows(tmp_path):
    path = tmp_path / "mood_log.csv"
    _write_log(path, [_row("idle", 3), _row("steady", "oops"), _row("deep_work", 600, "User corrected")])

    df = train_ai.load_mood_log(str(path))
    assert list(df["mood"]) == ["idle", "deep_work"]
    assert list(df["typing_speed"]) == [3, 600]

    labeled = train_ai.load_mood_log(str(path), labeled_only=True)
    assert list(labeled["mood"]) == ["deep_work"]


def test_train_main_writes_a_usable_model(tmp_path):
    import pickle

    import pandas as pd

    path = tmp_path / "mood_log.csv"
    model = tmp_path / "model.pkl"
    rows = [_row("idle", i % 10) for i in range(25)] + [_row("deep_work", 500 + i) for i in range(25)]
    _write_log(path, rows)

    assert train_ai.main(["--csv", str(path), "--model", str(model)]) == 0
    clf = pickle.loads(model.read_bytes())
    sample = pd.DataFrame([[520, 5, 1, 0.2, 0.01]], columns=list(FEATURE_NAMES))
    assert clf.predict(sample)[0] == "deep_work"


def test_train_main_refuses_tiny_logs(tmp_path):
    path = tmp_path / "mood_log.csv"
    _write_log(path, [_row("idle", 1)])
    assert train_ai.main(["--csv", str(path), "--model", str(tmp_path / "m.pkl")]) == 1
