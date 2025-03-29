from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QLabel, QPushButton, QGridLayout, 
                             QSlider, QComboBox, QLineEdit, QFileDialog, QProgressBar,
                             QMessageBox, QSizePolicy, QSpacerItem, QTabWidget) # Added QTabWidget
from PyQt6.QtCore import Qt, QThread, pyqtSignal
import os
import sys
import traceback

# Ensure the core Applio logic can be imported
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

# Import core functions
from core import run_infer_script #, run_batch_infer_script # Batch script later
# Import helper functions from original Gradio tab (or reimplement)
from tabs.inference.inference import (get_speakers_id, match_index, output_path_fn, 
                                      extract_model_and_epoch, get_indexes) # Reuse helpers

# Define constants based on original file
MODEL_ROOT = os.path.join(project_root, "logs")
AUDIO_ROOT = os.path.join(project_root, "assets", "audios")
SUP_AUDIOEXT = {
    "wav", "mp3", "flac", "ogg", "opus", "m4a", "mp4", "aac", "alac", "wma", "aiff", "webm", "ac3",
}

class InferenceWorker(QThread):
    """Worker thread for running inference to avoid blocking the UI."""
    progress = pyqtSignal(int) # Signal for progress updates (0-100) - Might not be usable yet
    status = pyqtSignal(str)   # Signal for status messages
    finished = pyqtSignal(str, str) # Signal when done (message, output_audio_path)
    error = pyqtSignal(str)     # Signal on error

    def __init__(self, params):
        super().__init__()
        self.params = params
        self._is_running = True

    def run(self):
        """Execute the inference task."""
        try:
            self.status.emit("Starting inference...")
            # Call the actual inference function from core.py
            # Note: run_infer_script expects volume_envelope as int 0-100, but slider is 0-1
            # Adjusting here, or adjust slider range/value reading later
            # Also, many params are missing from the placeholder UI, using defaults from core.py for now
            
            # Map UI params to core function params (ensure names match core.py function signature)
            core_params = {
                "pitch": self.params.get("pitch", 0),
                "index_rate": self.params.get("index_rate", 0.75),
                "volume_envelope": int(self.params.get("rms_mix_rate", 1.0) * 100), # Convert 0-1 to 0-100 if needed, check core.py
                "protect": self.params.get("protect", 0.5),
                "hop_length": self.params.get("hop_length", 128),
                "f0_method": self.params.get("f0_method", "rmvpe"),
                "input_path": self.params.get("input_path"),
                "output_path": self.params.get("output_path"),
                "pth_path": self.params.get("pth_path"),
                "index_path": self.params.get("index_path"),
                "split_audio": self.params.get("split_audio", False),
                "f0_autotune": self.params.get("f0_autotune", False),
                "f0_autotune_strength": self.params.get("f0_autotune_strength", 1.0),
                "clean_audio": self.params.get("clean_audio", False),
                "clean_strength": self.params.get("clean_strength", 0.7),
                "export_format": self.params.get("export_format", "WAV"),
                "f0_file": self.params.get("f0_file", None),
                "embedder_model": self.params.get("embedder_model", "contentvec"),
                "embedder_model_custom": self.params.get("embedder_model_custom", None),
                "sid": self.params.get("sid", 0),
                # Add other params as they are implemented in the UI
                "formant_shifting": self.params.get("formant_shifting", False),
                "formant_qfrency": self.params.get("formant_qfrency", 1.0),
                "formant_timbre": self.params.get("formant_timbre", 1.0),
                "post_process": self.params.get("post_process", False),
                # Add post-processing effect params...
            }

            # Remove None values which might cause issues if core func doesn't expect them
            core_params = {k: v for k, v in core_params.items() if v is not None}

            # --- Actual Call ---
            message, output_path = run_infer_script(**core_params)
            # --- End Actual Call ---

            # --- Placeholder for progress (since core func doesn't yield) ---
            self.progress.emit(50) # Indicate work started
            # Simulate some work based on file size? Difficult without modifying core.
            import time
            time.sleep(1) # Minimal simulation
            self.progress.emit(100)
            # --- End Placeholder ---

            if self._is_running:
                self.status.emit(message)
                self.finished.emit(message, output_path)
        except Exception as e:
            error_str = f"Inference Error: {e}\n{traceback.format_exc()}"
            self.error.emit(error_str)
        finally:
            if self._is_running: # Don't reset status if cancelled
                self.status.emit("Idle") # Reset status only if finished normally or errored

    def stop(self):
        self._is_running = False
        self.status.emit("Cancelling...")
        # TODO: Implement actual process termination if possible/needed
        # This might involve tracking the subprocess PID if core.py launches one,
        # or modifying core.py functions to be cancellable.


class InferenceTab(QWidget):
    """Widget for the Inference Tab."""
    def __init__(self):
        super().__init__()
        self.inference_worker = None
        self.setup_ui()
        self.refresh_models_and_indexes() # Initial population

    def setup_ui(self):
        main_layout = QVBoxLayout(self)

        # --- Model Selection ---
        model_group_box = QWidget()
        model_layout = QGridLayout(model_group_box)
        model_layout.setContentsMargins(0,0,0,0)

        model_layout.addWidget(QLabel("Voice Model:"), 0, 0)
        self.model_combo = QComboBox()
        self.model_combo.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.model_combo.currentIndexChanged.connect(self.on_model_selected)
        model_layout.addWidget(self.model_combo, 0, 1)

        model_layout.addWidget(QLabel("Index File:"), 1, 0)
        self.index_combo = QComboBox()
        self.index_combo.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        model_layout.addWidget(self.index_combo, 1, 1)

        refresh_button = QPushButton("Refresh")
        refresh_button.clicked.connect(self.refresh_models_and_indexes)
        model_layout.addWidget(refresh_button, 0, 2)

        unload_button = QPushButton("Unload")
        unload_button.clicked.connect(self.unload_model)
        model_layout.addWidget(unload_button, 1, 2)

        main_layout.addWidget(model_group_box)

        # --- Single Inference ---
        # Using QTabWidget for Single/Batch, though only Single is implemented now
        self.single_batch_tabs = QTabWidget()
        single_tab_widget = QWidget()
        single_tab_layout = QVBoxLayout(single_tab_widget)

        # Input Audio Section
        input_group_box = QWidget()
        input_layout = QGridLayout(input_group_box)
        input_layout.setContentsMargins(0,5,0,5) # Top margin

        input_layout.addWidget(QLabel("Input Audio:"), 0, 0)
        self.input_audio_path_edit = QLineEdit()
        self.input_audio_path_edit.setPlaceholderText("Select audio file")
        input_layout.addWidget(self.input_audio_path_edit, 0, 1)
        self.browse_input_button = QPushButton("Browse...")
        self.browse_input_button.clicked.connect(self.browse_input_audio)
        input_layout.addWidget(self.browse_input_button, 0, 2)
        # TODO: Add dropdown for existing audio files? Or just file browse? Keeping simple for now.
        # TODO: Add audio player/recorder widget if possible/needed

        single_tab_layout.addWidget(input_group_box)

        # Output Path Section
        output_group_box = QWidget()
        output_layout = QGridLayout(output_group_box)
        output_layout.setContentsMargins(0,0,0,5) # Bottom margin

        output_layout.addWidget(QLabel("Output Path:"), 0, 0)
        self.output_audio_path_edit = QLineEdit()
        self.output_audio_path_edit.setPlaceholderText("Select output file path")
        output_layout.addWidget(self.output_audio_path_edit, 0, 1)
        self.browse_output_button = QPushButton("Browse...")
        self.browse_output_button.clicked.connect(self.browse_output_path)
        output_layout.addWidget(self.browse_output_button, 0, 2)

        single_tab_layout.addWidget(output_group_box)

        # Basic Settings Section
        basic_settings_group_box = QWidget()
        basic_settings_layout = QGridLayout(basic_settings_group_box)
        basic_settings_layout.setContentsMargins(0,0,0,0)

        self.pitch_label = QLabel("Pitch (0):")
        basic_settings_layout.addWidget(self.pitch_label, 0, 0)
        self.pitch_slider = QSlider(Qt.Orientation.Horizontal)
        self.pitch_slider.setRange(-24, 24)
        self.pitch_slider.setValue(0)
        self.pitch_slider.valueChanged.connect(lambda val: self.pitch_label.setText(f"Pitch ({val}):"))
        basic_settings_layout.addWidget(self.pitch_slider, 0, 1, 1, 2) # Span 2 columns

        self.index_rate_label = QLabel("Index Rate (0.75):")
        basic_settings_layout.addWidget(self.index_rate_label, 1, 0)
        self.index_rate_slider = QSlider(Qt.Orientation.Horizontal)
        self.index_rate_slider.setRange(0, 100) # Use 0-100 for easier steps
        self.index_rate_slider.setValue(75)
        self.index_rate_slider.valueChanged.connect(lambda val: self.index_rate_label.setText(f"Index Rate ({val/100.0:.2f}):"))
        basic_settings_layout.addWidget(self.index_rate_slider, 1, 1, 1, 2)

        self.rms_mix_rate_label = QLabel("Volume Env (1.00):")
        basic_settings_layout.addWidget(self.rms_mix_rate_label, 2, 0)
        self.rms_mix_rate_slider = QSlider(Qt.Orientation.Horizontal)
        self.rms_mix_rate_slider.setRange(0, 100)
        self.rms_mix_rate_slider.setValue(100)
        self.rms_mix_rate_slider.valueChanged.connect(lambda val: self.rms_mix_rate_label.setText(f"Volume Env ({val/100.0:.2f}):"))
        basic_settings_layout.addWidget(self.rms_mix_rate_slider, 2, 1, 1, 2)

        self.protect_label = QLabel("Protect (0.50):")
        basic_settings_layout.addWidget(self.protect_label, 3, 0)
        self.protect_slider = QSlider(Qt.Orientation.Horizontal)
        self.protect_slider.setRange(0, 50) # 0 to 0.5
        self.protect_slider.setValue(50)
        self.protect_slider.valueChanged.connect(lambda val: self.protect_label.setText(f"Protect ({val/100.0:.2f}):"))
        basic_settings_layout.addWidget(self.protect_slider, 3, 1, 1, 2)

        single_tab_layout.addWidget(basic_settings_group_box)

        # --- Advanced Settings (Placeholder Group) ---
        # TODO: Implement properly with QGroupBox/QScrollArea if needed
        advanced_settings_group = QWidget()
        advanced_layout = QGridLayout(advanced_settings_group)
        advanced_layout.setContentsMargins(0,10,0,0) # Top margin

        advanced_layout.addWidget(QLabel("F0 Method:"), 0, 0)
        self.f0_method_combo = QComboBox()
        self.f0_method_combo.addItems(["rmvpe", "crepe", "crepe-tiny", "fcpe", "hybrid[rmvpe+fcpe]"]) # From original
        self.f0_method_combo.setCurrentText("rmvpe")
        advanced_layout.addWidget(self.f0_method_combo, 0, 1)

        advanced_layout.addWidget(QLabel("Speaker ID:"), 1, 0)
        self.sid_combo = QComboBox()
        # Speaker ID needs to be populated when model changes
        advanced_layout.addWidget(self.sid_combo, 1, 1)

        advanced_layout.addWidget(QLabel("Export Format:"), 2, 0)
        self.export_format_combo = QComboBox()
        self.export_format_combo.addItems(["WAV", "MP3", "FLAC", "OGG", "M4A"])
        advanced_layout.addWidget(self.export_format_combo, 2, 1)

        # TODO: Add other advanced settings (Checkboxes, Sliders, Custom Embedder section)

        single_tab_layout.addWidget(advanced_settings_group)

        # Add spacer to push controls up
        single_tab_layout.addSpacerItem(QSpacerItem(20, 40, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Expanding))

        self.single_batch_tabs.addTab(single_tab_widget, "Single")
        # TODO: Add Batch Tab
        main_layout.addWidget(self.single_batch_tabs)


        # --- Action Buttons & Status ---
        action_status_group = QWidget()
        action_status_layout = QVBoxLayout(action_status_group)
        action_status_layout.setContentsMargins(0,10,0,0)

        self.convert_button = QPushButton("Convert")
        self.convert_button.clicked.connect(self.start_inference)
        action_status_layout.addWidget(self.convert_button)

        self.status_label = QLabel("Status: Idle")
        action_status_layout.addWidget(self.status_label)

        self.progress_bar = QProgressBar()
        self.progress_bar.setValue(0)
        self.progress_bar.setTextVisible(False)
        action_status_layout.addWidget(self.progress_bar)

        main_layout.addWidget(action_status_group)

        self.setLayout(main_layout)

    def refresh_models_and_indexes(self):
        """Scans logs directory and updates model/index dropdowns."""
        print("Refreshing models and indexes...")
        self.model_combo.clear()
        self.index_combo.clear()

        # Find models (.pth/.onnx)
        model_files = []
        if os.path.exists(MODEL_ROOT):
            for root, _, files in os.walk(MODEL_ROOT):
                for file in files:
                    if file.endswith((".pth", ".onnx")) and not (file.startswith("G_") or file.startswith("D_")):
                         model_files.append(os.path.join(root, file))
        
        # Sort models (optional, based on original logic)
        try:
            sorted_models = sorted(model_files, key=lambda x: extract_model_and_epoch(x))
        except Exception: # Fallback if sorting fails
             sorted_models = sorted(model_files)

        if not sorted_models:
            self.model_combo.addItem("No models found")
            self.model_combo.setEnabled(False)
        else:
            self.model_combo.setEnabled(True)
            for model_path in sorted_models:
                # Display name could be just the filename or relative path
                display_name = os.path.relpath(model_path, MODEL_ROOT)
                self.model_combo.addItem(display_name, userData=model_path) # Store full path in userData

        # Find indexes
        index_files = get_indexes() # Use helper from original
        if not index_files:
             self.index_combo.addItem("No index files found")
             self.index_combo.setEnabled(False)
        else:
             self.index_combo.setEnabled(True)
             self.index_combo.addItem("", userData="") # Add empty option
             for index_path in sorted(index_files):
                 display_name = os.path.relpath(index_path, MODEL_ROOT)
                 self.index_combo.addItem(display_name, userData=index_path)

        # Trigger update for selected model
        self.on_model_selected()
        print("Refresh complete.")


    def on_model_selected(self):
        """Updates index file and speaker ID when a model is selected."""
        selected_model_path = self.model_combo.currentData() # Get full path

        if not selected_model_path:
            self.sid_combo.clear()
            self.sid_combo.addItem("0")
            self.sid_combo.setEnabled(False)
            # Try to clear index selection
            index = self.index_combo.findData("")
            if index >= 0:
                self.index_combo.setCurrentIndex(index)
            return

        # Auto-select matching index file
        matched_index = match_index(selected_model_path)
        if matched_index:
            index = self.index_combo.findData(matched_index)
            if index >= 0:
                self.index_combo.setCurrentIndex(index)
            else: # If matched index not in list (maybe deleted?), add it? Or clear selection? Clear for now.
                 index = self.index_combo.findData("")
                 if index >= 0: self.index_combo.setCurrentIndex(index)
        else:
             index = self.index_combo.findData("")
             if index >= 0: self.index_combo.setCurrentIndex(index)


        # Update Speaker ID dropdown
        self.sid_combo.clear()
        speaker_ids = get_speakers_id(selected_model_path) # Use helper
        if speaker_ids:
            self.sid_combo.addItems([str(sid) for sid in speaker_ids])
            self.sid_combo.setEnabled(True)
        else:
            self.sid_combo.addItem("0") # Default if no speaker info
            self.sid_combo.setEnabled(False)


    def unload_model(self):
        """Clears model and index selection."""
        self.model_combo.setCurrentIndex(-1)
        self.index_combo.setCurrentIndex(self.index_combo.findData("")) # Select empty index
        self.sid_combo.clear()
        self.sid_combo.addItem("0")
        self.sid_combo.setEnabled(False)

    def browse_input_audio(self):
        # Use project_root or a more sensible default directory
        start_dir = AUDIO_ROOT if os.path.exists(AUDIO_ROOT) else project_root
        # Create filter string from SUP_AUDIOEXT
        audio_filter = "Audio Files (" + " ".join(f"*.{ext}" for ext in SUP_AUDIOEXT) + ");;All Files (*)"
        file_path, _ = QFileDialog.getOpenFileName(self, "Select Input Audio", start_dir, audio_filter)
        if file_path:
            self.input_audio_path_edit.setText(file_path)
            # Update default output path based on input
            default_output = output_path_fn(file_path) # Use helper
            self.output_audio_path_edit.setText(default_output)

    def browse_output_path(self):
        start_dir = os.path.dirname(self.output_audio_path_edit.text()) if self.output_audio_path_edit.text() else AUDIO_ROOT
        if not os.path.exists(start_dir):
            start_dir = AUDIO_ROOT if os.path.exists(AUDIO_ROOT) else project_root
            
        # Suggest filename based on input and selected format
        default_filename = os.path.basename(self.output_audio_path_edit.text()) if self.output_audio_path_edit.text() else "output.wav"
        selected_format = self.export_format_combo.currentText().lower()
        default_filename = os.path.splitext(default_filename)[0] + f".{selected_format}"

        # Create filter string
        format_filter = f"{selected_format.upper()} Files (*.{selected_format});;WAV Files (*.wav);;MP3 Files (*.mp3);;FLAC Files (*.flac);;OGG Files (*.ogg);;M4A Files (*.m4a)"

        file_path, _ = QFileDialog.getSaveFileName(self, "Select Output Path", os.path.join(start_dir, default_filename), format_filter)
        if file_path:
            # Ensure correct extension
            if not file_path.lower().endswith(f".{selected_format}"):
                file_path = os.path.splitext(file_path)[0] + f".{selected_format}"
            self.output_audio_path_edit.setText(file_path)

    def start_inference(self):
        if self.inference_worker and self.inference_worker.isRunning():
            # Ask user if they want to cancel the current job
            reply = QMessageBox.question(self, 'Inference Running', 
                                         'An inference task is already running. Cancel it and start a new one?',
                                         QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No, 
                                         QMessageBox.StandardButton.No)
            if reply == QMessageBox.StandardButton.Yes and self.inference_worker:
                self.inference_worker.stop()
                # Optionally wait briefly for thread to acknowledge stop?
            else:
                return # Don't start new job if user selects No or worker doesn't exist

        # --- Gather parameters from UI elements ---
        # Ensure paths are retrieved using currentData for reliability
        pth_path = self.model_combo.currentData()
        index_path = self.index_combo.currentData() if self.index_combo.currentIndex() > 0 else "" # Handle empty selection

        params = {
            "pitch": self.pitch_slider.value(),
            "index_rate": self.index_rate_slider.value() / 100.0,
            "rms_mix_rate": self.rms_mix_rate_slider.value() / 100.0, # Pass as 0-1
            "protect": self.protect_slider.value() / 100.0, # Pass as 0-0.5
            "input_path": self.input_audio_path_edit.text(),
            "output_path": self.output_audio_path_edit.text(),
            "pth_path": pth_path,
            "index_path": index_path,
            "f0_method": self.f0_method_combo.currentText(),
            "sid": int(self.sid_combo.currentText()) if self.sid_combo.currentText() else 0,
            "export_format": self.export_format_combo.currentText(),
            # TODO: Get values from other implemented advanced controls
            # Defaults for unimplemented controls:
            "hop_length": 128,
            "split_audio": False,
            "f0_autotune": False,
            "f0_autotune_strength": 1.0,
            "clean_audio": False,
            "clean_strength": 0.7,
            "f0_file": None,
            "embedder_model": "contentvec", # TODO: Get from UI when implemented
            "embedder_model_custom": None, # TODO: Get from UI when implemented
            "formant_shifting": False, # TODO: Get from UI when implemented
            "formant_qfrency": 1.0, # TODO: Get from UI when implemented
            "formant_timbre": 1.0, # TODO: Get from UI when implemented
            "post_process": False, # TODO: Get from UI when implemented
            # Add post-processing effect params...
        }

        # --- Validate parameters ---
        if not params["input_path"] or not os.path.exists(params["input_path"]):
            self.update_status("Error: Input audio path is invalid.")
            QMessageBox.warning(self, "Input Error", "Please select a valid input audio file.")
            return
        if not params["output_path"]:
            self.update_status("Error: Output path cannot be empty.")
            QMessageBox.warning(self, "Output Error", "Please specify an output file path.")
            return
        if not params["pth_path"] or not os.path.exists(params["pth_path"]):
             self.update_status("Error: Voice model (.pth) not selected or not found.")
             QMessageBox.warning(self, "Model Error", "Please select a valid voice model file.")
             return
        # Index file is optional, but check if selected path exists
        if params["index_path"] and not os.path.exists(params["index_path"]):
             self.update_status(f"Warning: Selected index file not found: {params['index_path']}")
             # Allow proceeding without index, but maybe warn user?
             # QMessageBox.warning(self, "Index Warning", f"Selected index file not found:\n{params['index_path']}\nProceeding without index.")
             # params["index_path"] = "" # Clear invalid path? Or let core handle it? Let core handle for now.

        # --- Start worker thread ---
        self.convert_button.setEnabled(False)
        self.progress_bar.setValue(0)
        self.progress_bar.setFormat("Processing...") # Indicate activity
        self.progress_bar.setTextVisible(True)

        self.inference_worker = InferenceWorker(params)
        self.inference_worker.progress.connect(self.update_progress)
        self.inference_worker.status.connect(self.update_status)
        self.inference_worker.finished.connect(self.on_inference_finished)
        self.inference_worker.error.connect(self.on_inference_error)
        # Use lambda with argument check for finished signal connection
        self.inference_worker.finished.connect(lambda msg, path: self.reset_ui_state())
        self.inference_worker.error.connect(lambda err_msg: self.reset_ui_state())

        self.inference_worker.start()

    def reset_ui_state(self):
        """Resets buttons and progress bar after task completion or error."""
        self.convert_button.setEnabled(True)
        self.progress_bar.setValue(0)
        self.progress_bar.setTextVisible(False)


    def update_progress(self, value):
        # For now, just set value. Real progress needs core changes.
        self.progress_bar.setValue(value)
        if value < 100:
             self.progress_bar.setFormat(f"Processing... {value}%") # Show percentage if possible
        else:
             self.progress_bar.setFormat("Finishing...")


    def update_status(self, message):
        self.status_label.setText(f"Status: {message}")

    def on_inference_finished(self, message, output_audio_path):
        self.update_status(f"Finished: {message}")
        # self.progress_bar.setValue(100) # Reset in reset_ui_state
        QMessageBox.information(self, "Inference Complete", f"{message}\nOutput saved to:\n{output_audio_path}")
        # TODO: Enable output audio player with output_audio_path
        print(f"Output audio at: {output_audio_path}")

    def on_inference_error(self, error_message):
        self.update_status("Error occurred") # Keep status brief
        # self.progress_bar.setValue(0) # Reset in reset_ui_state
        QMessageBox.critical(self, "Inference Error", f"An error occurred:\n{error_message}")
        print(f"Error details:\n{error_message}")

    # TODO: Add method to cancel inference (call self.inference_worker.stop())
