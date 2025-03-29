from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QGridLayout, 
                             QLineEdit, QMessageBox, QApplication, QSizePolicy, QSpacerItem, 
                             QGroupBox) # Added QGroupBox
from PyQt6.QtCore import Qt, QThread, pyqtSignal
import os
import sys
import traceback

# Ensure the core Applio logic can be imported
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

# Import core functions
from core import run_download_script

class DownloadWorker(QThread):
    """Worker thread for downloading models."""
    status = pyqtSignal(str)
    finished = pyqtSignal(str)
    error = pyqtSignal(str)
    # TODO: Add progress signal if download script can provide it

    def __init__(self, model_link):
        super().__init__()
        self.model_link = model_link
        self._is_running = True # Added for potential cancellation

    def run(self):
        """Execute the download task."""
        try:
            self.status.emit(f"Starting download from {self.model_link}...")
            
            # --- Actual Call ---
            message = run_download_script(self.model_link)
            # --- End Actual Call ---

            if self._is_running:
                self.status.emit(message)
                self.finished.emit(message)
        except Exception as e:
            error_str = f"Download Error: {e}\n{traceback.format_exc()}"
            self.error.emit(error_str)
        finally:
            if self._is_running: 
                self.status.emit("Idle")

    def stop(self): # Added stop method
        self._is_running = False
        self.status.emit("Cancelling download...")
        # TODO: Implement actual download cancellation if possible


class DownloadTab(QWidget):
    """Widget for the Download Tab."""
    def __init__(self):
        super().__init__()
        self.worker = None
        self.setup_ui()

    def setup_ui(self):
        main_layout = QVBoxLayout(self)

        # --- Download Model from Link ---
        link_group = QGroupBox("Download Model from Link")
        link_layout = QGridLayout(link_group)

        link_layout.addWidget(QLabel("Model Link (URL):"), 0, 0)
        self.model_link_edit = QLineEdit()
        self.model_link_edit.setPlaceholderText("Enter direct download link for .zip, .pth, or .index file")
        link_layout.addWidget(self.model_link_edit, 0, 1)

        self.download_button = QPushButton("Download Model")
        self.download_button.clicked.connect(self.start_download)
        link_layout.addWidget(self.download_button, 1, 0, 1, 2) # Span 2 columns

        self.status_label = QLabel("Status: Idle")
        link_layout.addWidget(self.status_label, 2, 0, 1, 2)

        main_layout.addWidget(link_group)

        # TODO: Add sections for File Drop and Pretrained Download later

        # Add spacer
        main_layout.addSpacerItem(QSpacerItem(20, 40, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Expanding))

        self.setLayout(main_layout)

    def start_download(self):
        """Starts the download process."""
        if self.worker and self.worker.isRunning():
            QMessageBox.warning(self, "Process Running", "A download is already in progress.")
            return

        model_link = self.model_link_edit.text().strip()

        # --- Validate parameters ---
        if not model_link:
            QMessageBox.warning(self, "Input Error", "Please enter a model download link.")
            return
        # Basic URL check (can be improved)
        if not (model_link.startswith("http://") or model_link.startswith("https://")):
             QMessageBox.warning(self, "Input Error", "Please enter a valid HTTP or HTTPS URL.")
             return

        # --- Start worker thread ---
        self.download_button.setEnabled(False)
        self.status_label.setText("Status: Starting download...")

        self.worker = DownloadWorker(model_link)
        self.worker.status.connect(self.update_status)
        self.worker.finished.connect(self.on_download_finished)
        self.worker.error.connect(self.on_download_error)
        self.worker.finished.connect(self.reset_ui_state) # Re-enable button on finish/error
        self.worker.error.connect(self.reset_ui_state)
        self.worker.start()

    def reset_ui_state(self):
        """Re-enables button after task completion or error."""
        self.download_button.setEnabled(True)
        self.status_label.setText("Status: Idle") # Reset status too

    def update_status(self, message):
        self.status_label.setText(f"Status: {message}")

    def on_download_finished(self, message):
        self.update_status(f"Finished: {message}")
        QMessageBox.information(self, "Download Complete", message)
        # TODO: Trigger model list refresh in Inference/TTS/Blender tabs?

    def on_download_error(self, error_message):
        self.update_status("Error occurred")
        QMessageBox.critical(self, "Download Error", f"An error occurred:\n{error_message}")
        print(f"Error details:\n{error_message}")
