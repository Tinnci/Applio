from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QLabel, QPushButton, QGridLayout, 
                             QSlider, QComboBox, QCheckBox, QLineEdit, QFileDialog, QProgressBar,
                             QMessageBox, QSizePolicy, QSpacerItem, QTabWidget, 
                             QGroupBox) # Added QRadioButton
from PyQt6.QtCore import Qt, QThread, pyqtSignal
import os
import sys
import traceback

# Ensure the core Applio logic can be imported
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

# Import core functions
from core import run_infer_script, run_batch_infer_script # Added batch script import
# Import helper functions from original Gradio tab (or reimplement)
from tabs.inference.inference import (get_speakers_id, match_index, output_path_fn, 
                                      extract_model_and_epoch, get_indexes, 
                                      list_json_files, update_sliders_formant, # Added helpers
                                      refresh_embedders_folders) # Added embedder refresh
                                      # Removed faulty CUSTOM_EMBEDDER_ROOT import

# Define constants based on original file
MODEL_ROOT = os.path.join(project_root, "logs")
AUDIO_ROOT = os.path.join(project_root, "assets", "audios")
# Define CUSTOM_EMBEDDER_ROOT directly based on original logic
CUSTOM_EMBEDDER_ROOT = os.path.join(project_root, "rvc", "models", "embedders", "embedders_custom")
PRESETS_DIR = os.path.join(project_root, "assets", "presets")
FORMANTSHIFT_DIR = os.path.join(project_root, "assets", "formant_shift")
AUDIO_ROOT = os.path.join(project_root, "assets", "audios")
SUP_AUDIOEXT = {
    "wav", "mp3", "flac", "ogg", "opus", "m4a", "mp4", "aac", "alac", "wma", "aiff", "webm", "ac3",
}

class InferenceWorker(QThread):
    """Worker thread for running inference to avoid blocking the UI."""
    progress = pyqtSignal(int) 
    status = pyqtSignal(str)   
    finished = pyqtSignal(str, str) 
    error = pyqtSignal(str)     

    def __init__(self, params, is_batch=False): # Added is_batch flag
        super().__init__()
        self.params = params
        self.is_batch = is_batch
        self._is_running = True

    def run(self):
        """Execute the inference task."""
        task_name = "Batch Inference" if self.is_batch else "Inference"
        try:
            self.status.emit(f"Starting {task_name}...")
            
            # Map UI params to core function params
            core_params = {
                "pitch": self.params.get("pitch", 0),
                "index_rate": self.params.get("index_rate", 0.75),
                "volume_envelope": int(self.params.get("rms_mix_rate", 1.0) * 100), 
                "protect": self.params.get("protect", 0.5),
                "hop_length": self.params.get("hop_length", 128),
                "f0_method": self.params.get("f0_method", "rmvpe"),
                "pth_path": self.params.get("pth_path"),
                "index_path": self.params.get("index_path"),
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
                "formant_shifting": self.params.get("formant_shifting", False),
                "formant_qfrency": self.params.get("formant_qfrency", 1.0),
                "formant_timbre": self.params.get("formant_timbre", 1.0),
                "post_process": self.params.get("post_process", False),
                # --- Add post-processing effect params ---
                "reverb": self.params.get("reverb", False),
                "pitch_shift": self.params.get("pitch_shift", False),
                "limiter": self.params.get("limiter", False),
                "gain": self.params.get("gain", False),
                "distortion": self.params.get("distortion", False),
                "chorus": self.params.get("chorus", False),
                "bitcrush": self.params.get("bitcrush", False),
                "clipping": self.params.get("clipping", False),
                "compressor": self.params.get("compressor", False),
                "delay": self.params.get("delay", False),
                "reverb_room_size": self.params.get("reverb_room_size", 0.5),
                "reverb_damping": self.params.get("reverb_damping", 0.5),
                "reverb_wet_gain": self.params.get("reverb_wet_gain", 0.33), # Default from original
                "reverb_dry_gain": self.params.get("reverb_dry_gain", 0.4), # Default from original
                "reverb_width": self.params.get("reverb_width", 1.0), # Default from original
                "reverb_freeze_mode": self.params.get("reverb_freeze_mode", 0.0), # Default from original
                "pitch_shift_semitones": self.params.get("pitch_shift_semitones", 0.0),
                "limiter_threshold": self.params.get("limiter_threshold", -6.0),
                "limiter_release_time": self.params.get("limiter_release_time", 0.05),
                "gain_db": self.params.get("gain_db", 0.0),
                "distortion_gain": self.params.get("distortion_gain", 25.0),
                "chorus_rate": self.params.get("chorus_rate", 1.0),
                "chorus_depth": self.params.get("chorus_depth", 0.25),
                "chorus_center_delay": self.params.get("chorus_center_delay", 7.0),
                "chorus_feedback": self.params.get("chorus_feedback", 0.0),
                "chorus_mix": self.params.get("chorus_mix", 0.5),
                "bitcrush_bit_depth": self.params.get("bitcrush_bit_depth", 8),
                "clipping_threshold": self.params.get("clipping_threshold", -6.0),
                "compressor_threshold": self.params.get("compressor_threshold", 0.0),
                "compressor_ratio": self.params.get("compressor_ratio", 1.0),
                "compressor_attack": self.params.get("compressor_attack", 1.0),
                "compressor_release": self.params.get("compressor_release", 100.0),
                "delay_seconds": self.params.get("delay_seconds", 0.5),
                "delay_feedback": self.params.get("delay_feedback", 0.0),
                "delay_mix": self.params.get("delay_mix", 0.5),
            }
            
            # Add/replace batch-specific params
            if self.is_batch:
                 core_params["input_folder"] = self.params.get("input_folder")
                 core_params["output_folder"] = self.params.get("output_folder")
                 core_params.pop("input_path", None); core_params.pop("output_path", None)
            else:
                 core_params["input_path"] = self.params.get("input_path")
                 core_params["output_path"] = self.params.get("output_path")

            core_params = {k: v for k, v in core_params.items() if v is not None}

            # --- Actual Call ---
            if self.is_batch:
                 message = run_batch_infer_script(**core_params)
                 output_path = self.params.get("output_folder") 
            else:
                 message, output_path = run_infer_script(**core_params)
            # --- End Actual Call ---

            self.progress.emit(50) 
            import time; time.sleep(1) 
            self.progress.emit(100)

            if self._is_running:
                self.status.emit(message)
                self.finished.emit(message, output_path)
        except Exception as e:
            error_str = f"{task_name} Error: {e}\n{traceback.format_exc()}"
            self.error.emit(error_str)
        finally:
            if self._is_running: self.status.emit("Idle") 

    def stop(self):
        self._is_running = False
        self.status.emit("Cancelling...")


class InferenceTab(QWidget):
    """Widget for the Inference Tab."""
    def __init__(self):
        super().__init__()
        self.inference_worker = None
        self.setup_ui()
        self.refresh_models_and_indexes() 

    def setup_ui(self):
        main_layout = QVBoxLayout(self)

        # --- Model Selection ---
        model_group_box = QWidget()
        model_layout = QGridLayout(model_group_box)
        model_layout.setContentsMargins(0,0,0,0)
        model_layout.addWidget(QLabel("Voice Model:"), 0, 0)
        self.model_combo = QComboBox(); self.model_combo.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed); self.model_combo.currentIndexChanged.connect(self.on_model_selected); model_layout.addWidget(self.model_combo, 0, 1)
        model_layout.addWidget(QLabel("Index File:"), 1, 0)
        self.index_combo = QComboBox(); self.index_combo.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed); model_layout.addWidget(self.index_combo, 1, 1)
        refresh_button = QPushButton("Refresh"); refresh_button.clicked.connect(self.refresh_models_and_indexes); model_layout.addWidget(refresh_button, 0, 2)
        unload_button = QPushButton("Unload"); unload_button.clicked.connect(self.unload_model); model_layout.addWidget(unload_button, 1, 2)
        main_layout.addWidget(model_group_box)

        # --- Single/Batch Tabs ---
        self.single_batch_tabs = QTabWidget()
        
        # --- Single Tab Widget ---
        single_tab_widget = QWidget()
        single_tab_layout = QVBoxLayout(single_tab_widget)
        self.setup_single_tab_ui(single_tab_layout) 
        self.single_batch_tabs.addTab(single_tab_widget, "Single")
        
        # --- Batch Tab Widget ---
        batch_tab_widget = QWidget()
        batch_tab_layout = QVBoxLayout(batch_tab_widget)
        self.setup_batch_tab_ui(batch_tab_layout) 
        self.single_batch_tabs.addTab(batch_tab_widget, "Batch")
        
        main_layout.addWidget(self.single_batch_tabs)

        # --- Action Buttons & Status ---
        action_status_group = QWidget()
        action_status_layout = QVBoxLayout(action_status_group)
        action_status_layout.setContentsMargins(0,10,0,0)
        self.convert_button = QPushButton("Convert"); self.convert_button.clicked.connect(self.start_inference); action_status_layout.addWidget(self.convert_button)
        self.status_label = QLabel("Status: Idle"); action_status_layout.addWidget(self.status_label)
        self.progress_bar = QProgressBar(); self.progress_bar.setValue(0); self.progress_bar.setTextVisible(False); action_status_layout.addWidget(self.progress_bar)
        main_layout.addWidget(action_status_group)

        self.setLayout(main_layout)

    def setup_single_tab_ui(self, single_tab_layout):
        """Sets up the UI elements for the Single Inference tab."""
        # Input Audio Section
        input_group_box = QWidget(); input_layout = QGridLayout(input_group_box); input_layout.setContentsMargins(0,5,0,5) 
        input_layout.addWidget(QLabel("Input Audio:"), 0, 0); self.input_audio_path_edit = QLineEdit(); self.input_audio_path_edit.setPlaceholderText("Select audio file"); input_layout.addWidget(self.input_audio_path_edit, 0, 1)
        self.browse_input_button = QPushButton("Browse..."); self.browse_input_button.clicked.connect(self.browse_input_audio); input_layout.addWidget(self.browse_input_button, 0, 2)
        single_tab_layout.addWidget(input_group_box)

        # Output Path Section
        output_group_box = QWidget(); output_layout = QGridLayout(output_group_box); output_layout.setContentsMargins(0,0,0,5) 
        output_layout.addWidget(QLabel("Output Path:"), 0, 0); self.output_audio_path_edit = QLineEdit(); self.output_audio_path_edit.setPlaceholderText("Select output file path"); output_layout.addWidget(self.output_audio_path_edit, 0, 1)
        self.browse_output_button = QPushButton("Browse..."); self.browse_output_button.clicked.connect(self.browse_output_path); output_layout.addWidget(self.browse_output_button, 0, 2)
        single_tab_layout.addWidget(output_group_box)

        # Basic Settings Section
        basic_settings_group_box = QWidget(); basic_settings_layout = QGridLayout(basic_settings_group_box); basic_settings_layout.setContentsMargins(0,0,0,0)
        self.pitch_label = QLabel("Pitch (0):"); basic_settings_layout.addWidget(self.pitch_label, 0, 0)
        self.pitch_slider = QSlider(Qt.Orientation.Horizontal); self.pitch_slider.setRange(-24, 24); self.pitch_slider.setValue(0); self.pitch_slider.valueChanged.connect(lambda val: self.pitch_label.setText(f"Pitch ({val}):")); basic_settings_layout.addWidget(self.pitch_slider, 0, 1, 1, 2) 
        self.index_rate_label = QLabel("Index Rate (0.75):"); basic_settings_layout.addWidget(self.index_rate_label, 1, 0)
        self.index_rate_slider = QSlider(Qt.Orientation.Horizontal); self.index_rate_slider.setRange(0, 100); self.index_rate_slider.setValue(75); self.index_rate_slider.valueChanged.connect(lambda val: self.index_rate_label.setText(f"Index Rate ({val/100.0:.2f}):")); basic_settings_layout.addWidget(self.index_rate_slider, 1, 1, 1, 2)
        self.rms_mix_rate_label = QLabel("Volume Env (1.00):"); basic_settings_layout.addWidget(self.rms_mix_rate_label, 2, 0)
        self.rms_mix_rate_slider = QSlider(Qt.Orientation.Horizontal); self.rms_mix_rate_slider.setRange(0, 100); self.rms_mix_rate_slider.setValue(100); self.rms_mix_rate_slider.valueChanged.connect(lambda val: self.rms_mix_rate_label.setText(f"Volume Env ({val/100.0:.2f}):")); basic_settings_layout.addWidget(self.rms_mix_rate_slider, 2, 1, 1, 2)
        self.protect_label = QLabel("Protect (0.50):"); basic_settings_layout.addWidget(self.protect_label, 3, 0)
        self.protect_slider = QSlider(Qt.Orientation.Horizontal); self.protect_slider.setRange(0, 50); self.protect_slider.setValue(50); self.protect_slider.valueChanged.connect(lambda val: self.protect_label.setText(f"Protect ({val/100.0:.2f}):")); basic_settings_layout.addWidget(self.protect_slider, 3, 1, 1, 2)
        single_tab_layout.addWidget(basic_settings_group_box)

        # --- Advanced Settings Group ---
        advanced_settings_group = QGroupBox("Advanced Settings"); advanced_settings_group.setCheckable(True); advanced_settings_group.setChecked(False); advanced_layout = QGridLayout(advanced_settings_group)
        advanced_layout.addWidget(QLabel("F0 Method:"), 0, 0); self.f0_method_combo = QComboBox(); self.f0_method_combo.addItems(["rmvpe", "crepe", "crepe-tiny", "fcpe", "hybrid[rmvpe+fcpe]"]); self.f0_method_combo.setCurrentText("rmvpe"); advanced_layout.addWidget(self.f0_method_combo, 0, 1)
        advanced_layout.addWidget(QLabel("Speaker ID:"), 0, 2); self.sid_combo = QComboBox(); advanced_layout.addWidget(self.sid_combo, 0, 3)
        advanced_layout.addWidget(QLabel("Export Format:"), 0, 4); self.export_format_combo = QComboBox(); self.export_format_combo.addItems(["WAV", "MP3", "FLAC", "OGG", "M4A"]); advanced_layout.addWidget(self.export_format_combo, 0, 5)
        self.split_audio_checkbox = QCheckBox("Split Audio"); advanced_layout.addWidget(self.split_audio_checkbox, 1, 0, 1, 2) 
        self.autotune_checkbox = QCheckBox("Autotune"); advanced_layout.addWidget(self.autotune_checkbox, 1, 2, 1, 2) 
        self.clean_audio_checkbox = QCheckBox("Clean Audio"); advanced_layout.addWidget(self.clean_audio_checkbox, 1, 4, 1, 2) 
        self.autotune_strength_label = QLabel("Autotune Strength:"); self.autotune_strength_label.setVisible(False); advanced_layout.addWidget(self.autotune_strength_label, 2, 2)
        self.autotune_strength_slider = QSlider(Qt.Orientation.Horizontal); self.autotune_strength_slider.setRange(0, 100); self.autotune_strength_slider.setValue(100); self.autotune_strength_slider.setVisible(False); advanced_layout.addWidget(self.autotune_strength_slider, 2, 3)
        self.autotune_checkbox.stateChanged.connect(lambda state: self.autotune_strength_label.setVisible(state == Qt.CheckState.Checked.value)); self.autotune_checkbox.stateChanged.connect(lambda state: self.autotune_strength_slider.setVisible(state == Qt.CheckState.Checked.value))
        self.clean_strength_label = QLabel("Clean Strength:"); self.clean_strength_label.setVisible(False); advanced_layout.addWidget(self.clean_strength_label, 3, 4)
        self.clean_strength_slider = QSlider(Qt.Orientation.Horizontal); self.clean_strength_slider.setRange(0, 100); self.clean_strength_slider.setValue(50); self.clean_strength_slider.setVisible(False); advanced_layout.addWidget(self.clean_strength_slider, 3, 5)
        self.clean_audio_checkbox.stateChanged.connect(lambda state: self.clean_strength_label.setVisible(state == Qt.CheckState.Checked.value)); self.clean_audio_checkbox.stateChanged.connect(lambda state: self.clean_strength_slider.setVisible(state == Qt.CheckState.Checked.value))
        self.formant_shifting_checkbox = QCheckBox("Formant Shifting"); advanced_layout.addWidget(self.formant_shifting_checkbox, 4, 0, 1, 2) 
        self.post_process_checkbox = QCheckBox("Post-Process Effects"); advanced_layout.addWidget(self.post_process_checkbox, 4, 2, 1, 2); self.post_process_checkbox.stateChanged.connect(self.toggle_post_process_visibility)
        self.formant_preset_label = QLabel("Formant Preset:"); self.formant_preset_label.setVisible(False); advanced_layout.addWidget(self.formant_preset_label, 5, 0)
        self.formant_preset_combo = QComboBox(); self.formant_preset_combo.setVisible(False); advanced_layout.addWidget(self.formant_preset_combo, 5, 1)
        self.formant_refresh_button = QPushButton("Refresh"); self.formant_refresh_button.setVisible(False); advanced_layout.addWidget(self.formant_refresh_button, 5, 2)
        self.formant_shifting_checkbox.stateChanged.connect(lambda state: self.formant_preset_label.setVisible(state == Qt.CheckState.Checked.value)); self.formant_shifting_checkbox.stateChanged.connect(lambda state: self.formant_preset_combo.setVisible(state == Qt.CheckState.Checked.value)); self.formant_shifting_checkbox.stateChanged.connect(lambda state: self.formant_refresh_button.setVisible(state == Qt.CheckState.Checked.value)); self.formant_shifting_checkbox.stateChanged.connect(self.refresh_formant_presets); self.formant_refresh_button.clicked.connect(self.refresh_formant_presets); self.formant_preset_combo.currentTextChanged.connect(self.update_formant_sliders_from_preset)
        self.formant_qfrency_label = QLabel("Quefrency:"); self.formant_qfrency_label.setVisible(False); advanced_layout.addWidget(self.formant_qfrency_label, 6, 0)
        self.formant_qfrency_slider = QSlider(Qt.Orientation.Horizontal); self.formant_qfrency_slider.setRange(0, 160); self.formant_qfrency_slider.setValue(10); self.formant_qfrency_slider.setVisible(False); advanced_layout.addWidget(self.formant_qfrency_slider, 6, 1)
        self.formant_shifting_checkbox.stateChanged.connect(lambda state: self.formant_qfrency_label.setVisible(state == Qt.CheckState.Checked.value)); self.formant_shifting_checkbox.stateChanged.connect(lambda state: self.formant_qfrency_slider.setVisible(state == Qt.CheckState.Checked.value))
        self.formant_timbre_label = QLabel("Timbre:"); self.formant_timbre_label.setVisible(False); advanced_layout.addWidget(self.formant_timbre_label, 6, 2)
        self.formant_timbre_slider = QSlider(Qt.Orientation.Horizontal); self.formant_timbre_slider.setRange(0, 160); self.formant_timbre_slider.setValue(10); self.formant_timbre_slider.setVisible(False); advanced_layout.addWidget(self.formant_timbre_slider, 6, 3)
        self.formant_shifting_checkbox.stateChanged.connect(lambda state: self.formant_timbre_label.setVisible(state == Qt.CheckState.Checked.value)); self.formant_shifting_checkbox.stateChanged.connect(lambda state: self.formant_timbre_slider.setVisible(state == Qt.CheckState.Checked.value))
        advanced_layout.addWidget(QLabel("Embedder Model:"), 7, 0); self.embedder_model_combo = QComboBox(); self.embedder_model_combo.addItems(["contentvec", "chinese-hubert-base", "japanese-hubert-base", "korean-hubert-base", "custom"]); self.embedder_model_combo.setCurrentText("contentvec"); self.embedder_model_combo.currentTextChanged.connect(self.toggle_custom_embedder_visibility); advanced_layout.addWidget(self.embedder_model_combo, 7, 1)
        self.custom_embedder_group = QGroupBox("Custom Embedder"); self.custom_embedder_group.setVisible(False); custom_embedder_layout = QGridLayout(self.custom_embedder_group); custom_embedder_layout.addWidget(QLabel("Select Custom Embedder:"), 0, 0); self.embedder_model_custom_combo = QComboBox(); self.refresh_embedder_folders(); custom_embedder_layout.addWidget(self.embedder_model_custom_combo, 0, 1); self.refresh_embedders_button = QPushButton("Refresh"); self.refresh_embedders_button.clicked.connect(self.refresh_embedder_folders); custom_embedder_layout.addWidget(self.refresh_embedders_button, 0, 2); advanced_layout.addWidget(self.custom_embedder_group, 8, 0, 1, 6) 
        advanced_layout.addWidget(QLabel("F0 File (Optional):"), 9, 0); self.f0_file_edit = QLineEdit(); self.f0_file_edit.setPlaceholderText("Path to .f0 file"); advanced_layout.addWidget(self.f0_file_edit, 9, 1, 1, 4); self.f0_file_browse_button = QPushButton("Browse..."); self.f0_file_browse_button.clicked.connect(self.browse_f0_file); advanced_layout.addWidget(self.f0_file_browse_button, 9, 5)
        
        # --- Post-Process Effects Section (Conditional) ---
        self.post_process_group = QGroupBox("Post-Process Effects"); self.post_process_group.setVisible(False); post_process_layout = QGridLayout(self.post_process_group)
        # Add Checkboxes for each effect
        self.reverb_checkbox = QCheckBox("Reverb"); post_process_layout.addWidget(self.reverb_checkbox, 0, 0)
        self.pitch_shift_checkbox = QCheckBox("Pitch Shift"); post_process_layout.addWidget(self.pitch_shift_checkbox, 0, 1)
        self.limiter_checkbox = QCheckBox("Limiter"); post_process_layout.addWidget(self.limiter_checkbox, 0, 2)
        self.gain_checkbox = QCheckBox("Gain"); post_process_layout.addWidget(self.gain_checkbox, 1, 0)
        self.distortion_checkbox = QCheckBox("Distortion"); post_process_layout.addWidget(self.distortion_checkbox, 1, 1)
        self.chorus_checkbox = QCheckBox("Chorus"); post_process_layout.addWidget(self.chorus_checkbox, 1, 2)
        self.bitcrush_checkbox = QCheckBox("Bitcrush"); post_process_layout.addWidget(self.bitcrush_checkbox, 2, 0)
        self.clipping_checkbox = QCheckBox("Clipping"); post_process_layout.addWidget(self.clipping_checkbox, 2, 1)
        self.compressor_checkbox = QCheckBox("Compressor"); post_process_layout.addWidget(self.compressor_checkbox, 2, 2)
        self.delay_checkbox = QCheckBox("Delay"); post_process_layout.addWidget(self.delay_checkbox, 3, 0)
        # TODO: Add sliders for each effect, make them conditional on their checkbox
        advanced_layout.addWidget(self.post_process_group, 10, 0, 1, 6) # Add group to main advanced layout

        single_tab_layout.addWidget(advanced_settings_group)
        single_tab_layout.addSpacerItem(QSpacerItem(20, 40, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Expanding))

    def setup_batch_tab_ui(self, batch_tab_layout):
        """Sets up the UI elements for the Batch Inference tab."""
        # Input Folder Section
        input_folder_group = QWidget(); input_folder_layout = QGridLayout(input_folder_group); input_folder_layout.setContentsMargins(0,5,0,5) 
        input_folder_layout.addWidget(QLabel("Input Folder:"), 0, 0); self.input_folder_edit_batch = QLineEdit(); self.input_folder_edit_batch.setPlaceholderText("Select folder containing audio files"); input_folder_layout.addWidget(self.input_folder_edit_batch, 0, 1)
        self.browse_input_folder_button_batch = QPushButton("Browse..."); self.browse_input_folder_button_batch.clicked.connect(self.browse_input_folder_batch); input_folder_layout.addWidget(self.browse_input_folder_button_batch, 0, 2)
        batch_tab_layout.addWidget(input_folder_group)

        # Output Folder Section
        output_folder_group = QWidget(); output_folder_layout = QGridLayout(output_folder_group); output_folder_layout.setContentsMargins(0,0,0,5) 
        output_folder_layout.addWidget(QLabel("Output Folder:"), 0, 0); self.output_folder_edit_batch = QLineEdit(); self.output_folder_edit_batch.setPlaceholderText("Select folder for output files"); output_folder_layout.addWidget(self.output_folder_edit_batch, 0, 1)
        self.browse_output_folder_button_batch = QPushButton("Browse..."); self.browse_output_folder_button_batch.clicked.connect(self.browse_output_folder_batch); output_folder_layout.addWidget(self.browse_output_folder_button_batch, 0, 2)
        batch_tab_layout.addWidget(output_folder_group)

        # Basic Settings Section (Mirror Single Tab)
        basic_settings_group_box_batch = QWidget(); basic_settings_layout_batch = QGridLayout(basic_settings_group_box_batch); basic_settings_layout_batch.setContentsMargins(0,0,0,0)
        self.pitch_label_batch = QLabel("Pitch (0):"); basic_settings_layout_batch.addWidget(self.pitch_label_batch, 0, 0)
        self.pitch_slider_batch = QSlider(Qt.Orientation.Horizontal); self.pitch_slider_batch.setRange(-24, 24); self.pitch_slider_batch.setValue(0); self.pitch_slider_batch.valueChanged.connect(lambda val: self.pitch_label_batch.setText(f"Pitch ({val}):")); basic_settings_layout_batch.addWidget(self.pitch_slider_batch, 0, 1, 1, 2) 
        self.index_rate_label_batch = QLabel("Index Rate (0.75):"); basic_settings_layout_batch.addWidget(self.index_rate_label_batch, 1, 0)
        self.index_rate_slider_batch = QSlider(Qt.Orientation.Horizontal); self.index_rate_slider_batch.setRange(0, 100); self.index_rate_slider_batch.setValue(75); self.index_rate_slider_batch.valueChanged.connect(lambda val: self.index_rate_label_batch.setText(f"Index Rate ({val/100.0:.2f}):")); basic_settings_layout_batch.addWidget(self.index_rate_slider_batch, 1, 1, 1, 2)
        self.rms_mix_rate_label_batch = QLabel("Volume Env (1.00):"); basic_settings_layout_batch.addWidget(self.rms_mix_rate_label_batch, 2, 0)
        self.rms_mix_rate_slider_batch = QSlider(Qt.Orientation.Horizontal); self.rms_mix_rate_slider_batch.setRange(0, 100); self.rms_mix_rate_slider_batch.setValue(100); self.rms_mix_rate_slider_batch.valueChanged.connect(lambda val: self.rms_mix_rate_label_batch.setText(f"Volume Env ({val/100.0:.2f}):")); basic_settings_layout_batch.addWidget(self.rms_mix_rate_slider_batch, 2, 1, 1, 2)
        self.protect_label_batch = QLabel("Protect (0.50):"); basic_settings_layout_batch.addWidget(self.protect_label_batch, 3, 0)
        self.protect_slider_batch = QSlider(Qt.Orientation.Horizontal); self.protect_slider_batch.setRange(0, 50); self.protect_slider_batch.setValue(50); self.protect_slider_batch.valueChanged.connect(lambda val: self.protect_label_batch.setText(f"Protect ({val/100.0:.2f}):")); basic_settings_layout_batch.addWidget(self.protect_slider_batch, 3, 1, 1, 2)
        batch_tab_layout.addWidget(basic_settings_group_box_batch)

        # --- Advanced Settings Group (Mirror Single Tab) ---
        advanced_settings_group_batch = QGroupBox("Advanced Settings"); advanced_settings_group_batch.setCheckable(True); advanced_settings_group_batch.setChecked(False); advanced_layout_batch = QGridLayout(advanced_settings_group_batch)
        advanced_layout_batch.addWidget(QLabel("F0 Method:"), 0, 0); self.f0_method_combo_batch = QComboBox(); self.f0_method_combo_batch.addItems(["rmvpe", "crepe", "crepe-tiny", "fcpe", "hybrid[rmvpe+fcpe]"]); self.f0_method_combo_batch.setCurrentText("rmvpe"); advanced_layout_batch.addWidget(self.f0_method_combo_batch, 0, 1)
        advanced_layout_batch.addWidget(QLabel("Speaker ID:"), 0, 2); self.sid_combo_batch = QComboBox(); advanced_layout_batch.addWidget(self.sid_combo_batch, 0, 3)
        advanced_layout_batch.addWidget(QLabel("Export Format:"), 0, 4); self.export_format_combo_batch = QComboBox(); self.export_format_combo_batch.addItems(["WAV", "MP3", "FLAC", "OGG", "M4A"]); advanced_layout_batch.addWidget(self.export_format_combo_batch, 0, 5)
        self.split_audio_checkbox_batch = QCheckBox("Split Audio"); advanced_layout_batch.addWidget(self.split_audio_checkbox_batch, 1, 0, 1, 2) 
        self.autotune_checkbox_batch = QCheckBox("Autotune"); advanced_layout_batch.addWidget(self.autotune_checkbox_batch, 1, 2, 1, 2) 
        self.clean_audio_checkbox_batch = QCheckBox("Clean Audio"); advanced_layout_batch.addWidget(self.clean_audio_checkbox_batch, 1, 4, 1, 2) 
        self.autotune_strength_label_batch = QLabel("Autotune Strength:"); self.autotune_strength_label_batch.setVisible(False); advanced_layout_batch.addWidget(self.autotune_strength_label_batch, 2, 2)
        self.autotune_strength_slider_batch = QSlider(Qt.Orientation.Horizontal); self.autotune_strength_slider_batch.setRange(0, 100); self.autotune_strength_slider_batch.setValue(100); self.autotune_strength_slider_batch.setVisible(False); advanced_layout_batch.addWidget(self.autotune_strength_slider_batch, 2, 3)
        self.autotune_checkbox_batch.stateChanged.connect(lambda state: self.autotune_strength_label_batch.setVisible(state == Qt.CheckState.Checked.value)); self.autotune_checkbox_batch.stateChanged.connect(lambda state: self.autotune_strength_slider_batch.setVisible(state == Qt.CheckState.Checked.value))
        self.clean_strength_label_batch = QLabel("Clean Strength:"); self.clean_strength_label_batch.setVisible(False); advanced_layout_batch.addWidget(self.clean_strength_label_batch, 3, 4)
        self.clean_strength_slider_batch = QSlider(Qt.Orientation.Horizontal); self.clean_strength_slider_batch.setRange(0, 100); self.clean_strength_slider_batch.setValue(50); self.clean_strength_slider_batch.setVisible(False); advanced_layout_batch.addWidget(self.clean_strength_slider_batch, 3, 5)
        self.clean_audio_checkbox_batch.stateChanged.connect(lambda state: self.clean_strength_label_batch.setVisible(state == Qt.CheckState.Checked.value)); self.clean_audio_checkbox_batch.stateChanged.connect(lambda state: self.clean_strength_slider_batch.setVisible(state == Qt.CheckState.Checked.value))
        self.formant_shifting_checkbox_batch = QCheckBox("Formant Shifting"); advanced_layout_batch.addWidget(self.formant_shifting_checkbox_batch, 4, 0, 1, 2) 
        self.post_process_checkbox_batch = QCheckBox("Post-Process Effects"); advanced_layout_batch.addWidget(self.post_process_checkbox_batch, 4, 2, 1, 2)
        self.formant_preset_label_batch = QLabel("Formant Preset:"); self.formant_preset_label_batch.setVisible(False); advanced_layout_batch.addWidget(self.formant_preset_label_batch, 5, 0)
        self.formant_preset_combo_batch = QComboBox(); self.formant_preset_combo_batch.setVisible(False); advanced_layout_batch.addWidget(self.formant_preset_combo_batch, 5, 1)
        self.formant_refresh_button_batch = QPushButton("Refresh"); self.formant_refresh_button_batch.setVisible(False); advanced_layout_batch.addWidget(self.formant_refresh_button_batch, 5, 2)
        self.formant_shifting_checkbox_batch.stateChanged.connect(lambda state: self.formant_preset_label_batch.setVisible(state == Qt.CheckState.Checked.value)); self.formant_shifting_checkbox_batch.stateChanged.connect(lambda state: self.formant_preset_combo_batch.setVisible(state == Qt.CheckState.Checked.value)); self.formant_shifting_checkbox_batch.stateChanged.connect(lambda state: self.formant_refresh_button_batch.setVisible(state == Qt.CheckState.Checked.value)); self.formant_shifting_checkbox_batch.stateChanged.connect(self.refresh_formant_presets_batch); self.formant_refresh_button_batch.clicked.connect(self.refresh_formant_presets_batch); self.formant_preset_combo_batch.currentTextChanged.connect(self.update_formant_sliders_from_preset_batch)
        self.formant_qfrency_label_batch = QLabel("Quefrency:"); self.formant_qfrency_label_batch.setVisible(False); advanced_layout_batch.addWidget(self.formant_qfrency_label_batch, 6, 0)
        self.formant_qfrency_slider_batch = QSlider(Qt.Orientation.Horizontal); self.formant_qfrency_slider_batch.setRange(0, 160); self.formant_qfrency_slider_batch.setValue(10); self.formant_qfrency_slider_batch.setVisible(False); advanced_layout_batch.addWidget(self.formant_qfrency_slider_batch, 6, 1)
        self.formant_shifting_checkbox_batch.stateChanged.connect(lambda state: self.formant_qfrency_label_batch.setVisible(state == Qt.CheckState.Checked.value)); self.formant_shifting_checkbox_batch.stateChanged.connect(lambda state: self.formant_qfrency_slider_batch.setVisible(state == Qt.CheckState.Checked.value))
        self.formant_timbre_label_batch = QLabel("Timbre:"); self.formant_timbre_label_batch.setVisible(False); advanced_layout_batch.addWidget(self.formant_timbre_label_batch, 6, 2)
        self.formant_timbre_slider_batch = QSlider(Qt.Orientation.Horizontal); self.formant_timbre_slider_batch.setRange(0, 160); self.formant_timbre_slider_batch.setValue(10); self.formant_timbre_slider_batch.setVisible(False); advanced_layout_batch.addWidget(self.formant_timbre_slider_batch, 6, 3)
        self.formant_shifting_checkbox_batch.stateChanged.connect(lambda state: self.formant_timbre_label_batch.setVisible(state == Qt.CheckState.Checked.value)); self.formant_shifting_checkbox_batch.stateChanged.connect(lambda state: self.formant_timbre_slider_batch.setVisible(state == Qt.CheckState.Checked.value))
        advanced_layout_batch.addWidget(QLabel("Embedder Model:"), 7, 0); self.embedder_model_combo_batch = QComboBox(); self.embedder_model_combo_batch.addItems(["contentvec", "chinese-hubert-base", "japanese-hubert-base", "korean-hubert-base", "custom"]); self.embedder_model_combo_batch.setCurrentText("contentvec"); self.embedder_model_combo_batch.currentTextChanged.connect(self.toggle_custom_embedder_visibility_batch); advanced_layout_batch.addWidget(self.embedder_model_combo_batch, 7, 1)
        self.custom_embedder_group_batch = QGroupBox("Custom Embedder"); self.custom_embedder_group_batch.setVisible(False); custom_embedder_layout_batch = QGridLayout(self.custom_embedder_group_batch); custom_embedder_layout_batch.addWidget(QLabel("Select Custom Embedder:"), 0, 0); self.embedder_model_custom_combo_batch = QComboBox(); self.refresh_embedder_folders_batch(); custom_embedder_layout_batch.addWidget(self.embedder_model_custom_combo_batch, 0, 1); self.refresh_embedders_button_batch = QPushButton("Refresh"); self.refresh_embedders_button_batch.clicked.connect(self.refresh_embedder_folders_batch); custom_embedder_layout_batch.addWidget(self.refresh_embedders_button_batch, 0, 2); advanced_layout_batch.addWidget(self.custom_embedder_group_batch, 8, 0, 1, 6) 
        advanced_layout_batch.addWidget(QLabel("F0 File Folder (Optional):"), 9, 0); self.f0_folder_edit_batch = QLineEdit(); self.f0_folder_edit_batch.setPlaceholderText("Path to folder containing .f0 files (optional)"); advanced_layout_batch.addWidget(self.f0_folder_edit_batch, 9, 1, 1, 4); self.f0_folder_browse_button_batch = QPushButton("Browse..."); self.f0_folder_browse_button_batch.clicked.connect(self.browse_f0_folder_batch); advanced_layout_batch.addWidget(self.f0_folder_browse_button_batch, 9, 5)
        batch_tab_layout.addWidget(advanced_settings_group_batch)

        # Add spacer
        batch_tab_layout.addSpacerItem(QSpacerItem(20, 40, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Expanding))

    # --- Common Methods ---
    def toggle_post_process_visibility(self, state):
        """Shows/hides the post-process effects group."""
        self.post_process_group.setVisible(state == Qt.CheckState.Checked.value)

    def toggle_custom_embedder_visibility(self, text):
        self.custom_embedder_group.setVisible(text == "custom")
    
    def toggle_custom_embedder_visibility_batch(self, text):
        self.custom_embedder_group_batch.setVisible(text == "custom")

    def refresh_embedder_folders(self):
        self.embedder_model_custom_combo.clear()
        try:
            folders = refresh_embedders_folders() 
            if folders: self.embedder_model_custom_combo.addItems(folders)
            else: self.embedder_model_custom_combo.addItem("No custom embedders found")
        except Exception as e: print(f"Error refreshing embedder folders: {e}"); self.embedder_model_custom_combo.addItem("Error loading embedders")

    def refresh_embedder_folders_batch(self):
        self.embedder_model_custom_combo_batch.clear()
        try:
            folders = refresh_embedders_folders() 
            if folders: self.embedder_model_custom_combo_batch.addItems(folders)
            else: self.embedder_model_custom_combo_batch.addItem("No custom embedders found")
        except Exception as e: print(f"Error refreshing embedder folders: {e}"); self.embedder_model_custom_combo_batch.addItem("Error loading embedders")

    def browse_f0_file(self):
        start_dir = os.path.dirname(self.input_audio_path_edit.text()) if self.input_audio_path_edit.text() else project_root
        file_path, _ = QFileDialog.getOpenFileName(self, "Select F0 File", start_dir, "F0 Files (*.f0);;All Files (*)")
        if file_path: self.f0_file_edit.setText(file_path)

    def browse_f0_folder_batch(self):
        dir_path = QFileDialog.getExistingDirectory(self, "Select F0 File Folder", project_root)
        if dir_path: self.f0_folder_edit_batch.setText(dir_path)

    def refresh_formant_presets(self):
        if not self.formant_shifting_checkbox.isChecked(): return
        self.formant_preset_combo.clear()
        try:
            presets = list_json_files(FORMANTSHIFT_DIR); self.formant_preset_combo.addItems([""] + presets) 
        except Exception as e: print(f"Error listing formant presets: {e}"); self.formant_preset_combo.addItem("Error loading presets")

    def refresh_formant_presets_batch(self):
        if not self.formant_shifting_checkbox_batch.isChecked(): return
        self.formant_preset_combo_batch.clear()
        try:
            presets = list_json_files(FORMANTSHIFT_DIR); self.formant_preset_combo_batch.addItems([""] + presets) 
        except Exception as e: print(f"Error listing formant presets: {e}"); self.formant_preset_combo_batch.addItem("Error loading presets")

    def update_formant_sliders_from_preset(self, preset_name):
        if not preset_name: self.formant_qfrency_slider.setValue(10); self.formant_timbre_slider.setValue(10); return
        try:
            qfrency, timbre = update_sliders_formant(preset_name)
            self.formant_qfrency_slider.setValue(int(qfrency * 10)); self.formant_timbre_slider.setValue(int(timbre * 10))
        except Exception as e: print(f"Error loading formant preset '{preset_name}': {e}"); self.formant_qfrency_slider.setValue(10); self.formant_timbre_slider.setValue(10)

    def update_formant_sliders_from_preset_batch(self, preset_name):
        if not preset_name: self.formant_qfrency_slider_batch.setValue(10); self.formant_timbre_slider_batch.setValue(10); return
        try:
            qfrency, timbre = update_sliders_formant(preset_name)
            self.formant_qfrency_slider_batch.setValue(int(qfrency * 10)); self.formant_timbre_slider_batch.setValue(int(timbre * 10))
        except Exception as e: print(f"Error loading formant preset '{preset_name}': {e}"); self.formant_qfrency_slider_batch.setValue(10); self.formant_timbre_slider_batch.setValue(10)

    def refresh_models_and_indexes(self):
        print("Refreshing models and indexes...")
        self.model_combo.clear(); self.index_combo.clear()
        model_files = []
        if os.path.exists(MODEL_ROOT):
            for root, _, files in os.walk(MODEL_ROOT):
                for file in files:
                    if file.endswith((".pth", ".onnx")) and not (file.startswith("G_") or file.startswith("D_")): model_files.append(os.path.join(root, file))
        try: sorted_models = sorted(model_files, key=lambda x: extract_model_and_epoch(x))
        except Exception: sorted_models = sorted(model_files)
        if not sorted_models: self.model_combo.addItem("No models found"); self.model_combo.setEnabled(False)
        else:
            self.model_combo.setEnabled(True)
            for model_path in sorted_models: self.model_combo.addItem(os.path.relpath(model_path, MODEL_ROOT), userData=model_path) 
        index_files = get_indexes() 
        if not index_files: self.index_combo.addItem("No index files found"); self.index_combo.setEnabled(False)
        else:
             self.index_combo.setEnabled(True); self.index_combo.addItem("", userData="") 
             for index_path in sorted(index_files): self.index_combo.addItem(os.path.relpath(index_path, MODEL_ROOT), userData=index_path)
        self.on_model_selected(); print("Refresh complete.")

    def on_model_selected(self):
        selected_model_path = self.model_combo.currentData() 
        if not selected_model_path:
            index = self.index_combo.findData("") 
            if index >= 0: self.index_combo.setCurrentIndex(index)
        else:
            matched_index = match_index(selected_model_path)
            if matched_index:
                index = self.index_combo.findData(matched_index)
                if index >= 0: self.index_combo.setCurrentIndex(index)
                else: index = self.index_combo.findData("") 
                if index >= 0: self.index_combo.setCurrentIndex(index)
            else: index = self.index_combo.findData("") 
            if index >= 0: self.index_combo.setCurrentIndex(index)
        
        self.sid_combo.clear(); self.sid_combo_batch.clear()
        speaker_ids = get_speakers_id(selected_model_path) 
        if speaker_ids:
            str_ids = [str(sid) for sid in speaker_ids]
            self.sid_combo.addItems(str_ids); self.sid_combo.setEnabled(True)
            self.sid_combo_batch.addItems(str_ids); self.sid_combo_batch.setEnabled(True)
        else:
            self.sid_combo.addItem("0"); self.sid_combo.setEnabled(False)
            self.sid_combo_batch.addItem("0"); self.sid_combo_batch.setEnabled(False)

    def unload_model(self):
        self.model_combo.setCurrentIndex(-1)
        self.index_combo.setCurrentIndex(self.index_combo.findData("")) 
        self.sid_combo.clear(); self.sid_combo.addItem("0"); self.sid_combo.setEnabled(False)
        self.sid_combo_batch.clear(); self.sid_combo_batch.addItem("0"); self.sid_combo_batch.setEnabled(False)

    def browse_input_audio(self):
        start_dir = AUDIO_ROOT if os.path.exists(AUDIO_ROOT) else project_root
        audio_filter = "Audio Files (" + " ".join(f"*.{ext}" for ext in SUP_AUDIOEXT) + ");;All Files (*)"
        file_path, _ = QFileDialog.getOpenFileName(self, "Select Input Audio", start_dir, audio_filter)
        if file_path:
            self.input_audio_path_edit.setText(file_path)
            default_output = output_path_fn(file_path) 
            self.output_audio_path_edit.setText(default_output)

    def browse_output_path(self):
        start_dir = os.path.dirname(self.output_audio_path_edit.text()) if self.output_audio_path_edit.text() else AUDIO_ROOT
        if not os.path.exists(start_dir): start_dir = AUDIO_ROOT if os.path.exists(AUDIO_ROOT) else project_root
        default_filename = os.path.basename(self.output_audio_path_edit.text()) if self.output_audio_path_edit.text() else "output.wav"
        selected_format = self.export_format_combo.currentText().lower()
        default_filename = os.path.splitext(default_filename)[0] + f".{selected_format}"
        format_filter = f"{selected_format.upper()} Files (*.{selected_format});;WAV Files (*.wav);;MP3 Files (*.mp3);;FLAC Files (*.flac);;OGG Files (*.ogg);;M4A Files (*.m4a)"
        file_path, _ = QFileDialog.getSaveFileName(self, "Select Output Path", os.path.join(start_dir, default_filename), format_filter)
        if file_path:
            if not file_path.lower().endswith(f".{selected_format}"): file_path = os.path.splitext(file_path)[0] + f".{selected_format}"
            self.output_audio_path_edit.setText(file_path)

    def browse_input_folder_batch(self):
        dir_path = QFileDialog.getExistingDirectory(self, "Select Input Folder", AUDIO_ROOT if os.path.exists(AUDIO_ROOT) else project_root)
        if dir_path: self.input_folder_edit_batch.setText(dir_path)

    def browse_output_folder_batch(self):
        dir_path = QFileDialog.getExistingDirectory(self, "Select Output Folder", AUDIO_ROOT if os.path.exists(AUDIO_ROOT) else project_root)
        if dir_path: self.output_folder_edit_batch.setText(dir_path)

    def start_inference(self):
        current_tab_index = self.single_batch_tabs.currentIndex()
        is_batch = self.single_batch_tabs.tabText(current_tab_index) == "Batch"

        if self.inference_worker and self.inference_worker.isRunning():
            reply = QMessageBox.question(self, 'Inference Running', 'An inference task is already running. Cancel it and start a new one?', QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No, QMessageBox.StandardButton.No)
            if reply == QMessageBox.StandardButton.Yes and self.inference_worker: self.inference_worker.stop()
            else: return 

        pth_path = self.model_combo.currentData()
        index_path = self.index_combo.currentData() if self.index_combo.currentIndex() > 0 else "" 
        
        # Gather common params first
        params = { 
            "pth_path": pth_path, "index_path": index_path,
        }

        # Gather params based on active tab
        if is_batch:
            params.update({
                "pitch": self.pitch_slider_batch.value(),
                "index_rate": self.index_rate_slider_batch.value() / 100.0,
                "rms_mix_rate": self.rms_mix_rate_slider_batch.value() / 100.0, 
                "protect": self.protect_slider_batch.value() / 100.0, 
                "input_folder": self.input_folder_edit_batch.text(),
                "output_folder": self.output_folder_edit_batch.text(),
                "f0_method": self.f0_method_combo_batch.currentText(),
                "sid": int(self.sid_combo_batch.currentText()) if self.sid_combo_batch.currentText() else 0,
                "export_format": self.export_format_combo_batch.currentText(),
                "split_audio": self.split_audio_checkbox_batch.isChecked(),
                "f0_autotune": self.autotune_checkbox_batch.isChecked(),
                "f0_autotune_strength": self.autotune_strength_slider_batch.value() / 100.0 if self.autotune_checkbox_batch.isChecked() else 1.0,
                "clean_audio": self.clean_audio_checkbox_batch.isChecked(),
                "clean_strength": self.clean_strength_slider_batch.value() / 100.0 if self.clean_audio_checkbox_batch.isChecked() else 0.5,
                "formant_shifting": self.formant_shifting_checkbox_batch.isChecked(),
                "formant_qfrency": self.formant_qfrency_slider_batch.value() / 10.0 if self.formant_shifting_checkbox_batch.isChecked() else 1.0,
                "formant_timbre": self.formant_timbre_slider_batch.value() / 10.0 if self.formant_shifting_checkbox_batch.isChecked() else 1.0,
                "hop_length": 128, 
                "f0_file": self.f0_folder_edit_batch.text().strip() or None, # Assuming f0_file is folder path for batch
                "embedder_model": self.embedder_model_combo_batch.currentText(),
                "embedder_model_custom": self.embedder_model_custom_combo_batch.currentText() if self.embedder_model_combo_batch.currentText() == "custom" else None,
                "post_process": self.post_process_checkbox_batch.isChecked(),
                # TODO: Add batch post-process params
            })
            # Validation for batch folders
            if not params["input_folder"] or not os.path.isdir(params["input_folder"]):
                 QMessageBox.warning(self, "Input Error", "Please select a valid Input Folder for batch processing."); return
            if not params["output_folder"]: 
                 QMessageBox.warning(self, "Output Error", "Please specify an Output Folder for batch processing."); return
        else: # Single mode
             params.update({
                "pitch": self.pitch_slider.value(),
                "index_rate": self.index_rate_slider.value() / 100.0,
                "rms_mix_rate": self.rms_mix_rate_slider.value() / 100.0, 
                "protect": self.protect_slider.value() / 100.0, 
                "input_path": self.input_audio_path_edit.text(),
                "output_path": self.output_audio_path_edit.text(),
                "f0_method": self.f0_method_combo.currentText(),
                "sid": int(self.sid_combo.currentText()) if self.sid_combo.currentText() else 0,
                "export_format": self.export_format_combo.currentText(),
                "split_audio": self.split_audio_checkbox.isChecked(),
                "f0_autotune": self.autotune_checkbox.isChecked(),
                "f0_autotune_strength": self.autotune_strength_slider.value() / 100.0 if self.autotune_checkbox.isChecked() else 1.0,
                "clean_audio": self.clean_audio_checkbox.isChecked(),
                "clean_strength": self.clean_strength_slider.value() / 100.0 if self.clean_audio_checkbox.isChecked() else 0.5,
                "formant_shifting": self.formant_shifting_checkbox.isChecked(),
                "formant_qfrency": self.formant_qfrency_slider.value() / 10.0 if self.formant_shifting_checkbox.isChecked() else 1.0,
                "formant_timbre": self.formant_timbre_slider.value() / 10.0 if self.formant_shifting_checkbox.isChecked() else 1.0,
                "hop_length": 128, 
                "f0_file": self.f0_file_edit.text().strip() or None,
                "embedder_model": self.embedder_model_combo.currentText(),
                "embedder_model_custom": self.embedder_model_custom_combo.currentText() if self.embedder_model_combo.currentText() == "custom" else None,
                "post_process": self.post_process_checkbox.isChecked(),
                # --- Add single post-process params ---
                "reverb": self.reverb_checkbox.isChecked() if self.post_process_checkbox.isChecked() else False,
                "pitch_shift": self.pitch_shift_checkbox.isChecked() if self.post_process_checkbox.isChecked() else False,
                "limiter": self.limiter_checkbox.isChecked() if self.post_process_checkbox.isChecked() else False,
                "gain": self.gain_checkbox.isChecked() if self.post_process_checkbox.isChecked() else False,
                "distortion": self.distortion_checkbox.isChecked() if self.post_process_checkbox.isChecked() else False,
                "chorus": self.chorus_checkbox.isChecked() if self.post_process_checkbox.isChecked() else False,
                "bitcrush": self.bitcrush_checkbox.isChecked() if self.post_process_checkbox.isChecked() else False,
                "clipping": self.clipping_checkbox.isChecked() if self.post_process_checkbox.isChecked() else False,
                "compressor": self.compressor_checkbox.isChecked() if self.post_process_checkbox.isChecked() else False,
                "delay": self.delay_checkbox.isChecked() if self.post_process_checkbox.isChecked() else False,
                # TODO: Get slider values for enabled effects
             })
             # Validation for single files
             if not params["input_path"] or not os.path.exists(params["input_path"]):
                 QMessageBox.warning(self, "Input Error", "Please select a valid input audio file."); return
             if not params["output_path"]:
                 QMessageBox.warning(self, "Output Error", "Please specify an output file path."); return

        # Common model validation
        if not params["pth_path"] or not os.path.exists(params["pth_path"]):
             QMessageBox.warning(self, "Model Error", "Please select a valid voice model file."); return
        if params["index_path"] and not os.path.exists(params["index_path"]):
             self.update_status(f"Warning: Selected index file not found: {params['index_path']}")

        # --- Start worker thread ---
        self.convert_button.setEnabled(False) 
        self.progress_bar.setValue(0); self.progress_bar.setFormat("Processing..."); self.progress_bar.setTextVisible(True)

        self.inference_worker = InferenceWorker(params, is_batch=is_batch) 
        self.inference_worker.progress.connect(self.update_progress)
        self.inference_worker.status.connect(self.update_status)
        self.inference_worker.finished.connect(self.on_inference_finished)
        self.inference_worker.error.connect(self.on_inference_error)
        self.inference_worker.finished.connect(lambda msg, path: self.reset_ui_state())
        self.inference_worker.error.connect(lambda err_msg: self.reset_ui_state())
        self.inference_worker.start()

    def reset_ui_state(self):
        self.convert_button.setEnabled(True)
        self.progress_bar.setValue(0); self.progress_bar.setTextVisible(False)

    def update_progress(self, value):
        self.progress_bar.setValue(value)
        if value < 100: self.progress_bar.setFormat(f"Processing... {value}%") 
        else: self.progress_bar.setFormat("Finishing...")

    def update_status(self, message):
        self.status_label.setText(f"Status: {message}")

    def on_inference_finished(self, message, output_path): 
        self.update_status(f"Finished: {message}")
        QMessageBox.information(self, "Inference Complete", f"{message}\nOutput saved to:\n{output_path}")
        print(f"Output saved to: {output_path}")

    def on_inference_error(self, error_message):
        self.update_status("Error occurred") 
        QMessageBox.critical(self, "Inference Error", f"An error occurred:\n{error_message}")
        print(f"Error details:\n{error_message}")
