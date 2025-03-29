from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QGridLayout, 
                             QSlider, QComboBox, QCheckBox, QLineEdit, QFileDialog, QProgressBar,
                             QMessageBox, QApplication, QSizePolicy, QSpacerItem, QTabWidget, 
                             QGroupBox, QTextEdit) # Added QTabWidget, QTextEdit
from PyQt6.QtCore import Qt, QThread, pyqtSignal
from PyQt6.QtGui import QPixmap # Added for image display
import os
import sys
import traceback

# Ensure the core Applio logic can be imported
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

# Import core functions
from core import run_model_information_script, run_audio_analyzer_script
# Import F0 extractor logic directly from its original file
try:
    from tabs.extra.sections.f0_extractor import extract_f0_curve
except ImportError as e:
    print(f"Could not import F0 extractor function: {e}")
    extract_f0_curve = None # Handle gracefully if import fails

# Define constants
LOGS_DIR = os.path.join(project_root, "logs") # For F0 output default
MODEL_ROOT = os.path.join(project_root, "logs") # For model browser

class ExtraWorker(QThread):
    """Worker thread for extra utilities."""
    status = pyqtSignal(str)
    # Finished signal sends: message, result_type ("text", "image_text", "image"), result_data (str or tuple)
    finished = pyqtSignal(str, str, object) 
    error = pyqtSignal(str)

    def __init__(self, task, params):
        super().__init__()
        self.task = task # e.g., "model_info", "analyze_audio", "extract_f0"
        self.params = params
        self._is_running = True

    def run(self):
        """Execute the extra task."""
        try:
            self.status.emit(f"Starting {self.task}...")
            result_data = None
            result_type = "text" # Default result type
            message = ""

            # --- Actual Call ---
            if self.task == "model_info":
                core_params = {"pth_path": self.params.get("pth_path")}
                message = run_model_information_script(**core_params)
                result_data = message # The message itself is the result
            elif self.task == "analyze_audio":
                core_params = {"input_path": self.params.get("input_path")}
                # Define output path for plot if not provided
                default_plot_path = os.path.join(LOGS_DIR, "audio_analysis.png")
                core_params["save_plot_path"] = self.params.get("save_plot_path", default_plot_path)
                message, result_data = run_audio_analyzer_script(**core_params)
                result_type = "image_text" # Returns text info and image path
            elif self.task == "extract_f0":
                if extract_f0_curve is None:
                     raise RuntimeError("F0 Extractor function not available.")
                core_params = {
                    "audio_path": self.params.get("audio_path"),
                    "method": self.params.get("method", "rmvpe")
                }
                # extract_f0_curve saves files and returns paths
                image_path, txt_path = extract_f0_curve(**core_params)
                message = f"F0 curve extracted to {txt_path} and plot saved to {image_path}"
                result_data = (image_path, txt_path) # Return both paths
                result_type = "image_text_files" # Special type for F0 result
            else:
                raise ValueError(f"Unknown extra task: {self.task}")
            # --- End Actual Call ---

            if self._is_running:
                self.status.emit(message)
                self.finished.emit(message, result_type, result_data)
        except Exception as e:
            error_str = f"{self.task.capitalize()} Error: {e}\n{traceback.format_exc()}"
            self.error.emit(error_str)
        finally:
            if self._is_running: 
                self.status.emit("Idle")

    def stop(self):
        self._is_running = False
        self.status.emit(f"Cancelling {self.task}...")


class ExtraTab(QWidget):
    """Widget for the Extra Tab."""
    def __init__(self):
        super().__init__()
        self.worker = None
        self.setup_ui()

    def setup_ui(self):
        main_layout = QVBoxLayout(self)
        tab_widget = QTabWidget()

        # --- Model Information Sub-Tab ---
        model_info_widget = QWidget()
        model_info_layout = QVBoxLayout(model_info_widget)
        model_info_grid = QGridLayout()

        model_info_grid.addWidget(QLabel("Model Path (.pth):"), 0, 0)
        self.mi_pth_path_edit = QLineEdit()
        model_info_grid.addWidget(self.mi_pth_path_edit, 0, 1)
        mi_browse_button = QPushButton("Browse...")
        mi_browse_button.clicked.connect(self.browse_mi_pth)
        model_info_grid.addWidget(mi_browse_button, 0, 2)

        mi_view_button = QPushButton("View Information")
        mi_view_button.clicked.connect(self.start_model_info)
        model_info_layout.addLayout(model_info_grid)
        model_info_layout.addWidget(mi_view_button)

        self.mi_output_text = QTextEdit()
        self.mi_output_text.setReadOnly(True)
        model_info_layout.addWidget(self.mi_output_text)
        
        tab_widget.addTab(model_info_widget, "Model Information")

        # --- F0 Curve Sub-Tab ---
        f0_widget = QWidget()
        f0_layout = QVBoxLayout(f0_widget)
        f0_grid = QGridLayout()

        f0_grid.addWidget(QLabel("Audio Input:"), 0, 0)
        self.f0_audio_path_edit = QLineEdit()
        f0_grid.addWidget(self.f0_audio_path_edit, 0, 1)
        f0_browse_button = QPushButton("Browse...")
        f0_browse_button.clicked.connect(self.browse_f0_audio)
        f0_grid.addWidget(f0_browse_button, 0, 2)

        f0_grid.addWidget(QLabel("F0 Method:"), 1, 0)
        self.f0_method_combo = QComboBox()
        self.f0_method_combo.addItems(["rmvpe", "crepe", "fcpe"]) # Methods used by extractor
        self.f0_method_combo.setCurrentText("rmvpe")
        f0_grid.addWidget(self.f0_method_combo, 1, 1)

        f0_extract_button = QPushButton("Extract F0 Curve")
        f0_extract_button.clicked.connect(self.start_f0_extraction)
        f0_layout.addLayout(f0_grid)
        f0_layout.addWidget(f0_extract_button)

        self.f0_image_label = QLabel("F0 Plot will appear here")
        self.f0_image_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.f0_image_label.setMinimumSize(200, 100) # Give it some size
        f0_layout.addWidget(self.f0_image_label)
        # TODO: Add display/link for the output .txt file?

        tab_widget.addTab(f0_widget, "F0 Curve")

        # --- Audio Analyzer Sub-Tab ---
        analyzer_widget = QWidget()
        # Use a QVBoxLayout as the main layout for this sub-tab widget
        analyzer_main_layout = QVBoxLayout(analyzer_widget) 
        
        # Use a QGridLayout for the input elements
        analyzer_input_grid = QGridLayout() 
        analyzer_input_grid.addWidget(QLabel("Audio Input:"), 0, 0)
        self.analyzer_audio_path_edit = QLineEdit()
        analyzer_input_grid.addWidget(self.analyzer_audio_path_edit, 0, 1) # Add to grid
        analyzer_browse_button = QPushButton("Browse...")
        analyzer_browse_button.clicked.connect(self.browse_analyzer_audio)
        analyzer_input_grid.addWidget(analyzer_browse_button, 0, 2) # Add to grid
        
        # Add the grid layout to the main vertical layout
        analyzer_main_layout.addLayout(analyzer_input_grid) 

        analyzer_get_info_button = QPushButton("Get Information")
        analyzer_get_info_button.clicked.connect(self.start_audio_analysis)
        # Add the button to the main vertical layout
        analyzer_main_layout.addWidget(analyzer_get_info_button) 

        self.analyzer_output_text = QTextEdit()
        self.analyzer_output_text.setReadOnly(True)
        # Add the text output to the main vertical layout
        analyzer_main_layout.addWidget(self.analyzer_output_text) 

        self.analyzer_image_label = QLabel("Analysis Plot will appear here")
        self.analyzer_image_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.analyzer_image_label.setMinimumSize(200, 100)
        # Add the image label to the main vertical layout
        analyzer_main_layout.addWidget(self.analyzer_image_label) 

        tab_widget.addTab(analyzer_widget, "Audio Analyzer")

        main_layout.addWidget(tab_widget)

        # --- Status Label (Common for all sub-tabs) ---
        self.status_label = QLabel("Status: Idle")
        main_layout.addWidget(self.status_label)

        self.setLayout(main_layout)

    # --- Browse Methods ---
    def browse_mi_pth(self):
        file_path, _ = QFileDialog.getOpenFileName(self, "Select Model File", MODEL_ROOT, "PyTorch Model Files (*.pth)")
        if file_path:
            self.mi_pth_path_edit.setText(file_path)

    def browse_f0_audio(self):
        # Reuse audio filter logic from InferenceTab if possible, or redefine
        audio_filter = "Audio Files (*.wav *.mp3 *.flac *.ogg);;All Files (*)"
        file_path, _ = QFileDialog.getOpenFileName(self, "Select Audio File", project_root, audio_filter)
        if file_path:
            self.f0_audio_path_edit.setText(file_path)

    def browse_analyzer_audio(self):
        audio_filter = "Audio Files (*.wav *.mp3 *.flac *.ogg);;All Files (*)"
        file_path, _ = QFileDialog.getOpenFileName(self, "Select Audio File", project_root, audio_filter)
        if file_path:
            self.analyzer_audio_path_edit.setText(file_path)

    # --- Worker Start Methods ---
    def start_model_info(self):
        pth_path = self.mi_pth_path_edit.text().strip()
        if not pth_path or not os.path.exists(pth_path):
            QMessageBox.warning(self, "Input Error", "Please select a valid .pth model file.")
            return
        params = {"pth_path": pth_path}
        self.start_worker("model_info", params)

    def start_f0_extraction(self):
        audio_path = self.f0_audio_path_edit.text().strip()
        if not audio_path or not os.path.exists(audio_path):
            QMessageBox.warning(self, "Input Error", "Please select a valid audio file.")
            return
        params = {
            "audio_path": audio_path,
            "method": self.f0_method_combo.currentText()
        }
        self.start_worker("extract_f0", params)

    def start_audio_analysis(self):
        audio_path = self.analyzer_audio_path_edit.text().strip()
        if not audio_path or not os.path.exists(audio_path):
            QMessageBox.warning(self, "Input Error", "Please select a valid audio file.")
            return
        params = {"input_path": audio_path}
        self.start_worker("analyze_audio", params)

    def start_worker(self, task_name, params):
        """Generic method to start the worker thread."""
        if self.worker and self.worker.isRunning():
            QMessageBox.warning(self, "Process Running", f"An {self.worker.task} task is already running.")
            return

        # TODO: Disable relevant buttons
        self.status_label.setText(f"Status: Starting {task_name}...")
        self.mi_output_text.clear() # Clear previous results
        self.analyzer_output_text.clear()
        self.f0_image_label.clear()
        self.analyzer_image_label.clear()


        self.worker = ExtraWorker(task_name, params)
        self.worker.status.connect(self.update_status)
        self.worker.finished.connect(self.on_task_finished)
        self.worker.error.connect(self.on_task_error)
        self.worker.finished.connect(self.reset_ui_state) 
        self.worker.error.connect(self.reset_ui_state)
        self.worker.start()

    # --- UI Update Slots ---
    def reset_ui_state(self):
        """Re-enables buttons after task completion or error."""
        # TODO: Re-enable buttons more selectively
        self.status_label.setText("Status: Idle")

    def update_status(self, message):
        self.status_label.setText(f"Status: {message}")

    def on_task_finished(self, message, result_type, result_data):
        self.update_status(f"Finished: {message}")
        QMessageBox.information(self, f"{self.worker.task.capitalize()} Complete", message)

        # Display results based on type
        if result_type == "text":
            if self.worker.task == "model_info":
                self.mi_output_text.setText(str(result_data))
        elif result_type == "image_text":
             if self.worker.task == "analyze_audio":
                 text_info, image_path = result_data
                 self.analyzer_output_text.setText(str(text_info))
                 if image_path and os.path.exists(image_path):
                     pixmap = QPixmap(image_path)
                     self.analyzer_image_label.setPixmap(pixmap.scaled(self.analyzer_image_label.size(), 
                                                                       Qt.AspectRatioMode.KeepAspectRatio, 
                                                                       Qt.TransformationMode.SmoothTransformation))
                 else:
                      self.analyzer_image_label.setText("Plot image not found.")
        elif result_type == "image_text_files":
             if self.worker.task == "extract_f0":
                 image_path, txt_path = result_data
                 if image_path and os.path.exists(image_path):
                     pixmap = QPixmap(image_path)
                     self.f0_image_label.setPixmap(pixmap.scaled(self.f0_image_label.size(), 
                                                                 Qt.AspectRatioMode.KeepAspectRatio, 
                                                                 Qt.TransformationMode.SmoothTransformation))
                 else:
                      self.f0_image_label.setText("F0 plot image not found.")
                 # Optionally display txt_path or its content
                 print(f"F0 curve data saved to: {txt_path}")


    def on_task_error(self, error_message):
        self.update_status(f"Error during {self.worker.task}")
        QMessageBox.critical(self, f"{self.worker.task.capitalize()} Error", f"An error occurred:\n{error_message}")
        print(f"Error details:\n{error_message}")
