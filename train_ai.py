"""
Train the mood classifier from mood_log.csv.

    python train_ai.py                 # train on every logged row
    python train_ai.py --labeled-only  # train only on rows you corrected via feedback

Rows in mood_log.csv are labelled by the app itself (rule-based or model
prediction) unless you corrected them in the feedback dialog, so training on
all rows mostly teaches the model the built-in rules; --labeled-only trains
on your own corrections. The model is saved to mood_classifier.pkl, which
run_popup.py loads on start-up.
"""
from __future__ import annotations

import argparse
import os
import pickle
import sys

import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import accuracy_score
from sklearn.model_selection import train_test_split

from mood_engine import FEATURE_NAMES

CSV_FILE = "mood_log.csv"
MODEL_FILE = "mood_classifier.pkl"
MIN_ROWS = 20


def load_mood_log(path: str = CSV_FILE, labeled_only: bool = False) -> pd.DataFrame:
    """Read the app's mood log (with header) and return clean numeric rows."""
    df = pd.read_csv(path, header=0, on_bad_lines="skip")
    missing = [c for c in ("mood", *FEATURE_NAMES) if c not in df.columns]
    if missing:
        raise ValueError(f"{path} is missing columns: {missing}")

    cols = list(FEATURE_NAMES)
    df[cols] = df[cols].apply(pd.to_numeric, errors="coerce")
    df = df.dropna(subset=cols + ["mood"])

    if labeled_only:
        feedback = df.get("feedback", pd.Series("", index=df.index)).fillna("").astype(str)
        df = df[feedback.str.strip() != ""]
    return df


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--csv", default=CSV_FILE)
    parser.add_argument("--model", default=MODEL_FILE)
    parser.add_argument("--labeled-only", action="store_true", help="use only rows corrected via feedback")
    args = parser.parse_args(argv)

    if not os.path.exists(args.csv):
        print(f"{args.csv} not found. Run the app for a while first so it can log mood checks.")
        return 1

    df = load_mood_log(args.csv, labeled_only=args.labeled_only)
    if len(df) < MIN_ROWS:
        print(f"Not enough data: need at least {MIN_ROWS} rows, have {len(df)}.")
        return 1

    X, y = df[list(FEATURE_NAMES)], df["mood"]
    clf = RandomForestClassifier(n_estimators=100, random_state=42)

    if y.nunique() > 1 and len(df) >= 2 * MIN_ROWS:
        X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)
        clf.fit(X_train, y_train)
        acc = accuracy_score(y_test, clf.predict(X_test)) * 100
        print(f"Hold-out accuracy: {acc:.1f}% on {len(X_test)} rows")

    clf.fit(X, y)  # final model uses all rows
    with open(args.model, "wb") as fh:
        pickle.dump(clf, fh)
    print(f"Model trained on {len(df)} rows ({y.value_counts().to_dict()}) and saved to {args.model}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
