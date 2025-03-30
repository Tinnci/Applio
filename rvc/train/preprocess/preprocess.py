import os
import sys
import time
import signal # Added
import multiprocessing # Added
from scipy import signal
from scipy.io import wavfile
import numpy as np
import concurrent.futures
from tqdm import tqdm
import json
from distutils.util import strtobool
import librosa
import multiprocessing
import noisereduce as nr
import soxr

now_directory = os.getcwd()
sys.path.append(now_directory)

from rvc.lib.utils import load_audio
from rvc.train.preprocess.slicer import Slicer

import logging

logging.getLogger("numba.core.byteflow").setLevel(logging.WARNING)
logging.getLogger("numba.core.ssa").setLevel(logging.WARNING)
logging.getLogger("numba.core.interpreter").setLevel(logging.WARNING)

# Cancellation Handling Globals
_is_cancelled = False
_cancel_event = None # Will be initialized in main

def signal_handler(sig, frame):
    global _is_cancelled, _cancel_event
    print(f'>>> Signal {sig} received in preprocess, requesting cancellation...')
    _is_cancelled = True
    if _cancel_event:
        _cancel_event.set() # Signal workers via the event

OVERLAP = 0.3
PERCENTAGE = 3.0
MAX_AMPLITUDE = 0.9
ALPHA = 0.75
HIGH_PASS_CUTOFF = 48
SAMPLE_RATE_16K = 16000
RES_TYPE = "soxr_vhq"


class PreProcess:
    def __init__(self, sr: int, exp_dir: str):
        self.slicer = Slicer(
            sr=sr,
            threshold=-42,
            min_length=1500,
            min_interval=400,
            hop_size=15,
            max_sil_kept=500,
        )
        self.sr = sr
        self.b_high, self.a_high = signal.butter(
            N=5, Wn=HIGH_PASS_CUTOFF, btype="high", fs=self.sr
        )
        self.exp_dir = exp_dir
        self.device = "cpu"
        self.gt_wavs_dir = os.path.join(exp_dir, "sliced_audios")
        self.wavs16k_dir = os.path.join(exp_dir, "sliced_audios_16k")
        os.makedirs(self.gt_wavs_dir, exist_ok=True)
        os.makedirs(self.wavs16k_dir, exist_ok=True)

    def _normalize_audio(self, audio: np.ndarray):
        tmp_max = np.abs(audio).max()
        if tmp_max > 2.5:
            return None
        return (audio / tmp_max * (MAX_AMPLITUDE * ALPHA)) + (1 - ALPHA) * audio

    def process_audio_segment(
        self,
        normalized_audio: np.ndarray,
        sid: int,
        idx0: int,
        idx1: int,
        cancel_event: multiprocessing.Event, # Added cancel_event
    ):
        # Check cancellation
        if cancel_event.is_set():
            print(f"Worker {os.getpid()}: Cancellation detected in process_audio_segment for {sid}_{idx0}_{idx1}.")
            return

        if normalized_audio is None:
            print(f"{sid}-{idx0}-{idx1}-filtered")
            return
        wavfile.write(
            os.path.join(self.gt_wavs_dir, f"{sid}_{idx0}_{idx1}.wav"),
            self.sr,
            normalized_audio.astype(np.float32),
        )
        audio_16k = librosa.resample(
            normalized_audio,
            orig_sr=self.sr,
            target_sr=SAMPLE_RATE_16K,
            res_type=RES_TYPE,
        )
        wavfile.write(
            os.path.join(self.wavs16k_dir, f"{sid}_{idx0}_{idx1}.wav"),
            SAMPLE_RATE_16K,
            audio_16k.astype(np.float32),
        )

    def simple_cut(
        self,
        audio: np.ndarray,
        sid: int,
        idx0: int,
        chunk_len: float,
        overlap_len: float,
        cancel_event: multiprocessing.Event, # Added cancel_event
    ):
        chunk_length = int(self.sr * chunk_len)
        overlap_length = int(self.sr * overlap_len)
        i = 0
        while i < len(audio):
            # Check cancellation inside loop
            if cancel_event.is_set():
                print(f"Worker {os.getpid()}: Cancellation detected in simple_cut loop for {sid}_{idx0}.")
                return

            chunk = audio[i : i + chunk_length]
            if len(chunk) == chunk_length:
                # full SR for training
                wavfile.write(
                    os.path.join(
                        self.gt_wavs_dir,
                        f"{sid}_{idx0}_{i // (chunk_length - overlap_length)}.wav",
                    ),
                    self.sr,
                    chunk.astype(np.float32),
                )
                # 16KHz for feature extraction
                chunk_16k = librosa.resample(
                    chunk, orig_sr=self.sr, target_sr=SAMPLE_RATE_16K, res_type=RES_TYPE
                )
                wavfile.write(
                    os.path.join(
                        self.wavs16k_dir,
                        f"{sid}_{idx0}_{i // (chunk_length - overlap_length)}.wav",
                    ),
                    SAMPLE_RATE_16K,
                    chunk_16k.astype(np.float32),
                )
            i += chunk_length - overlap_length

    def process_audio(
        self,
        path: str,
        idx0: int,
        sid: int,
        cut_preprocess: str,
        process_effects: bool,
        noise_reduction: bool,
        reduction_strength: float,
        chunk_len: float,
        overlap_len: float,
        cancel_event: multiprocessing.Event, # Added cancel_event
    ):
        audio_length = 0
        try:
            # Check cancellation at start
            if cancel_event.is_set():
                print(f"Worker {os.getpid()}: Cancellation detected at start of process_audio for {path}.")
                return None
            audio = load_audio(path, self.sr)
            audio_length = librosa.get_duration(y=audio, sr=self.sr)

            if process_effects:
                audio = signal.lfilter(self.b_high, self.a_high, audio)
                audio = self._normalize_audio(audio)
            if noise_reduction:
                audio = nr.reduce_noise(
                    y=audio, sr=self.sr, prop_decrease=reduction_strength
                )
            if cut_preprocess == "Skip":
                # no cutting
                self.process_audio_segment(
                    audio,
                    sid,
                    idx0,
                    0,
                    cancel_event, # Pass event
                )
            elif cut_preprocess == "Simple":
                # simple
                if cancel_event.is_set(): print(f"Worker {os.getpid()}: Cancellation detected before simple_cut for {path}."); return None
                self.simple_cut(audio, sid, idx0, chunk_len, overlap_len, cancel_event) # Pass event
            elif cut_preprocess == "Automatic":
                idx1 = 0
                if cancel_event.is_set(): print(f"Worker {os.getpid()}: Cancellation detected before slicer loop for {path}."); return None
                # legacy
                for audio_segment in self.slicer.slice(audio):
                    # Check cancellation inside outer loop
                    if cancel_event.is_set():
                        print(f"Worker {os.getpid()}: Cancellation detected in slicer loop for {path}.")
                        return None # Exit if cancelled

                    i = 0
                    while True:
                        # Check cancellation inside inner loop
                        if cancel_event.is_set():
                            print(f"Worker {os.getpid()}: Cancellation detected in slicer inner loop for {path}.")
                            return None # Exit if cancelled
                        start = int(self.sr * (PERCENTAGE - OVERLAP) * i)
                        i += 1
                        if (
                            len(audio_segment[start:])
                            > (PERCENTAGE + OVERLAP) * self.sr
                        ):
                            tmp_audio = audio_segment[
                                start : start + int(PERCENTAGE * self.sr)
                            ]
                            self.process_audio_segment(
                                tmp_audio,
                                sid,
                                idx0,
                                idx1,
                                cancel_event, # Pass event
                            )
                            idx1 += 1
                        else:
                            tmp_audio = audio_segment[start:]
                            self.process_audio_segment(
                                tmp_audio,
                                sid,
                                idx0,
                                idx1,
                                cancel_event, # Pass event
                            )
                            idx1 += 1
                            break

        except Exception as error:
            print(f"Error processing audio: {error}")
        return audio_length


def format_duration(seconds):
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    seconds = int(seconds % 60)
    return f"{hours:02}:{minutes:02}:{seconds:02}"


def save_dataset_duration(file_path, dataset_duration):
    try:
        with open(file_path, "r") as f:
            data = json.load(f)
    except FileNotFoundError:
        data = {}

    formatted_duration = format_duration(dataset_duration)
    new_data = {
        "total_dataset_duration": formatted_duration,
        "total_seconds": dataset_duration,
    }
    data.update(new_data)

    with open(file_path, "w") as f:
        json.dump(data, f, indent=4)


def process_audio_wrapper(args):
    (
        pp,
        file,
        cut_preprocess,
        process_effects,
        noise_reduction,
        reduction_strength,
        chunk_len,
        overlap_len,
        cancel_event # Unpack event
    ) = args

    # <<< CHECK CANCELLATION HERE >>>
    if cancel_event.is_set():
        print(f"Worker {os.getpid()}: Cancellation detected before processing {file[0]}.")
        return None # Indicate cancellation

    file_path, idx0, sid = file
    return pp.process_audio( # Pass event down
        file_path,
        idx0,
        sid,
        cut_preprocess,
        process_effects,
        noise_reduction,
        reduction_strength,
        chunk_len,
        overlap_len,
        cancel_event # Pass event
    )


def preprocess_training_set(
    input_root: str,
    sr: int,
    num_processes: int,
    exp_dir: str,
    cut_preprocess: str,
    process_effects: bool,
    noise_reduction: bool,
    reduction_strength: float,
    chunk_len: float,
    overlap_len: float,
    cancel_event: multiprocessing.Event, # Added cancel_event
):
    start_time = time.time()
    pp = PreProcess(sr, exp_dir)
    print(f"Starting preprocess with {num_processes} processes...")

    files = []
    idx = 0

    for root, _, filenames in os.walk(input_root):
        try:
            sid = 0 if root == input_root else int(os.path.basename(root))
            for f in filenames:
                if f.lower().endswith((".wav", ".mp3", ".flac", ".ogg")):
                    files.append((os.path.join(root, f), idx, sid))
                    idx += 1
        except ValueError:
            print(
                f'Speaker ID folder is expected to be integer, got "{os.path.basename(root)}" instead.'
            )

    # print(f"Number of files: {len(files)}")
    audio_length = []
    try: # Use try...finally to ensure executor shutdown
        with tqdm(total=len(files)) as pbar:
            with concurrent.futures.ProcessPoolExecutor(max_workers=num_processes) as executor:
                futures = [
                    executor.submit(
                        process_audio_wrapper,
                        (
                            pp,
                            file,
                            cut_preprocess,
                            process_effects,
                            noise_reduction,
                            reduction_strength,
                            chunk_len,
                            overlap_len,
                            cancel_event # Pass event here
                        ),
                    )
                    for file in files
                ]
                for future in concurrent.futures.as_completed(futures):
                    # <<< CHECK CANCELLATION HERE >>>
                    if cancel_event.is_set():
                        print(">>> Cancellation detected in main preprocess loop. Stopping...")
                        # Attempt to cancel pending futures (best effort)
                        for f in futures:
                            if not f.done():
                                f.cancel()
                        break # Exit the result processing loop

                    try:
                        result = future.result() # Get result if not cancelled
                        if result is not None: # Check if worker returned due to cancellation
                            audio_length.append(result)
                    except concurrent.futures.CancelledError:
                        print("A future was cancelled.")
                    except Exception as exc:
                        print(f'Generated an exception: {exc}')

                    pbar.update(1)
    finally:
             # Executor is automatically shut down by 'with' statement exit
             # If not using 'with', call executor.shutdown() here
             if cancel_event.is_set():
                 print(">>> Preprocessing cancelled.")
             else:
                 # Normal completion logic
                 # Ensure audio_length only contains valid numbers before summing
                 valid_lengths = [length for length in audio_length if isinstance(length, (int, float))]
                 audio_length_sum = sum(valid_lengths)
                 save_dataset_duration(
                     os.path.join(exp_dir, "model_info.json"), dataset_duration=audio_length_sum
                 )
                 elapsed_time = time.time() - start_time
                 print(
                     f"Preprocess completed in {elapsed_time:.2f} seconds on {format_duration(audio_length_sum)} seconds of audio."
                 )
        # The original print/save logic outside the try/finally is now handled within the 'else' part of the finally block.


if __name__ == "__main__":
    experiment_directory = str(sys.argv[1])
    input_root = str(sys.argv[2])
    sample_rate = int(sys.argv[3])
    num_processes = sys.argv[4]
    if num_processes.lower() == "none":
        num_processes = multiprocessing.cpu_count()
    else:
        num_processes = int(num_processes)
    cut_preprocess = str(sys.argv[5])
    process_effects = strtobool(sys.argv[6])
    noise_reduction = strtobool(sys.argv[7])
    reduction_strength = float(sys.argv[8])
    chunk_len = float(sys.argv[9])
    overlap_len = float(sys.argv[10])

    manager = multiprocessing.Manager()
    cancel_event = manager.Event()
    _cancel_event = cancel_event # Assign to global for handler

    print("Registering signal handler for preprocess...")
    signal.signal(signal.SIGINT, signal_handler)
    try:
        signal.signal(signal.SIGTERM, signal_handler)
    except AttributeError:
        pass

    preprocess_training_set(
        input_root,
        sample_rate,
        num_processes,
        experiment_directory,
        cut_preprocess,
        process_effects,
        noise_reduction,
        reduction_strength,
        chunk_len,
        overlap_len,
        cancel_event # Pass the event
    )
