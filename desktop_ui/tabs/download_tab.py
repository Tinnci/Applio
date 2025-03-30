from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QGridLayout,
                             QLineEdit, QMessageBox, QApplication, QSizePolicy, QSpacerItem,
                             QGroupBox) # Added QGroupBox
from PyQt6.QtCore import Qt, QThread, pyqtSignal
import os
import sys
import traceback
import shutil # For file operations
from urllib.parse import urlparse # To handle file URLs

# Ensure the core Applio logic can be imported
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

# Define logs directory based on project root
LOGS_DIR = os.path.join(project_root, "logs")

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

# --- Custom Drop Area Widget ---
class DropArea(QLabel):
    """A QLabel subclass that accepts file drops."""
    filesDropped = pyqtSignal(list) # Signal emitting list of file paths

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAcceptDrops(True)
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.setText(self.tr("Drop .pth, .index, or .zip files here"))
        self.setStyleSheet("""
            QLabel {
                border: 2px dashed #aaa;
                border-radius: 5px;
                padding: 20px;
                background-color: #f0f0f0; /* Adjust for theme later */
                color: #555; /* Adjust for theme later */
            }
            QLabel[dragOver="true"] {
                border-color: #3399ff;
                background-color: #e0eeff; /* Adjust for theme later */
            }
        """)
        self.setProperty("dragOver", False)

    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()
            self.setProperty("dragOver", True)
            self.style().polish(self) # Force style update
        else:
            event.ignore()

    def dragLeaveEvent(self, event):
        self.setProperty("dragOver", False)
        self.style().polish(self)

    def dropEvent(self, event):
        self.setProperty("dragOver", False)
        self.style().polish(self)
        urls = event.mimeData().urls()
        file_paths = [url.toLocalFile() for url in urls if url.isLocalFile()]
        if file_paths:
            self.filesDropped.emit(file_paths)
        event.acceptProposedAction()

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

        # --- File Drop Install Section ---
        drop_group = QGroupBox(self.tr("Install Model by File Drop"))
        drop_layout = QVBoxLayout(drop_group) # Use QVBoxLayout for simplicity

        self.drop_area = DropArea()
        self.drop_area.filesDropped.connect(self.handle_dropped_files)
        drop_layout.addWidget(self.drop_area)

        self.drop_status_label = QLabel(self.tr("Status: Ready to accept files"))
        drop_layout.addWidget(self.drop_status_label)

        main_layout.addWidget(drop_group)

        # --- Pretrained Model Browser/Download Section ---
        pretrained_group = QGroupBox(self.tr("Download Pretrained Models"))
        pretrained_layout = QVBoxLayout(pretrained_group)

        # Placeholder for model list/tree view
        self.pretrained_model_list = QLabel(self.tr("(Pretrained model browser/list will go here)"))
        self.pretrained_model_list.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.pretrained_model_list.setStyleSheet("padding: 20px; background-color: #e8e8e8; border-radius: 5px;") # Basic styling
        pretrained_layout.addWidget(self.pretrained_model_list)

        # Placeholder for download button
        self.download_pretrained_button = QPushButton(self.tr("Download Selected Pretrained Model"))
        self.download_pretrained_button.setEnabled(False) # Disabled until browser is implemented
        # self.download_pretrained_button.clicked.connect(self.start_pretrained_download) # Connect later
        pretrained_layout.addWidget(self.download_pretrained_button)

        main_layout.addWidget(pretrained_group)

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

    def handle_dropped_files(self, file_paths):
        """Processes files dropped onto the DropArea."""
        self.drop_status_label.setText(self.tr("Processing dropped files..."))
        QApplication.processEvents() # Update UI

        installed_count = 0
        errors = []
        valid_extensions = {".pth", ".index", ".zip"}

        if not os.path.exists(LOGS_DIR):
            try:
                os.makedirs(LOGS_DIR)
            except OSError as e:
                 errors.append(self.tr("Error creating logs directory: {0}").format(e))
                 self.drop_status_label.setText(self.tr("Error: Could not create logs directory."))
                 return

        for file_path in file_paths:
            try:
                filename = os.path.basename(file_path)
                _, ext = os.path.splitext(filename)

                if ext.lower() not in valid_extensions:
                    errors.append(self.tr("Skipped '{0}': Invalid file type.").format(filename))
                    continue

                if ext.lower() == ".zip":
                    # TODO: Implement zip extraction in a worker thread
                    errors.append(self.tr("Skipped '{0}': ZIP installation not yet implemented.").format(filename))
                    continue
                else: # .pth or .index
                    # Assume model name is the filename without extension
                    model_name = os.path.splitext(filename)[0]
                    target_dir = os.path.join(LOGS_DIR, model_name)
                    if not os.path.exists(target_dir):
                        os.makedirs(target_dir)
                    target_path = os.path.join(target_dir, filename)
                    shutil.copy2(file_path, target_path) # copy2 preserves metadata
                    installed_count += 1
                    print(f"Installed '{filename}' to '{target_dir}'")

            except Exception as e:
                errors.append(self.tr("Error installing '{0}': {1}").format(filename, e))

        final_message = self.tr("Finished processing drop. Installed {0} file(s).").format(installed_count)
        if errors:
            final_message += "\n" + self.tr("Errors encountered:") + "\n- " + "\n- ".join(errors)
            QMessageBox.warning(self, self.tr("Drop Installation Issues"), final_message)
        else:
            QMessageBox.information(self, self.tr("Drop Installation Complete"), final_message)

        self.drop_status_label.setText(self.tr("Status: Ready to accept files"))
        # TODO: Trigger model list refresh?
