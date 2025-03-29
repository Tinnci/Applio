from PyQt6.QtWidgets import QWidget, QVBoxLayout, QLabel, QComboBox, QCheckBox, QPushButton, QLineEdit
import os
import sys
import json

# Ensure the core Applio logic can be imported
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

# TODO: Import necessary functions for saving/loading settings, restarting, etc.
# from assets.themes import loadThemes # Example
# from assets.i18n import i18n # Example
# from core import restart_applio # Example

class SettingsTab(QWidget):
    """Widget for the Settings Tab."""
    def __init__(self):
        super().__init__()
        self.config_path = os.path.join(project_root, "assets", "config.json")
        self.setup_ui()
        self.load_settings()

    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.addWidget(QLabel("Settings Tab Content (Placeholder)"))

        # --- General Settings ---
        # Theme
        layout.addWidget(QLabel("Theme:"))
        self.theme_combo = QComboBox()
        # TODO: Populate themes from assets/themes/theme_list.json
        # self.theme_combo.addItems(loadThemes.get_theme_list()) # Example
        layout.addWidget(self.theme_combo)

        # Language
        layout.addWidget(QLabel("Language:"))
        self.language_combo = QComboBox()
        # TODO: Populate languages from assets/i18n/languages/
        # self.language_combo.addItems(["Auto Detect"] + i18n._get_available_languages()) # Example
        layout.addWidget(self.language_combo)

        # Discord Presence
        self.discord_checkbox = QCheckBox("Enable Discord Presence")
        layout.addWidget(self.discord_checkbox)

        # --- Training Settings ---
        layout.addWidget(QLabel("Model Author Name:"))
        self.author_edit = QLineEdit()
        layout.addWidget(self.author_edit)

        # --- Actions ---
        self.save_button = QPushButton("Save Settings & Restart")
        self.save_button.clicked.connect(self.save_and_restart)
        layout.addWidget(self.save_button)

        self.setLayout(layout)

    def load_settings(self):
        """Load settings from config.json"""
        try:
            with open(self.config_path, 'r', encoding='utf-8') as f:
                config = json.load(f)

            # TODO: Set UI elements based on loaded config
            # Example:
            # theme_file = config.get("theme", {}).get("file", "Applio.py")
            # theme_class = config.get("theme", {}).get("class", "Applio")
            # theme_name = f"{theme_file.replace('.py', '')}/{theme_class}" # Reconstruct name? Need better way
            # index = self.theme_combo.findText(theme_name) # Find based on reconstructed name
            # if index >= 0:
            #     self.theme_combo.setCurrentIndex(index)

            self.discord_checkbox.setChecked(config.get("discord_presence", False))
            self.author_edit.setText(config.get("model_author", ""))

            # lang_override = config.get("lang", {}).get("override", False)
            # selected_lang = config.get("lang", {}).get("selected_lang", "en_US")
            # lang_value = selected_lang if lang_override else "Auto Detect"
            # index = self.language_combo.findText(lang_value)
            # if index >= 0:
            #     self.language_combo.setCurrentIndex(index)

        except FileNotFoundError:
            print(f"Warning: Config file not found at {self.config_path}")
        except Exception as e:
            print(f"Error loading settings: {e}")

    def save_settings(self):
        """Save current UI settings to config.json"""
        try:
            # Read existing config first to preserve other settings
            try:
                with open(self.config_path, 'r', encoding='utf-8') as f:
                    config = json.load(f)
            except (FileNotFoundError, json.JSONDecodeError):
                config = {} # Start fresh if file doesn't exist or is invalid

            # Update config with current UI values
            # TODO: Get theme file/class based on combo selection
            # config["theme"] = {"file": "...", "class": "..."}

            config["discord_presence"] = self.discord_checkbox.isChecked()
            config["model_author"] = self.author_edit.text()

            # TODO: Handle language saving logic
            # selected_lang_text = self.language_combo.currentText()
            # if selected_lang_text == "Auto Detect":
            #     config["lang"] = {"override": False, "selected_lang": config.get("lang", {}).get("selected_lang", "en_US")}
            # else:
            #     config["lang"] = {"override": True, "selected_lang": selected_lang_text}


            with open(self.config_path, 'w', encoding='utf-8') as f:
                json.dump(config, f, indent=2)
            print("Settings saved successfully.")
            return True
        except Exception as e:
            print(f"Error saving settings: {e}")
            # TODO: Show error message dialog
            return False

    def save_and_restart(self):
        if self.save_settings():
            print("Restarting application...")
            # TODO: Implement restart logic (might need to call an external script or use QProcess)
            # Example: restart_applio() # This likely won't work directly in PyQt
            # QApplication.instance().quit() # Or maybe just quit and let user restart manually?
            pass # Placeholder
