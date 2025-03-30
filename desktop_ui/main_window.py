import sys
import os

# Ensure the core Applio logic can be imported
# Add the project root directory to the Python path
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from PyQt6.QtWidgets import (
    QMainWindow,
    QApplication,
    QTabWidget,
    QWidget,
    QVBoxLayout,
    QLabel,
)

# Import tab widgets
from desktop_ui.tabs.inference_tab import InferenceTab
from desktop_ui.tabs.train_tab import TrainTab
from desktop_ui.tabs.tts_tab import TtsTab
from desktop_ui.tabs.voice_blender_tab import VoiceBlenderTab
from desktop_ui.tabs.plugins_tab import PluginsTab
from desktop_ui.tabs.download_tab import DownloadTab
from desktop_ui.tabs.extra_tab import ExtraTab
from desktop_ui.tabs.settings_tab import SettingsTab


class MainWindow(QMainWindow):
    """Main application window."""

    def __init__(self):
        super().__init__()
        # Use self.tr() for translatable strings
        self.setWindowTitle(self.tr("Applio Desktop"))
        self.setGeometry(100, 100, 1000, 700)  # x, y, width, height

        self.setup_ui()

    def setup_ui(self):
        """Sets up the main UI components, including the tab widget."""
        self.tab_widget = QTabWidget()
        self.setCentralWidget(self.tab_widget)

        # --- Create and add tabs ---
        # Use self.tr() for translatable tab names
        self.inference_tab = InferenceTab()
        self.tab_widget.addTab(self.inference_tab, self.tr("Inference"))

        self.train_tab = TrainTab()
        self.tab_widget.addTab(self.train_tab, self.tr("Training"))

        self.tts_tab = TtsTab()
        self.tab_widget.addTab(self.tts_tab, self.tr("TTS"))

        self.voice_blender_tab = VoiceBlenderTab()
        self.tab_widget.addTab(self.voice_blender_tab, self.tr("Voice Blender"))

        self.plugins_tab = PluginsTab()
        self.tab_widget.addTab(self.plugins_tab, self.tr("Plugins"))

        self.download_tab = DownloadTab()
        self.tab_widget.addTab(self.download_tab, self.tr("Download"))

        self.extra_tab = ExtraTab()
        self.tab_widget.addTab(self.extra_tab, self.tr("Extra"))

        self.settings_tab = SettingsTab()
        self.tab_widget.addTab(self.settings_tab, self.tr("Settings"))

        # TODO: Add menu bar, status bar if needed


# Example usage for testing this file directly (optional)
if __name__ == "__main__":
    app = QApplication(sys.argv)
    main_win = MainWindow()
    main_win.show()
    sys.exit(app.exec())
