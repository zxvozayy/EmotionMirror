import os
from PyQt6.QtWidgets import QDialog, QVBoxLayout, QPushButton, QLabel, QApplication, QFrame, QComboBox, QMessageBox
from PyQt6.QtGui import QPixmap, QIcon
from PyQt6.QtCore import Qt, QSize, pyqtSignal
from utils import resource_path
class CharacterSelectionDialog(QDialog):
    # 🎯 FIX: Signal now emits a tuple of (head_path, popup_path)
    character_selected = pyqtSignal(tuple, str)


    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Choose Your Buddy")
        self.setFixedSize(1050, 800)  # 3x bigger
        self.selected_paths = None

    # Center the window on the screen
        self.center()

        # Set up the main frame for styling and content
        main_frame = QFrame(self)
        main_frame.setFixedSize(self.size()) # Make frame same size as dialog
        main_frame.setStyleSheet("""
            QFrame {
                background-color: rgba(20, 20, 20, 255); /* Solid black background */
                border: 2px solid #55aaff;
                border-radius: 15px;
            }
            QLabel {
                color: #ffffff;
                font-weight: bold;
                font-size: 14pt;
                padding: 10px;
            }
            QPushButton {
                background-color: rgba(0, 0, 0, 0);
                border: none;
            }
            QPushButton:hover {
                background-color: rgba(255, 255, 255, 20);
                border-radius: 10px;
            }
        """)

        # 🎯 FIX: Layout for the main_frame, defined here in __init__
        layout = QVBoxLayout(main_frame)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        title_label = QLabel("Choose Your Companion")
        title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title_label)

        # Character 1: The original buddy
        # buddy3.png is for peeking (head), buddy.png is for popup
        buddy1_head_path = resource_path("resources/buddy3.png")
        buddy1_popup_path = resource_path("resources/buddy.png")
        if os.path.exists(buddy1_head_path) and os.path.exists(buddy1_popup_path):
            buddy1_button = QPushButton()
            # Display the popup image on the button
            buddy1_button.setIcon(QIcon(buddy1_popup_path))
            buddy1_button.setIconSize(QSize(150, 150))
            # 🎯 Emit both paths when selected
            buddy1_button.clicked.connect(lambda: self.select_character(buddy1_head_path, buddy1_popup_path))
            layout.addWidget(buddy1_button)
        else:
            print(f"Warning: Character 1 images (head: {buddy1_head_path}, popup: {buddy1_popup_path}) not found. Please check 'resources' folder.")

        # Character 2: The new woman character
        # woman2.png is for peeking (head), woman.png is for popup
        buddy2_head_path = resource_path("resources/woman2.png")
        buddy2_popup_path = resource_path("resources/woman.png")
        if os.path.exists(buddy2_head_path) and os.path.exists(buddy2_popup_path):
            buddy2_button = QPushButton()
            # Display the popup image on the button
            buddy2_button.setIcon(QIcon(buddy2_popup_path))
            buddy2_button.setIconSize(QSize(150, 150))
            # 🎯 Emit both paths when selected
            buddy2_button.clicked.connect(lambda: self.select_character(buddy2_head_path, buddy2_popup_path))
            layout.addWidget(buddy2_button)
        else:
            print(f"Warning: Character 2 images (head: {buddy2_head_path}, popup: {buddy2_popup_path}) not found. Please check 'resources' folder.")

                # --- Divider ---
        divider = QLabel("──────────────")
        divider.setAlignment(Qt.AlignmentFlag.AlignCenter)
        divider.setStyleSheet("color: gray; margin: 5px;")
        layout.addWidget(divider)

        # --- Talking Style Selection ---
        mode_label = QLabel("Select Talking Style:")
        mode_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        mode_label.setStyleSheet("font-size: 14px; color: white; margin-top: 10px;")
        layout.addWidget(mode_label)

        self.mode_dropdown = QComboBox()
        self.mode_dropdown.addItems(["Teacher", "Best Friend", "Love"])
        self.mode_dropdown.setStyleSheet("""
            QComboBox {
                background-color: #2C2C2C;
                color: white;
                border: 1px solid gray;
                border-radius: 5px;
                padding: 5px;
            }
            QComboBox::drop-down {
                border: 0px;
            }
        """)
        layout.addWidget(self.mode_dropdown)

        # --- Confirm Button ---
        confirm_button = QPushButton("Start")
        confirm_button.setStyleSheet("""
            QPushButton {
                background-color: #4A90E2;
                color: white;
                font-weight: bold;
                border-radius: 8px;
                padding: 8px 16px;
            }
            QPushButton:hover {
                background-color: #357ABD;
            }
        """)
        confirm_button.clicked.connect(self.confirm_selection)
        layout.addWidget(confirm_button)

    def center(self):
        screen_geometry = QApplication.primaryScreen().availableGeometry()
        x = (screen_geometry.width() - self.width()) / 2
        y = (screen_geometry.height() - self.height()) / 2
        self.move(int(x), int(y))

    # 🎯 FIX: This method now accepts two paths and emits them as a tuple
    def select_character(self, head_path, popup_path):
        self.selected_paths = (head_path, popup_path)
        print(f"✅ Character selected: {self.selected_paths}")

    def confirm_selection(self):
        selected_mode = self.mode_dropdown.currentText()
        if hasattr(self, 'selected_paths'):
            self.character_selected.emit(self.selected_paths, selected_mode)
            self.accept()
        else:
            QMessageBox.warning(self, "No Character Selected", "Please choose a character first.")


