# Applio PyQt6 Desktop UI Implementation Status

This document tracks the progress of implementing the PyQt6 desktop UI for Applio.

**Last Updated:** 2025-03-30

## Overall Structure

- [x] Main application entry point (`main.py`)
- [x] Main window with tabbed interface (`main_window.py`)
- [x] Basic `QThread` worker structure for background tasks in each tab.
- [x] Basic status label and progress bar in relevant tabs.
- [x] Basic error handling and display using `QMessageBox`.
- [ ] Internationalization (i18n) support. *(Framework setup, integration pending)*
- [x] Theme application based on settings. *(Initial loading logic added)*
- [ ] Robust task cancellation.
- [ ] Granular progress reporting (requires core changes).
- [x] Audio playback widgets. *(Widget created, integrated in TTS)*

## Tab Status

- **Inference (`inference_tab.py`)**
    - [x] Basic UI layout (Model/Index select, Input/Output paths, Basic Sliders)
    - [x] Single Inference core logic connection (`run_infer_script`)
    - [x] Advanced Settings UI (F0, SID, Format, Split, Autotune, Clean, Formant, Embedder, F0 File)
    - [x] Conditional visibility for advanced settings sliders/groups.
    - [x] Batch Inference sub-tab UI structure.
    - [x] Batch Inference core logic connection (`run_batch_infer_script`).
    - [x] Post-Process Effects UI and logic (Single & Batch). *(UI elements added)*
    - [x] Preset saving/loading UI and logic (Single & Batch). *(UI and basic functions added)*
    - [ ] Custom Embedder file management UI (Upload/Move).

- **Training (`train_tab.py`)**
    - [x] Basic UI layout (Model Name, Dataset Path, Sample Rate, Step Buttons)
    *   [x] Advanced Settings UI (CPU Cores, Preprocessing options, F0 Method, Hop Length, Embedder, Epochs, Batch Size, Save Options, GPU, Pretrained, Overtraining, Cache, Vocoder, Checkpointing, Cleanup, Index Algorithm)
    *   [x] Conditional visibility for advanced settings (Hop Length, Overtraining Threshold, Custom Pretrained).
    - [x] Core logic connection for Preprocess, Extract, Train, Index steps (`run_*_script`).
    - [ ] Refine UI layout for clarity.
    - [ ] Implement GPU selection validation/parsing if needed beyond simple string.

- **TTS (`tts_tab.py`)**
    - [x] Basic UI layout (Text Input, Voice Select, Rate Slider, RVC Model/Params, Output Path)
    - [x] TTS Voice dropdown population.
    - [x] Reused RVC Model/Index/Parameter widgets from Inference tab.
    - [x] Core logic connection (`run_tts_script`) using temporary file.
    - [x] Add missing RVC advanced parameters (Split, Autotune, Clean, etc.). *(UI elements added)*
    - [x] Add audio playback for output. *(AudioPlayer integrated)*

- **Voice Blender (`voice_blender_tab.py`)**
    - [x] Basic UI layout (Model A/B Select, Ratio Slider, Output Name)
    - [x] Reused RVC Model selection logic.
    - [x] Core logic connection (`run_model_blender_script`).
    - [x] Model list refresh on success.

- **Plugins (`plugins_tab.py`)**
    - [x] Basic UI layout (Install Button, List Widget, Refresh Button)
    - [x] Plugin installation logic (Zip extraction, requirements install via pip).
    - [x] Installed plugin listing logic.
    - [ ] Dynamic loading/display of plugin UIs (Major task, likely out of scope for initial build).

- **Download (`download_tab.py`)**
    - [x] Basic UI layout (Link Input, Download Button, Status Label)
    - [x] Core logic connection (`run_download_script`).
    - [x] Implement File Drop install section. *(UI and basic file handling added)*
    - [ ] Implement Pretrained model browser/download section. *(Placeholder added)*

- **Extra (`extra_tab.py`)**
    - [x] Sub-tab structure (Model Info, F0 Curve, Audio Analyzer).
    - [x] UI elements for inputs in each sub-tab.
    - [x] Core logic connection for Model Info (`run_model_information_script`).
    - [x] Core logic connection for Audio Analyzer (`run_audio_analyzer_script`).
    - [x] Core logic connection for F0 Curve (`extract_f0_curve`).
    - [x] Display text and image results.

- **Settings (`settings_tab.py`)**
    - [x] Basic UI layout (Theme, Language, Discord, Author).
    - [x] Theme dropdown population.
    - [x] Language dropdown population.
    - [x] Loading settings from `config.json`.
    - [x] Saving settings to `config.json`.
    - [x] Prompting user for manual restart.
    - [x] Actual theme application on startup. *(Loading logic added)*
    - [ ] Actual language application (i18n integration). *(Framework setup, integration pending)*
