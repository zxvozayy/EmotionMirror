import pandas as pd
from sklearn.model_selection import train_test_split
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import accuracy_score
import pickle
import os

# --- Config ---
csv_file = "mood_log.csv"
model_file = "mood_classifier.pkl"

# Column names
column_names = [
    'timestamp',
    'mood',
    'typing_speed',
    'mouse_activity',
    'backspace_activity',  # NEW
    'avg_keystroke_interval',
    'typing_rhythm_variance'
]

# --- Read CSV safely ---
if not os.path.exists(csv_file):
    raise FileNotFoundError(f"{csv_file} not found. Make sure to clean your log file first.")

df = pd.read_csv(csv_file, header=None, names=column_names, on_bad_lines='skip')

# Convert numeric columns
numeric_cols = ['typing_speed', 'mouse_activity', 'backspace_activity', 'avg_keystroke_interval', 'typing_rhythm_variance']
for col in numeric_cols:
    df[col] = pd.to_numeric(df[col], errors='coerce')

# Drop rows with NaNs in numeric columns
df.dropna(subset=numeric_cols, inplace=True)

# Features and labels
X = df[numeric_cols]
y = df['mood']

# Train/test split
X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)

# Train model
clf = RandomForestClassifier(n_estimators=100, random_state=42)
clf.fit(X_train, y_train)

# Evaluate
y_pred = clf.predict(X_test)
accuracy = accuracy_score(y_test, y_pred) * 100
print(f"Model trained! Accuracy: {accuracy:.2f}%")

# Save model
with open(model_file, "wb") as f:
    pickle.dump(clf, f)

print(f"Model saved as {model_file}")
