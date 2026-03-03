import pandas as pd
import pickle
import os

# --- Config ---
csv_file = "mood_log.csv"
model_file = "mood_classifier.pkl"

# Check files
if not os.path.isfile(csv_file):
    raise FileNotFoundError(f"{csv_file} not found.")
if not os.path.isfile(model_file):
    raise FileNotFoundError(f"{model_file} not found.")

# Load trained model
with open(model_file, "rb") as f:
    model = pickle.load(f)

# Load latest data
column_names = [
    "timestamp",
    "mood",
    "typing_speed",
    "mouse_activity",
    "backspace_activity",
    "avg_keystroke_interval",
    "typing_rhythm_variance"
]
df = pd.read_csv(csv_file, names=column_names, parse_dates=[0], dayfirst=True, header=0)

# Latest row
latest_row = df.iloc[-1]
features = latest_row[["typing_speed", "mouse_activity", "backspace_activity",
                       "avg_keystroke_interval", "typing_rhythm_variance"]].values.reshape(1, -1)

# Convert to DataFrame to avoid sklearn warnings
feature_names = ["typing_speed", "mouse_activity", "backspace_activity",
                 "avg_keystroke_interval", "typing_rhythm_variance"]
features_df = pd.DataFrame(features, columns=feature_names)

# Predict
predicted_mood = model.predict(features_df)[0]
print(f"Latest mood prediction: {predicted_mood}")
