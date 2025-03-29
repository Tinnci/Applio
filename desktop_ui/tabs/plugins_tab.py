from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QGridLayout, 
                             QLineEdit, QFileDialog, QMessageBox, QApplication, QSizePolicy, 
                             QSpacerItem, QGroupBox, QListWidget) # Added QListWidget
from PyQt6.QtCore import Qt, QThread, pyqtSignal
import os
import sys
import traceback
import zipfile
import shutil
import subprocess
import json

# Ensure the core Applio logic can be imported
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

# Define paths
PLUGINS_INSTALL_DIR = os.path.join(project_root, "tabs", "plugins", "installed")
CONFIG_PATH = os.path.join(project_root, "assets", "config.json")
VENV_PYTHON = os.path.join(project_root, ".venv", "Scripts", "python.exe") # Adjust for non-Windows if needed

# Ensure plugins directory exists
os.makedirs(PLUGINS_INSTALL_DIR, exist_ok=True)

class PluginInstallWorker(QThread):
    """Worker thread for installing plugins."""
    status = pyqtSignal(str)
    finished = pyqtSignal(str, str) # message, plugin_name
    error = pyqtSignal(str)

    def __init__(self, zip_file_path):
        super().__init__()
        self.zip_file_path = zip_file_path
        self._is_running = True

    def run(self):
        """Extracts zip, installs requirements."""
        plugin_name = os.path.basename(self.zip_file_path).replace(".zip", "")
        extract_path = os.path.join(PLUGINS_INSTALL_DIR, plugin_name)
        
        try:
            self.status.emit(f"Extracting {plugin_name}...")
            
            # Ensure target directory doesn't exist or is empty
            if os.path.exists(extract_path):
                 self.status.emit(f"Removing existing folder: {plugin_name}")
                 shutil.rmtree(extract_path)
                 
            with zipfile.ZipFile(self.zip_file_path, 'r') as zip_ref:
                zip_ref.extractall(PLUGINS_INSTALL_DIR)
            self.status.emit("Extraction complete.")

            # Install requirements if they exist
            req_file = os.path.join(extract_path, "requirements.txt")
            if os.path.exists(req_file):
                self.status.emit(f"Installing requirements for {plugin_name}...")
                # Use uv pip install if available, otherwise fallback to venv pip
                # For simplicity, using venv pip directly for now
                if not os.path.exists(VENV_PYTHON):
                     raise FileNotFoundError("Virtual environment Python not found. Cannot install requirements.")
                     
                # Command execution might need adjustments based on OS/environment
                # Using shell=True might be needed depending on path issues, but less secure
                process = subprocess.run(
                    [VENV_PYTHON, "-m", "pip", "install", "-r", req_file],
                    capture_output=True, text=True, check=False, # Don't check=True, handle errors manually
                    cwd=project_root # Run from project root
                ) 
                if process.returncode != 0:
                    error_details = f"pip install failed with code {process.returncode}\nstdout:\n{process.stdout}\nstderr:\n{process.stderr}"
                    raise RuntimeError(f"Failed to install requirements for {plugin_name}.\n{error_details}")
                self.status.emit("Requirements installed.")
            else:
                self.status.emit("No requirements.txt found.")

            # Update config.json (optional but matches original logic)
            self.update_config(plugin_name)

            message = f"Plugin '{plugin_name}' installed successfully."
            self.finished.emit(message, plugin_name)

        except Exception as e:
            error_str = f"Installation Error for {plugin_name}: {e}\n{traceback.format_exc()}"
            self.error.emit(error_str)
            # Clean up extracted folder on error? Maybe not, user might want to inspect.
        finally:
            # Clean up the original zip file? Original script did this.
            # try:
            #     if os.path.exists(self.zip_file_path): os.remove(self.zip_file_path)
            # except OSError as e:
            #     print(f"Warning: Could not remove zip file {self.zip_file_path}: {e}")
            if self._is_running:
                self.status.emit("Idle")

    def update_config(self, plugin_name):
        """Adds the plugin name to the config file."""
        try:
            config = {}
            if os.path.exists(CONFIG_PATH):
                with open(CONFIG_PATH, 'r', encoding='utf-8') as f:
                    config = json.load(f)
            
            if "plugins" not in config:
                config["plugins"] = []
                
            if plugin_name not in config["plugins"]:
                config["plugins"].append(plugin_name)
                
                with open(CONFIG_PATH, 'w', encoding='utf-8') as f:
                    json.dump(config, f, indent=2)
                self.status.emit(f"Updated config for {plugin_name}.")
            else:
                 self.status.emit(f"Config already contains {plugin_name}.")

        except Exception as e:
            print(f"Warning: Could not update config file for plugin {plugin_name}: {e}")
            # Don't emit error signal for config update failure, it's non-critical

    def stop(self):
        self._is_running = False
        self.status.emit("Cancelling installation...")
        # TODO: Implement cancellation (tricky for subprocess/extraction)


class PluginsTab(QWidget):
    """Widget for the Plugins Tab."""
    def __init__(self):
        super().__init__()
        self.worker = None
        self.setup_ui()
        self.refresh_plugin_list() # Load initial list

    def setup_ui(self):
        main_layout = QVBoxLayout(self)

        # --- Install Plugin Section ---
        install_group = QGroupBox("Install Plugin")
        install_layout = QGridLayout(install_group)

        self.install_button = QPushButton("Install Plugin from .zip...")
        self.install_button.clicked.connect(self.select_and_install_plugin)
        install_layout.addWidget(self.install_button, 0, 0)

        self.install_status_label = QLabel("Status: Idle")
        install_layout.addWidget(self.install_status_label, 1, 0)

        main_layout.addWidget(install_group)

        # --- Installed Plugins Section ---
        list_group = QGroupBox("Installed Plugins")
        list_layout = QVBoxLayout(list_group) # Use QVBoxLayout

        self.plugin_list_widget = QListWidget()
        list_layout.addWidget(self.plugin_list_widget)

        refresh_button = QPushButton("Refresh List")
        refresh_button.clicked.connect(self.refresh_plugin_list)
        list_layout.addWidget(refresh_button)

        main_layout.addWidget(list_group)

        # Add spacer
        main_layout.addSpacerItem(QSpacerItem(20, 40, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Expanding))

        self.setLayout(main_layout)

    def refresh_plugin_list(self):
        """Scans the plugin directory and updates the list widget."""
        self.plugin_list_widget.clear()
        try:
            if os.path.exists(PLUGINS_INSTALL_DIR):
                for item in os.listdir(PLUGINS_INSTALL_DIR):
                    if os.path.isdir(os.path.join(PLUGINS_INSTALL_DIR, item)):
                        self.plugin_list_widget.addItem(item)
            else:
                 self.plugin_list_widget.addItem("Plugin directory not found.")
        except Exception as e:
            print(f"Error refreshing plugin list: {e}")
            self.plugin_list_widget.addItem("Error listing plugins.")


    def select_and_install_plugin(self):
        """Opens file dialog to select zip and starts installation."""
        if self.worker and self.worker.isRunning():
            QMessageBox.warning(self, "Process Running", "An installation is already in progress.")
            return

        zip_path, _ = QFileDialog.getOpenFileName(self, "Select Plugin Zip File", project_root, "Zip Files (*.zip)")
        
        if zip_path:
            self.install_button.setEnabled(False)
            self.install_status_label.setText("Status: Starting installation...")

            self.worker = PluginInstallWorker(zip_path)
            self.worker.status.connect(self.update_install_status)
            self.worker.finished.connect(self.on_install_finished)
            self.worker.error.connect(self.on_install_error)
            self.worker.finished.connect(self.reset_install_ui_state) 
            self.worker.error.connect(self.reset_install_ui_state)
            self.worker.start()

    def reset_install_ui_state(self):
        """Re-enables button after task completion or error."""
        self.install_button.setEnabled(True)
        self.install_status_label.setText("Status: Idle") 

    def update_install_status(self, message):
        self.install_status_label.setText(f"Status: {message}")

    def on_install_finished(self, message, plugin_name):
        self.update_install_status(f"Finished: {message}")
        QMessageBox.information(self, "Installation Complete", f"{message}\nPlease restart Applio to load the new plugin.")
        self.refresh_plugin_list() # Update list

    def on_install_error(self, error_message):
        self.update_install_status("Error occurred")
        QMessageBox.critical(self, "Installation Error", f"An error occurred:\n{error_message}")
        print(f"Error details:\n{error_message}")
