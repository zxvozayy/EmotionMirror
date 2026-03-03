# 🪞 EmotionMirror

> A real-time mood detection desktop app that analyzes your typing and mouse behavior to understand how you're feeling — and responds with an AI-powered animated companion.

---

## 🧠 What It Does

EmotionMirror runs silently in the background, passively monitoring behavioral signals like typing speed, mouse activity, backspace frequency, and keystroke rhythm. Using a trained machine learning model, it predicts your current emotional state and surfaces a friendly animated character that reacts to your mood in real time.

No camera. No microphone. Just behavior.

---

## ✨ Features

- **Real-time mood detection** — Continuously analyzes keyboard & mouse patterns every 60 seconds
- **ML-powered predictions** — Random Forest classifier trained on your own behavioral data
- **Personalized baseline** — Adapts over time to your unique typing style using exponential moving averages
- **AI companion** — Choose between characters with different talking styles (Teacher, Best Friend, Love)
- **Mood logging** — All sessions logged to CSV for model retraining
- **Self-improving AI** — Retrain the model on new data with a single script
- **Sound feedback** — Optional audio responses to mood changes
- **Fully local** — All data stays on your machine

---

## 🖥️ Tech Stack

| Layer | Technology |
|-------|-----------|
| GUI | PyQt6 |
| Input tracking | pynput |
| ML model | scikit-learn (Random Forest) |
| Data processing | pandas, numpy |
| Packaging | PyInstaller |
| Audio | pygame |

---

## 🔍 How It Works

```
User Activity (keyboard + mouse)
        ↓
Feature Engineering (ai.py)
  - typing_count, click_count, mouse_dist
  - keystroke interval mean/std/CV
  - idle time
        ↓
Baseline Comparison (baseline_tracker.py)
  - Dynamic thresholds per user
  - Exponential moving average update
        ↓
Mood Prediction (mood_classifier.pkl)
  - Labels: focused / energized / tired / restless / bored / neutral
        ↓
Animated Popup (mood_popup.py)
  - Character reacts with AI-generated message
```

---

## 🚀 Getting Started

### Prerequisites

- Python 3.10+
- Windows (tested on Windows 10/11)

### Installation

```bash
# Clone the repo
git clone https://github.com/YOUR_USERNAME/EmotionMirror.git
cd EmotionMirror

# Install dependencies
pip install -r requirements.txt
```

### Run

```bash
python run_popup.py
```

On first launch, you'll be prompted to choose your companion character and talking style.

### Train the AI (optional)

If you have collected enough mood data (`mood_log.csv`):

```bash
python train_ai.py
```

To retrain on newly collected data:

```bash
python retrain_ai.py
```

---

## 📁 Project Structure

```
EmotionMirror/
├── ai.py                  # Feature engineering & weak labeling
├── baseline_tracker.py    # Personalized baseline with EMA updates
├── character_selection.py # Character & talking style UI dialog
├── mood_popup.py          # Animated popup with AI-generated responses
├── run_popup.py           # Main entry point
├── train_ai.py            # Initial model training
├── retrain_ai.py          # Retrain model on new data
├── predict_ai.py          # Standalone mood prediction script
├── utils.py               # Resource path helper (dev + PyInstaller)
├── settings.json          # User preferences
├── user_baseline.json     # Personalized behavioral baseline
├── requirements.txt       # Python dependencies
└── resources/             # Character images & sounds
```

---

## 📊 Mood Labels

| Label | Description |
|-------|-------------|
| `focused` | High typing, low clicks — deep work mode |
| `energized` | High typing AND high clicks — active & engaged |
| `tired` | Low typing, low clicks — low activity |
| `restless` | Low typing, high clicks — distracted or browsing |
| `bored` | No typing, no clicks, high idle time |
| `neutral` | Average activity levels |

---

## 🔒 Privacy

EmotionMirror is **100% local**. Your behavioral data never leaves your machine. No data is sent to any server. Logs are stored as CSV files on your own disk.

---

## 📜 License

This project is licensed under a custom restrictive license.  
You may **download and use** this software for personal use only.  
**Copying, modifying, merging, distributing, sublicensing, or selling** any part of this project is strictly prohibited without explicit written permission from the author.  
See the [LICENSE](LICENSE) file for full details.

---

## 👤 Author

Built with ❤️ as a personal project exploring the intersection of behavioral psychology, machine learning, and human-computer interaction.
