import sys
import os
import json
from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import QTranslator, QLibraryInfo, QLocale # Added QTranslator, QLibraryInfo, QLocale
from main_window import MainWindow  # Assuming main_window.py is in the same directory

# Determine project root relative to this script
# Determine project root and other paths relative to this script
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
config_path = os.path.join(project_root, "assets", "config.json")
theme_dir = os.path.join(project_root, "assets", "themes", "qt")
locale_dir = os.path.join(project_root, "desktop_ui", "locales") # Define locale directory

def load_and_apply_theme(app: QApplication):
    """Loads theme setting from config.json and applies the QSS stylesheet."""
    default_theme = "Light" # Default theme if config/file is missing or invalid
    theme_name = default_theme
    stylesheet = ""

    try:
        if os.path.exists(config_path):
            with open(config_path, 'r', encoding='utf-8') as f:
                config_data = json.load(f)
                # Assuming the key is 'theme' in the config file
                theme_name = config_data.get("theme", default_theme)
        else:
            print(f"Warning: Config file not found at {config_path}. Using default theme.", file=sys.stderr)

        # Construct theme file path (assuming lowercase filename, e.g., "Dark" -> "dark.qss")
        qss_filename = f"{theme_name.lower()}.qss"
        qss_path = os.path.join(theme_dir, qss_filename)

        if os.path.exists(qss_path):
            with open(qss_path, 'r', encoding='utf-8') as f:
                stylesheet = f.read()
            print(f"Applying theme: {theme_name} from {qss_path}")
            app.setStyleSheet(stylesheet)
        elif theme_name.lower() != default_theme.lower(): # Don't warn if default theme file is missing
            print(f"Warning: Theme file not found for '{theme_name}' at {qss_path}. No theme applied.", file=sys.stderr)
        # If default theme file is missing, no specific style is applied (uses system default)

    except json.JSONDecodeError:
        print(f"Error: Could not decode JSON from {config_path}. Using default theme.", file=sys.stderr)
    except Exception as e:
        print(f"Error loading or applying theme: {e}", file=sys.stderr)


def load_and_install_translator(app: QApplication):
    """Loads language setting from config.json and installs the QTranslator."""
    default_lang = "en_US" # Default language code
    lang_code = default_lang
    translator = QTranslator(app)
    qt_translator = QTranslator(app) # For standard Qt dialogs etc.

    try:
        if os.path.exists(config_path):
            with open(config_path, 'r', encoding='utf-8') as f:
                config_data = json.load(f)
                # Assuming the key is 'language' in the config file (e.g., "en_US", "zh_CN")
                lang_code = config_data.get("language", default_lang)
        else:
            print(f"Warning: Config file not found at {config_path}. Using default language.", file=sys.stderr)

        # Load Qt base translations
        qt_lang_code = lang_code.split('_')[0] # Qt uses language code like 'qt_zh'
        qt_translation_path = QLibraryInfo.path(QLibraryInfo.LibraryPath.TranslationsPath)
        if qt_translator.load(f"qt_{qt_lang_code}", qt_translation_path):
             app.installTranslator(qt_translator)
             print(f"Loaded Qt base translations for: {qt_lang_code}")
        else:
             print(f"Warning: Could not load Qt base translations for {qt_lang_code} from {qt_translation_path}", file=sys.stderr)


        # Load application translations
        qm_filename = f"applio_{lang_code}.qm"
        qm_path = os.path.join(locale_dir, qm_filename)

        if os.path.exists(qm_path):
            if translator.load(qm_path):
                app.installTranslator(translator)
                print(f"Loaded application translations: {qm_path}")
            else:
                print(f"Error: Failed to load application translation file: {qm_path}", file=sys.stderr)
        elif lang_code != default_lang: # Don't warn if default language file is missing
            print(f"Warning: Application translation file not found for '{lang_code}' at {qm_path}", file=sys.stderr)

    except json.JSONDecodeError:
        print(f"Error: Could not decode JSON from {config_path}. Using default language.", file=sys.stderr)
    except Exception as e:
        print(f"Error loading or installing translator: {e}", file=sys.stderr)


def main():
    """Main function to initialize and run the PyQt6 application."""
    app = QApplication(sys.argv)

    # Load and apply theme from config file
    load_and_apply_theme(app)

    # Load and install translations
    load_and_install_translator(app)

    main_window = MainWindow()
    main_window.show()

    sys.exit(app.exec())

if __name__ == "__main__":
    main()
