import os
if os.name == "nt":
    os.environ.setdefault("QT_MEDIA_BACKEND", "windows")  # must be set before importing PyQt6
# Optional: still keep logging rules
os.environ["QT_LOGGING_RULES"] = "qt.multimedia.ffmpeg.debug=false;qt.multimedia.ffmpeg.warning=false"


import sys
import time
import threading
import csv
import pickle
import json
import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from pynput import keyboard, mouse
from utils import resource_path
from mood_engine import (
    FEATURE_NAMES,
    LOG_COLUMNS,
    WINDOW_SECONDS,
    BaselineTracker,
    Features,
    NonRepeatingPicker,
    Settings,
    compute_features,
    prune_older_than,
    rule_based_mood,
    load_settings as _load_settings_file,
    save_settings as _save_settings_file,
)
from character_selection import CharacterSelectionDialog
from mood_popup import MoodPopup

from PyQt6.QtGui import QPixmap, QColor, QIcon, QAction, QFont
from PyQt6.QtCore import Qt, QTimer, QProcess, QUrl  # QUrl is needed for media path
from PyQt6.QtWidgets import (
    QApplication, QLabel, QDialog, QSystemTrayIcon, QMenu,
    QVBoxLayout, QPushButton, QInputDialog, QMessageBox, QWidget
)
# >>> NEW IMPORTS FOR VIDEO <<<
from PyQt6.QtMultimedia import QMediaPlayer, QAudioOutput, QMediaDevices
from PyQt6.QtMultimediaWidgets import QVideoWidget
import pygame.mixer
import traceback, sys
def _excepthook(exc_type, exc, tb):
    print("UNHANDLED EXCEPTION:\n", "".join(traceback.format_exception(exc_type, exc, tb)), flush=True)
    try:
        from PyQt6.QtWidgets import QApplication
        QApplication.quit()
    except Exception:
        pass
sys.excepthook = _excepthook

# --- Video Splash Screen ---
# --- Video Splash Screen ---
# --- Video Splash Screen (REPLACE YOUR CLASS WITH THIS) ---
from PyQt6.QtCore import Qt, QTimer, QUrl
from PyQt6.QtWidgets import QDialog, QVBoxLayout, QApplication
from PyQt6.QtMultimedia import QMediaPlayer, QAudioOutput
from PyQt6.QtMultimediaWidgets import QVideoWidget

class VideoSplash(QDialog):
    def __init__(self, video_path: str, parent=None):
        super().__init__(parent)

        # frameless + on-top so you actually see it
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint |
            Qt.WindowType.WindowStaysOnTopHint
        )
        self.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose)
        self.setStyleSheet("background:black;")

        # widgets
        self.video_widget = QVideoWidget(self)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.video_widget)

        # player + audio
        self.player = QMediaPlayer(self)
        self.audio_output = QAudioOutput(self)
        self.audio_output.setVolume(1.0)           # make sure it's audible
        self.player.setAudioOutput(self.audio_output)
        self.player.setVideoOutput(self.video_widget)

        # source
        abs_video = os.path.abspath(video_path)
        if os.path.exists(abs_video):
            self.player.setSource(QUrl.fromLocalFile(abs_video))
            print(f"✅ Video source set: {abs_video}")
        else:
            print(f"❌ Error: Video file not found at {abs_video}")
            QTimer.singleShot(300, self.accept)
            return

        # finish / error hooks
        self.player.playbackStateChanged.connect(self._on_state)
        self.player.mediaStatusChanged.connect(self._on_status)
        self.player.errorOccurred.connect(self._on_error)

        # hard safety timeout: close after 10s no matter what
        self._timeout = QTimer(self)
        self._timeout.setSingleShot(True)
        self._timeout.timeout.connect(self.accept)
        self._timeout.start(10000)

    def play_video(self, fullscreen: bool = True):

            self.resize(835, 470)
            sg = QApplication.primaryScreen().availableGeometry()
            self.move(sg.center() - self.rect().center())
            self.show()
            self.raise_()
            self.activateWindow()
            self.player.play()

    # --- slots ---
    def _on_state(self, state):
        from PyQt6.QtMultimedia import QMediaPlayer as MP
        if state == MP.PlaybackState.StoppedState:
            print("ℹ️ Player stopped (end).")
            self.accept()

    def _on_status(self, status):
        from PyQt6.QtMultimedia import QMediaPlayer as MP
        if status == MP.MediaStatus.BufferedMedia:
            print("ℹ️ Media buffered.")
        elif status == MP.MediaStatus.EndOfMedia:
            print("ℹ️ End of media reached.")
            self.accept()
        elif status in (MP.MediaStatus.InvalidMedia, MP.MediaStatus.NoMedia):
            print(f"⚠️ Media status problematic: {status}")
            self.accept()

    def _on_error(self, error, error_string):
        # PyQt6: error is QMediaPlayer.Error enum; error_string is str
        print(f"❌ QMedia error: {error} - {error_string}")
        self.accept()





# ----------------------------------------------------------------------
# (REST OF YOUR ORIGINAL CODE FOLLOWS)
# ----------------------------------------------------------------------

from PyQt6.QtWidgets import (
    QCheckBox, QHBoxLayout, QSpacerItem, QSizePolicy, QFrame
)
from PyQt6.QtGui import QPixmap, QIcon, QFont
from PyQt6.QtWidgets import QGraphicsDropShadowEffect

class InfoDialog(QDialog):
    """
    Aesthetic first-run dialog with a card layout, gradient header,
    emoji bullets, rounded corners & shadow, and a 'Don't show again' option.
    """
    def __init__(self, parent=None):
        super().__init__(parent)

        # --- Window setup (transparent bg so rounded card looks clean) ---
        self.setObjectName("InfoRoot")
        self.setWindowTitle("Welcome • Emotion Mirror")
        self.setWindowIcon(QIcon(resource_path("resources/ZXV.ico")))
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setWindowFlags(
            self.windowFlags()
            & ~Qt.WindowType.WindowContextHelpButtonHint
        )
        self.resize(720, 520)  # nice default size

        # --- Outer layout (transparent) ---
        outer = QVBoxLayout(self)
        outer.setContentsMargins(24, 24, 24, 24)

        # --- Card container ---
        card = QFrame(self)
        card.setObjectName("Card")
        card.setFrameShape(QFrame.Shape.NoFrame)
        card.setMinimumHeight(460)
        card.setStyleSheet("""
            #Card {
                background: #ffffff;
                border-radius: 18px;
            }
        """)

        # Shadow
        shadow = QGraphicsDropShadowEffect(card)
        shadow.setBlurRadius(32)
        shadow.setOffset(0, 16)
        shadow.setColor(QColor(0, 0, 0, 40))
        card.setGraphicsEffect(shadow)

        outer.addWidget(card)

        # --- Card layout ---
        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(0, 0, 0, 0)
        card_layout.setSpacing(0)

        # --- Hero / header area (gradient) ---
        header = QFrame(card)
        header.setObjectName("Header")
        header.setFixedHeight(170)
        header.setStyleSheet("""
            #Header {
                border-top-left-radius: 18px;
                border-top-right-radius: 18px;
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 #7F7DFF, stop:1 #00C2FF);
            }
        """)
        header_layout = QHBoxLayout(header)
        header_layout.setContentsMargins(22, 22, 22, 22)
        header_layout.setSpacing(16)

        # App icon / hero
        icon_lbl = QLabel(header)
        icon_pix = QPixmap(resource_path("resources/ZXV.ico"))
        if not icon_pix.isNull():
            icon_pix = icon_pix.scaled(96, 96, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
            icon_lbl.setPixmap(icon_pix)
        icon_lbl.setFixedSize(96, 96)
        header_layout.addWidget(icon_lbl)

        # Title + subtitle
        title_box = QVBoxLayout()
        title = QLabel("Welcome to Emotion Mirror")
        title.setStyleSheet("color: white;")
        title.setFont(QFont("Segoe UI", 20, QFont.Weight.Bold))
        subtitle = QLabel("Your friendly desktop buddy that reflects your work rhythm.\nPrivacy-first. Lightweight. Helpful.")
        subtitle.setStyleSheet("color: rgba(255,255,255,0.95);")
        subtitle.setFont(QFont("Segoe UI", 11))
        subtitle.setWordWrap(True)

        title_box.addWidget(title)
        title_box.addWidget(subtitle)
        title_box.addStretch(1)
        header_layout.addLayout(title_box)
        header_layout.addStretch(1)

        card_layout.addWidget(header)

        # --- Content area ---
        body = QFrame(card)
        body_layout = QVBoxLayout(body)
        body_layout.setContentsMargins(26, 20, 26, 10)
        body_layout.setSpacing(10)

        # Bullets / features
        blurb = QLabel(
            "Here’s how it helps you stay on track:"
        )
        blurb.setFont(QFont("Segoe UI", 11, QFont.Weight.DemiBold))

        bullets = QLabel(
            "• ✨ <b>Smart Mood Nudges</b> — gentle tips based on your typing & clicking pace.<br>"
            "• 🔒 <b>Private by Design</b> — no passwords or content are read, only activity patterns.<br>"
            "• 📝 <b>Quick Notes</b> — jot ideas, save them with a click.<br>"
            "• 🛎️ <b>Tray Controls</b> — show/hide character, check mood, reset state."
        )
        bullets.setWordWrap(True)
        bullets.setFont(QFont("Segoe UI", 10))
        bullets.setStyleSheet("color: #333;")

        body_layout.addWidget(blurb)
        body_layout.addWidget(bullets)

        # Tip box
        tip_box = QFrame(body)
        tip_box.setObjectName("TipBox")
        tip_box.setStyleSheet("""
            #TipBox {
                background: #F6FAFF;
                border: 1px solid #000000;
                border-radius: 12px;
            }
        """)
        tip_layout = QHBoxLayout(tip_box)
        tip_layout.setContentsMargins(14, 12, 14, 12)
        tip_layout.setSpacing(6)
        tip_layout.setAlignment(Qt.AlignmentFlag.AlignVCenter)

        tip_icon = QLabel("💡")
        tip_icon.setFont(QFont("Segoe UI Emoji", 18))
        tip_icon.setFixedWidth(28)  # 👈 limits its bounding box width tightly
        tip_icon.setAlignment(Qt.AlignmentFlag.AlignVCenter)
        tip_icon.setStyleSheet("margin-right: 0px; padding: 0px;")

        tip_text = QLabel(
            "Pro tip: you can always right-click the system-tray icon to access controls like "
            "<i>Check My Mood</i> or <i>Reset & Forget Me</i>."
        )
        tip_text.setStyleSheet("color: #000;")

        tip_text.setWordWrap(True)
        tip_text.setFont(QFont("Segoe UI", 10))
        tip_layout.addWidget(tip_icon)
        tip_layout.addWidget(tip_text)

        body_layout.addWidget(tip_box)

        # Spacer
        body_layout.addItem(QSpacerItem(0, 8, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Expanding))

        # Footer row: checkbox + buttons
        footer = QHBoxLayout()
        footer.setContentsMargins(0, 6, 0, 0)

        self.never_show_again = QCheckBox("Don’t show this again")
        self.never_show_again.setFont(QFont("Segoe UI", 9))
        footer.addWidget(self.never_show_again)
        footer.addStretch(1)

        btn_privacy = QPushButton("Privacy")
        btn_privacy.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_privacy.setStyleSheet("""
            QPushButton {
                padding: 8px 14px;
                border-radius: 8px;
                background: #eef2ff;
                color: #3949ab;
                border: 1px solid #dde3ff;
                font-weight: 600;
            }
            QPushButton:hover { background: #e7ecff; }
            QPushButton:pressed { background: #dde4ff; }
        """)

        btn_continue = QPushButton("Let’s get started")
        btn_continue.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_continue.setDefault(True)
        btn_continue.setStyleSheet("""
            QPushButton {
                padding: 10px 18px;
                border-radius: 10px;
                color: white;
                font-weight: 700;
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 #6C63FF, stop:1 #00B0FF);
            }
            QPushButton:hover { filter: brightness(1.05); }
            QPushButton:pressed { filter: brightness(0.95); }
        """)

        footer.addWidget(btn_privacy)
        footer.addWidget(btn_continue)

        body_layout.addLayout(footer)
        card_layout.addWidget(body)

        # --- Signals ---
        btn_privacy.clicked.connect(self._show_privacy)
        btn_continue.clicked.connect(self.accept)

        self.setStyleSheet("""
        #Card QLabel, #Card QCheckBox, #Card QPushButton {
            color: black;
        }
        """)

    # Center on screen
        self._center()

    def _center(self):
        screen_geom = QApplication.primaryScreen().availableGeometry()
        self.move(screen_geom.center() - self.rect().center())

    def _show_privacy(self):
        QMessageBox.information(
            self,
            "Privacy",
            (
                "Emotion Mirror observes <b>behavioral signals only</b> (typing cadence, mouse clicks/movement counts) "
                "to estimate your work rhythm.\n\n"
                "• It does <b>not</b> read keystroke content, passwords, or files.\n"
                "• Logs stay on your device.\n"
                "• You can reset & delete all data anytime from the tray menu.\n"
            )
        )



class SystemTrayIcon(QSystemTrayIcon):
    def __init__(self, icon, popup_widget, head_widget, parent=None):
        super().__init__(icon, parent)
        self.popup_widget = popup_widget
        self.head_widget = head_widget

        # external reset callback (set from main)
        self._reset_callback = None

        # Create context menu (right-click menu)
        menu = QMenu()

        # Menu actions
        show_character_action = QAction("Show Character", self)
        show_character_action.triggered.connect(self.show_character)

        check_mood_action = QAction("Check My Mood", self)
        check_mood_action.triggered.connect(self.check_mood_now)

        separator1 = menu.addSeparator()

        hide_character_action = QAction("Hide Character", self)
        hide_character_action.triggered.connect(self.hide_character)

        # --- Reset & Forget Me action (new) ---
        reset_action = QAction("Reset & Forget Me", self)
        reset_action.triggered.connect(self._on_reset_clicked)

        separator2 = menu.addSeparator()

        quit_action = QAction("Exit Mood Tracker", self)
        quit_action.triggered.connect(self.exit_app)

        # Add actions to menu
        menu.addAction(show_character_action)
        menu.addAction(check_mood_action)
        menu.addAction(separator1)
        menu.addAction(hide_character_action)
        menu.addAction(reset_action)        # <-- reset button in tray
        menu.addAction(separator2)
        menu.addAction(quit_action)

        self.setContextMenu(menu)
        self.setToolTip("Mood Tracker - Click to open menu")

        # Double-click to show character
        self.activated.connect(self.on_tray_click)

    def set_reset_callback(self, cb):
        """Register a callback to perform a hard reset (wired from main)."""
        self._reset_callback = cb

    def _on_reset_clicked(self):
        if self._reset_callback:
            self._reset_callback()
        else:
            QMessageBox.information(None, "Reset", "Reset action is not configured.")

    def on_tray_click(self, reason):
        if reason == QSystemTrayIcon.ActivationReason.DoubleClick:
            self.show_character()

    def show_character(self):
        if self.head_widget:
            self.head_widget.show()
            self.head_widget.raise_()
            print("👁️ Character shown from system tray")

    def hide_character(self):
        if self.head_widget:
            self.head_widget.hide()
            print("👁️ Character hidden via system tray")

    def check_mood_now(self):
        if self.popup_widget:
            self.popup_widget.mood_requested.emit()
            print("🔍 Mood check requested from system tray")

    def exit_app(self):
        print("🚪 Exiting from system tray...")
        QApplication.quit()

# --- Define paths to your local image files ---
HEAD_IMAGE_PATH = resource_path("resources/buddy3.png")
BUDDY_IMAGE_PATH = resource_path("resources/buddy.png")
BUDDY3_IMAGE_PATH = resource_path("resources/buddy3.png")

POPIN_SOUND_PATH = resource_path("resources/giris.wav")
POPOUT_SOUND_PATH = resource_path("resources/cikis.wav")
CLICK_SOUND_PATH = resource_path("resources/menu.wav")

# >>> NEW: Define video path <<<
INTRO_VIDEO_PATH = resource_path("resources/Black_Video.mp4")


# Check if files exist
def check_files():
    files_to_check = [HEAD_IMAGE_PATH, BUDDY_IMAGE_PATH, POPIN_SOUND_PATH, POPOUT_SOUND_PATH, CLICK_SOUND_PATH, INTRO_VIDEO_PATH]
    for file_path in files_to_check:
        if not os.path.exists(file_path):
            print(f"⚠️ Warning: File not found at {file_path}")
        else:
            print(f"✅ Found: {file_path}")


# MODEL CONFIGURATION
MODEL_PATH = "mood_classifier.pkl"
RETRAIN_INTERVAL = 12

# Try to load trained model
clf = None
if os.path.exists(MODEL_PATH):
    try:
        with open(MODEL_PATH, "rb") as f:
            clf = pickle.load(f)
        print("✅ AI model loaded!")
    except Exception as e:
        print(f"⚠️ Error loading model: {e}. Model will not be used.")
        clf = None
else:
    print("⚠️ No trained model found, using rule-based fallback.")


# --- Configuration & Settings Management ---
class Config:
    MOOD_DATA = {
        "idle": {
            "comments": [
                "You’ve been quiet for a while — quick stretch maybe?",
                "Looks like you stepped away. Don’t forget to hydrate.",
                "Screen break time? Good idea for the eyes."
            ],
            "tips": [
                "💡 Walk around a bit — it helps your focus reset.",
                "💡 Maybe check your posture while you’re at it."
            ],
            "color": QColor(135, 206, 250),
        },
        "low_energy": {
            "comments": [
                "You seem a little tired — been at it for a while?",
                "Your pace slowed down; maybe take a quick breather.",
                "Eyes on the screen too long? Stand up for a sec."
            ],
            "tips": [
                "😴 2-minute stretch might do wonders right now.",
                "😴 Refill your drink and take a deep breath."
            ],
            "color": QColor(144, 238, 144),
        },
        "deep_work": {
            "comments": [
                "Deep focus detected. You’re locked in, my friend.",
                "That’s the creative flow — rare and powerful.",
                "Every click and key press feels natural right now, huh?"
            ],
            "tips": [
                "🧠 Silence distractions and ride this wave of focus.",
                "🧠 Don’t forget to rest your wrists occasionally."
            ],
            "color": QColor(255, 228, 181),
        },
        "struggling": {
            "comments": [
                "Lots of corrections happening... debugging life?",
                "Take a breath — not everything compiles on first try.",
                "Might be time for a snack or a small walk?"
            ],
            "tips": [
                "🤔 Step away for a minute, clarity comes easier then.",
                "🤔 Don’t fight the code — talk it through instead."
            ],
            "color": QColor(173, 216, 230),
        },
        "browsing": {
            "comments": [
                "Lots of clicking… research mode or procrastination?",
                "Tab hopping detected. You okay, explorer?",
                "You’re drifting — maybe time to refocus?"
            ],
            "tips": [
                "🌐 Limit yourself to 3 open tabs for better focus.",
                "🌐 Jot down distractions for later, stay on track."
            ],
            "color": QColor(255, 102, 0, 230),
        },
        "steady": {
            "comments": [
                "You’ve got a nice steady pace going — good balance.",
                "Consistent activity, calm focus. Keep it up!",
                "You’re working smart, not hard. That’s the goal."
            ],
            "tips": [
                "😌 Stay in this rhythm — balance breeds productivity.",
                "😌 Reward yourself after this task."
            ],
            "color": QColor(120, 150, 150, 230),
        },
    }

    LOG_FILE = "mood_log.csv"
    NOTES_FILE = "notes.txt"
    SETTINGS_FILE = "settings.json"  # New settings file
    POPUP_DURATION_MS = 12000
    CHECK_INTERVAL_MS = 300000

    FEEDBACK_BATCH_SIZE = 5


def load_settings(settings=None):
    """Load settings.json; defaults are used (and later saved) when it is missing."""
    loaded = _load_settings_file(Config.SETTINGS_FILE)
    if settings is None:
        return loaded
    settings.__dict__.update(loaded.__dict__)
    if os.path.exists(Config.SETTINGS_FILE):
        print("✅ Settings loaded.")
    else:
        print("ℹ️ Settings file not found. Using default settings.")
    return settings


def save_settings(settings):
    try:
        _save_settings_file(
            Settings(
                is_feedback_enabled=settings.is_feedback_enabled,
                is_first_run=settings.is_first_run,
                user_name=settings.user_name,
                is_sound_enabled=settings.is_sound_enabled,
            ),
            Config.SETTINGS_FILE,
        )
        print("✅ Settings saved.")
    except Exception as e:
        print(f"❌ Error saving settings: {e}")


# --- AI Retraining ---
def retrain_model(window_size: int = 800, min_labeled_total: int = 24, min_per_class: int = 5):
    """
    Retrain the model using only the last `window_size` labeled rows,
    and only if there are >= `min_labeled_total` labeled rows AND
    every mood present has at least `min_per_class` labeled samples.
    """
    csv_file = Config.LOG_FILE
    model_file = MODEL_PATH

    if not os.path.exists(csv_file):
        print("ℹ️ No mood log yet. Skipping retrain.")
        return None

    try:
        df = pd.read_csv(csv_file, header=0)

        # Guard: required columns
        required_cols = {'mood', 'feedback', *FEATURE_NAMES}
        missing = [c for c in required_cols if c not in df.columns]
        if missing:
            print(f"⚠️ Retrain aborted: missing columns in CSV: {missing}")
            return None

        # Keep only labeled rows (user feedback present & not empty)
        df['feedback'] = df['feedback'].fillna('').astype(str)
        df_labeled = df[df['feedback'].str.strip() != ''].copy()

        labeled_total = len(df_labeled)
        if labeled_total < min_labeled_total:
            print(f"⏭️ Retrain skipped: need at least {min_labeled_total} labeled rows, have {labeled_total}.")
            return None

        # Sliding window: only last N labeled rows
        df_labeled = df_labeled.tail(window_size)

        # Make sure feature columns are numeric & drop NaNs
        feature_cols = list(FEATURE_NAMES)
        df_labeled[feature_cols] = df_labeled[feature_cols].apply(pd.to_numeric, errors='coerce')
        before_drop = len(df_labeled)
        df_labeled.dropna(subset=feature_cols + ['mood'], inplace=True)
        after_drop = len(df_labeled)
        if after_drop == 0:
            print("⏭️ Retrain skipped: no valid rows after cleaning.")
            return None
        if after_drop < min_labeled_total:
            print(f"⏭️ Retrain skipped: only {after_drop} valid labeled rows after cleaning; need {min_labeled_total}.")
            return None

        # Class coverage: each present mood must have at least `min_per_class` samples
        class_counts = df_labeled['mood'].value_counts()
        too_small = class_counts[class_counts < min_per_class]
        if not too_small.empty:
            print(
                "⏭️ Retrain skipped: not enough labeled examples per mood.\n"
                f"   Counts: {class_counts.to_dict()}\n"
                f"   Each mood needs ≥ {min_per_class} in the current window."
            )
            return None

        # Prepare X/y
        X = df_labeled[feature_cols]
        y = df_labeled['mood']

        # Train
        clf_local = RandomForestClassifier(n_estimators=100, random_state=42)
        clf_local.fit(X, y)

        # Persist
        with open(model_file, "wb") as f:
            pickle.dump(clf_local, f)

        print(
            f"✅ AI retrained on {len(df_labeled)} labeled rows "
            f"(window={window_size}). Class counts: {class_counts.to_dict()}"
        )
        return clf_local

    except Exception as e:
        print(f"❌ Error during retraining: {e}")
        return None



# --- Input Tracking Class ---
class InputTracker:
    def __init__(self):
        self.keystrokes = []
        self.keystroke_timings = []
        self.mouse_clicks = []
        self.mouse_movements = []
        self.backspace_presses = []
        self.last_keystroke_time = None
        self.lock = threading.Lock()
        self.mood_check_counter = 0
        self.retrain_counter = 0

    def on_key_press(self, key):
        current_time = time.time()
        with self.lock:
            if key == keyboard.Key.backspace:
                self.backspace_presses.append(current_time)
            else:
                self.keystrokes.append(current_time)
            if self.last_keystroke_time is not None:
                # (timestamp, gap) so rhythm stats use the same rolling window
                self.keystroke_timings.append((current_time, current_time - self.last_keystroke_time))
            self.last_keystroke_time = current_time

    def on_click(self, x, y, button, pressed):
        if pressed:
            with self.lock:
                self.mouse_clicks.append(time.time())

    def on_mouse_move(self, x, y):
        current_time = time.time()
        with self.lock:
            if not self.mouse_movements or current_time - self.mouse_movements[-1][0] > 0.5:
                self.mouse_movements.append((current_time, x, y))

    def analyze_mood(self):
        """Return (mood, Features) for the last WINDOW_SECONDS of activity."""
        now = time.time()
        with self.lock:
            # Keep memory bounded: only the current window is ever needed.
            for items in (self.keystrokes, self.mouse_clicks, self.backspace_presses,
                          self.keystroke_timings, self.mouse_movements):
                prune_older_than(items, now, WINDOW_SECONDS)
            features = compute_features(
                self.keystrokes, self.mouse_clicks, self.backspace_presses,
                self.keystroke_timings, now, WINDOW_SECONDS,
            )

        global clf
        if clf is not None:
            try:
                features_df = pd.DataFrame([features.as_row()], columns=list(FEATURE_NAMES))
                return clf.predict(features_df)[0], features
            except Exception as e:
                print(f"Error with AI prediction: {e}. Falling back to rule-based.")
        return rule_based_mood(features), features


# --- GUI Components ---
class PersistentHead(QLabel):
    def __init__(self, head_image_path, popup):
        super().__init__()
        self.resize(1200, 900)  # 3× larger (default is usually around 400x300)

        self.popup = popup
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.WindowStaysOnTopHint)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        if os.path.exists(head_image_path):
            if "woman2.png" in head_image_path:
                self.head_pixmap = QPixmap(head_image_path).scaled(200, 200, Qt.AspectRatioMode.KeepAspectRatioByExpanding, Qt.TransformationMode.SmoothTransformation)
            else:
                self.head_pixmap = QPixmap(head_image_path).scaled(100, 100, Qt.AspectRatioMode.KeepAspectRatioByExpanding, Qt.TransformationMode.SmoothTransformation)
            self.setPixmap(self.head_pixmap)
            self.setFixedSize(self.head_pixmap.size())
        else:
            self.setFixedSize(100, 100)
            self.setStyleSheet("background-color: rgba(255, 100, 100, 200); border-radius: 50px; color: white;")
            self.setText("🤖")
            self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        try:
            screen_geom = QApplication.primaryScreen().availableGeometry()
            self.move(screen_geom.right() - self.width() + 15, screen_geom.top() + (screen_geom.height() - self.height()) // 2)
        except Exception as e:
            self.move(100, 100)
        self.show()

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            # Play a sound when the character is clicked
            if self.popup.is_sound_enabled:
                try:
                    if pygame.mixer.get_init():
                        sound = pygame.mixer.Sound(CLICK_SOUND_PATH)
                        sound.play()
                except Exception as e:
                    print(f"Could not play sound: {e}")
            self.popup.show_menu()

_PICKER = NonRepeatingPicker()


# --- Helper Functions ---
def get_comment_and_tip(mood):
    """Pick a curated comment + tip for the mood (tone is applied by MoodPopup)."""
    mood_info = Config.MOOD_DATA.get(mood, None)
    if mood_info:
        comment = _PICKER.pick(mood, "comments", mood_info["comments"])
        tip = _PICKER.pick(mood, "tips", mood_info["tips"])
        color = mood_info["color"]
    else:
        comment = "Feeling... mysterious. 👀"
        tip = "Just keep going."
        color = QColor(200, 200, 200, 230)
    return comment, tip, color


def log_mood(mood, features: Features, feedback=None):
    file_exists = os.path.isfile(Config.LOG_FILE)
    with open(Config.LOG_FILE, 'a', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        if not file_exists:
            writer.writerow(LOG_COLUMNS)
        writer.writerow([
            time.strftime('%Y-%m-%d %H:%M:%S', time.localtime()),
            mood,
            *[round(v, 3) for v in features.as_row()],
            feedback if feedback is not None else ""
        ])


# --- Mood Check and Popup Logic ---
def mood_check_and_show(popup, tracker, baseline, settings, forced_mood=None):
    print("🔍 Running mood check...")
    if forced_mood:
        mood = forced_mood
        features = Features(0, 0, 0, 0.0, 0.0)
    else:
        mood, features = tracker.analyze_mood()
        baseline.update({name: getattr(features, name) for name in FEATURE_NAMES})

    log_mood(mood, features, feedback="")
    comment, tip, color = get_comment_and_tip(mood)

    popup.show_mood(comment, tip, color)

    tracker.mood_check_counter += 1
    tracker.retrain_counter += 1

    # Check if feedback is enabled before showing the dialog
    if settings.is_feedback_enabled and tracker.mood_check_counter >= Config.FEEDBACK_BATCH_SIZE:
        tracker.mood_check_counter = 0
        popup.show_feedback_dialog(auto_trigger=True)

    if tracker.retrain_counter >= RETRAIN_INTERVAL:
        tracker.retrain_counter = 0
        global clf
        clf_new = retrain_model()
        if clf_new is not None:
            clf = clf_new


# --- Event Handlers ---
def handle_mood_request(popup, tracker, baseline, settings):
    print("📱 Manual mood check requested")
    mood_check_and_show(popup, tracker, baseline, settings)


def handle_reset_request(popup, tracker, baseline, settings):
    print("🔄 Reset request - user feeling better!")
    mood_check_and_show(popup, tracker, baseline, settings, forced_mood="steady")


def handle_save_notes(note_text):
    print(f"💾 Saving note: {note_text[:50]}...")
    try:
        with open(Config.NOTES_FILE, 'a', encoding='utf-8') as f:
            timestamp = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime())
            f.write(f"--- {timestamp} ---\n{note_text}\n\n")
        print("✅ Note saved successfully")
    except Exception as e:
        print(f"❌ Error saving note: {e}")


def handle_sound_toggle(state):
    global settings
    settings.is_sound_enabled = state
    save_settings(settings)
    print(f"Sound effects {'enabled' if state else 'disabled'}.")


def handle_feedback_submitted(new_mood, feedback_text):
    print(f"📝 Feedback received: {new_mood} - {feedback_text}")

    if not os.path.exists(Config.LOG_FILE):
        print("⚠️ Mood CSV not found, feedback skipped.")
        return

    # Read all rows
    with open(Config.LOG_FILE, 'r', newline='', encoding='utf-8') as f:
        rows = list(csv.reader(f))

    # Need at least header + one data row
    if len(rows) <= 1:
        print("ℹ️ No rows to update.")
        return

    # Update ONLY the last data row (the most recent mood)
    last_idx = len(rows) - 1
    rows[last_idx][1] = new_mood          # overwrite mood column
    rows[last_idx][-1] = feedback_text    # write feedback text

    # Write back
    with open(Config.LOG_FILE, 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerows(rows)

    print("✅ Last mood updated in CSV")



# New handler to toggle feedback state
def handle_feedback_toggle(state):
    global settings
    settings.is_feedback_enabled = state
    save_settings(settings)
    print(f"Feedback popups {'enabled' if state else 'disabled'}.")


# --- Restart helper (NEW) ---
def restart_app():
    """
    Relaunches the current program as a new detached process and exits this one.
    Works for both plain scripts and PyInstaller bundles.
    """
    try:
        program = sys.executable  # python.exe OR the PyInstaller .exe
        args = sys.argv[:]        # preserve CLI args

        ok = QProcess.startDetached(program, args)
        if not ok:
            print("⚠️ QProcess.startDetached failed. You may need to relaunch manually.")
        else:
            print("♻️ Relaunch started successfully.")
    except Exception as e:
        print(f"⚠️ Restart failed to spawn: {e}")
    finally:
        QApplication.quit()


# --- Hard Reset helper (uses restart_app now) ---
def hard_reset_ai(app, tracker, baseline, settings):
    reply = QMessageBox.question(
        None,
        "Reset & Forget Me",
        "This will delete your settings, logs, model and notes, and restart the app.\n\nContinue?",
        QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        QMessageBox.StandardButton.No,
        )
    if reply != QMessageBox.StandardButton.Yes:
        return

    # Files to delete
    for path in [Config.SETTINGS_FILE, Config.LOG_FILE, MODEL_PATH, Config.NOTES_FILE]:
        try:
            if os.path.exists(path):
                os.remove(path)
                print(f"🗑️ Deleted: {path}")
        except Exception as e:
            print(f"⚠️ Could not delete {path}: {e}")

    # Clear in-memory state
    try:
        tracker.keystrokes.clear()
        tracker.keystroke_timings.clear()
        tracker.mouse_clicks.clear()
        tracker.mouse_movements.clear()
        tracker.backspace_presses.clear()
        tracker.last_keystroke_time = None
        tracker.mood_check_counter = 0
        tracker.retrain_counter = 0
        baseline.history.clear()
        print("🧹 Cleared in-memory trackers.")
    except Exception as e:
        print(f"⚠️ Could not clear runtime state: {e}")

    # Reset settings and mark as first run
    try:
        settings.is_first_run = True
        settings.user_name = "User"
        settings.is_sound_enabled = True
        settings.is_feedback_enabled = True
        save_settings(settings)
        print("🔄 Settings reset to defaults.")
    except Exception as e:
        print(f"⚠️ Could not reset settings: {e}")

    # 🔁 Restart the app (Qt-native, reliable)
    print("♻️ Restarting application...")
    restart_app()
    return

class NameDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Let's Get Acquainted ✨")
        self.setFixedSize(420, 300)
        self.setWindowFlags(
            Qt.WindowType.Dialog | Qt.WindowType.FramelessWindowHint
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)

        # --- Outer layout ---
        outer_layout = QVBoxLayout(self)
        outer_layout.setContentsMargins(15, 15, 15, 15)

        # --- Card container ---
        card = QWidget()
        card.setObjectName("Card")
        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(30, 30, 30, 30)
        card_layout.setSpacing(18)

        # Title
        title = QLabel("Before we begin… 💭")
        title.setFont(QFont("Segoe UI", 16, QFont.Weight.Bold))
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title.setStyleSheet("color: black;")  # 👈 Black text

        # Subtitle
        subtitle = QLabel("What should your buddy call you?")
        subtitle.setFont(QFont("Segoe UI", 11))
        subtitle.setAlignment(Qt.AlignmentFlag.AlignCenter)
        subtitle.setStyleSheet("color: black;")  # 👈 Black text

        # Input field
        from PyQt6.QtWidgets import QLineEdit, QPushButton
        self.name_input = QLineEdit()
        self.name_input.setPlaceholderText("Enter your name here...")
        self.name_input.setFont(QFont("Segoe UI", 11))
        self.name_input.setFixedHeight(36)
        self.name_input.setStyleSheet("""
            QLineEdit {
                border: 2px solid #aaa;
                border-radius: 10px;
                padding-left: 10px;
                background-color: white;
                color: black;
            }
            QLineEdit:focus {
                border: 2px solid #6699ff;
            }
        """)

        # OK button
        ok_button = QPushButton("Continue →")
        ok_button.setFont(QFont("Segoe UI Semibold", 11))
        ok_button.setCursor(Qt.CursorShape.PointingHandCursor)
        ok_button.clicked.connect(self.accept)
        ok_button.setStyleSheet("""
            QPushButton {
                background-color: white;
                color: black;
                border: 2px solid #555;
                border-radius: 10px;
                padding: 8px 20px;
            }
            QPushButton:hover {
                background-color: #f2f2f2;
            }
        """)

        # Add widgets
        card_layout.addWidget(title)
        card_layout.addWidget(subtitle)
        card_layout.addWidget(self.name_input)
        card_layout.addWidget(ok_button, alignment=Qt.AlignmentFlag.AlignCenter)
        outer_layout.addWidget(card)

        # --- Card style ---
        self.setStyleSheet("""
            #Card {
                background-color: white;
                border-radius: 18px;
            }
        """)

    def get_name(self):
        return self.name_input.text().strip()


# --- Main Function ---
def main():
    global settings  # handlers use this
    print("🚀 Starting Mood Tracker...")
    check_files()

    app = QApplication(sys.argv)
    app.setWindowIcon(QIcon(resource_path("resources/ZXV.ico")))
    app.setQuitOnLastWindowClosed(False)
    app.setApplicationName("Mood Tracker")
    app.setApplicationDisplayName("Mood Tracker")
    app.setApplicationVersion("1.0")
    app.setOrganizationName("EmotionMirror")
    app.setOrganizationDomain("mood-tracker.local")
    # --- VIDEO SPLASH SCREEN RUNS HERE ---
    # after: app = QApplication(sys.argv)
    if os.path.exists(INTRO_VIDEO_PATH):
        splash = VideoSplash(INTRO_VIDEO_PATH)
        splash.play_video(fullscreen=True)   # or False to use a centered 960x540 window
        print("🎬 Splash shown (visible:", splash.isVisible(), ", fullscreen:", splash.isFullScreen(), ")")
        splash.exec()                        # blocks until video finishes/closes
        print("✅ Video playback finished. Launching application.")
    else:
        print("ℹ️ Skipping video splash: Video file not found.")




    # Settings
    settings = load_settings()
    if not os.path.exists(Config.SETTINGS_FILE):
        save_settings(settings)  # create settings.json with defaults on first launch

    # Sounds (optional: only init if enabled)
    try:
        pygame.mixer.init()
        print("✅ Pygame mixer initialized.")
    except Exception as e:
        print(f"⚠️ Error initializing pygame mixer: {e}. Sound effects will be disabled.")

    baseline = BaselineTracker()
    print("✅ QApplication created")

    # First-run welcome
    if settings.is_first_run:
        info_dialog = InfoDialog()
        info_dialog.exec()
        name_dialog = NameDialog()
        if name_dialog.exec() == QDialog.DialogCode.Accepted:
            entered_name = name_dialog.get_name()
            settings.user_name = entered_name if entered_name else "Buddy"
        else:
            settings.user_name = "Buddy"

    # If user checks "Don't show again", keep it hidden next time
        settings.is_first_run = not info_dialog.never_show_again.isChecked()
        save_settings(settings)

    # --- Character selection (single dialog, single exec, single connect) ---
    dialog = CharacterSelectionDialog()

    # Defaults in case user cancels
    selected_buddy_paths = (resource_path("resources/buddy3.png"),
                            resource_path("resources/buddy.png"))
    selected_mode = "Best Friend"

    def on_character_selected(paths, mode):
        nonlocal selected_buddy_paths, selected_mode
        selected_buddy_paths = paths        # tuple: (head, popup)
        selected_mode = mode
        print(f"✅ Selected character: {paths}, Mode: {mode}")

    dialog.character_selected.connect(on_character_selected)

    if dialog.exec() != QDialog.DialogCode.Accepted:
        print("⚠️ No selection made. Using default character and mode.")

    head_image_path, popup_image_path = selected_buddy_paths

    # --- App widgets ---
    tracker = InputTracker()

    # ✅ If sound files are missing, disable them to prevent mixer-related crashes
    popin_path_safe = POPIN_SOUND_PATH if (POPIN_SOUND_PATH and os.path.exists(POPIN_SOUND_PATH)) else None
    popout_path_safe = POPOUT_SOUND_PATH if (POPOUT_SOUND_PATH and os.path.exists(POPOUT_SOUND_PATH)) else None

    popup = MoodPopup(
        popup_image_path,
        settings.user_name,
        selected_mode=selected_mode,
        is_feedback_enabled_initial=settings.is_feedback_enabled,
        is_sound_enabled_initial=settings.is_sound_enabled,
        POPIN_SOUND_PATH=popin_path_safe,
        POPOUT_SOUND_PATH=popout_path_safe
    )
    settings.selected_mode = selected_mode
    print("✅ Popup initialized")

    head = PersistentHead(head_image_path, popup)
    popup.set_head_widget(head)
    print("✅ Head widget created and linked")

    # Connect popup signals
    popup.mood_requested.connect(lambda: handle_mood_request(popup, tracker, baseline, settings))
    popup.reset_requested.connect(lambda: handle_reset_request(popup, tracker, baseline, settings))
    popup.save_notes_requested.connect(handle_save_notes)
    popup.feedback_submitted.connect(handle_feedback_submitted)
    popup.feedback_toggled.connect(handle_feedback_toggle)
    popup.sound_toggled.connect(handle_sound_toggle)

    # System tray
    if not QSystemTrayIcon.isSystemTrayAvailable():
        print("⚠️ System tray is not available on this system.")
    else:
        # Correct indentation and simple fallback icon
        icon_path = resource_path("resources/ZXV.ico") if os.name == 'nt' else resource_path("resources/buddy3.png")
        if os.path.exists(icon_path):
            tray_icon = QIcon(icon_path)
        else:
            pixmap = QPixmap(32, 32)
            pixmap.fill(QColor(100, 150, 250))
            tray_icon = QIcon(pixmap)

        app.system_tray = SystemTrayIcon(tray_icon, popup, head, app)
        # wire reset callback here:
        app.system_tray.set_reset_callback(lambda: hard_reset_ai(app, tracker, baseline, settings))
        app.system_tray.show()
        print("✅ System tray icon created and shown")

    # Input listeners (daemon=True so they don't block shutdown)
    try:
        kb_listener = keyboard.Listener(on_press=tracker.on_key_press)
        kb_listener.daemon = True  # <-- added
        ms_listener = mouse.Listener(on_click=tracker.on_click, on_move=tracker.on_mouse_move)
        ms_listener.daemon = True  # <-- added
        kb_listener.start()
        ms_listener.start()
        print("✅ Input listeners started")
    except Exception as e:
        print(f"⚠️ Error starting input listeners: {e}. Please check permissions.")

    # Periodic checks
    app.mood_timer = QTimer()  # keep a reference on the app object
    app.mood_timer.setInterval(Config.CHECK_INTERVAL_MS)  # 300_000 ms = 5 min
    app.mood_timer.timeout.connect(lambda: mood_check_and_show(popup, tracker, baseline, settings))
    app.mood_timer.start()
    print("✅ Periodic checks scheduled")

    print("🎉 Application ready! Look for your character and popup...")
    sys.exit(app.exec())


if __name__ == "__main__":
    main()