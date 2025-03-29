from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QGridLayout, 
                             QSlider, QComboBox, QLineEdit, QMessageBox, QApplication, 
                             QSizePolicy, QSpacerItem, QGroupBox) # Added QGroupBox
from PyQt6.QtCore import Qt, QThread, pyqtSignal
import os
import sys
import traceback

# Ensure the core Applio logic can be imported
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

# Import core functions
from core import run_model_blender_script
# Import helper functions/constants from inference tab for reuse
from desktop_ui.tabs.inference_tab import MODEL_ROOT, InferenceTab # Import class to reuse methods

class VoiceBlenderWorker(QThread):
    """Worker thread for blending models."""
    status = pyqtSignal(str)
    finished = pyqtSignal(str, str) # message, output_model_path
    error = pyqtSignal(str)

    def __init__(self, params):
        super().__init__()
        self.params = params
        self._is_running = True # Added for potential cancellation later

    def run(self):
        """Execute the model blending task."""
        try:
            self.status.emit("Starting model blending...")
            
            # Map UI params to core function params
            core_params = {
                "model_name": self.params.get("model_name"),
                "pth_path_1": self.params.get("pth_path_1"),
                "pth_path_2": self.params.get("pth_path_2"),
                "ratio": self.params.get("ratio", 0.5),
            }
            core_params = {k: v for k, v in core_params.items() if v is not None}

            # --- Actual Call ---
            message, output_path = run_model_blender_script(**core_params)
            # --- End Actual Call ---

            if self._is_running:
                self.status.emit(message)
                self.finished.emit(message, output_path)
        except Exception as e:
            error_str = f"Blending Error: {e}\n{traceback.format_exc()}"
            self.error.emit(error_str)
        finally:
            if self._is_running: 
                self.status.emit("Idle")

    def stop(self): # Added stop method
        self._is_running = False
        self.status.emit("Cancelling blending...")


class VoiceBlenderTab(QWidget):
    """Widget for the Voice Blender Tab."""
    def __init__(self):
        super().__init__()
        self.worker = None
        # Create an instance of InferenceTab to reuse its methods/widgets
        self._inference_tab_helpers = InferenceTab() 
        self.setup_ui()
        self.refresh_models() # Initial population

    def setup_ui(self):
        main_layout = QVBoxLayout(self)

        # --- Model Selection ---
        model_select_group = QGroupBox("Select Models to Blend")
        model_select_layout = QGridLayout(model_select_group)

        model_select_layout.addWidget(QLabel("Model A:"), 0, 0)
        self.model_a_combo = QComboBox()
        self.model_a_combo.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        model_select_layout.addWidget(self.model_a_combo, 0, 1)

        model_select_layout.addWidget(QLabel("Model B:"), 1, 0)
        self.model_b_combo = QComboBox()
        self.model_b_combo.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        model_select_layout.addWidget(self.model_b_combo, 1, 1)

        refresh_button = QPushButton("Refresh Models")
        refresh_button.clicked.connect(self.refresh_models)
        model_select_layout.addWidget(refresh_button, 0, 2, 2, 1) # Span 2 rows

        main_layout.addWidget(model_select_group)

        # --- Blend Settings ---
        blend_settings_group = QGroupBox("Blend Settings")
        blend_settings_layout = QGridLayout(blend_settings_group)

        self.ratio_label = QLabel("Blend Ratio (0.50):")
        blend_settings_layout.addWidget(self.ratio_label, 0, 0)
        self.ratio_slider = QSlider(Qt.Orientation.Horizontal)
        self.ratio_slider.setRange(0, 100) # 0.0 to 1.0
        self.ratio_slider.setValue(50)
        self.ratio_slider.valueChanged.connect(lambda val: self.ratio_label.setText(f"Blend Ratio ({val/100.0:.2f}):"))
        blend_settings_layout.addWidget(self.ratio_slider, 0, 1)

        blend_settings_layout.addWidget(QLabel("New Model Name:"), 1, 0)
        self.output_name_edit = QLineEdit()
        self.output_name_edit.setPlaceholderText("Enter name for the blended model (e.g., ModelA_ModelB_50)")
        blend_settings_layout.addWidget(self.output_name_edit, 1, 1)

        main_layout.addWidget(blend_settings_group)

        # --- Action Button & Status ---
        action_status_group = QWidget()
        action_status_layout = QVBoxLayout(action_status_group)
        action_status_layout.setContentsMargins(0,10,0,0)

        self.blend_button = QPushButton("Blend Models")
        self.blend_button.clicked.connect(self.start_blending)
        action_status_layout.addWidget(self.blend_button)

        self.status_label = QLabel("Status: Idle")
        action_status_layout.addWidget(self.status_label)
        
        main_layout.addWidget(action_status_group)

        # Add spacer
        main_layout.addSpacerItem(QSpacerItem(20, 40, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Expanding))

        self.setLayout(main_layout)

    def refresh_models(self):
        """Refreshes the model dropdowns."""
        # Use the helper method, but apply to both combos
        self._inference_tab_helpers.refresh_models_and_indexes() 
        # Clear and repopulate our specific combos using the helper's combo items
        self.model_a_combo.clear()
        self.model_b_combo.clear()
        for i in range(self._inference_tab_helpers.model_combo.count()):
            text = self._inference_tab_helpers.model_combo.itemText(i)
            data = self._inference_tab_helpers.model_combo.itemData(i)
            self.model_a_combo.addItem(text, userData=data)
            self.model_b_combo.addItem(text, userData=data)
        
        # Reset index if possible
        if self.model_a_combo.count() > 0:
            self.model_a_combo.setCurrentIndex(0)
        if self.model_b_combo.count() > 1:
            self.model_b_combo.setCurrentIndex(1) # Default to second model if available
        elif self.model_b_combo.count() > 0:
             self.model_b_combo.setCurrentIndex(0)


    def start_blending(self):
        """Starts the model blending process."""
        if self.worker and self.worker.isRunning():
            QMessageBox.warning(self, "Process Running", "A blending process is already running.")
            return

        # --- Gather parameters ---
        model_a_path = self.model_a_combo.currentData()
        model_b_path = self.model_b_combo.currentData()
        output_name = self.output_name_edit.text().strip()
        ratio = self.ratio_slider.value() / 100.0

        # --- Validate parameters ---
        if not model_a_path or not model_b_path:
            QMessageBox.warning(self, "Input Error", "Please select both Model A and Model B.")
            return
        if model_a_path == model_b_path:
             QMessageBox.warning(self, "Input Error", "Please select two different models to blend.")
             return
        if not output_name:
            QMessageBox.warning(self, "Input Error", "Please enter a name for the new blended model.")
            return
        # Basic check for invalid characters in name (OS might handle more complex cases)
        if any(c in output_name for c in r'/\:*?"<>|'):
             QMessageBox.warning(self, "Input Error", "Model name contains invalid characters.")
             return

        params = {
            "model_name": output_name,
            "pth_path_1": model_a_path,
            "pth_path_2": model_b_path,
            "ratio": ratio,
        }

        # --- Start worker thread ---
        self.blend_button.setEnabled(False)
        self.status_label.setText("Status: Blending...")

        self.worker = VoiceBlenderWorker(params)
        self.worker.status.connect(self.update_status)
        self.worker.finished.connect(self.on_blending_finished)
        self.worker.error.connect(self.on_blending_error)
        self.worker.finished.connect(lambda msg, path: self.reset_ui_state())
        self.worker.error.connect(lambda err_msg: self.reset_ui_state())
        self.worker.start()

    def reset_ui_state(self):
        """Re-enables button after task completion or error."""
        self.blend_button.setEnabled(True)
        self.status_label.setText("Status: Idle") # Reset status too

    def update_status(self, message):
        self.status_label.setText(f"Status: {message}")

    def on_blending_finished(self, message, output_model_path):
        self.update_status(f"Finished: {message}")
        QMessageBox.information(self, "Blending Complete", f"{message}\nOutput saved to:\n{output_model_path}")
        print(f"Blended model saved to: {output_model_path}")
        self.refresh_models() # Refresh dropdowns to include the new model

    def on_blending_error(self, error_message):
        self.update_status("Error occurred")
        QMessageBox.critical(self, "Blending Error", f"An error occurred:\n{error_message}")
        print(f"Error details:\n{error_message}")
