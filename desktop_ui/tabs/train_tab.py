from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QGridLayout, 
                             QSlider, QComboBox, QCheckBox, QLineEdit, QFileDialog, QProgressBar,
                             QMessageBox, QApplication, QSizePolicy, QSpacerItem, QTabWidget, 
                             QGroupBox, QSpinBox) # Added QGroupBox, QSpinBox
from PyQt6.QtCore import Qt, QThread, pyqtSignal
import os
import sys
import traceback

# Ensure the core Applio logic can be imported
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

# Import core functions
from core import run_preprocess_script, run_extract_script, run_train_script, run_index_script

class TrainWorker(QThread):
    """Worker thread for running training steps."""
    progress = pyqtSignal(int) # Progress (0-100 or step count)
    status = pyqtSignal(str)   # Status messages
    finished = pyqtSignal(str) # Finished message
    error = pyqtSignal(str)    # Error message

    def __init__(self, step, params):
        super().__init__()
        self.step = step # e.g., "preprocess", "extract", "train", "index"
        self.params = params
        self._is_running = True

    def run(self):
        """Execute the training task step."""
        try:
            self.status.emit(f"Starting {self.step}...")
            message = ""
            
            # --- Actual Call ---
            if self.step == "preprocess":
                # Map UI params to core function params
                core_params = {
                    "model_name": self.params.get("model_name"),
                    "dataset_path": self.params.get("dataset_path"),
                    "sample_rate": self.params.get("sample_rate"),
                    "cpu_cores": self.params.get("cpu_cores"),
                    "cut_preprocess": self.params.get("cut_preprocess"),
                    "process_effects": self.params.get("process_effects", False), # Assuming default if not in UI yet
                    "noise_reduction": self.params.get("noise_reduction", False), # Assuming default
                    "clean_strength": self.params.get("clean_strength", 0.7), # Assuming default
                    "chunk_len": self.params.get("chunk_len", 3.0), # Assuming default
                    "overlap_len": self.params.get("overlap_len", 0.3), # Assuming default
                }
                core_params = {k: v for k, v in core_params.items() if v is not None}
                message = run_preprocess_script(**core_params)
            elif self.step == "extract":
                 core_params = {
                    "model_name": self.params.get("model_name"),
                    "f0_method": self.params.get("f0_method"),
                    "hop_length": self.params.get("hop_length"),
                    "cpu_cores": self.params.get("cpu_cores"),
                    "gpu": self.params.get("gpu"),
                    "sample_rate": self.params.get("sample_rate"),
                    "embedder_model": self.params.get("embedder_model"),
                    "embedder_model_custom": self.params.get("embedder_model_custom"),
                    "include_mutes": self.params.get("include_mutes", 2), # Assuming default
                 }
                 core_params = {k: v for k, v in core_params.items() if v is not None}
                 message = run_extract_script(**core_params)
            elif self.step == "train":
                 core_params = {
                    "model_name": self.params.get("model_name"),
                    "save_every_epoch": self.params.get("save_every_epoch"),
                    "save_only_latest": self.params.get("save_only_latest"),
                    "save_every_weights": self.params.get("save_every_weights"),
                    "total_epoch": self.params.get("total_epoch"),
                    "sample_rate": self.params.get("sample_rate"),
                    "batch_size": self.params.get("batch_size"),
                    "gpu": self.params.get("gpu"),
                    "overtraining_detector": self.params.get("overtraining_detector"),
                    "overtraining_threshold": self.params.get("overtraining_threshold"),
                    "pretrained": self.params.get("pretrained"),
                    "cleanup": self.params.get("cleanup", False), # Assuming default
                    "index_algorithm": self.params.get("index_algorithm"), # Passed here for final indexing
                    "cache_data_in_gpu": self.params.get("cache_data_in_gpu"),
                    "custom_pretrained": self.params.get("custom_pretrained"),
                    "g_pretrained_path": self.params.get("g_pretrained_path"),
                    "d_pretrained_path": self.params.get("d_pretrained_path"),
                    "vocoder": self.params.get("vocoder", "HiFi-GAN"), # Assuming default
                    "checkpointing": self.params.get("checkpointing", False), # Assuming default
                 }
                 core_params = {k: v for k, v in core_params.items() if v is not None}
                 message = run_train_script(**core_params) # Note: run_train_script calls run_index_script internally
            elif self.step == "index": # Separate index step if needed
                 core_params = {
                     "model_name": self.params.get("model_name"),
                     "index_algorithm": self.params.get("index_algorithm"),
                 }
                 core_params = {k: v for k, v in core_params.items() if v is not None}
                 message = run_index_script(**core_params)
            else:
                raise ValueError(f"Unknown training step: {self.step}")
            # --- End Actual Call ---

            # --- Placeholder for progress ---
            self.progress.emit(50) 
            import time
            time.sleep(1) # Simulate work
            self.progress.emit(100)
            # --- End Placeholder ---

            if self._is_running:
                self.status.emit(message)
                self.finished.emit(message)
        except Exception as e:
            error_str = f"{self.step.capitalize()} Error: {e}\n{traceback.format_exc()}"
            self.error.emit(error_str)
        finally:
            if self._is_running: 
                self.status.emit("Idle")

    def stop(self):
        self._is_running = False
        self.status.emit(f"Cancelling {self.step}...")
        # TODO: Implement actual process termination if possible/needed


class TrainTab(QWidget):
    """Widget for the Training Tab."""
    def __init__(self):
        super().__init__()
        self.worker = None
        self.setup_ui()

    def setup_ui(self):
        main_layout = QVBoxLayout(self)

        # --- Top Section: Model Name & Dataset ---
        top_group = QGroupBox("Model & Dataset")
        top_layout = QGridLayout(top_group)

        top_layout.addWidget(QLabel("Model Name:"), 0, 0)
        self.model_name_edit = QLineEdit()
        self.model_name_edit.setPlaceholderText("Enter a unique name for your model")
        top_layout.addWidget(self.model_name_edit, 0, 1, 1, 2) # Span 2 cols

        top_layout.addWidget(QLabel("Dataset Path:"), 1, 0)
        self.dataset_path_edit = QLineEdit()
        self.dataset_path_edit.setPlaceholderText("Path to your audio dataset folder")
        top_layout.addWidget(self.dataset_path_edit, 1, 1)
        self.browse_dataset_button = QPushButton("Browse...")
        self.browse_dataset_button.clicked.connect(self.browse_dataset_path)
        top_layout.addWidget(self.browse_dataset_button, 1, 2)

        top_layout.addWidget(QLabel("Sample Rate:"), 2, 0)
        self.sample_rate_combo = QComboBox()
        self.sample_rate_combo.addItems(["40000", "48000", "32000"]) # Match core.py choices order? Check defaults
        self.sample_rate_combo.setCurrentText("40000") # Default?
        top_layout.addWidget(self.sample_rate_combo, 2, 1)

        main_layout.addWidget(top_group)

        # --- Preprocessing Section ---
        preprocess_group = QGroupBox("1. Preprocessing")
        preprocess_layout = QGridLayout(preprocess_group)

        preprocess_layout.addWidget(QLabel("CPU Cores:"), 0, 0)
        self.cpu_cores_spinbox = QSpinBox()
        self.cpu_cores_spinbox.setRange(1, os.cpu_count() or 1) # Set max to available cores
        self.cpu_cores_spinbox.setValue(os.cpu_count() or 1) # Default to max
        preprocess_layout.addWidget(self.cpu_cores_spinbox, 0, 1)

        # TODO: Add other preprocessing options (Cut method, Effects, Noise Reduction, Chunk/Overlap)

        self.preprocess_button = QPushButton("Preprocess Dataset")
        self.preprocess_button.clicked.connect(lambda: self.start_training_step("preprocess"))
        preprocess_layout.addWidget(self.preprocess_button, 1, 0, 1, 3) # Span 3 cols

        main_layout.addWidget(preprocess_group)

        # --- Feature Extraction Section ---
        extract_group = QGroupBox("2. Feature Extraction")
        extract_layout = QGridLayout(extract_group)

        extract_layout.addWidget(QLabel("F0 Method:"), 0, 0)
        self.f0_method_combo_train = QComboBox()
        self.f0_method_combo_train.addItems(["rmvpe", "crepe", "crepe-tiny"]) # Training options differ
        self.f0_method_combo_train.setCurrentText("rmvpe")
        extract_layout.addWidget(self.f0_method_combo_train, 0, 1)

        # TODO: Add Hop Length (conditional), Embedder Model (Radio + Custom)

        self.extract_button = QPushButton("Extract Features")
        self.extract_button.clicked.connect(lambda: self.start_training_step("extract"))
        extract_layout.addWidget(self.extract_button, 1, 0, 1, 3)

        main_layout.addWidget(extract_group)

        # --- Training Section ---
        train_group = QGroupBox("3. Model Training")
        train_layout = QGridLayout(train_group)

        train_layout.addWidget(QLabel("Total Epochs:"), 0, 0)
        self.total_epoch_spinbox = QSpinBox()
        self.total_epoch_spinbox.setRange(1, 10000); self.total_epoch_spinbox.setValue(1000)
        train_layout.addWidget(self.total_epoch_spinbox, 0, 1)

        train_layout.addWidget(QLabel("Batch Size:"), 0, 2)
        self.batch_size_spinbox = QSpinBox()
        self.batch_size_spinbox.setRange(1, 50); self.batch_size_spinbox.setValue(8) # Check reasonable max
        train_layout.addWidget(self.batch_size_spinbox, 0, 3)

        train_layout.addWidget(QLabel("Save Every Epoch:"), 1, 0)
        self.save_epoch_spinbox = QSpinBox()
        self.save_epoch_spinbox.setRange(1, 100); self.save_epoch_spinbox.setValue(10)
        train_layout.addWidget(self.save_epoch_spinbox, 1, 1)

        self.save_latest_checkbox = QCheckBox("Save Only Latest Ckpt")
        train_layout.addWidget(self.save_latest_checkbox, 1, 2)

        self.save_weights_checkbox = QCheckBox("Save Every Weights")
        self.save_weights_checkbox.setChecked(True) # Default from core.py
        train_layout.addWidget(self.save_weights_checkbox, 1, 3)

        # TODO: Add GPU, Pretrained, Overtraining, Cache, Index Algorithm, Vocoder, Checkpointing options

        self.train_button = QPushButton("Train Model")
        self.train_button.clicked.connect(lambda: self.start_training_step("train"))
        train_layout.addWidget(self.train_button, 2, 0, 1, 4) # Span 4

        main_layout.addWidget(train_group)

        # --- Index Training Section ---
        index_group = QGroupBox("4. Index Training")
        index_layout = QGridLayout(index_group)

        index_layout.addWidget(QLabel("Index Algorithm:"), 0, 0)
        self.index_algo_combo = QComboBox()
        self.index_algo_combo.addItems(["Auto", "Faiss", "KMeans"])
        index_layout.addWidget(self.index_algo_combo, 0, 1)

        self.index_button = QPushButton("Train Index")
        self.index_button.clicked.connect(lambda: self.start_training_step("index"))
        index_layout.addWidget(self.index_button, 1, 0, 1, 2) # Span 2

        main_layout.addWidget(index_group)

        # --- Status/Progress ---
        status_group = QWidget()
        status_layout = QVBoxLayout(status_group)
        status_layout.setContentsMargins(0,10,0,0)

        self.status_label = QLabel("Status: Idle")
        status_layout.addWidget(self.status_label)

        self.progress_bar = QProgressBar()
        self.progress_bar.setValue(0)
        self.progress_bar.setTextVisible(False)
        status_layout.addWidget(self.progress_bar)

        main_layout.addWidget(status_group)

        # Add spacer to push controls up
        main_layout.addSpacerItem(QSpacerItem(20, 40, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Expanding))

        self.setLayout(main_layout)

    def browse_dataset_path(self):
        dir_path = QFileDialog.getExistingDirectory(self, "Select Dataset Directory", project_root)
        if dir_path:
            self.dataset_path_edit.setText(dir_path)

    def get_common_params(self):
        """Gathers parameters common to multiple steps."""
        return {
            "model_name": self.model_name_edit.text().strip(),
            "sample_rate": int(self.sample_rate_combo.currentText()),
            "cpu_cores": self.cpu_cores_spinbox.value(),
            # Add GPU when implemented
        }

    def start_training_step(self, step_name):
        """Starts a specific step of the training process."""
        if self.worker and self.worker.isRunning():
            QMessageBox.warning(self, "Process Running", f"A {self.worker.step} process is already running.")
            return

        common_params = self.get_common_params()
        if not common_params["model_name"]:
             QMessageBox.warning(self, "Input Error", "Please enter a Model Name.")
             return

        params = common_params.copy()

        # Gather step-specific parameters
        if step_name == "preprocess":
            dataset_path = self.dataset_path_edit.text().strip()
            if not dataset_path or not os.path.isdir(dataset_path):
                 QMessageBox.warning(self, "Input Error", "Please select a valid Dataset Path.")
                 return
            params.update({
                "dataset_path": dataset_path,
                "cut_preprocess": "Automatic", # TODO: Get from UI
                # Add other preprocess params...
            })
        elif step_name == "extract":
             params.update({
                 "f0_method": self.f0_method_combo_train.currentText(),
                 "hop_length": 128, # TODO: Get from UI
                 "embedder_model": "contentvec", # TODO: Get from UI
                 "embedder_model_custom": None, # TODO: Get from UI
                 "gpu": "0", # TODO: Get from UI
             })
        elif step_name == "train":
             params.update({
                 "save_every_epoch": self.save_epoch_spinbox.value(),
                 "save_only_latest": self.save_latest_checkbox.isChecked(),
                 "save_every_weights": self.save_weights_checkbox.isChecked(),
                 "total_epoch": self.total_epoch_spinbox.value(),
                 "batch_size": self.batch_size_spinbox.value(),
                 "gpu": "0", # TODO: Get from UI
                 "overtraining_detector": False, # TODO: Get from UI
                 "overtraining_threshold": 50, # TODO: Get from UI
                 "pretrained": True, # TODO: Get from UI
                 "cache_data_in_gpu": False, # TODO: Get from UI
                 "index_algorithm": self.index_algo_combo.currentText(), # Pass for final indexing
                 "custom_pretrained": False, # TODO: Get from UI
                 "g_pretrained_path": None, # TODO: Get from UI
                 "d_pretrained_path": None, # TODO: Get from UI
             })
        elif step_name == "index":
             params.update({
                 "index_algorithm": self.index_algo_combo.currentText(),
             })
        else:
             QMessageBox.critical(self, "Error", f"Unknown step: {step_name}")
             return

        # Disable button(s) and start worker
        # TODO: Disable relevant buttons more selectively
        self.preprocess_button.setEnabled(False)
        self.extract_button.setEnabled(False)
        self.train_button.setEnabled(False)
        self.index_button.setEnabled(False)
        self.progress_bar.setValue(0)
        self.progress_bar.setFormat(f"{step_name.capitalize()}...")
        self.progress_bar.setTextVisible(True)

        self.worker = TrainWorker(step_name, params)
        self.worker.progress.connect(self.update_progress)
        self.worker.status.connect(self.update_status)
        self.worker.finished.connect(self.on_step_finished)
        self.worker.error.connect(self.on_step_error)
        self.worker.start()

    def reset_ui_state(self):
        """Re-enables buttons and resets progress."""
        self.preprocess_button.setEnabled(True)
        self.extract_button.setEnabled(True)
        self.train_button.setEnabled(True)
        self.index_button.setEnabled(True)
        self.progress_bar.setValue(0)
        self.progress_bar.setTextVisible(False)

    def update_progress(self, value):
        self.progress_bar.setValue(value)
        # Potentially update format string based on step/value

    def update_status(self, message):
        self.status_label.setText(f"Status: {message}")

    def on_step_finished(self, message):
        self.update_status(f"Finished: {message}")
        QMessageBox.information(self, f"{self.worker.step.capitalize()} Complete", message)
        self.reset_ui_state()

    def on_step_error(self, error_message):
        self.update_status(f"Error during {self.worker.step}")
        QMessageBox.critical(self, f"{self.worker.step.capitalize()} Error", f"An error occurred:\n{error_message}")
        print(f"Error details:\n{error_message}")
        self.reset_ui_state()
