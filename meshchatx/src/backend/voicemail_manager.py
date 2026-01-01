import os
import platform
import shutil
import subprocess
import threading
import time

import LXST
import RNS
from LXST.Codecs import Null
from LXST.Pipeline import Pipeline
from LXST.Sinks import OpusFileSink
from LXST.Sources import OpusFileSource


class VoicemailManager:
    def __init__(self, db, telephone_manager, storage_dir):
        self.db = db
        self.telephone_manager = telephone_manager
        self.storage_dir = os.path.join(storage_dir, "voicemails")
        self.greetings_dir = os.path.join(self.storage_dir, "greetings")
        self.recordings_dir = os.path.join(self.storage_dir, "recordings")

        # Ensure directories exist
        os.makedirs(self.greetings_dir, exist_ok=True)
        os.makedirs(self.recordings_dir, exist_ok=True)

        self.is_recording = False
        self.recording_pipeline = None
        self.recording_sink = None
        self.recording_start_time = None
        self.recording_remote_identity = None
        self.recording_filename = None

        # Paths to executables
        self.espeak_path = self._find_espeak()
        self.ffmpeg_path = self._find_ffmpeg()

        # Check for presence
        self.has_espeak = self.espeak_path is not None
        self.has_ffmpeg = self.ffmpeg_path is not None

        if self.has_espeak:
            RNS.log(f"Voicemail: Found eSpeak at {self.espeak_path}", RNS.LOG_DEBUG)
        else:
            RNS.log("Voicemail: eSpeak not found", RNS.LOG_ERROR)

        if self.has_ffmpeg:
            RNS.log(f"Voicemail: Found ffmpeg at {self.ffmpeg_path}", RNS.LOG_DEBUG)
        else:
            RNS.log("Voicemail: ffmpeg not found", RNS.LOG_ERROR)

    def _find_espeak(self):
        # Try standard name first
        path = shutil.which("espeak-ng")
        if path:
            return path

        # Try without -ng suffix
        path = shutil.which("espeak")
        if path:
            return path

        # Windows common install locations if not in PATH
        if platform.system() == "Windows":
            common_paths = [
                os.path.expandvars(r"%ProgramFiles%\eSpeak NG\espeak-ng.exe"),
                os.path.expandvars(r"%ProgramFiles(x86)%\eSpeak NG\espeak-ng.exe"),
                os.path.expandvars(r"%ProgramFiles%\eSpeak\espeak.exe"),
            ]
            for p in common_paths:
                if os.path.exists(p):
                    return p

        return None

    def _find_ffmpeg(self):
        path = shutil.which("ffmpeg")
        if path:
            return path

        # Windows common install locations
        if platform.system() == "Windows":
            common_paths = [
                os.path.expandvars(r"%ProgramFiles%\ffmpeg\bin\ffmpeg.exe"),
                os.path.expandvars(r"%ProgramFiles(x86)%\ffmpeg\bin\ffmpeg.exe"),
            ]
            for p in common_paths:
                if os.path.exists(p):
                    return p

        return None

    def generate_greeting(self, text):
        if not self.has_espeak or not self.has_ffmpeg:
            msg = "espeak-ng and ffmpeg are required for greeting generation"
            raise RuntimeError(msg)

        wav_path = os.path.join(self.greetings_dir, "greeting.wav")
        opus_path = os.path.join(self.greetings_dir, "greeting.opus")

        try:
            # espeak-ng to WAV
            subprocess.run([self.espeak_path, "-w", wav_path, text], check=True)

            # ffmpeg to Opus
            if os.path.exists(opus_path):
                os.remove(opus_path)

            subprocess.run(
                [
                    self.ffmpeg_path,
                    "-i",
                    wav_path,
                    "-c:a",
                    "libopus",
                    "-b:a",
                    "16k",
                    "-vbr",
                    "on",
                    opus_path,
                ],
                check=True,
            )

            return opus_path
        finally:
            if os.path.exists(wav_path):
                os.remove(wav_path)

    def handle_incoming_call(self, caller_identity):
        if not self.db.config.voicemail_enabled.get():
            return

        delay = self.db.config.voicemail_auto_answer_delay_seconds.get()

        def voicemail_job():
            time.sleep(delay)

            # Check if still ringing and no other active call
            telephone = self.telephone_manager.telephone
            if (
                telephone
                and telephone.active_call
                and telephone.active_call.get_remote_identity() == caller_identity
                and telephone.call_status == LXST.Signalling.STATUS_RINGING
            ):
                RNS.log(
                    f"Auto-answering call from {RNS.prettyhexrep(caller_identity.hash)} for voicemail",
                    RNS.LOG_DEBUG,
                )
                self.start_voicemail_session(caller_identity)

        threading.Thread(target=voicemail_job, daemon=True).start()

    def start_voicemail_session(self, caller_identity):
        telephone = self.telephone_manager.telephone
        if not telephone:
            return

        # Answer the call
        if not telephone.answer(caller_identity):
            return

        # Stop microphone if it's active to prevent local noise being sent or recorded
        if telephone.audio_input:
            telephone.audio_input.stop()

        # Play greeting
        greeting_path = os.path.join(self.greetings_dir, "greeting.opus")
        if not os.path.exists(greeting_path):
            # Fallback if no greeting generated yet
            self.generate_greeting(self.db.config.voicemail_greeting.get())

        def session_job():
            try:
                # 1. Play greeting
                greeting_source = OpusFileSource(greeting_path, target_frame_ms=60)
                # Attach to transmit mixer
                greeting_pipeline = Pipeline(
                    source=greeting_source, codec=Null(), sink=telephone.transmit_mixer
                )
                greeting_pipeline.start()

                # Wait for greeting to finish
                while greeting_source.running:
                    time.sleep(0.1)
                    if not telephone.active_call:
                        return

                greeting_pipeline.stop()

                # 2. Play beep
                beep_source = LXST.ToneSource(
                    frequency=800,
                    gain=0.1,
                    target_frame_ms=60,
                    codec=Null(),
                    sink=telephone.transmit_mixer,
                )
                beep_source.start()
                time.sleep(0.5)
                beep_source.stop()

                # 3. Start recording
                self.start_recording(caller_identity)

                # 4. Wait for max recording time or hangup
                max_time = self.db.config.voicemail_max_recording_seconds.get()
                start_wait = time.time()
                while self.is_recording and (time.time() - start_wait < max_time):
                    time.sleep(0.5)
                    if not telephone.active_call:
                        break

                # 5. End session
                if telephone.active_call:
                    telephone.hangup()

                self.stop_recording()

            except Exception as e:
                RNS.log(f"Error during voicemail session: {e}", RNS.LOG_ERROR)
                if self.is_recording:
                    self.stop_recording()

        threading.Thread(target=session_job, daemon=True).start()

    def start_recording(self, caller_identity):
        telephone = self.telephone_manager.telephone
        if not telephone or not telephone.active_call:
            return

        timestamp = time.time()
        filename = f"voicemail_{caller_identity.hash.hex()}_{int(timestamp)}.opus"
        filepath = os.path.join(self.recordings_dir, filename)

        try:
            self.recording_sink = OpusFileSink(filepath)
            # Connect the caller's audio source to our sink
            # active_call.audio_source is a LinkSource that feeds into receive_mixer
            # We want to record what we receive.
            self.recording_pipeline = Pipeline(
                source=telephone.active_call.audio_source,
                codec=Null(),
                sink=self.recording_sink,
            )
            self.recording_pipeline.start()

            self.is_recording = True
            self.recording_start_time = timestamp
            self.recording_remote_identity = caller_identity
            self.recording_filename = filename

            RNS.log(
                f"Started recording voicemail from {RNS.prettyhexrep(caller_identity.hash)}",
                RNS.LOG_DEBUG,
            )
        except Exception as e:
            RNS.log(f"Failed to start recording: {e}", RNS.LOG_ERROR)

    def stop_recording(self):
        if not self.is_recording:
            return

        try:
            duration = int(time.time() - self.recording_start_time)
            self.recording_pipeline.stop()
            self.recording_sink = None
            self.recording_pipeline = None

            # Save to database if long enough
            if duration >= 1:
                remote_name = self.telephone_manager.get_name_for_identity_hash(
                    self.recording_remote_identity.hash.hex()
                )
                self.db.voicemails.add_voicemail(
                    remote_identity_hash=self.recording_remote_identity.hash.hex(),
                    remote_identity_name=remote_name,
                    filename=self.recording_filename,
                    duration_seconds=duration,
                    timestamp=self.recording_start_time,
                )
                RNS.log(
                    f"Saved voicemail from {RNS.prettyhexrep(self.recording_remote_identity.hash)} ({duration}s)",
                    RNS.LOG_DEBUG,
                )
            else:
                # Delete short/empty recording
                filepath = os.path.join(self.recordings_dir, self.recording_filename)
                if os.path.exists(filepath):
                    os.remove(filepath)

            self.is_recording = False
            self.recording_start_time = None
            self.recording_remote_identity = None
            self.recording_filename = None

        except Exception as e:
            RNS.log(f"Error stopping recording: {e}", RNS.LOG_ERROR)
            self.is_recording = False
