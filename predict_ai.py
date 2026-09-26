"""Predict the mood for the most recent row of mood_log.csv with the trained model."""
from __future__ import annotations

import os
import pickle
import sys

from mood_engine import FEATURE_NAMES
from train_ai import CSV_FILE, MODEL_FILE, load_mood_log


def main() -> int:
    for path in (CSV_FILE, MODEL_FILE):
        if not os.path.isfile(path):
            print(f"{path} not found (run the app, then `python train_ai.py`).")
            return 1

    with open(MODEL_FILE, "rb") as fh:
        model = pickle.load(fh)

    df = load_mood_log(CSV_FILE)
    if df.empty:
        print("No usable rows in the log yet.")
        return 1

    latest = df.iloc[[-1]][list(FEATURE_NAMES)]
    print(f"Latest mood prediction: {model.predict(latest)[0]}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
