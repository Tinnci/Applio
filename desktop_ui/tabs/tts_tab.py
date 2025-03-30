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
# Import the new audio player widget
from desktop_ui.widgets.audio_player import AudioPlayer

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
        self.audio_player = None # Placeholder for the player widget
        self.setup_ui()
        self.refresh_models_and_indexes() # Initial population for RVC part

    def setup_ui(self):
        main_layout = QVBoxLayout(self)

        # --- TTS Settings ---
        tts_group = QGroupBox(self.tr("Text-to-Speech Settings"))
        tts_layout = QGridLayout(tts_group)

        tts_layout.addWidget(QLabel(self.tr("Text to Synthesize:")), 0, 0, 1, 4)
        self.tts_text_input = QTextEdit()
        self.tts_text_input.setPlaceholderText(self.tr("Enter text here..."))
        self.tts_text_input.setMinimumHeight(100) # Give it some initial height
        tts_layout.addWidget(self.tts_text_input, 1, 0, 1, 4) # Span 4 columns

        tts_layout.addWidget(QLabel(self.tr("TTS Voice:")), 2, 0)
        self.tts_voice_combo = QComboBox()
        self.tts_voice_combo.addItems(sorted(locales)) # Populate from core.locales
        # TODO: Set a sensible default? Maybe first in list?
        tts_layout.addWidget(self.tts_voice_combo, 2, 1)

        # Dynamic label update needs translation of the format string
        self.tts_rate_label = QLabel(self.tr("TTS Rate ({0}):").format(0))
        tts_layout.addWidget(self.tts_rate_label, 2, 2)
        self.tts_rate_slider = QSlider(Qt.Orientation.Horizontal)
        self.tts_rate_slider.setRange(-100, 100) # Range from core.py
        self.tts_rate_slider.setValue(0)
        self.tts_rate_slider.valueChanged.connect(lambda val: self.tts_rate_label.setText(self.tr("TTS Rate ({0}):").format(val)))
        tts_layout.addWidget(self.tts_rate_slider, 2, 3)

        main_layout.addWidget(tts_group)

        # --- RVC Settings (Reusing InferenceTab structure) ---
        rvc_group = QGroupBox(self.tr("RVC Voice Conversion Settings"))
        rvc_layout = QGridLayout(rvc_group)

        # Model Selection (reuse widgets/logic)
        # Assuming labels like "RVC Voice Model:" are handled by the reused InferenceTab widgets if they are translated there.
        # If not, they should be created here like: rvc_layout.addWidget(QLabel(self.tr("RVC Voice Model:")), 0, 0)
        rvc_layout.addWidget(QLabel(self.tr("RVC Voice Model:")), 0, 0) # Explicitly add label here for clarity
        self.model_combo = self._inference_tab_helpers.model_combo # Reuse combo
        rvc_layout.addWidget(self.model_combo, 0, 1)

        rvc_layout.addWidget(QLabel(self.tr("RVC Index File:")), 1, 0) # Explicitly add label here for clarity
        self.index_combo = self._inference_tab_helpers.index_combo # Reuse combo
        rvc_layout.addWidget(self.index_combo, 1, 1)

        rvc_refresh_button = QPushButton(self.tr("Refresh Models"))
        rvc_refresh_button.clicked.connect(self.refresh_models_and_indexes)
        rvc_layout.addWidget(rvc_refresh_button, 0, 2)

        rvc_unload_button = QPushButton(self.tr("Unload Model"))
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
        # Assuming labels are handled by reused widgets if translated there.
        rvc_layout.addWidget(QLabel(self.tr("RVC F0 Method:")), 6, 0) # Explicitly add label here
        self.f0_method_combo = self._inference_tab_helpers.f0_method_combo # Reuse combo
        rvc_layout.addWidget(self.f0_method_combo, 6, 1)

        rvc_layout.addWidget(QLabel(self.tr("RVC Speaker ID:")), 6, 2) # Explicitly add label here
        self.sid_combo = self._inference_tab_helpers.sid_combo # Reuse combo
        rvc_layout.addWidget(self.sid_combo, 6, 3)

        # --- Add Missing Advanced RVC Settings ---
        # Row 7: Checkboxes
        self.split_audio_checkbox_tts = QCheckBox(self.tr("Split Audio")); rvc_layout.addWidget(self.split_audio_checkbox_tts, 7, 0)
        self.autotune_checkbox_tts = QCheckBox(self.tr("Autotune")); rvc_layout.addWidget(self.autotune_checkbox_tts, 7, 1)
        self.clean_audio_checkbox_tts = QCheckBox(self.tr("Clean Audio")); rvc_layout.addWidget(self.clean_audio_checkbox_tts, 7, 2)
        self.formant_shifting_checkbox_tts = QCheckBox(self.tr("Formant Shift")); rvc_layout.addWidget(self.formant_shifting_checkbox_tts, 7, 3)

        # Row 8: Conditional Sliders/Widgets
        self.autotune_strength_label_tts = QLabel(self.tr("Autotune Strength:")); self.autotune_strength_label_tts.setVisible(False); rvc_layout.addWidget(self.autotune_strength_label_tts, 8, 0)
        self.autotune_strength_slider_tts = QSlider(Qt.Orientation.Horizontal); self.autotune_strength_slider_tts.setRange(0, 100); self.autotune_strength_slider_tts.setValue(100); self.autotune_strength_slider_tts.setVisible(False); rvc_layout.addWidget(self.autotune_strength_slider_tts, 8, 1)
        self.autotune_checkbox_tts.stateChanged.connect(lambda state: self.autotune_strength_label_tts.setVisible(state == Qt.CheckState.Checked.value)); self.autotune_checkbox_tts.stateChanged.connect(lambda state: self.autotune_strength_slider_tts.setVisible(state == Qt.CheckState.Checked.value))

        self.clean_strength_label_tts = QLabel(self.tr("Clean Strength:")); self.clean_strength_label_tts.setVisible(False); rvc_layout.addWidget(self.clean_strength_label_tts, 8, 2)
        self.clean_strength_slider_tts = QSlider(Qt.Orientation.Horizontal); self.clean_strength_slider_tts.setRange(0, 100); self.clean_strength_slider_tts.setValue(50); self.clean_strength_slider_tts.setVisible(False); rvc_layout.addWidget(self.clean_strength_slider_tts, 8, 3)
        self.clean_audio_checkbox_tts.stateChanged.connect(lambda state: self.clean_strength_label_tts.setVisible(state == Qt.CheckState.Checked.value)); self.clean_audio_checkbox_tts.stateChanged.connect(lambda state: self.clean_strength_slider_tts.setVisible(state == Qt.CheckState.Checked.value))

        # Row 9: Formant Sliders (Conditional)
        self.formant_qfrency_label_tts = QLabel(self.tr("Quefrency:")); self.formant_qfrency_label_tts.setVisible(False); rvc_layout.addWidget(self.formant_qfrency_label_tts, 9, 0)
        self.formant_qfrency_slider_tts = QSlider(Qt.Orientation.Horizontal); self.formant_qfrency_slider_tts.setRange(0, 160); self.formant_qfrency_slider_tts.setValue(10); self.formant_qfrency_slider_tts.setVisible(False); rvc_layout.addWidget(self.formant_qfrency_slider_tts, 9, 1)
        self.formant_shifting_checkbox_tts.stateChanged.connect(lambda state: self.formant_qfrency_label_tts.setVisible(state == Qt.CheckState.Checked.value)); self.formant_shifting_checkbox_tts.stateChanged.connect(lambda state: self.formant_qfrency_slider_tts.setVisible(state == Qt.CheckState.Checked.value))

        self.formant_timbre_label_tts = QLabel(self.tr("Timbre:")); self.formant_timbre_label_tts.setVisible(False); rvc_layout.addWidget(self.formant_timbre_label_tts, 9, 2)
        self.formant_timbre_slider_tts = QSlider(Qt.Orientation.Horizontal); self.formant_timbre_slider_tts.setRange(0, 160); self.formant_timbre_slider_tts.setValue(10); self.formant_timbre_slider_tts.setVisible(False); rvc_layout.addWidget(self.formant_timbre_slider_tts, 9, 3)
        self.formant_shifting_checkbox_tts.stateChanged.connect(lambda state: self.formant_timbre_label_tts.setVisible(state == Qt.CheckState.Checked.value)); self.formant_shifting_checkbox_tts.stateChanged.connect(lambda state: self.formant_timbre_slider_tts.setVisible(state == Qt.CheckState.Checked.value))

        # Row 10: Embedder (Reused) and Export Format
        rvc_layout.addWidget(QLabel(self.tr("Embedder Model:")), 10, 0)
        self.embedder_model_combo_tts = self._inference_tab_helpers.embedder_model_combo # Reuse combo
        rvc_layout.addWidget(self.embedder_model_combo_tts, 10, 1)
        # Note: Custom embedder group visibility is handled by the reused combo's signal in InferenceTab

        rvc_layout.addWidget(QLabel(self.tr("Export Format:")), 10, 2)
        self.export_format_combo_tts = QComboBox(); self.export_format_combo_tts.addItems(["WAV", "MP3", "FLAC", "OGG", "M4A"]); rvc_layout.addWidget(self.export_format_combo_tts, 10, 3)

        # Row 11: F0 File
        rvc_layout.addWidget(QLabel(self.tr("F0 File (Optional):")), 11, 0)
        self.f0_file_edit_tts = QLineEdit(); self.f0_file_edit_tts.setPlaceholderText(self.tr("Path to .f0 file")); rvc_layout.addWidget(self.f0_file_edit_tts, 11, 1, 1, 2)
        self.f0_file_browse_button_tts = QPushButton(self.tr("Browse...")); self.f0_file_browse_button_tts.clicked.connect(self.browse_f0_file_tts); rvc_layout.addWidget(self.f0_file_browse_button_tts, 11, 3)

        main_layout.addWidget(rvc_group)

        # --- Output ---
        output_group = QGroupBox(self.tr("Output"))
        output_layout = QGridLayout(output_group)
        output_layout.addWidget(QLabel(self.tr("Output Path (RVC):")), 0, 0)
        self.output_rvc_path_edit = QLineEdit()
        self.output_rvc_path_edit.setPlaceholderText(self.tr("Select final output file path"))
        output_layout.addWidget(self.output_rvc_path_edit, 0, 1)
        self.browse_output_button = QPushButton(self.tr("Browse..."))
        self.browse_output_button.clicked.connect(self.browse_output_rvc_path)
        output_layout.addWidget(self.browse_output_button, 0, 2)

        # Add the audio player widget
        self.audio_player = AudioPlayer()
        output_layout.addWidget(self.audio_player, 1, 0, 1, 3) # Span across columns

        main_layout.addWidget(output_group)


        # --- Action Button & Status ---
        action_status_group = QWidget()
        action_status_layout = QVBoxLayout(action_status_group)
        action_status_layout.setContentsMargins(0,10,0,0)

        self.synthesize_button = QPushButton(self.tr("Synthesize & Convert"))
        self.synthesize_button.clicked.connect(self.start_synthesis)
        action_status_layout.addWidget(self.synthesize_button)

        self.status_label = QLabel(self.tr("Status: Idle")) # Translate initial status
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
        selected_format = self.export_format_combo_tts.currentText().lower() # Get format from new combo
        default_filename = os.path.splitext(default_filename)[0] + f".{selected_format}"

        # Translate parts of the filter string and add more formats
        format_filter = f"{selected_format.upper()} Files (*.{selected_format});;WAV Files (*.wav);;MP3 Files (*.mp3);;FLAC Files (*.flac);;OGG Files (*.ogg);;M4A Files (*.m4a);;{self.tr('All Files (*)')}"

        file_path, _ = QFileDialog.getSaveFileName(self, self.tr("Select RVC Output Path"), os.path.join(start_dir, default_filename), format_filter)
        if file_path:
            # Ensure the selected format is appended if missing (logic remains the same)
            if not file_path.lower().endswith(f".{selected_format}"):
                file_path = os.path.splitext(file_path)[0] + f".{selected_format}"
            self.output_rvc_path_edit.setText(file_path)

    def start_synthesis(self):
        if self.worker and self.worker.isRunning():
            QMessageBox.warning(self, self.tr("Process Running"), self.tr("A TTS/RVC process is already running."))
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
            # Get new RVC params
            "split_audio": self.split_audio_checkbox_tts.isChecked(),
            "f0_autotune": self.autotune_checkbox_tts.isChecked(),
            "f0_autotune_strength": self.autotune_strength_slider_tts.value() / 100.0 if self.autotune_checkbox_tts.isChecked() else 1.0,
            "clean_audio": self.clean_audio_checkbox_tts.isChecked(),
            "clean_strength": self.clean_strength_slider_tts.value() / 100.0 if self.clean_audio_checkbox_tts.isChecked() else 0.5,
            "export_format": self.export_format_combo_tts.currentText(),
            "embedder_model": self.embedder_model_combo_tts.currentText(),
            "embedder_model_custom": self._inference_tab_helpers.embedder_model_custom_combo.currentText() if self.embedder_model_combo_tts.currentText() == "custom" else None, # Get from reused widget
            "f0_file": self.f0_file_edit_tts.text().strip() or None,
            "formant_shifting": self.formant_shifting_checkbox_tts.isChecked(),
            "formant_qfrency": self.formant_qfrency_slider_tts.value() / 10.0 if self.formant_shifting_checkbox_tts.isChecked() else 1.0,
            "formant_timbre": self.formant_timbre_slider_tts.value() / 10.0 if self.formant_shifting_checkbox_tts.isChecked() else 1.0,
            "hop_length": 128, # Assuming default, could add UI later if needed
        }

        # --- Validate parameters ---
        if not params["tts_text"]:
            QMessageBox.warning(self, self.tr("Input Error"), self.tr("Please enter text to synthesize."))
            return
        if not params["output_rvc_path"]:
            QMessageBox.warning(self, self.tr("Output Error"), self.tr("Please specify an output file path."))
            return
        if not params["pth_path"] or not os.path.exists(params["pth_path"]):
             QMessageBox.warning(self, self.tr("Model Error"), self.tr("Please select a valid RVC voice model file."))
             return
        # Index validation (optional) - Translate the warning prefix
        if params["index_path"] and not os.path.exists(params["index_path"]):
             self.update_status(self.tr("Warning: Selected index file not found: {0}").format(params['index_path']))

        # --- Start worker thread ---
        self.synthesize_button.setEnabled(False)
        self.progress_bar.setValue(0)
        self.progress_bar.setFormat(self.tr("Synthesizing...")) # Translate progress format
        self.progress_bar.setTextVisible(True)

        # Reset audio player before starting
        if self.audio_player:
            self.audio_player.reset_player()

        self.worker = TtsWorker(params)
        self.worker.progress.connect(self.update_progress)
        self.worker.status.connect(self.update_status)
        self.worker.finished.connect(self.on_synthesis_finished)
        self.worker.error.connect(self.on_synthesis_error)
        self.worker.finished.connect(lambda msg, path: self.reset_ui_state())
        self.worker.error.connect(lambda err_msg: self.reset_ui_state())
        self.worker.start()

    def browse_f0_file_tts(self):
        # Similar to browse_f0_file in InferenceTab
        start_dir = os.path.dirname(self.output_rvc_path_edit.text()) if self.output_rvc_path_edit.text() else project_root
        file_path, _ = QFileDialog.getOpenFileName(self, self.tr("Select F0 File"), start_dir, self.tr("F0 Files (*.f0);;All Files (*)"))
        if file_path:
            self.f0_file_edit_tts.setText(file_path)

    def reset_ui_state(self, reset_player=True):
        self.synthesize_button.setEnabled(True)
        self.progress_bar.setValue(0)
        self.progress_bar.setTextVisible(False)
        # Optionally reset player on finish/error
        if reset_player and self.audio_player:
            self.audio_player.reset_player()

    def update_progress(self, value):
        self.progress_bar.setValue(value)
        # Translate progress format strings
        if value < 100:
             self.progress_bar.setFormat(self.tr("Processing... {0}%").format(value))
        else:
             self.progress_bar.setFormat(self.tr("Finishing..."))

    def update_status(self, message):
        # Translate the "Status: " prefix
        # Note: The 'message' itself might come from the worker and may not be translated here.
        self.status_label.setText(self.tr("Status: {0}").format(message))

    def on_synthesis_finished(self, message, output_audio_path):
        # Translate the "Finished: " prefix for status
        self.update_status(self.tr("Finished: {0}").format(message))
        # Translate QMessageBox title and the static part of the text
        QMessageBox.information(self, self.tr("Synthesis Complete"), self.tr("{0}\nOutput saved to:\n{1}").format(message, output_audio_path))
        print(f"Output audio at: {output_audio_path}")
        # Load audio into player
        if self.audio_player and output_audio_path and os.path.exists(output_audio_path):
            self.audio_player.set_media(output_audio_path)

    def on_synthesis_error(self, error_message):
        # Translate status and QMessageBox
        self.update_status(self.tr("Error occurred"))
        # Reset player on error (pass False to reset_ui_state to avoid double reset)
        if self.audio_player:
            self.audio_player.reset_player()
        QMessageBox.critical(self, self.tr("Synthesis Error"), self.tr("An error occurred:\n{0}").format(error_message))
        print(f"Error details:\n{error_message}")
