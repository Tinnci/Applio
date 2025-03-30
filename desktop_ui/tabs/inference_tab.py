from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QGridLayout,
                             QSlider, QComboBox, QCheckBox, QLineEdit, QFileDialog, QProgressBar,
                             QMessageBox, QSizePolicy, QSpacerItem, QTabWidget,
                             QGroupBox, QDoubleSpinBox, QSpinBox) # Added more widgets
from PyQt6.QtCore import Qt, QThread, pyqtSignal
import os
import sys
import traceback
import json # Added for presets

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

        # Initialize preset list
        self.load_presets()

    def setup_single_tab_ui(self, single_tab_layout):
        """Sets up the UI elements for the Single Inference tab."""

        # --- Preset Section ---
        preset_group = QGroupBox(self.tr("Presets"))
        preset_layout = QGridLayout(preset_group)
        preset_layout.addWidget(QLabel(self.tr("Load Preset:")), 0, 0)
        self.preset_combo = QComboBox(); preset_layout.addWidget(self.preset_combo, 0, 1)
        self.load_preset_button = QPushButton(self.tr("Load")); self.load_preset_button.clicked.connect(self.load_preset_settings); preset_layout.addWidget(self.load_preset_button, 0, 2)
        self.refresh_presets_button = QPushButton(self.tr("Refresh")); self.refresh_presets_button.clicked.connect(self.load_presets); preset_layout.addWidget(self.refresh_presets_button, 0, 3)
        preset_layout.addWidget(QLabel(self.tr("Save Preset As:")), 1, 0)
        self.save_preset_name_edit = QLineEdit(); self.save_preset_name_edit.setPlaceholderText(self.tr("Enter preset name")); preset_layout.addWidget(self.save_preset_name_edit, 1, 1)
        self.save_preset_button = QPushButton(self.tr("Save")); self.save_preset_button.clicked.connect(self.save_preset_settings); preset_layout.addWidget(self.save_preset_button, 1, 2)
        single_tab_layout.addWidget(preset_group)

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
        self.post_process_checkbox = QCheckBox(self.tr("Post-Process Effects")); advanced_layout.addWidget(self.post_process_checkbox, 4, 2, 1, 2); self.post_process_checkbox.stateChanged.connect(self.toggle_post_process_visibility)
        self.formant_preset_label = QLabel(self.tr("Formant Preset:")); self.formant_preset_label.setVisible(False); advanced_layout.addWidget(self.formant_preset_label, 5, 0)
        self.formant_preset_combo = QComboBox(); self.formant_preset_combo.setVisible(False); advanced_layout.addWidget(self.formant_preset_combo, 5, 1)
        self.formant_refresh_button = QPushButton(self.tr("Refresh")); self.formant_refresh_button.setVisible(False); advanced_layout.addWidget(self.formant_refresh_button, 5, 2)
        self.formant_shifting_checkbox.stateChanged.connect(lambda state: self.formant_preset_label.setVisible(state == Qt.CheckState.Checked.value)); self.formant_shifting_checkbox.stateChanged.connect(lambda state: self.formant_preset_combo.setVisible(state == Qt.CheckState.Checked.value)); self.formant_shifting_checkbox.stateChanged.connect(lambda state: self.formant_refresh_button.setVisible(state == Qt.CheckState.Checked.value)); self.formant_shifting_checkbox.stateChanged.connect(self.refresh_formant_presets); self.formant_refresh_button.clicked.connect(self.refresh_formant_presets); self.formant_preset_combo.currentTextChanged.connect(self.update_formant_sliders_from_preset)
        self.formant_qfrency_label = QLabel(self.tr("Quefrency:")); self.formant_qfrency_label.setVisible(False); advanced_layout.addWidget(self.formant_qfrency_label, 6, 0)
        self.formant_qfrency_slider = QSlider(Qt.Orientation.Horizontal); self.formant_qfrency_slider.setRange(0, 160); self.formant_qfrency_slider.setValue(10); self.formant_qfrency_slider.setVisible(False); advanced_layout.addWidget(self.formant_qfrency_slider, 6, 1)
        self.formant_shifting_checkbox.stateChanged.connect(lambda state: self.formant_qfrency_label.setVisible(state == Qt.CheckState.Checked.value)); self.formant_shifting_checkbox.stateChanged.connect(lambda state: self.formant_qfrency_slider.setVisible(state == Qt.CheckState.Checked.value))
        self.formant_timbre_label = QLabel(self.tr("Timbre:")); self.formant_timbre_label.setVisible(False); advanced_layout.addWidget(self.formant_timbre_label, 6, 2)
        self.formant_timbre_slider = QSlider(Qt.Orientation.Horizontal); self.formant_timbre_slider.setRange(0, 160); self.formant_timbre_slider.setValue(10); self.formant_timbre_slider.setVisible(False); advanced_layout.addWidget(self.formant_timbre_slider, 6, 3)
        self.formant_shifting_checkbox.stateChanged.connect(lambda state: self.formant_timbre_label.setVisible(state == Qt.CheckState.Checked.value)); self.formant_shifting_checkbox.stateChanged.connect(lambda state: self.formant_timbre_slider.setVisible(state == Qt.CheckState.Checked.value))
        advanced_layout.addWidget(QLabel(self.tr("Embedder Model:")), 7, 0); self.embedder_model_combo = QComboBox(); self.embedder_model_combo.addItems(["contentvec", "chinese-hubert-base", "japanese-hubert-base", "korean-hubert-base", "custom"]); self.embedder_model_combo.setCurrentText("contentvec"); self.embedder_model_combo.currentTextChanged.connect(self.toggle_custom_embedder_visibility); advanced_layout.addWidget(self.embedder_model_combo, 7, 1)
        self.custom_embedder_group = QGroupBox(self.tr("Custom Embedder")); self.custom_embedder_group.setVisible(False); custom_embedder_layout = QGridLayout(self.custom_embedder_group); custom_embedder_layout.addWidget(QLabel(self.tr("Select Custom Embedder:")), 0, 0); self.embedder_model_custom_combo = QComboBox(); self.refresh_embedder_folders(); custom_embedder_layout.addWidget(self.embedder_model_custom_combo, 0, 1); self.refresh_embedders_button = QPushButton(self.tr("Refresh")); self.refresh_embedders_button.clicked.connect(self.refresh_embedder_folders); custom_embedder_layout.addWidget(self.refresh_embedders_button, 0, 2); advanced_layout.addWidget(self.custom_embedder_group, 8, 0, 1, 6)
        advanced_layout.addWidget(QLabel(self.tr("F0 File (Optional):")), 9, 0); self.f0_file_edit = QLineEdit(); self.f0_file_edit.setPlaceholderText(self.tr("Path to .f0 file")); advanced_layout.addWidget(self.f0_file_edit, 9, 1, 1, 4); self.f0_file_browse_button = QPushButton(self.tr("Browse...")); self.f0_file_browse_button.clicked.connect(self.browse_f0_file); advanced_layout.addWidget(self.f0_file_browse_button, 9, 5)

        # --- Post-Process Effects Section (Conditional) ---
        self.post_process_group = QGroupBox(self.tr("Post-Process Effects")); self.post_process_group.setVisible(False); post_process_layout = QGridLayout(self.post_process_group)
        self.setup_post_process_ui(post_process_layout) # Call helper to create UI
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
        self.post_process_checkbox_batch = QCheckBox(self.tr("Post-Process Effects")); advanced_layout_batch.addWidget(self.post_process_checkbox_batch, 4, 2, 1, 2); self.post_process_checkbox_batch.stateChanged.connect(self.toggle_post_process_visibility_batch)
        self.formant_preset_label_batch = QLabel(self.tr("Formant Preset:")); self.formant_preset_label_batch.setVisible(False); advanced_layout_batch.addWidget(self.formant_preset_label_batch, 5, 0)
        self.formant_preset_combo_batch = QComboBox(); self.formant_preset_combo_batch.setVisible(False); advanced_layout_batch.addWidget(self.formant_preset_combo_batch, 5, 1)
        self.formant_refresh_button_batch = QPushButton(self.tr("Refresh")); self.formant_refresh_button_batch.setVisible(False); advanced_layout_batch.addWidget(self.formant_refresh_button_batch, 5, 2)
        self.formant_shifting_checkbox_batch.stateChanged.connect(lambda state: self.formant_preset_label_batch.setVisible(state == Qt.CheckState.Checked.value)); self.formant_shifting_checkbox_batch.stateChanged.connect(lambda state: self.formant_preset_combo_batch.setVisible(state == Qt.CheckState.Checked.value)); self.formant_shifting_checkbox_batch.stateChanged.connect(lambda state: self.formant_refresh_button_batch.setVisible(state == Qt.CheckState.Checked.value)); self.formant_shifting_checkbox_batch.stateChanged.connect(self.refresh_formant_presets_batch); self.formant_refresh_button_batch.clicked.connect(self.refresh_formant_presets_batch); self.formant_preset_combo_batch.currentTextChanged.connect(self.update_formant_sliders_from_preset_batch)
        self.formant_qfrency_label_batch = QLabel(self.tr("Quefrency:")); self.formant_qfrency_label_batch.setVisible(False); advanced_layout_batch.addWidget(self.formant_qfrency_label_batch, 6, 0)
        self.formant_qfrency_slider_batch = QSlider(Qt.Orientation.Horizontal); self.formant_qfrency_slider_batch.setRange(0, 160); self.formant_qfrency_slider_batch.setValue(10); self.formant_qfrency_slider_batch.setVisible(False); advanced_layout_batch.addWidget(self.formant_qfrency_slider_batch, 6, 1)
        self.formant_shifting_checkbox_batch.stateChanged.connect(lambda state: self.formant_qfrency_label_batch.setVisible(state == Qt.CheckState.Checked.value)); self.formant_shifting_checkbox_batch.stateChanged.connect(lambda state: self.formant_qfrency_slider_batch.setVisible(state == Qt.CheckState.Checked.value))
        self.formant_timbre_label_batch = QLabel(self.tr("Timbre:")); self.formant_timbre_label_batch.setVisible(False); advanced_layout_batch.addWidget(self.formant_timbre_label_batch, 6, 2)
        self.formant_timbre_slider_batch = QSlider(Qt.Orientation.Horizontal); self.formant_timbre_slider_batch.setRange(0, 160); self.formant_timbre_slider_batch.setValue(10); self.formant_timbre_slider_batch.setVisible(False); advanced_layout_batch.addWidget(self.formant_timbre_slider_batch, 6, 3)
        self.formant_shifting_checkbox_batch.stateChanged.connect(lambda state: self.formant_timbre_label_batch.setVisible(state == Qt.CheckState.Checked.value)); self.formant_shifting_checkbox_batch.stateChanged.connect(lambda state: self.formant_timbre_slider_batch.setVisible(state == Qt.CheckState.Checked.value))
        advanced_layout_batch.addWidget(QLabel(self.tr("Embedder Model:")), 7, 0); self.embedder_model_combo_batch = QComboBox(); self.embedder_model_combo_batch.addItems(["contentvec", "chinese-hubert-base", "japanese-hubert-base", "korean-hubert-base", "custom"]); self.embedder_model_combo_batch.setCurrentText("contentvec"); self.embedder_model_combo_batch.currentTextChanged.connect(self.toggle_custom_embedder_visibility_batch); advanced_layout_batch.addWidget(self.embedder_model_combo_batch, 7, 1)
        self.custom_embedder_group_batch = QGroupBox(self.tr("Custom Embedder")); self.custom_embedder_group_batch.setVisible(False); custom_embedder_layout_batch = QGridLayout(self.custom_embedder_group_batch); custom_embedder_layout_batch.addWidget(QLabel(self.tr("Select Custom Embedder:")), 0, 0); self.embedder_model_custom_combo_batch = QComboBox(); self.refresh_embedder_folders_batch(); custom_embedder_layout_batch.addWidget(self.embedder_model_custom_combo_batch, 0, 1); self.refresh_embedders_button_batch = QPushButton(self.tr("Refresh")); self.refresh_embedders_button_batch.clicked.connect(self.refresh_embedder_folders_batch); custom_embedder_layout_batch.addWidget(self.refresh_embedders_button_batch, 0, 2); advanced_layout_batch.addWidget(self.custom_embedder_group_batch, 8, 0, 1, 6)
        advanced_layout_batch.addWidget(QLabel(self.tr("F0 File Folder (Optional):")), 9, 0); self.f0_folder_edit_batch = QLineEdit(); self.f0_folder_edit_batch.setPlaceholderText(self.tr("Path to folder containing .f0 files (optional)")); advanced_layout_batch.addWidget(self.f0_folder_edit_batch, 9, 1, 1, 4); self.f0_folder_browse_button_batch = QPushButton(self.tr("Browse...")); self.f0_folder_browse_button_batch.clicked.connect(self.browse_f0_folder_batch); advanced_layout_batch.addWidget(self.f0_folder_browse_button_batch, 9, 5)

        # --- Post-Process Effects Section (Conditional) ---
        self.post_process_group_batch = QGroupBox(self.tr("Post-Process Effects")); self.post_process_group_batch.setVisible(False); post_process_layout_batch = QGridLayout(self.post_process_group_batch)
        self.setup_post_process_ui(post_process_layout_batch, is_batch=True) # Call helper for batch tab
        advanced_layout_batch.addWidget(self.post_process_group_batch, 10, 0, 1, 6) # Add group to batch advanced layout

        batch_tab_layout.addWidget(advanced_settings_group_batch)

        # Add spacer
        batch_tab_layout.addSpacerItem(QSpacerItem(20, 40, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Expanding))

        # --- Preset Section (Batch) ---
        preset_group_batch = QGroupBox(self.tr("Presets"))
        preset_layout_batch = QGridLayout(preset_group_batch)
        preset_layout_batch.addWidget(QLabel(self.tr("Load Preset:")), 0, 0)
        self.preset_combo_batch = QComboBox(); preset_layout_batch.addWidget(self.preset_combo_batch, 0, 1)
        self.load_preset_button_batch = QPushButton(self.tr("Load")); self.load_preset_button_batch.clicked.connect(self.load_preset_settings_batch); preset_layout_batch.addWidget(self.load_preset_button_batch, 0, 2)
        self.refresh_presets_button_batch = QPushButton(self.tr("Refresh")); self.refresh_presets_button_batch.clicked.connect(self.load_presets_batch); preset_layout_batch.addWidget(self.refresh_presets_button_batch, 0, 3)
        preset_layout_batch.addWidget(QLabel(self.tr("Save Preset As:")), 1, 0)
        self.save_preset_name_edit_batch = QLineEdit(); self.save_preset_name_edit_batch.setPlaceholderText(self.tr("Enter preset name")); preset_layout_batch.addWidget(self.save_preset_name_edit_batch, 1, 1)
        self.save_preset_button_batch = QPushButton(self.tr("Save")); self.save_preset_button_batch.clicked.connect(self.save_preset_settings_batch); preset_layout_batch.addWidget(self.save_preset_button_batch, 1, 2)
        batch_tab_layout.insertWidget(0, preset_group_batch) # Insert at the top

    # --- Helper to create post-process UI ---
    def setup_post_process_ui(self, layout, is_batch=False):
        """Creates the UI elements for post-processing effects."""
        prefix = "batch_" if is_batch else ""

        # Store widgets in dictionaries for easier access
        self.pp_checkboxes = {}
        self.pp_widgets = {} # Holds dicts of widgets per effect

        # Helper function to create label and slider/spinbox pairs
        def create_param_widget(effect_name, param_name, label_text, widget_type, range_min, range_max, default_val, decimals=2, step=0.1):
            container = QWidget()
            hbox = QHBoxLayout(container)
            hbox.setContentsMargins(0,0,0,0)
            label = QLabel(self.tr(label_text))
            if widget_type == QSlider:
                # Scale float ranges to integer sliders (e.g., 0.0-1.0 -> 0-100)
                scale = 10**decimals
                widget = QSlider(Qt.Orientation.Horizontal)
                widget.setRange(int(range_min * scale), int(range_max * scale))
                widget.setValue(int(default_val * scale))
                # Add a dynamic label to show the float value
                value_label = QLabel(f"{default_val:.{decimals}f}")
                widget.valueChanged.connect(lambda val, lbl=value_label, s=scale: lbl.setText(f"{val/s:.{decimals}f}"))
                hbox.addWidget(label)
                hbox.addWidget(widget)
                hbox.addWidget(value_label)
            elif widget_type == QDoubleSpinBox:
                widget = QDoubleSpinBox()
                widget.setRange(range_min, range_max)
                widget.setDecimals(decimals)
                widget.setSingleStep(step)
                widget.setValue(default_val)
                hbox.addWidget(label)
                hbox.addWidget(widget)
            elif widget_type == QSpinBox:
                widget = QSpinBox()
                widget.setRange(range_min, range_max)
                widget.setValue(default_val)
                hbox.addWidget(label)
                hbox.addWidget(widget)
            else: # Fallback for unexpected type
                widget = QLabel("Unsupported widget type")
                hbox.addWidget(label)
                hbox.addWidget(widget)

            container.setVisible(False) # Initially hidden
            self.pp_widgets[effect_name][param_name] = {"container": container, "widget": widget}
            return container

        # --- Define Effects and Parameters ---
        effects = {
            "reverb": [("room_size", "Room Size:", QSlider, 0.0, 1.0, 0.5), ("damping", "Damping:", QSlider, 0.0, 1.0, 0.5),
                       ("wet_gain", "Wet Gain:", QSlider, 0.0, 1.0, 0.33), ("dry_gain", "Dry Gain:", QSlider, 0.0, 1.0, 0.4),
                       ("width", "Width:", QSlider, 0.0, 1.0, 1.0), ("freeze_mode", "Freeze:", QSlider, 0.0, 1.0, 0.0)],
            "pitch_shift": [("semitones", "Semitones:", QDoubleSpinBox, -24.0, 24.0, 0.0, 1, 0.5)],
            "limiter": [("threshold", "Threshold (dB):", QDoubleSpinBox, -60.0, 0.0, -6.0, 1, 1.0),
                        ("release_time", "Release (s):", QDoubleSpinBox, 0.01, 1.0, 0.05, 2, 0.01)],
            "gain": [("db", "Gain (dB):", QDoubleSpinBox, -60.0, 60.0, 0.0, 1, 1.0)],
            "distortion": [("gain", "Drive:", QDoubleSpinBox, 0.0, 100.0, 25.0, 1, 1.0)],
            "chorus": [("rate", "Rate (Hz):", QDoubleSpinBox, 0.1, 10.0, 1.0, 1, 0.1), ("depth", "Depth:", QSlider, 0.0, 1.0, 0.25),
                       ("center_delay", "Delay (ms):", QDoubleSpinBox, 1.0, 20.0, 7.0, 1, 0.5), ("feedback", "Feedback:", QSlider, 0.0, 1.0, 0.0),
                       ("mix", "Mix:", QSlider, 0.0, 1.0, 0.5)],
            "bitcrush": [("bit_depth", "Bit Depth:", QSpinBox, 1, 16, 8)],
            "clipping": [("threshold", "Threshold (dB):", QDoubleSpinBox, -60.0, 0.0, -6.0, 1, 1.0)],
            "compressor": [("threshold", "Threshold (dB):", QDoubleSpinBox, -60.0, 0.0, 0.0, 1, 1.0), ("ratio", "Ratio:", QDoubleSpinBox, 1.0, 20.0, 1.0, 1, 0.5),
                           ("attack", "Attack (ms):", QDoubleSpinBox, 0.1, 100.0, 1.0, 1, 0.5), ("release", "Release (ms):", QDoubleSpinBox, 1.0, 1000.0, 100.0, 0, 10)],
            "delay": [("seconds", "Time (s):", QDoubleSpinBox, 0.01, 5.0, 0.5, 2, 0.01), ("feedback", "Feedback:", QSlider, 0.0, 1.0, 0.0),
                      ("mix", "Mix:", QSlider, 0.0, 1.0, 0.5)],
        }

        row, col = 0, 0
        max_cols = 3 # Adjust layout columns
        for effect_key, params in effects.items():
            checkbox = QCheckBox(self.tr(effect_key.replace("_", " ").title()))
            layout.addWidget(checkbox, row, col)
            setattr(self, f"{prefix}{effect_key}_checkbox", checkbox) # Store checkbox reference
            self.pp_checkboxes[effect_key] = checkbox
            self.pp_widgets[effect_key] = {} # Initialize dict for this effect's widgets

            param_widgets = []
            for param_key, label, w_type, r_min, r_max, d_val, *extra_args in params:
                param_widget = create_param_widget(effect_key, param_key, label, w_type, r_min, r_max, d_val, *extra_args)
                param_widgets.append(param_widget)
                layout.addWidget(param_widget, row + 1 + params.index((param_key, label, w_type, r_min, r_max, d_val, *extra_args)), col, 1, max_cols) # Span across columns below checkbox

            # Connect checkbox to toggle visibility of its parameter widgets
            checkbox.stateChanged.connect(lambda state, widgets=param_widgets: [w.setVisible(state == Qt.CheckState.Checked.value) for w in widgets])

            col += 1
            if col >= max_cols:
                col = 0
                # Find the max row used by the previous effect's params to start the next row
                max_param_row = row + len(params)
                row = max_param_row + 1 # Start next effect below the params of the previous one

    # --- Common Methods ---
    def toggle_post_process_visibility(self, state):
        """Shows/hides the post-process effects group."""
        is_visible = state == Qt.CheckState.Checked.value
        self.post_process_group.setVisible(is_visible)
        # Ensure individual param visibility respects checkboxes when group becomes visible
        if is_visible:
            for effect, widgets_dict in self.pp_widgets.items():
                is_effect_checked = self.pp_checkboxes[effect].isChecked()
                for param_data in widgets_dict.values():
                    param_data["container"].setVisible(is_effect_checked)

    def toggle_post_process_visibility_batch(self, state):
        """Shows/hides the post-process effects group for the batch tab."""
        is_visible = state == Qt.CheckState.Checked.value
        self.post_process_group_batch.setVisible(is_visible)
        # Similar logic for batch tab widgets if needed (assuming mirrored structure)
        # This requires storing batch widgets separately or passing the prefix
        # For now, assuming structure is mirrored and widgets are named with _batch suffix
        if is_visible:
             # Or refactor setup_post_process_ui to handle prefixes and store widgets accordingly
             # For now, assume the setup function correctly handles the 'is_batch' flag
             # to access the correct widgets (e.g., using getattr or storing them differently)
             # This requires the setup_post_process_ui to be robust.
             pass # Placeholder - Requires verification of setup_post_process_ui logic

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
            })
            # Add batch post-process params if enabled
            if params["post_process"]:
                 # Assuming batch widgets mirror single tab names with _batch suffix
                 # This needs refinement based on how setup_post_process_ui stores batch widgets
                 params.update({
                     "reverb": getattr(self, "batch_reverb_checkbox", QCheckBox()).isChecked(),
                     # ... add all other effect checkboxes ...
                     "reverb_room_size": getattr(self, "batch_reverb_room_size_slider", QSlider()).value() / 100.0, # Example
                     # ... add all other effect parameters ...
                 })
                 print("Warning: Gathering batch post-process params not fully implemented.")


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
             })
             # Add single post-process params if enabled
             if params["post_process"]:
                 for effect, widgets in self.pp_widgets.items():
                     checkbox = self.pp_checkboxes.get(effect)
                     if checkbox and checkbox.isChecked():
                         params[effect] = True # Enable the effect
                         for param, data in widgets.items():
                             widget = data["widget"]
                             param_key = f"{effect}_{param}" # e.g., reverb_room_size
                             if isinstance(widget, QSlider):
                                 # Find the scale based on decimals used during creation (default 2)
                                 decimals = 2 # Assuming default scale
                                 scale = 10**decimals
                                 params[param_key] = widget.value() / scale
                             elif isinstance(widget, (QDoubleSpinBox, QSpinBox)):
                                 params[param_key] = widget.value()
                     else:
                         params[effect] = False # Ensure effect is marked false if checkbox off

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

    # --- Preset Handling Methods ---
    def load_presets(self, is_batch=False):
        """Loads preset files into the appropriate combo box."""
        combo = self.preset_combo_batch if is_batch else self.preset_combo
        combo.clear()
        combo.addItem(self.tr("Select a preset..."), userData=None)
        try:
            if not os.path.exists(PRESETS_DIR):
                os.makedirs(PRESETS_DIR)
            presets = [f for f in os.listdir(PRESETS_DIR) if f.lower().endswith(".json")]
            if presets:
                combo.addItems(sorted([os.path.splitext(p)[0] for p in presets]))
            else:
                combo.addItem(self.tr("No presets found"))
                combo.setEnabled(False)
        except Exception as e:
            print(f"Error loading presets: {e}")
            combo.addItem(self.tr("Error loading presets"))
            combo.setEnabled(False)

    def load_presets_batch(self):
        self.load_presets(is_batch=True)

    def load_preset_settings(self, is_batch=False):
        """Loads settings from the selected preset file."""
        combo = self.preset_combo_batch if is_batch else self.preset_combo
        preset_name = combo.currentText()
        if not preset_name or preset_name == self.tr("Select a preset...") or preset_name == self.tr("No presets found") or preset_name == self.tr("Error loading presets"):
            return

        preset_path = os.path.join(PRESETS_DIR, f"{preset_name}.json")
        if not os.path.exists(preset_path):
            QMessageBox.warning(self, self.tr("Load Error"), self.tr("Preset file not found: {0}").format(preset_path))
            self.load_presets(is_batch) # Refresh list if file missing
            return

        try:
            with open(preset_path, 'r', encoding='utf-8') as f:
                settings = json.load(f)

            # Apply settings to UI elements (handle potential missing keys)
            prefix = "batch_" if is_batch else ""
            
            # Basic Sliders
            getattr(self, f"{prefix}pitch_slider", QSlider()).setValue(settings.get("pitch", 0))
            getattr(self, f"{prefix}index_rate_slider", QSlider()).setValue(int(settings.get("index_rate", 0.75) * 100))
            getattr(self, f"{prefix}rms_mix_rate_slider", QSlider()).setValue(int(settings.get("rms_mix_rate", 1.0) * 100))
            getattr(self, f"{prefix}protect_slider", QSlider()).setValue(int(settings.get("protect", 0.5) * 100))

            # Advanced Settings
            getattr(self, f"{prefix}f0_method_combo", QComboBox()).setCurrentText(settings.get("f0_method", "rmvpe"))
            # SID needs model context, cannot be reliably set from preset alone
            getattr(self, f"{prefix}export_format_combo", QComboBox()).setCurrentText(settings.get("export_format", "WAV"))
            getattr(self, f"{prefix}split_audio_checkbox", QCheckBox()).setChecked(settings.get("split_audio", False))
            getattr(self, f"{prefix}autotune_checkbox", QCheckBox()).setChecked(settings.get("f0_autotune", False))
            getattr(self, f"{prefix}autotune_strength_slider", QSlider()).setValue(int(settings.get("f0_autotune_strength", 1.0) * 100))
            getattr(self, f"{prefix}clean_audio_checkbox", QCheckBox()).setChecked(settings.get("clean_audio", False))
            getattr(self, f"{prefix}clean_strength_slider", QSlider()).setValue(int(settings.get("clean_strength", 0.5) * 100))
            getattr(self, f"{prefix}formant_shifting_checkbox", QCheckBox()).setChecked(settings.get("formant_shifting", False))
            getattr(self, f"{prefix}formant_qfrency_slider", QSlider()).setValue(int(settings.get("formant_qfrency", 1.0) * 10))
            getattr(self, f"{prefix}formant_timbre_slider", QSlider()).setValue(int(settings.get("formant_timbre", 1.0) * 10))
            getattr(self, f"{prefix}embedder_model_combo", QComboBox()).setCurrentText(settings.get("embedder_model", "contentvec"))
            # Custom embedder path cannot be set directly, user needs to select if 'custom' is loaded
            
            # Post-Process Settings
            getattr(self, f"{prefix}post_process_checkbox", QCheckBox()).setChecked(settings.get("post_process", False))
            if settings.get("post_process", False):
                 for effect, widgets in self.pp_widgets.items(): # Assuming pp_widgets is shared or handled by prefix
                     checkbox = getattr(self, f"{prefix}{effect}_checkbox", QCheckBox())
                     is_effect_enabled = settings.get(effect, False)
                     checkbox.setChecked(is_effect_enabled)
                     if is_effect_enabled:
                         for param, data in widgets.items():
                             widget = data["widget"]
                             param_key = f"{effect}_{param}"
                             value = settings.get(param_key) # Get saved value
                             if value is not None:
                                 if isinstance(widget, QSlider):
                                     decimals = 2 # Assume default scale
                                     scale = 10**decimals
                                     widget.setValue(int(value * scale))
                                 elif isinstance(widget, (QDoubleSpinBox, QSpinBox)):
                                     widget.setValue(value)

            self.update_status(self.tr("Preset '{0}' loaded.").format(preset_name))

        except json.JSONDecodeError:
            QMessageBox.critical(self, self.tr("Load Error"), self.tr("Failed to decode preset file: {0}").format(preset_path))
        except Exception as e:
            QMessageBox.critical(self, self.tr("Load Error"), self.tr("Error applying preset settings: {0}").format(e))
            print(f"Error applying preset '{preset_name}': {e}\n{traceback.format_exc()}")

    def load_preset_settings_batch(self):
        self.load_preset_settings(is_batch=True)

    def save_preset_settings(self, is_batch=False):
        """Saves the current settings to a preset file."""
        prefix = "batch_" if is_batch else ""
        name_edit = getattr(self, f"{prefix}save_preset_name_edit", QLineEdit())
        preset_name = name_edit.text().strip()

        if not preset_name:
            QMessageBox.warning(self, self.tr("Save Error"), self.tr("Please enter a name for the preset."))
            return

        # Basic validation for filename
        if not all(c.isalnum() or c in ('_', '-') for c in preset_name):
             QMessageBox.warning(self, self.tr("Save Error"), self.tr("Preset name can only contain letters, numbers, underscores, and hyphens."))
             return

        preset_path = os.path.join(PRESETS_DIR, f"{preset_name}.json")

        if os.path.exists(preset_path):
            reply = QMessageBox.question(self, self.tr("Overwrite Preset"),
                                         self.tr("Preset '{0}' already exists. Overwrite?").format(preset_name),
                                         QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                                         QMessageBox.StandardButton.No)
            if reply == QMessageBox.StandardButton.No:
                return

        # Gather settings from UI
        settings = {}
        try:
            # Basic Sliders
            settings["pitch"] = getattr(self, f"{prefix}pitch_slider", QSlider()).value()
            settings["index_rate"] = getattr(self, f"{prefix}index_rate_slider", QSlider()).value() / 100.0
            settings["rms_mix_rate"] = getattr(self, f"{prefix}rms_mix_rate_slider", QSlider()).value() / 100.0
            settings["protect"] = getattr(self, f"{prefix}protect_slider", QSlider()).value() / 100.0

            # Advanced Settings
            settings["f0_method"] = getattr(self, f"{prefix}f0_method_combo", QComboBox()).currentText()
            settings["export_format"] = getattr(self, f"{prefix}export_format_combo", QComboBox()).currentText()
            settings["split_audio"] = getattr(self, f"{prefix}split_audio_checkbox", QCheckBox()).isChecked()
            settings["f0_autotune"] = getattr(self, f"{prefix}autotune_checkbox", QCheckBox()).isChecked()
            settings["f0_autotune_strength"] = getattr(self, f"{prefix}autotune_strength_slider", QSlider()).value() / 100.0
            settings["clean_audio"] = getattr(self, f"{prefix}clean_audio_checkbox", QCheckBox()).isChecked()
            settings["clean_strength"] = getattr(self, f"{prefix}clean_strength_slider", QSlider()).value() / 100.0
            settings["formant_shifting"] = getattr(self, f"{prefix}formant_shifting_checkbox", QCheckBox()).isChecked()
            settings["formant_qfrency"] = getattr(self, f"{prefix}formant_qfrency_slider", QSlider()).value() / 10.0
            settings["formant_timbre"] = getattr(self, f"{prefix}formant_timbre_slider", QSlider()).value() / 10.0
            settings["embedder_model"] = getattr(self, f"{prefix}embedder_model_combo", QComboBox()).currentText()
            # Do not save custom embedder path, only the 'custom' selection

            # Post-Process Settings
            settings["post_process"] = getattr(self, f"{prefix}post_process_checkbox", QCheckBox()).isChecked()
            if settings["post_process"]:
                 for effect, widgets in self.pp_widgets.items(): # Assuming pp_widgets is shared or handled by prefix
                     checkbox = getattr(self, f"{prefix}{effect}_checkbox", QCheckBox())
                     settings[effect] = checkbox.isChecked()
                     if settings[effect]:
                         for param, data in widgets.items():
                             widget = data["widget"]
                             param_key = f"{effect}_{param}"
                             if isinstance(widget, QSlider):
                                 decimals = 2 # Assume default scale
                                 scale = 10**decimals
                                 settings[param_key] = widget.value() / scale
                             elif isinstance(widget, (QDoubleSpinBox, QSpinBox)):
                                 settings[param_key] = widget.value()

            # Write to JSON file
            with open(preset_path, 'w', encoding='utf-8') as f:
                json.dump(settings, f, indent=4)

            self.update_status(self.tr("Preset '{0}' saved.").format(preset_name))
            self.load_presets(is_batch) # Refresh the list
            # Select the newly saved preset
            combo = self.preset_combo_batch if is_batch else self.preset_combo
            index = combo.findText(preset_name)
            if index >= 0:
                combo.setCurrentIndex(index)

        except Exception as e:
            QMessageBox.critical(self, self.tr("Save Error"), self.tr("Error saving preset: {0}").format(e))
            print(f"Error saving preset '{preset_name}': {e}\n{traceback.format_exc()}")

    def save_preset_settings_batch(self):
        self.save_preset_settings(is_batch=True)
