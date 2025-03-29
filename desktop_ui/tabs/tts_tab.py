from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QGridLayout, 
                             QSlider, QComboBox, QCheckBox, QLineEdit, QFileDialog, QProgressBar,
                             QMessageBox, QApplication, QSizePolicy, QSpacerItem, QTabWidget, 
                             QGroupBox, QTextEdit) # Added QTextEdit, QGroupBox
from PyQt6.QtCore import Qt, QThread, pyqtSignal
import os
import sys
import traceback
import tempfile # For temporary TTS file

# Ensure the core Applio logic can be imported
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

# Import core functions and data
from core import run_tts_script, locales # Import locales for TTS voices
# Import helper functions/constants from inference tab for reuse
from desktop_ui.tabs.inference_tab import MODEL_ROOT, AUDIO_ROOT, InferenceTab # Added AUDIO_ROOT

class TtsWorker(QThread):
    """Worker thread for running TTS and RVC."""
    progress = pyqtSignal(int)
    status = pyqtSignal(str)
    finished = pyqtSignal(str, str) # message, output_audio_path
    error = pyqtSignal(str)

    def __init__(self, params):
        super().__init__()
        self.params = params
        self._is_running = True
        self.temp_tts_file = None

    def run(self):
        """Execute the TTS and RVC task."""
        try:
            self.status.emit("Starting TTS synthesis...")
            
            # Create a temporary file for the intermediate TTS output
            fd, self.temp_tts_file = tempfile.mkstemp(suffix=".wav", prefix="applio_tts_")
            os.close(fd) # Close the file descriptor
            print(f"Using temporary TTS file: {self.temp_tts_file}")

            # Map UI params to core function params
            core_params = {
                "tts_text": self.params.get("tts_text"),
                "tts_voice": self.params.get("tts_voice"),
                "tts_rate": self.params.get("tts_rate", 0),
                "output_tts_path": self.temp_tts_file, # Use temp file
                "pth_path": self.params.get("pth_path"),
                "index_path": self.params.get("index_path"),
                "pitch": self.params.get("pitch", 0),
                "output_rvc_path": self.params.get("output_rvc_path"),
                # Add other RVC params from self.params
                "index_rate": self.params.get("index_rate", 0.75),
                "volume_envelope": int(self.params.get("rms_mix_rate", 1.0) * 100),
                "protect": self.params.get("protect", 0.5),
                "hop_length": self.params.get("hop_length", 128),
                "f0_method": self.params.get("f0_method", "rmvpe"),
                "split_audio": self.params.get("split_audio", False),
                "f0_autotune": self.params.get("f0_autotune", False),
                "f0_autotune_strength": self.params.get("f0_autotune_strength", 1.0),
                "clean_audio": self.params.get("clean_audio", False),
                "clean_strength": self.params.get("clean_strength", 0.5),
                "export_format": self.params.get("export_format", "WAV"),
                "f0_file": self.params.get("f0_file", None),
                "embedder_model": self.params.get("embedder_model", "contentvec"),
                "embedder_model_custom": self.params.get("embedder_model_custom", None),
                "sid": self.params.get("sid", 0),
            }
            core_params = {k: v for k, v in core_params.items() if v is not None}

            # --- Actual Call ---
            # run_tts_script handles both TTS generation and RVC conversion
            message, output_path = run_tts_script(**core_params)
            # --- End Actual Call ---

            # --- Placeholder for progress ---
            self.progress.emit(50) 
            import time
            time.sleep(1) 
            self.progress.emit(100)
            # --- End Placeholder ---

            if self._is_running:
                self.status.emit(message)
                self.finished.emit(message, output_path)
        except Exception as e:
            error_str = f"TTS/RVC Error: {e}\n{traceback.format_exc()}"
            self.error.emit(error_str)
        finally:
            # Clean up temporary file
            if self.temp_tts_file and os.path.exists(self.temp_tts_file):
                try:
                    os.remove(self.temp_tts_file)
                    print(f"Removed temporary TTS file: {self.temp_tts_file}")
                except OSError as e:
                    print(f"Error removing temporary file {self.temp_tts_file}: {e}")
            if self._is_running: 
                self.status.emit("Idle")

    def stop(self):
        self._is_running = False
        self.status.emit("Cancelling TTS/RVC...")
        # TODO: Implement cancellation if possible (might need core changes)


class TtsTab(QWidget):
    """Widget for the TTS Tab."""
    def __init__(self):
        super().__init__()
        self.worker = None
        # Create an instance of InferenceTab to reuse its methods/widgets if needed
        # This is a bit of a hack, consider refactoring shared logic later
        self._inference_tab_helpers = InferenceTab() 
        self.setup_ui()
        self.refresh_models_and_indexes() # Initial population for RVC part

    def setup_ui(self):
        main_layout = QVBoxLayout(self)

        # --- TTS Settings ---
        tts_group = QGroupBox("Text-to-Speech Settings")
        tts_layout = QGridLayout(tts_group)

        tts_layout.addWidget(QLabel("Text to Synthesize:"), 0, 0, 1, 4)
        self.tts_text_input = QTextEdit()
        self.tts_text_input.setPlaceholderText("Enter text here...")
        self.tts_text_input.setMinimumHeight(100) # Give it some initial height
        tts_layout.addWidget(self.tts_text_input, 1, 0, 1, 4) # Span 4 columns

        tts_layout.addWidget(QLabel("TTS Voice:"), 2, 0)
        self.tts_voice_combo = QComboBox()
        self.tts_voice_combo.addItems(sorted(locales)) # Populate from core.locales
        # TODO: Set a sensible default? Maybe first in list?
        tts_layout.addWidget(self.tts_voice_combo, 2, 1)

        self.tts_rate_label = QLabel("TTS Rate (0):")
        tts_layout.addWidget(self.tts_rate_label, 2, 2)
        self.tts_rate_slider = QSlider(Qt.Orientation.Horizontal)
        self.tts_rate_slider.setRange(-100, 100) # Range from core.py
        self.tts_rate_slider.setValue(0)
        self.tts_rate_slider.valueChanged.connect(lambda val: self.tts_rate_label.setText(f"TTS Rate ({val}):"))
        tts_layout.addWidget(self.tts_rate_slider, 2, 3)

        main_layout.addWidget(tts_group)

        # --- RVC Settings (Reusing InferenceTab structure) ---
        rvc_group = QGroupBox("RVC Voice Conversion Settings")
        rvc_layout = QGridLayout(rvc_group)

        # Model Selection (reuse widgets/logic)
        rvc_layout.addWidget(QLabel("RVC Voice Model:"), 0, 0)
        self.model_combo = self._inference_tab_helpers.model_combo # Reuse combo
        rvc_layout.addWidget(self.model_combo, 0, 1)

        rvc_layout.addWidget(QLabel("RVC Index File:"), 1, 0)
        self.index_combo = self._inference_tab_helpers.index_combo # Reuse combo
        rvc_layout.addWidget(self.index_combo, 1, 1)

        rvc_refresh_button = QPushButton("Refresh Models")
        rvc_refresh_button.clicked.connect(self.refresh_models_and_indexes)
        rvc_layout.addWidget(rvc_refresh_button, 0, 2)

        rvc_unload_button = QPushButton("Unload Model")
        rvc_unload_button.clicked.connect(self.unload_model)
        rvc_layout.addWidget(rvc_unload_button, 1, 2)

        # Basic RVC Settings (reuse widgets/logic)
        self.pitch_label = self._inference_tab_helpers.pitch_label # Reuse label
        rvc_layout.addWidget(self.pitch_label, 2, 0)
        self.pitch_slider = self._inference_tab_helpers.pitch_slider # Reuse slider
        rvc_layout.addWidget(self.pitch_slider, 2, 1, 1, 2)

        self.index_rate_label = self._inference_tab_helpers.index_rate_label
        rvc_layout.addWidget(self.index_rate_label, 3, 0)
        self.index_rate_slider = self._inference_tab_helpers.index_rate_slider
        rvc_layout.addWidget(self.index_rate_slider, 3, 1, 1, 2)

        self.rms_mix_rate_label = self._inference_tab_helpers.rms_mix_rate_label
        rvc_layout.addWidget(self.rms_mix_rate_label, 4, 0)
        self.rms_mix_rate_slider = self._inference_tab_helpers.rms_mix_rate_slider
        rvc_layout.addWidget(self.rms_mix_rate_slider, 4, 1, 1, 2)

        self.protect_label = self._inference_tab_helpers.protect_label
        rvc_layout.addWidget(self.protect_label, 5, 0)
        self.protect_slider = self._inference_tab_helpers.protect_slider
        rvc_layout.addWidget(self.protect_slider, 5, 1, 1, 2)

        # Advanced RVC Settings (reuse widgets/logic)
        rvc_layout.addWidget(QLabel("RVC F0 Method:"), 6, 0)
        self.f0_method_combo = self._inference_tab_helpers.f0_method_combo # Reuse combo
        rvc_layout.addWidget(self.f0_method_combo, 6, 1)

        rvc_layout.addWidget(QLabel("RVC Speaker ID:"), 6, 2)
        self.sid_combo = self._inference_tab_helpers.sid_combo # Reuse combo
        rvc_layout.addWidget(self.sid_combo, 6, 3)
        
        # TODO: Add other advanced RVC settings if needed (Split, Autotune, Clean, etc.)

        main_layout.addWidget(rvc_group)

        # --- Output ---
        output_group = QGroupBox("Output")
        output_layout = QGridLayout(output_group)
        output_layout.addWidget(QLabel("Output Path (RVC):"), 0, 0)
        self.output_rvc_path_edit = QLineEdit()
        self.output_rvc_path_edit.setPlaceholderText("Select final output file path")
        output_layout.addWidget(self.output_rvc_path_edit, 0, 1)
        self.browse_output_button = QPushButton("Browse...")
        self.browse_output_button.clicked.connect(self.browse_output_rvc_path)
        output_layout.addWidget(self.browse_output_button, 0, 2)
        # TODO: Add audio player for output?
        main_layout.addWidget(output_group)


        # --- Action Button & Status ---
        action_status_group = QWidget()
        action_status_layout = QVBoxLayout(action_status_group)
        action_status_layout.setContentsMargins(0,10,0,0)

        self.synthesize_button = QPushButton("Synthesize & Convert")
        self.synthesize_button.clicked.connect(self.start_synthesis)
        action_status_layout.addWidget(self.synthesize_button)

        self.status_label = QLabel("Status: Idle")
        action_status_layout.addWidget(self.status_label)

        self.progress_bar = QProgressBar()
        self.progress_bar.setValue(0)
        self.progress_bar.setTextVisible(False)
        action_status_layout.addWidget(self.progress_bar)

        main_layout.addWidget(action_status_group)

        # Add spacer
        main_layout.addSpacerItem(QSpacerItem(20, 40, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Expanding))

        self.setLayout(main_layout)

    # --- Methods for populating/handling reused widgets ---
    def refresh_models_and_indexes(self):
        self._inference_tab_helpers.refresh_models_and_indexes()

    def on_model_selected(self):
         self._inference_tab_helpers.on_model_selected()

    def unload_model(self):
         self._inference_tab_helpers.unload_model()
    # --- End Reused Methods ---

    def browse_output_rvc_path(self):
        # Reuse similar logic from InferenceTab browse_output_path
        start_dir = os.path.dirname(self.output_rvc_path_edit.text()) if self.output_rvc_path_edit.text() else AUDIO_ROOT
        if not os.path.exists(start_dir):
            start_dir = AUDIO_ROOT if os.path.exists(AUDIO_ROOT) else project_root
            
        default_filename = os.path.basename(self.output_rvc_path_edit.text()) if self.output_rvc_path_edit.text() else "tts_output.wav"
        # TODO: Get export format from UI when added
        selected_format = "wav" # Placeholder
        default_filename = os.path.splitext(default_filename)[0] + f".{selected_format}"

        format_filter = f"{selected_format.upper()} Files (*.{selected_format});;All Files (*)" # Simplified filter

        file_path, _ = QFileDialog.getSaveFileName(self, "Select RVC Output Path", os.path.join(start_dir, default_filename), format_filter)
        if file_path:
            if not file_path.lower().endswith(f".{selected_format}"):
                file_path = os.path.splitext(file_path)[0] + f".{selected_format}"
            self.output_rvc_path_edit.setText(file_path)

    def start_synthesis(self):
        if self.worker and self.worker.isRunning():
            QMessageBox.warning(self, "Process Running", "A TTS/RVC process is already running.")
            return

        # --- Gather parameters ---
        pth_path = self.model_combo.currentData()
        index_path = self.index_combo.currentData() if self.index_combo.currentIndex() > 0 else ""

        params = {
            "tts_text": self.tts_text_input.toPlainText().strip(),
            "tts_voice": self.tts_voice_combo.currentText(),
            "tts_rate": self.tts_rate_slider.value(),
            "output_rvc_path": self.output_rvc_path_edit.text().strip(),
            "pth_path": pth_path,
            "index_path": index_path,
            "pitch": self.pitch_slider.value(),
            "index_rate": self.index_rate_slider.value() / 100.0,
            "rms_mix_rate": self.rms_mix_rate_slider.value() / 100.0,
            "protect": self.protect_slider.value() / 100.0,
            "f0_method": self.f0_method_combo.currentText(),
            "sid": int(self.sid_combo.currentText()) if self.sid_combo.currentText() else 0,
            # TODO: Get other RVC params (split, autotune, clean, format, etc.)
        }

        # --- Validate parameters ---
        if not params["tts_text"]:
            QMessageBox.warning(self, "Input Error", "Please enter text to synthesize.")
            return
        if not params["output_rvc_path"]:
            QMessageBox.warning(self, "Output Error", "Please specify an output file path.")
            return
        if not params["pth_path"] or not os.path.exists(params["pth_path"]):
             QMessageBox.warning(self, "Model Error", "Please select a valid RVC voice model file.")
             return
        # Index validation (optional)
        if params["index_path"] and not os.path.exists(params["index_path"]):
             self.update_status(f"Warning: Selected index file not found: {params['index_path']}")

        # --- Start worker thread ---
        self.synthesize_button.setEnabled(False)
        self.progress_bar.setValue(0)
        self.progress_bar.setFormat("Synthesizing...")
        self.progress_bar.setTextVisible(True)

        self.worker = TtsWorker(params)
        self.worker.progress.connect(self.update_progress)
        self.worker.status.connect(self.update_status)
        self.worker.finished.connect(self.on_synthesis_finished)
        self.worker.error.connect(self.on_synthesis_error)
        self.worker.finished.connect(lambda msg, path: self.reset_ui_state())
        self.worker.error.connect(lambda err_msg: self.reset_ui_state())
        self.worker.start()

    def reset_ui_state(self):
        self.synthesize_button.setEnabled(True)
        self.progress_bar.setValue(0)
        self.progress_bar.setTextVisible(False)

    def update_progress(self, value):
        self.progress_bar.setValue(value)
        if value < 100:
             self.progress_bar.setFormat(f"Processing... {value}%")
        else:
             self.progress_bar.setFormat("Finishing...")

    def update_status(self, message):
        self.status_label.setText(f"Status: {message}")

    def on_synthesis_finished(self, message, output_audio_path):
        self.update_status(f"Finished: {message}")
        QMessageBox.information(self, "Synthesis Complete", f"{message}\nOutput saved to:\n{output_audio_path}")
        print(f"Output audio at: {output_audio_path}")
        # TODO: Play audio

    def on_synthesis_error(self, error_message):
        self.update_status("Error occurred")
        QMessageBox.critical(self, "Synthesis Error", f"An error occurred:\n{error_message}")
        print(f"Error details:\n{error_message}")
