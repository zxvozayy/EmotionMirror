import os
import time
import pygame.mixer
from PyQt6.QtWidgets import QLabel, QFrame, QPushButton, QWidget, QVBoxLayout, QTextEdit, QMessageBox, QApplication, QInputDialog
from PyQt6.QtGui import QPixmap, QPainter, QColor, QFont, QPen, QFontMetrics
from PyQt6.QtCore import Qt, QTimer, QPropertyAnimation, QPoint, QEasingCurve, pyqtSignal, QRect
from utils import resource_path


class MoodPopup(QLabel):

    mood_requested = pyqtSignal()
    reset_requested = pyqtSignal()
    save_notes_requested = pyqtSignal(str)
    clear_notes_requested = pyqtSignal()
    feedback_submitted = pyqtSignal(str, str)
    feedback_toggled = pyqtSignal(bool)  # New signal for the toggle button
    sound_toggled = pyqtSignal(bool)

    def __init__(self, image_path, user_name, head_widget=None, selected_mode="Best Friend",
                 is_feedback_enabled_initial=True, is_sound_enabled_initial=True,
                 POPIN_SOUND_PATH=None, POPOUT_SOUND_PATH=None):
        super().__init__()
        self.head_widget = head_widget
        self.current_view = "main"
        self.user_name = user_name
        self.selected_mode = selected_mode
        print(f"🗣️ Talking mode set to: {self.selected_mode}")
        self.notes_file_path = "notes.txt"
        self.is_feedback_enabled = is_feedback_enabled_initial
        self.is_sound_enabled = is_sound_enabled_initial
        self.POPIN_SOUND_PATH = POPIN_SOUND_PATH
        self.POPOUT_SOUND_PATH = POPOUT_SOUND_PATH

        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint |
            Qt.WindowType.WindowStaysOnTopHint |
            Qt.WindowType.Tool
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)

        if os.path.exists(image_path):
            self.pixmap = QPixmap(image_path).scaled(180, 180, Qt.AspectRatioMode.KeepAspectRatio,
                                                     Qt.TransformationMode.SmoothTransformation)
        else:
            self.pixmap = QPixmap(180, 180)

        screen = QApplication.primaryScreen().availableGeometry()
        self.hide_x = screen.width()

        self.anim = QPropertyAnimation(self, b"pos")
        self.anim.setEasingCurve(QEasingCurve.Type.OutCubic)
        self.anim.setDuration(500)
        self.anim.finished.connect(self._handle_anim_finished)

        self.hide_timer = QTimer(self)
        self.hide_timer.timeout.connect(self.slide_out)

        self.comment = ""
        self.tip = ""
        self.current_color = QColor(153, 153, 153, 230)

        # --- Menu View ---
        self.menu_widget = QFrame(self)
        self.menu_widget.setFixedSize(self.pixmap.width(), self.pixmap.height() + 180)  # Increased height for new button
        menu_layout = QVBoxLayout(self.menu_widget)

        menu_title = QLabel(f"Hello, {self.user_name}!")
        menu_title.setStyleSheet("font-weight: bold; font-size: 11pt;")
        menu_title.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.check_mood_button = QPushButton("Check My Mood")
        self.check_mood_button.clicked.connect(self.mood_requested.emit)

        self.reset_mood_button = QPushButton("I'm Feeling Better!")
        self.reset_mood_button.clicked.connect(self.reset_requested.emit)

        self.notes_button = QPushButton("View/Take Notes")
        self.notes_button.clicked.connect(self.show_notes)

        # New button for feedback toggle
        self.toggle_feedback_button = QPushButton()
        self.toggle_feedback_button.clicked.connect(self.toggle_feedback)
        self.update_toggle_button_text()  # Set initial text

        self.toggle_sound_button = QPushButton()
        self.toggle_sound_button.clicked.connect(self.toggle_sound)
        self.update_sound_button_text()

        self.close_button = QPushButton("Close")
        self.close_button.clicked.connect(self.slide_out)

        menu_layout.addWidget(menu_title)
        menu_layout.addWidget(self.check_mood_button)
        menu_layout.addWidget(self.reset_mood_button)
        menu_layout.addWidget(self.notes_button)
        menu_layout.addWidget(self.toggle_feedback_button)
        menu_layout.addWidget(self.toggle_sound_button)
        menu_layout.addWidget(self.close_button)

        self.menu_widget.hide()
        self.menu_widget.setParent(self)

        # --- Notes View ---
        self.notes_widget = QFrame(self)
        self.notes_widget.setFixedSize(self.pixmap.width(), self.pixmap.height() + 140)
        notes_layout = QVBoxLayout(self.notes_widget)
        notes_title = QLabel("Quick Notes")
        notes_title.setStyleSheet("font-weight: bold; font-size: 11pt;")
        notes_title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.notes_editor = QTextEdit()
        self.notes_editor.setStyleSheet("background-color: white; color: black; border: 1px solid gray; padding: 5px;")
        self.notes_editor.setPlaceholderText("Start typing a new note...")
        self.save_button = QPushButton("Save Note")
        self.save_button.clicked.connect(self.save_note_and_slide_out)
        self.new_note_button = QPushButton("New Note")
        self.new_note_button.clicked.connect(self.start_new_note)
        self.clear_notes_button = QPushButton("Clear All Notes")
        self.clear_notes_button.clicked.connect(self.confirm_clear_notes)
        self.notes_close_button = QPushButton("Close")
        self.notes_close_button.clicked.connect(self.slide_out)
        notes_layout.addWidget(notes_title)
        notes_layout.addWidget(self.notes_editor)
        notes_layout.addWidget(self.save_button)
        notes_layout.addWidget(self.new_note_button)
        notes_layout.addWidget(self.clear_notes_button)
        notes_layout.addWidget(self.notes_close_button)
        self.notes_widget.hide()
        self.notes_widget.setParent(self)

    def set_head_widget(self, head_widget):
        self.head_widget = head_widget

    def _handle_anim_finished(self):
        if self.pos().x() >= self.screen().geometry().width():
            self.hide()
            if self.head_widget:
                self.head_widget.show()

    def toggle_sound(self):
        self.is_sound_enabled = not self.is_sound_enabled
        self.update_sound_button_text()
        self.sound_toggled.emit(self.is_sound_enabled)

    def update_sound_button_text(self):
        if self.is_sound_enabled:
            self.toggle_sound_button.setText("Disable Sound")
        else:
            self.toggle_sound_button.setText("Enable Sound")

    def update_character_image(self, image_path):
        if os.path.exists(image_path):
            self.pixmap = QPixmap(image_path).scaled(180, 180, Qt.AspectRatioMode.KeepAspectRatio,
                                                     Qt.TransformationMode.SmoothTransformation)
        else:
            self.pixmap = QPixmap(180, 180)

    def show_menu(self):
        # Stop any running animations and timers first
        self.hide_timer.stop()
        self.anim.stop()

        self.notes_widget.hide()
        self.menu_widget.show()
        self.current_view = "menu"

        self.update_size_and_position()
        if self.head_widget:
            self.head_widget.hide()

        self.menu_widget.move(0, 0)
        screen_geom = QApplication.primaryScreen().availableGeometry()
        self.final_x = screen_geom.width() - self.width()
        self.final_y = (screen_geom.height() // 2) - (self.height() // 2)

        self.anim.setStartValue(self.pos())
        self.anim.setEndValue(QPoint(self.final_x, self.final_y))
        self.show()
        self.raise_()
        self.anim.start()

    def show_notes(self):
        self.menu_widget.hide()
        self.notes_widget.show()
        self.current_view = "notes"
        self._load_notes_file()
        self.notes_editor.setReadOnly(True)
        self.notes_editor.setPlaceholderText("")
        if self.notes_editor.toPlainText().strip():
            self.notes_editor.verticalScrollBar().setValue(self.notes_editor.verticalScrollBar().maximum())
        self.update_size_and_position()
        self.anim.stop()
        self.hide_timer.stop()
        if self.head_widget:
            self.head_widget.hide()
        self.notes_widget.move(0, 0)
        screen_geom = QApplication.primaryScreen().availableGeometry()
        self.final_x = screen_geom.width() - self.width()
        self.final_y = (screen_geom.height() // 2) - (self.height() // 2)
        self.anim.setStartValue(self.pos())
        self.anim.setEndValue(QPoint(self.final_x, self.final_y))
        self.anim.start()

    def _load_notes_file(self):
        if os.path.exists(self.notes_file_path):
            try:
                with open(self.notes_file_path, "r") as f:
                    content = f.read()
                    self.notes_editor.setText(content)
            except Exception as e:
                self.notes_editor.clear()
        else:
            self.notes_editor.clear()

    def start_new_note(self):
        self.notes_editor.clear()
        self.notes_editor.setReadOnly(False)
        self.notes_editor.setPlaceholderText("Start typing a new note...")

    def confirm_clear_notes(self):
        msg_box = QMessageBox(self)
        msg_box.setWindowTitle("Confirm Clear")
        msg_box.setText("Are you sure you want to clear all notes?")
        msg_box.setInformativeText("This action cannot be undone.")
        msg_box.setStandardButtons(QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        msg_box.setDefaultButton(QMessageBox.StandardButton.No)
        reply = msg_box.exec()
        if reply == QMessageBox.StandardButton.Yes:
            if os.path.exists(self.notes_file_path):
                try:
                    open(self.notes_file_path, "w").close()
                    self.notes_editor.clear()
                    QMessageBox.information(self, "Notes Cleared", "All notes have been cleared.")
                except Exception as e:
                    QMessageBox.warning(self, "Error", f"Failed to clear notes: {e}")
            else:
                self.notes_editor.clear()
                QMessageBox.information(self, "Notes Cleared", "No notes file existed.")

    def save_note_and_slide_out(self):
        new_note_text = self.notes_editor.toPlainText()
        if new_note_text.strip():
            self.save_notes_requested.emit(new_note_text)
            self.notes_editor.clear()
        self.slide_out()

    def update_size_and_position(self):
        if self.current_view == "notes":
            self.setFixedSize(self.notes_widget.size())
        elif self.current_view == "menu":
            self.setFixedSize(self.menu_widget.size())
        else:
            font_bold, font_normal = QFont("Segoe UI", 11, QFont.Weight.Bold), QFont("Segoe UI", 9, QFont.Weight.Normal)
            comment_height = QFontMetrics(font_bold).boundingRect(
                0, 0, self.pixmap.width() - 20, 1000,
                      Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignHCenter | Qt.TextFlag.TextWordWrap,
                self.comment).height()
            tip_height = QFontMetrics(font_normal).boundingRect(
                0, 0, self.pixmap.width() - 20, 1000,
                      Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignHCenter | Qt.TextFlag.TextWordWrap,
                self.tip).height()
            needed_height = self.pixmap.height() + comment_height + tip_height + 40
            self.setFixedSize(self.pixmap.width(), needed_height)
        screen = QApplication.primaryScreen().availableGeometry()
        self.final_x = screen.width() - self.width()
        self.final_y = (screen.height() // 2) - (self.height() // 2)
        self.move(self.final_x, self.final_y)

    # -------------------
    # Tone-aware rendering
    # -------------------
    def _format_by_tone(self, mood: str, comment: str, tip: str) -> tuple[str, str]:
        """
        Rewrites comment/tip based on self.selected_mode.
        Non-invasive: only tone/style changes here.
        """
        mode = (self.selected_mode or "").lower()

        if mode == "teacher":
            # direct, instructive, actionable
            comment = f"Observation: {comment}"
            tip = f"Action: {tip.replace('Try', 'Try to').replace('Maybe', 'Consider').replace('Perfect time', 'It is a good time to')}"
        elif mode == "best friend":
            # warm, supportive, casual
            comment = f"{comment} You got this, {self.user_name}! 💪"
            tip = f"{tip} (I’m here if you want a quick check-in.)"
        elif mode == "love":
            # affectionate & gentle
            comment = f"{comment} I care about you, {self.user_name}. ❤️"
            tip = f"{tip}—one small step is enough."
        # else: unknown/custom -> leave as-is

        return comment, tip

    def show_mood(self, comment, tip, color, mood_name: str | None = None):
        # Apply tone formatting (mood_name is optional; backward-compatible)
        comment, tip = self._format_by_tone(mood_name or "", comment, tip)

        self.comment, self.tip, self.current_color = comment, tip, color
        self.current_view = "main"
        self.menu_widget.hide()
        self.notes_widget.hide()
        self.update_size_and_position()

        if self.head_widget:
            self.head_widget.hide()

        self.anim.stop()
        self.hide_timer.stop()
        self.show()
        self.raise_()

        # Play pop-in sound (fixed condition to check POPIN)
        if self.is_sound_enabled and self.POPIN_SOUND_PATH and os.path.exists(self.POPIN_SOUND_PATH):
            try:
                if pygame.mixer.get_init():
                    sound = pygame.mixer.Sound(self.POPIN_SOUND_PATH)
                    sound.play()
            except Exception as e:
                print(f"Could not play pop-in sound: {e}")

        self.anim.setStartValue(QPoint(self.hide_x, self.final_y))
        self.anim.setEndValue(QPoint(self.final_x, self.final_y))
        self.anim.start()
        self.hide_timer.start(12000)

    def slide_out(self):
        # Stop timers/anim first
        self.hide_timer.stop()
        self.anim.stop()

        # Play the pop-out sound (deduped condition)
        if self.is_sound_enabled and self.POPOUT_SOUND_PATH and os.path.exists(self.POPOUT_SOUND_PATH):
            try:
                if pygame.mixer.get_init():
                    sound = pygame.mixer.Sound(self.POPOUT_SOUND_PATH)
                    sound.play()
            except Exception as e:
                print(f"Could not play pop-out sound: {e}")

        # Start the slide-out animation
        screen = QApplication.primaryScreen().availableGeometry()
        self.anim.setStartValue(QPoint(self.final_x, self.final_y))
        self.anim.setEndValue(QPoint(self.hide_x, self.final_y))
        self.anim.start()

    def show_feedback_dialog(self, auto_trigger=False):
        mood_options = ["idle","low_energy", "deep_work", "struggling", "browsing", "steady"]
        if not auto_trigger:
            QMessageBox.information(self, "Feedback", "This feature is only available automatically after 5 mood checks.")
            return
        selected_mood, ok = QInputDialog.getItem(
            self, "Feedback on Mood Detection",
            "Was the last mood detection accurate?\nIf not, please select the correct mood:",
            mood_options, 0, False)
        if ok and selected_mood:
            feedback_text = f"User corrected mood to: {selected_mood}"
            self.feedback_submitted.emit(selected_mood, feedback_text)
            QMessageBox.information(self, "Feedback Received", f"Thank you for your feedback! You selected: {selected_mood}")
        else:
            QMessageBox.information(self, "Feedback Cancelled", "Feedback submission cancelled.")

    def toggle_feedback(self):
        self.is_feedback_enabled = not self.is_feedback_enabled
        self.update_toggle_button_text()
        self.feedback_toggled.emit(self.is_feedback_enabled)

    def update_toggle_button_text(self):
        if self.is_feedback_enabled:
            self.toggle_feedback_button.setText("Disable Feedback")
        else:
            self.toggle_feedback_button.setText("Enable Feedback")

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        if self.current_view == "main":
            painter.drawPixmap(0, 0, self.pixmap)

            rect_x, rect_y = 0, self.pixmap.height()
            rect_w, rect_h = self.width(), self.height() - self.pixmap.height()

            painter.setBrush(self.current_color)
            painter.setPen(Qt.PenStyle.NoPen)
            painter.drawRoundedRect(rect_x, rect_y, rect_w, rect_h, 10, 10)

            painter.setPen(QPen(QColor(50, 50, 50), 2))
            painter.drawRoundedRect(rect_x, rect_y, rect_w, rect_h, 10, 10)

            painter.setPen(QColor(0, 0, 0))
            font_comment = QFont("Segoe UI", 11, QFont.Weight.Bold)
            painter.setFont(font_comment)
            comment_metrics, text_margin = painter.fontMetrics(), 10
            comment_draw_rect = QRect(rect_x + text_margin, rect_y + text_margin,
                                      rect_w - 2 * text_margin, rect_h - 2 * text_margin)
            comment_bounds = comment_metrics.boundingRect(
                comment_draw_rect,
                Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignHCenter | Qt.TextFlag.TextWordWrap,
                self.comment
            )
            painter.drawText(
                comment_bounds,
                Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignHCenter | Qt.TextFlag.TextWordWrap,
                self.comment
            )

            painter.setPen(QColor(0, 0, 0))
            font_tip = QFont("Segoe UI", 9, QFont.Weight.Normal)
            painter.setFont(font_tip)
            tip_spacing_from_comment = 15
            tip_start_y = rect_y + text_margin + comment_bounds.height() + tip_spacing_from_comment
            tip_draw_rect = QRect(rect_x + text_margin, tip_start_y,
                                  rect_w - 2 * text_margin, rect_y + rect_h - tip_start_y - text_margin)
            if tip_draw_rect.height() > 0:
                painter.drawText(
                    tip_draw_rect,
                    Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignHCenter | Qt.TextFlag.TextWordWrap,
                    self.tip
                )
