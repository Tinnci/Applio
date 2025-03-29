from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QGridLayout, 
                             QSlider, QComboBox, QCheckBox, QLineEdit, QFileDialog, QProgressBar,
                             QMessageBox, QApplication, QSizePolicy, QSpacerItem, QTabWidget, 
                             QGroupBox, QSpinBox, QDoubleSpinBox) # Added QDoubleSpinBox
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
# Import helpers from other tabs if needed
from desktop_ui.tabs.inference_tab import refresh_embedders_folders, CUSTOM_EMBEDDER_ROOT # Reuse embedder logic

class TrainWorker(QThread):
    """Worker thread for running training steps."""
    progress = pyqtSignal(int) 
    status = pyqtSignal(str)   
    finished = pyqtSignal(str) 
    error = pyqtSignal(str)    

    def __init__(self, step, params):
        super().__init__()
        self.step = step 
        self.params = params
        self._is_running = True

    def run(self):
        """Execute the training task step."""
        try:
            self.status.emit(f"Starting {self.step}...")
            message = ""
            
            # --- Actual Call ---
            if self.step == "preprocess":
                core_params = {
                    "model_name": self.params.get("model_name"),
                    "dataset_path": self.params.get("dataset_path"),
                    "sample_rate": self.params.get("sample_rate"),
                    "cpu_cores": self.params.get("cpu_cores"),
                    "cut_preprocess": self.params.get("cut_preprocess"),
                    "process_effects": self.params.get("process_effects"), 
                    "noise_reduction": self.params.get("noise_reduction"), 
                    "clean_strength": self.params.get("clean_strength"), 
                    "chunk_len": self.params.get("chunk_len"), 
                    "overlap_len": self.params.get("overlap_len"), 
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
                    "include_mutes": self.params.get("include_mutes"), 
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
                    "cleanup": self.params.get("cleanup"), 
                    "index_algorithm": self.params.get("index_algorithm"), 
                    "cache_data_in_gpu": self.params.get("cache_data_in_gpu"),
                    "custom_pretrained": self.params.get("custom_pretrained"),
                    "g_pretrained_path": self.params.get("g_pretrained_path"),
                    "d_pretrained_path": self.params.get("d_pretrained_path"),
                    "vocoder": self.params.get("vocoder"), 
                    "checkpointing": self.params.get("checkpointing"), 
                 }
                 core_params = {k: v for k, v in core_params.items() if v is not None}
                 message = run_train_script(**core_params) 
            elif self.step == "index": 
                 core_params = {
                     "model_name": self.params.get("model_name"),
                     "index_algorithm": self.params.get("index_algorithm"),
                 }
                 core_params = {k: v for k, v in core_params.items() if v is not None}
                 message = run_index_script(**core_params)
            else:
                raise ValueError(f"Unknown training step: {self.step}")
            # --- End Actual Call ---

            self.progress.emit(50) 
            import time; time.sleep(1) 
            self.progress.emit(100)

            if self._is_running:
                self.status.emit(message)
                self.finished.emit(message)
        except Exception as e:
            error_str = f"{self.step.capitalize()} Error: {e}\n{traceback.format_exc()}"
            self.error.emit(error_str)
        finally:
            if self._is_running: self.status.emit("Idle")

    def stop(self):
        self._is_running = False
        self.status.emit(f"Cancelling {self.step}...")


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
        top_layout.addWidget(QLabel("Model Name:"), 0, 0); self.model_name_edit = QLineEdit(); self.model_name_edit.setPlaceholderText("Enter a unique name for your model"); top_layout.addWidget(self.model_name_edit, 0, 1, 1, 2) 
        top_layout.addWidget(QLabel("Dataset Path:"), 1, 0); self.dataset_path_edit = QLineEdit(); self.dataset_path_edit.setPlaceholderText("Path to your audio dataset folder"); top_layout.addWidget(self.dataset_path_edit, 1, 1)
        self.browse_dataset_button = QPushButton("Browse..."); self.browse_dataset_button.clicked.connect(self.browse_dataset_path); top_layout.addWidget(self.browse_dataset_button, 1, 2)
        top_layout.addWidget(QLabel("Sample Rate:"), 2, 0); self.sample_rate_combo = QComboBox(); self.sample_rate_combo.addItems(["40000", "48000", "32000"]); self.sample_rate_combo.setCurrentText("40000"); top_layout.addWidget(self.sample_rate_combo, 2, 1)
        main_layout.addWidget(top_group)

        # --- Preprocessing Section ---
        preprocess_group = QGroupBox("1. Preprocessing"); preprocess_layout = QGridLayout(preprocess_group)
        preprocess_layout.addWidget(QLabel("CPU Cores:"), 0, 0); self.cpu_cores_spinbox = QSpinBox(); self.cpu_cores_spinbox.setRange(1, os.cpu_count() or 1); self.cpu_cores_spinbox.setValue(os.cpu_count() or 1); preprocess_layout.addWidget(self.cpu_cores_spinbox, 0, 1)
        preprocess_layout.addWidget(QLabel("Audio Cutting:"), 1, 0); self.cut_preprocess_combo = QComboBox(); self.cut_preprocess_combo.addItems(["Automatic", "Simple", "Skip"]); self.cut_preprocess_combo.setCurrentText("Automatic"); preprocess_layout.addWidget(self.cut_preprocess_combo, 1, 1)
        self.process_effects_checkbox = QCheckBox("Process Effects"); self.process_effects_checkbox.setChecked(True); preprocess_layout.addWidget(self.process_effects_checkbox, 2, 0)
        self.noise_reduction_checkbox = QCheckBox("Noise Reduction"); preprocess_layout.addWidget(self.noise_reduction_checkbox, 2, 1)
        self.clean_strength_label = QLabel("NR Strength:"); self.clean_strength_label.setVisible(False); preprocess_layout.addWidget(self.clean_strength_label, 2, 2)
        self.clean_strength_slider = QSlider(Qt.Orientation.Horizontal); self.clean_strength_slider.setRange(0, 100); self.clean_strength_slider.setValue(50); self.clean_strength_slider.setVisible(False); preprocess_layout.addWidget(self.clean_strength_slider, 2, 3)
        self.noise_reduction_checkbox.stateChanged.connect(lambda state: self.clean_strength_label.setVisible(state == Qt.CheckState.Checked.value)); self.noise_reduction_checkbox.stateChanged.connect(lambda state: self.clean_strength_slider.setVisible(state == Qt.CheckState.Checked.value))
        preprocess_layout.addWidget(QLabel("Chunk Length (s):"), 3, 0); self.chunk_len_spinbox = QDoubleSpinBox(); self.chunk_len_spinbox.setRange(0.5, 5.0); self.chunk_len_spinbox.setValue(3.0); self.chunk_len_spinbox.setSingleStep(0.1); preprocess_layout.addWidget(self.chunk_len_spinbox, 3, 1)
        preprocess_layout.addWidget(QLabel("Overlap Length (s):"), 3, 2); self.overlap_len_spinbox = QDoubleSpinBox(); self.overlap_len_spinbox.setRange(0.0, 0.4); self.overlap_len_spinbox.setValue(0.3); self.overlap_len_spinbox.setSingleStep(0.1); preprocess_layout.addWidget(self.overlap_len_spinbox, 3, 3)
        self.preprocess_button = QPushButton("Preprocess Dataset"); self.preprocess_button.clicked.connect(lambda: self.start_training_step("preprocess")); preprocess_layout.addWidget(self.preprocess_button, 4, 0, 1, 4) 
        main_layout.addWidget(preprocess_group)

        # --- Feature Extraction Section ---
        extract_group = QGroupBox("2. Feature Extraction"); extract_layout = QGridLayout(extract_group)
        extract_layout.addWidget(QLabel("F0 Method:"), 0, 0); self.f0_method_combo_train = QComboBox(); self.f0_method_combo_train.addItems(["rmvpe", "crepe", "crepe-tiny"]); self.f0_method_combo_train.setCurrentText("rmvpe"); extract_layout.addWidget(self.f0_method_combo_train, 0, 1)
        self.hop_length_label = QLabel("Hop Length:"); self.hop_length_label.setVisible(False); extract_layout.addWidget(self.hop_length_label, 0, 2)
        self.hop_length_spinbox = QSpinBox(); self.hop_length_spinbox.setRange(1, 512); self.hop_length_spinbox.setValue(128); self.hop_length_spinbox.setVisible(False); extract_layout.addWidget(self.hop_length_spinbox, 0, 3)
        self.f0_method_combo_train.currentTextChanged.connect(lambda text: self.hop_length_label.setVisible("crepe" in text)); self.f0_method_combo_train.currentTextChanged.connect(lambda text: self.hop_length_spinbox.setVisible("crepe" in text))
        extract_layout.addWidget(QLabel("Embedder Model:"), 1, 0); self.embedder_model_combo_train = QComboBox(); self.embedder_model_combo_train.addItems(["contentvec", "chinese-hubert-base", "japanese-hubert-base", "korean-hubert-base", "custom"]); self.embedder_model_combo_train.setCurrentText("contentvec"); self.embedder_model_combo_train.currentTextChanged.connect(self.toggle_custom_embedder_visibility_train); extract_layout.addWidget(self.embedder_model_combo_train, 1, 1)
        extract_layout.addWidget(QLabel("Include Mutes:"), 1, 2); self.include_mutes_spinbox = QSpinBox(); self.include_mutes_spinbox.setRange(0, 10); self.include_mutes_spinbox.setValue(2); extract_layout.addWidget(self.include_mutes_spinbox, 1, 3)
        self.custom_embedder_group_train = QGroupBox("Custom Embedder"); self.custom_embedder_group_train.setVisible(False); custom_embedder_layout_train = QGridLayout(self.custom_embedder_group_train); custom_embedder_layout_train.addWidget(QLabel("Select Custom Embedder:"), 0, 0); self.embedder_model_custom_combo_train = QComboBox(); self.refresh_embedder_folders_train(); custom_embedder_layout_train.addWidget(self.embedder_model_custom_combo_train, 0, 1); self.refresh_embedders_button_train = QPushButton("Refresh"); self.refresh_embedders_button_train.clicked.connect(self.refresh_embedder_folders_train); custom_embedder_layout_train.addWidget(self.refresh_embedders_button_train, 0, 2); extract_layout.addWidget(self.custom_embedder_group_train, 2, 0, 1, 4) 
        self.extract_button = QPushButton("Extract Features"); self.extract_button.clicked.connect(lambda: self.start_training_step("extract")); extract_layout.addWidget(self.extract_button, 3, 0, 1, 4)
        main_layout.addWidget(extract_group)

        # --- Training Section ---
        train_group = QGroupBox("3. Model Training"); train_layout = QGridLayout(train_group)
        train_layout.addWidget(QLabel("Total Epochs:"), 0, 0); self.total_epoch_spinbox = QSpinBox(); self.total_epoch_spinbox.setRange(1, 10000); self.total_epoch_spinbox.setValue(500); train_layout.addWidget(self.total_epoch_spinbox, 0, 1)
        train_layout.addWidget(QLabel("Batch Size:"), 0, 2); self.batch_size_spinbox = QSpinBox(); self.batch_size_spinbox.setRange(1, 50); self.batch_size_spinbox.setValue(8); train_layout.addWidget(self.batch_size_spinbox, 0, 3)
        train_layout.addWidget(QLabel("Save Every Epoch:"), 1, 0); self.save_epoch_spinbox = QSpinBox(); self.save_epoch_spinbox.setRange(1, 100); self.save_epoch_spinbox.setValue(10); train_layout.addWidget(self.save_epoch_spinbox, 1, 1)
        self.save_latest_checkbox = QCheckBox("Save Only Latest Ckpt"); self.save_latest_checkbox.setChecked(True); train_layout.addWidget(self.save_latest_checkbox, 1, 2)
        self.save_weights_checkbox = QCheckBox("Save Every Weights"); self.save_weights_checkbox.setChecked(True); train_layout.addWidget(self.save_weights_checkbox, 1, 3)
        train_layout.addWidget(QLabel("GPU(s) (e.g., 0 or 0-1):"), 2, 0); self.gpu_edit = QLineEdit(); self.gpu_edit.setText("0"); train_layout.addWidget(self.gpu_edit, 2, 1) # Default to GPU 0
        train_layout.addWidget(QLabel("Vocoder:"), 2, 2); self.vocoder_combo = QComboBox(); self.vocoder_combo.addItems(["HiFi-GAN", "MRF HiFi-GAN", "RefineGAN"]); train_layout.addWidget(self.vocoder_combo, 2, 3) # TODO: Make conditional on Applio arch?
        self.pretrained_checkbox = QCheckBox("Use Pretrained"); self.pretrained_checkbox.setChecked(True); self.pretrained_checkbox.stateChanged.connect(self.toggle_pretrained_visibility); train_layout.addWidget(self.pretrained_checkbox, 3, 0)
        self.cache_gpu_checkbox = QCheckBox("Cache Dataset in GPU"); train_layout.addWidget(self.cache_gpu_checkbox, 3, 1)
        self.overtrain_checkbox = QCheckBox("Detect Overtraining"); self.overtrain_checkbox.stateChanged.connect(self.toggle_overtrain_visibility); train_layout.addWidget(self.overtrain_checkbox, 3, 2)
        self.checkpointing_checkbox = QCheckBox("Use Checkpointing"); train_layout.addWidget(self.checkpointing_checkbox, 3, 3)
        self.overtrain_thresh_label = QLabel("Overtrain Threshold:"); self.overtrain_thresh_label.setVisible(False); train_layout.addWidget(self.overtrain_thresh_label, 4, 2)
        self.overtrain_thresh_spinbox = QSpinBox(); self.overtrain_thresh_spinbox.setRange(1, 100); self.overtrain_thresh_spinbox.setValue(50); self.overtrain_thresh_spinbox.setVisible(False); train_layout.addWidget(self.overtrain_thresh_spinbox, 4, 3)
        self.custom_pretrained_checkbox = QCheckBox("Use Custom Pretrained"); self.custom_pretrained_checkbox.stateChanged.connect(self.toggle_pretrained_visibility); train_layout.addWidget(self.custom_pretrained_checkbox, 5, 0)
        self.custom_pretrained_group = QGroupBox("Custom Pretrained Models"); self.custom_pretrained_group.setVisible(False); custom_pretrained_layout = QGridLayout(self.custom_pretrained_group)
        custom_pretrained_layout.addWidget(QLabel("Generator (.pth):"), 0, 0); self.g_pretrained_edit = QLineEdit(); custom_pretrained_layout.addWidget(self.g_pretrained_edit, 0, 1); g_browse = QPushButton("Browse..."); g_browse.clicked.connect(lambda: self.browse_pretrained(self.g_pretrained_edit)); custom_pretrained_layout.addWidget(g_browse, 0, 2)
        custom_pretrained_layout.addWidget(QLabel("Discriminator (.pth):"), 1, 0); self.d_pretrained_edit = QLineEdit(); custom_pretrained_layout.addWidget(self.d_pretrained_edit, 1, 1); d_browse = QPushButton("Browse..."); d_browse.clicked.connect(lambda: self.browse_pretrained(self.d_pretrained_edit)); custom_pretrained_layout.addWidget(d_browse, 1, 2)
        train_layout.addWidget(self.custom_pretrained_group, 6, 0, 1, 4)
        self.cleanup_checkbox = QCheckBox("Fresh Training (Cleanup Logs)"); train_layout.addWidget(self.cleanup_checkbox, 7, 0)
        self.train_button = QPushButton("Train Model"); self.train_button.clicked.connect(lambda: self.start_training_step("train")); train_layout.addWidget(self.train_button, 8, 0, 1, 4) 
        main_layout.addWidget(train_group)

        # --- Index Training Section ---
        index_group = QGroupBox("4. Index Training"); index_layout = QGridLayout(index_group)
        index_layout.addWidget(QLabel("Index Algorithm:"), 0, 0); self.index_algo_combo = QComboBox(); self.index_algo_combo.addItems(["Auto", "Faiss", "KMeans"]); index_layout.addWidget(self.index_algo_combo, 0, 1)
        self.index_button = QPushButton("Train Index"); self.index_button.clicked.connect(lambda: self.start_training_step("index")); index_layout.addWidget(self.index_button, 1, 0, 1, 2) 
        main_layout.addWidget(index_group)

        # --- Status/Progress ---
        status_group = QWidget(); status_layout = QVBoxLayout(status_group); status_layout.setContentsMargins(0,10,0,0)
        self.status_label = QLabel("Status: Idle"); status_layout.addWidget(self.status_label)
        self.progress_bar = QProgressBar(); self.progress_bar.setValue(0); self.progress_bar.setTextVisible(False); status_layout.addWidget(self.progress_bar)
        main_layout.addWidget(status_group)

        main_layout.addSpacerItem(QSpacerItem(20, 40, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Expanding))
        self.setLayout(main_layout)

    def browse_dataset_path(self):
        dir_path = QFileDialog.getExistingDirectory(self, "Select Dataset Directory", project_root)
        if dir_path: self.dataset_path_edit.setText(dir_path)

    def browse_pretrained(self, line_edit_widget):
        # Assuming pretrained models are in assets or logs? Adjust start dir if needed.
        file_path, _ = QFileDialog.getOpenFileName(self, "Select Pretrained Model", project_root, "PyTorch Model Files (*.pth)")
        if file_path: line_edit_widget.setText(file_path)

    def toggle_overtrain_visibility(self, state):
        is_checked = state == Qt.CheckState.Checked.value
        self.overtrain_thresh_label.setVisible(is_checked)
        self.overtrain_thresh_spinbox.setVisible(is_checked)

    def toggle_pretrained_visibility(self):
        use_pretrained = self.pretrained_checkbox.isChecked()
        use_custom = self.custom_pretrained_checkbox.isChecked()
        self.custom_pretrained_checkbox.setVisible(use_pretrained)
        self.custom_pretrained_group.setVisible(use_pretrained and use_custom)

    def toggle_custom_embedder_visibility_train(self, text):
        self.custom_embedder_group_train.setVisible(text == "custom")

    def refresh_embedder_folders_train(self): # Separate refresh for train tab
        self.embedder_model_custom_combo_train.clear()
        try:
            folders = refresh_embedders_folders(); 
            if folders: self.embedder_model_custom_combo_train.addItems(folders)
            else: self.embedder_model_custom_combo_train.addItem("No custom embedders found")
        except Exception as e: print(f"Error refreshing embedder folders: {e}"); self.embedder_model_custom_combo_train.addItem("Error loading embedders")

    def get_common_params(self):
        """Gathers parameters common to multiple steps."""
        return {
            "model_name": self.model_name_edit.text().strip(),
            "sample_rate": int(self.sample_rate_combo.currentText()),
            "cpu_cores": self.cpu_cores_spinbox.value(),
            "gpu": self.gpu_edit.text().strip(), # Pass GPU string
        }

    def start_training_step(self, step_name):
        """Starts a specific step of the training process."""
        if self.worker and self.worker.isRunning():
            QMessageBox.warning(self, "Process Running", f"A {self.worker.step} process is already running.")
            return

        common_params = self.get_common_params()
        if not common_params["model_name"]:
             QMessageBox.warning(self, "Input Error", "Please enter a Model Name."); return

        params = common_params.copy()

        # Gather step-specific parameters
        if step_name == "preprocess":
            dataset_path = self.dataset_path_edit.text().strip()
            if not dataset_path or not os.path.isdir(dataset_path):
                 QMessageBox.warning(self, "Input Error", "Please select a valid Dataset Path."); return
            params.update({
                "dataset_path": dataset_path,
                "cut_preprocess": self.cut_preprocess_combo.currentText(),
                "process_effects": self.process_effects_checkbox.isChecked(),
                "noise_reduction": self.noise_reduction_checkbox.isChecked(),
                "clean_strength": self.clean_strength_slider.value() / 100.0 if self.noise_reduction_checkbox.isChecked() else 0.7,
                "chunk_len": self.chunk_len_spinbox.value(),
                "overlap_len": self.overlap_len_spinbox.value(),
            })
        elif step_name == "extract":
             params.update({
                 "f0_method": self.f0_method_combo_train.currentText(),
                 "hop_length": self.hop_length_spinbox.value() if "crepe" in self.f0_method_combo_train.currentText() else 128,
                 "embedder_model": self.embedder_model_combo_train.currentText(),
                 "embedder_model_custom": self.embedder_model_custom_combo_train.currentText() if self.embedder_model_combo_train.currentText() == "custom" else None,
                 "include_mutes": self.include_mutes_spinbox.value(),
             })
        elif step_name == "train":
             g_path = self.g_pretrained_edit.text().strip() if self.custom_pretrained_checkbox.isChecked() else None
             d_path = self.d_pretrained_edit.text().strip() if self.custom_pretrained_checkbox.isChecked() else None
             params.update({
                 "save_every_epoch": self.save_epoch_spinbox.value(),
                 "save_only_latest": self.save_latest_checkbox.isChecked(),
                 "save_every_weights": self.save_weights_checkbox.isChecked(),
                 "total_epoch": self.total_epoch_spinbox.value(),
                 "batch_size": self.batch_size_spinbox.value(),
                 "overtraining_detector": self.overtrain_checkbox.isChecked(),
                 "overtraining_threshold": self.overtrain_thresh_spinbox.value() if self.overtrain_checkbox.isChecked() else 50,
                 "pretrained": self.pretrained_checkbox.isChecked(),
                 "cache_data_in_gpu": self.cache_gpu_checkbox.isChecked(),
                 "index_algorithm": self.index_algo_combo.currentText(), 
                 "custom_pretrained": self.custom_pretrained_checkbox.isChecked(),
                 "g_pretrained_path": g_path if g_path else None,
                 "d_pretrained_path": d_path if d_path else None,
                 "vocoder": self.vocoder_combo.currentText(),
                 "checkpointing": self.checkpointing_checkbox.isChecked(),
                 "cleanup": self.cleanup_checkbox.isChecked(),
             })
        elif step_name == "index":
             params.update({"index_algorithm": self.index_algo_combo.currentText()})
        else:
             QMessageBox.critical(self, "Error", f"Unknown step: {step_name}"); return

        # Disable button(s) and start worker
        self.set_buttons_enabled(False)
        self.progress_bar.setValue(0); self.progress_bar.setFormat(f"{step_name.capitalize()}..."); self.progress_bar.setTextVisible(True)

        self.worker = TrainWorker(step_name, params)
        self.worker.progress.connect(self.update_progress)
        self.worker.status.connect(self.update_status)
        self.worker.finished.connect(self.on_step_finished)
        self.worker.error.connect(self.on_step_error)
        self.worker.start()

    def set_buttons_enabled(self, enabled):
        """Enable/disable all step buttons."""
        self.preprocess_button.setEnabled(enabled)
        self.extract_button.setEnabled(enabled)
        self.train_button.setEnabled(enabled)
        self.index_button.setEnabled(enabled)

    def reset_ui_state(self):
        """Re-enables buttons and resets progress."""
        self.set_buttons_enabled(True)
        self.progress_bar.setValue(0); self.progress_bar.setTextVisible(False)

    def update_progress(self, value):
        self.progress_bar.setValue(value)

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
