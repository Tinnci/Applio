import sys
import os
from PyQt6.QtWidgets import (
    QWidget,
    QPushButton,
    QSlider,
    QLabel,
    QHBoxLayout,
    QVBoxLayout,
    QSizePolicy,
    QStyle,
    QApplication,
)
from PyQt6.QtMultimedia import QMediaPlayer, QAudioOutput
from PyQt6.QtCore import Qt, QUrl, QStandardPaths


class AudioPlayer(QWidget):
    """A reusable widget for playing audio files."""

    def __init__(self, parent=None):
        super().__init__(parent)

        self._media_player = QMediaPlayer(self)
        self._audio_output = QAudioOutput(self) # Required for playback
        self._media_player.setAudioOutput(self._audio_output)

        self._play_button = QPushButton()
        self._play_button.setIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_MediaPlay))
        self._play_button.setEnabled(False)
        self._play_button.clicked.connect(self._toggle_playback)

        self._stop_button = QPushButton()
        self._stop_button.setIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_MediaStop))
        self._stop_button.setEnabled(False)
        self._stop_button.clicked.connect(self._stop_playback)

        self._seek_slider = QSlider(Qt.Orientation.Horizontal)
        self._seek_slider.setRange(0, 0)
        self._seek_slider.setEnabled(False)
        self._seek_slider.sliderMoved.connect(self._set_position)
        self._seek_slider.valueChanged.connect(self._set_position_on_value_change) # Handle clicks

        self._time_label = QLabel("00:00 / 00:00")
        self._time_label.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Fixed)

        self._volume_slider = QSlider(Qt.Orientation.Horizontal)
        self._volume_slider.setRange(0, 100)
        self._volume_slider.setValue(75) # Default volume
        self._volume_slider.valueChanged.connect(self._set_volume)
        self._audio_output.setVolume(0.75) # Set initial volume for audio output

        # Layouts
        control_layout = QHBoxLayout()
        control_layout.setContentsMargins(0, 0, 0, 0)
        control_layout.addWidget(self._play_button)
        control_layout.addWidget(self._stop_button)
        control_layout.addWidget(self._seek_slider)
        control_layout.addWidget(self._time_label)

        volume_layout = QHBoxLayout()
        volume_layout.addWidget(QLabel("Volume:"))
        volume_layout.addWidget(self._volume_slider)

        main_layout = QVBoxLayout()
        main_layout.addLayout(control_layout)
        main_layout.addLayout(volume_layout)
        self.setLayout(main_layout)

        # Connect signals
        self._media_player.playbackStateChanged.connect(self._update_buttons)
        self._media_player.positionChanged.connect(self._update_position)
        self._media_player.durationChanged.connect(self._update_duration)
        self._media_player.errorOccurred.connect(self._handle_error)

    def set_media(self, file_path: str):
        """Loads the specified audio file into the player."""
        if not file_path or not os.path.exists(file_path):
            self._handle_error(QMediaPlayer.Error.ResourceError, "File not found or invalid path.")
            self.reset_player()
            return

        try:
            media_url = QUrl.fromLocalFile(file_path)
            self._media_player.setSource(media_url)
            self._play_button.setEnabled(True)
            self._stop_button.setEnabled(True)
            self._seek_slider.setEnabled(True)
            # Reset time label until duration is known
            self._time_label.setText("00:00 / 00:00")
        except Exception as e:
            self._handle_error(QMediaPlayer.Error.ResourceError, f"Error setting media source: {e}")
            self.reset_player()

    def reset_player(self):
        """Resets the player to its initial state."""
        self._media_player.stop()
        self._media_player.setSource(QUrl()) # Clear source
        self._play_button.setIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_MediaPlay))
        self._play_button.setEnabled(False)
        self._stop_button.setEnabled(False)
        self._seek_slider.setEnabled(False)
        self._seek_slider.setValue(0)
        self._time_label.setText("00:00 / 00:00")

    def _toggle_playback(self):
        """Plays or pauses the media."""
        if self._media_player.playbackState() == QMediaPlayer.PlaybackState.PlayingState:
            self._media_player.pause()
        else:
            self._media_player.play()

    def _stop_playback(self):
        """Stops the media playback."""
        self._media_player.stop()

    def _update_buttons(self, state):
        """Updates the play/pause button icon based on playback state."""
        if state == QMediaPlayer.PlaybackState.PlayingState:
            self._play_button.setIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_MediaPause))
        else:
            self._play_button.setIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_MediaPlay))

    def _update_position(self, position):
        """Updates the seek slider position and time label."""
        if not self._seek_slider.isSliderDown(): # Only update if user isn't dragging
             self._seek_slider.setValue(position)
        self._update_time_label(position, self._media_player.duration())

    def _update_duration(self, duration):
        """Updates the seek slider range and time label."""
        self._seek_slider.setRange(0, duration)
        self._update_time_label(self._media_player.position(), duration)

    def _set_position(self, position):
        """Sets the media player position based on slider movement."""
        # Only set position if the player is ready and duration is valid
        if self._media_player.duration() > 0:
            self._media_player.setPosition(position)

    def _set_position_on_value_change(self, position):
        """Sets the media player position when the slider value changes (e.g., by clicking)."""
        # Avoid setting position if the slider is being dragged (handled by _set_position)
        if not self._seek_slider.isSliderDown():
             self._set_position(position)

    def _set_volume(self, volume):
        """Sets the media player volume."""
        self._audio_output.setVolume(volume / 100.0)

    def _update_time_label(self, position, duration):
        """Formats and updates the time label."""
        if duration == 0:
            self._time_label.setText("00:00 / 00:00")
            return

        pos_seconds = position // 1000
        dur_seconds = duration // 1000

        pos_str = f"{pos_seconds // 60:02d}:{pos_seconds % 60:02d}"
        dur_str = f"{dur_seconds // 60:02d}:{dur_seconds % 60:02d}"
        self._time_label.setText(f"{pos_str} / {dur_str}")

    def _handle_error(self, error, error_string=""):
        """Handles media player errors."""
        # Reset UI elements on error
        self.reset_player()
        print(f"Audio Player Error ({error}): {self._media_player.errorString()} - {error_string}", file=sys.stderr)
        # Optionally show a message box to the user here


# Example usage for testing this file directly
if __name__ == "__main__":
    app = QApplication(sys.argv)
    player = AudioPlayer()

    # --- Test Setup ---
    # Create a dummy file path for testing (replace with a real audio file if available)
    # On Windows, QUrl might need an absolute path. Let's try finding a common location.
    music_dir = QStandardPaths.standardLocations(QStandardPaths.StandardLocation.MusicLocation)
    test_file_path = ""
    if music_dir:
        # Look for a common audio file type in the music directory
        for ext in [".wav", ".mp3", ".ogg", ".flac"]:
             potential_files = [f for f in os.listdir(music_dir[0]) if f.lower().endswith(ext)]
             if potential_files:
                 test_file_path = os.path.join(music_dir[0], potential_files[0])
                 print(f"Attempting to load test file: {test_file_path}")
                 break

    if test_file_path:
        player.set_media(test_file_path)
    else:
        print("No suitable audio file found in Music directory for testing.", file=sys.stderr)
        # You might want to manually set a path here for testing if needed
        # test_file_path = "path/to/your/test/audio.wav"
        # if os.path.exists(test_file_path):
        #    player.set_media(test_file_path)
        # else:
        #    print(f"Test file not found: {test_file_path}", file=sys.stderr)

    player.setWindowTitle("Audio Player Test")
    player.resize(400, 100)
    player.show()
    sys.exit(app.exec())
