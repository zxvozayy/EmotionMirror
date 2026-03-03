import pandas as pd
import pickle
import os
from sklearn.ensemble import RandomForestClassifier

MODEL_PATH = "mood_classifier.pkl"
CSV_FILE = "mood_log.csv"
MIN_ROWS = 20  # minimum rows required for retraining

# --- Define column names to match your CSV ---
column_names = [
    'timestamp',
    'mood',
    'typing_speed',
    'mouse_activity',
    'backspace_activity',
    'avg_keystroke_interval',
    'typing_rhythm_variance',
    'feedback'
]

# Check if CSV exists
if not os.path.exists(CSV_FILE):
    print(f"⚠️ {CSV_FILE} not found. Cannot retrain AI.")
    exit()

# Load CSV without assuming a header
df = pd.read_csv(CSV_FILE, names=column_names, header=None)

# Convert numeric columns to numeric type
numeric_cols = ['typing_speed', 'mouse_activity', 'backspace_activity', 'avg_keystroke_interval', 'typing_rhythm_variance']
df[numeric_cols] = df[numeric_cols].apply(pd.to_numeric, errors='coerce')

# Drop rows with missing numeric data
df.dropna(subset=numeric_cols, inplace=True)

if len(df) < MIN_ROWS:
    print(f"⚠️ Not enough data to retrain. Need at least {MIN_ROWS} rows, got {len(df)}.")
    exit()

# Separate features and target
X = df[numeric_cols]
y = df['mood']

# Train RandomForestClassifier
clf = RandomForestClassifier(n_estimators=100, random_state=42)
clf.fit(X, y)

# Save model
with open(MODEL_PATH, "wb") as f:
    pickle.dump(clf, f)

print(f"✅ AI retrained successfully on {len(df)} entries!")
