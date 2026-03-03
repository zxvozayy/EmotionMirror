import json
import os
import numpy as np

BASELINE_FILE = "user_baseline.json"

class BaselineTracker:
    def __init__(self):
        self.baseline = {
            "typing_speed": {"mean": 200, "std": 50},     # default guess
            "backspaces": {"mean": 5, "std": 3},
            "mouse_activity": {"mean": 100, "std": 30},
            "tab_switches": {"mean": 10, "std": 5}
        }
        self.load()

    def load(self):
        if os.path.exists(BASELINE_FILE):
            with open(BASELINE_FILE, "r") as f:
                self.baseline = json.load(f)

    def save(self):
        with open(BASELINE_FILE, "w") as f:
            json.dump(self.baseline, f, indent=4)

    def update(self, features: dict):
        """
        Update baseline with new observed data.
        features = {
            "typing_speed": int,
            "backspaces": int,
            "mouse_activity": int,
            "tab_switches": int
        }
        """
        for key in self.baseline:
            old_mean = self.baseline[key]["mean"]
            old_std = self.baseline[key]["std"]
            new_val = features[key]

            # simple exponential moving average
            updated_mean = 0.9 * old_mean + 0.1 * new_val
            updated_std = 0.9 * old_std + 0.1 * abs(new_val - updated_mean)

            self.baseline[key]["mean"] = round(updated_mean, 2)
            self.baseline[key]["std"] = round(updated_std, 2)

        self.save()

    def get_thresholds(self):
        """
        Returns dynamic thresholds as (low, high) per feature.
        """
        thresholds = {}
        for key, stats in self.baseline.items():
            mean, std = stats["mean"], stats["std"]
            thresholds[key] = (mean - 2*std, mean + 2*std)
        return thresholds
