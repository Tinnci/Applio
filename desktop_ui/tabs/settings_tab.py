from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QGridLayout, 
                             QComboBox, QCheckBox, QLineEdit, QMessageBox, QApplication, 
                             QSizePolicy, QSpacerItem, QGroupBox) # Added QGroupBox
from PyQt6.QtCore import Qt
import os
import sys
import json
import glob # For listing language files

# Ensure the core Applio logic can be imported
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

# Define paths
CONFIG_PATH = os.path.join(project_root, "assets", "config.json")
THEME_LIST_PATH = os.path.join(project_root, "assets", "themes", "theme_list.json")
LANG_DIR = os.path.join(project_root, "assets", "i18n", "languages")

# TODO: Import restart logic if possible, otherwise just prompt user

class SettingsTab(QWidget):
    """Widget for the Settings Tab."""
    def __init__(self):
        super().__init__()
        self.available_themes = [] # Store theme data
        self.available_langs = [] # Store language codes
        self.setup_ui()
        self.load_settings()

    def setup_ui(self):
        main_layout = QVBoxLayout(self)

        # --- General Settings ---
        general_group = QGroupBox("General Settings")
        general_layout = QGridLayout(general_group)

        # Theme
        general_layout.addWidget(QLabel("Theme:"), 0, 0)
        self.theme_combo = QComboBox()
        self.populate_themes() # Populate dropdown
        general_layout.addWidget(self.theme_combo, 0, 1)

        # Language
        general_layout.addWidget(QLabel("Language:"), 1, 0)
        self.language_combo = QComboBox()
        self.populate_languages() # Populate dropdown
        general_layout.addWidget(self.language_combo, 1, 1)

        # Discord Presence
        self.discord_checkbox = QCheckBox("Enable Discord Presence")
        general_layout.addWidget(self.discord_checkbox, 2, 0, 1, 2) # Span 2 columns

        main_layout.addWidget(general_group)

        # --- Training Settings ---
        training_group = QGroupBox("Training Settings")
        training_layout = QGridLayout(training_group)

        training_layout.addWidget(QLabel("Model Author Name:"), 0, 0)
        self.author_edit = QLineEdit()
        self.author_edit.setPlaceholderText("Name to embed in trained models")
        training_layout.addWidget(self.author_edit, 0, 1)

        main_layout.addWidget(training_group)

        # --- Actions ---
        action_group = QWidget()
        action_layout = QHBoxLayout(action_group)
        action_layout.setContentsMargins(0,10,0,0)

        self.save_button = QPushButton("Save Settings")
        self.save_button.setToolTip("Save the current settings. A restart is required for some changes (Theme, Language).")
        self.save_button.clicked.connect(self.save_settings_and_prompt_restart)
        action_layout.addWidget(self.save_button)
        
        # TODO: Add a dedicated Restart button if feasible, otherwise remove '& Restart' from save button text

        main_layout.addWidget(action_group)

        # Add spacer
        main_layout.addSpacerItem(QSpacerItem(20, 40, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Expanding))

        self.setLayout(main_layout)

    def populate_themes(self):
        """Loads themes from theme_list.json and populates the dropdown."""
        self.theme_combo.clear()
        self.available_themes = []
        try:
            with open(THEME_LIST_PATH, 'r', encoding='utf-8') as f:
                themes_data = json.load(f)
            
            # Add Applio theme first if it exists (or handle custom themes differently)
            # Assuming Applio theme is defined in config.json, not theme_list.json?
            # For now, just load from the list
            
            for theme_info in themes_data:
                theme_id = theme_info.get("id")
                if theme_id:
                    self.available_themes.append({"id": theme_id})
                    self.theme_combo.addItem(theme_id, userData=theme_id) # Store ID as data
                    
            # Add local Applio theme manually if needed (assuming structure)
            local_theme_name = "Applio/Applio" # Example structure
            self.available_themes.append({"id": local_theme_name, "local": True})
            self.theme_combo.insertItem(0, local_theme_name, userData=local_theme_name) # Add at top

        except FileNotFoundError:
            print(f"Warning: Theme list file not found at {THEME_LIST_PATH}")
            self.theme_combo.addItem("Error loading themes")
        except Exception as e:
            print(f"Error populating themes: {e}")
            self.theme_combo.addItem("Error loading themes")

    def populate_languages(self):
        """Scans language directory and populates the dropdown."""
        self.language_combo.clear()
        self.available_langs = []
        self.language_combo.addItem("Auto Detect", userData="auto")
        try:
            lang_files = glob.glob(os.path.join(LANG_DIR, "*.json"))
            for lang_file in sorted(lang_files):
                lang_code = os.path.basename(lang_file).replace(".json", "")
                # TODO: Maybe read the JSON to get a display name? For now, use code.
                display_name = lang_code 
                self.available_langs.append(lang_code)
                self.language_combo.addItem(display_name, userData=lang_code)
        except Exception as e:
            print(f"Error populating languages: {e}")
            self.language_combo.addItem("Error loading languages")


    def load_settings(self):
        """Load settings from config.json and update UI."""
        try:
            with open(CONFIG_PATH, 'r', encoding='utf-8') as f:
                config = json.load(f)

            # Set Theme
            # Note: Original Gradio uses theme ID. PyQt needs custom handling.
            # We'll store the ID in config and find it in the combo.
            # The actual theme application happens in main_window.py or main.py on startup.
            current_theme_id = config.get("theme", {}).get("id", "gradio/default") # Default Gradio theme ID
            # Handle local theme case
            if config.get("theme", {}).get("file") == "Applio.py":
                 current_theme_id = "Applio/Applio"

            index = self.theme_combo.findData(current_theme_id)
            if index >= 0:
                self.theme_combo.setCurrentIndex(index)
            else:
                 # If saved theme not found, default to Applio/Applio or first item
                 index = self.theme_combo.findData("Applio/Applio")
                 if index >= 0: self.theme_combo.setCurrentIndex(index)
                 elif self.theme_combo.count() > 0: self.theme_combo.setCurrentIndex(0)


            # Set Language
            lang_override = config.get("lang", {}).get("override", False)
            selected_lang = config.get("lang", {}).get("selected_lang", "en_US")
            if lang_override:
                index = self.language_combo.findData(selected_lang)
                if index >= 0:
                    self.language_combo.setCurrentIndex(index)
                else: # Lang not found, default to Auto
                    self.language_combo.setCurrentIndex(0) 
            else:
                self.language_combo.setCurrentIndex(0) # Index 0 is "Auto Detect"

            # Set Discord Presence
            self.discord_checkbox.setChecked(config.get("discord_presence", False))

            # Set Model Author
            self.author_edit.setText(config.get("model_author", ""))

        except FileNotFoundError:
            print(f"Warning: Config file not found at {CONFIG_PATH}. Using defaults.")
            # Set UI to defaults if config not found
            index = self.theme_combo.findData("Applio/Applio")
            if index >= 0: self.theme_combo.setCurrentIndex(index)
            self.language_combo.setCurrentIndex(0)
            self.discord_checkbox.setChecked(False)
            self.author_edit.setText("")
        except Exception as e:
            print(f"Error loading settings: {e}")
            QMessageBox.warning(self, "Load Settings Error", f"Could not load settings:\n{e}")

    def save_settings(self):
        """Save current UI settings to config.json"""
        try:
            # Read existing config first to preserve other settings
            try:
                with open(CONFIG_PATH, 'r', encoding='utf-8') as f:
                    config = json.load(f)
            except (FileNotFoundError, json.JSONDecodeError):
                config = {} # Start fresh if file doesn't exist or is invalid

            # --- Update config with current UI values ---
            
            # Theme: Store the selected theme ID. Actual theme loading is handled elsewhere.
            selected_theme_id = self.theme_combo.currentData()
            if selected_theme_id == "Applio/Applio": # Handle local theme case
                 config["theme"] = {"file": "Applio.py", "class": "Applio", "id": selected_theme_id}
            elif selected_theme_id:
                 config["theme"] = {"id": selected_theme_id} # Store Gradio theme ID
            else: # Should not happen if populated correctly
                 config["theme"] = {"id": "gradio/default"} 

            # Language
            selected_lang_data = self.language_combo.currentData()
            if selected_lang_data == "auto":
                config["lang"] = {"override": False, "selected_lang": config.get("lang", {}).get("selected_lang", "en_US")}
            else:
                config["lang"] = {"override": True, "selected_lang": selected_lang_data}

            # Discord Presence
            config["discord_presence"] = self.discord_checkbox.isChecked()

            # Model Author
            config["model_author"] = self.author_edit.text().strip() or "None" # Store "None" if empty

            # --- Write updated config ---
            with open(CONFIG_PATH, 'w', encoding='utf-8') as f:
                json.dump(config, f, indent=2)
            print("Settings saved successfully.")
            return True
        except Exception as e:
            print(f"Error saving settings: {e}")
            QMessageBox.critical(self, "Save Settings Error", f"Could not save settings:\n{e}")
            return False

    def save_settings_and_prompt_restart(self):
        """Saves settings and informs the user a restart is needed."""
        if self.save_settings():
            QMessageBox.information(self, "Settings Saved", 
                                    "Settings have been saved successfully.\n"
                                    "Please restart Applio for changes like Theme or Language to take effect.")
            # We don't attempt an automatic restart here.
