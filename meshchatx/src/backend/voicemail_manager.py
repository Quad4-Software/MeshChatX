import os
import platform
import shutil
import subprocess
import sys
import threading
import time

import LXST
import RNS
from LXST.Codecs import Null
from LXST.Pipeline import Pipeline
from LXST.Sinks import OpusFileSink
from LXST.Sources import OpusFileSource


class VoicemailManager:
    def __init__(self, db, config, telephone_manager, storage_dir):
        self.db = db
        self.config = config
        self.telephone_manager = telephone_manager
        self.storage_dir = os.path.join(storage_dir, "voicemails")
        self.greetings_dir = os.path.join(self.storage_dir, "greetings")
        self.recordings_dir = os.path.join(self.storage_dir, "recordings")

        # Ensure directories exist
        os.makedirs(self.greetings_dir, exist_ok=True)
        os.makedirs(self.recordings_dir, exist_ok=True)

        self.is_recording = False
        self.is_greeting_recording = False
        self.recording_pipeline = None
        self.recording_sink = None
        self.recording_start_time = None
        self.recording_remote_identity = None
        self.recording_filename = None

        self.on_new_voicemail_callback = None

        # stabilization delay for voicemail greeting
        self.STABILIZATION_DELAY = 2.5

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

    def get_name_for_identity_hash(self, identity_hash):
        """Default implementation, should be patched by ReticulumMeshChat"""
        return

    def _find_bundled_binary(self, name):
        if getattr(sys, "frozen", False):
            exe_dir = os.path.dirname(sys.executable)
            # Try in bin/ subdirectory of the executable
            local_bin = os.path.join(exe_dir, "bin", name)
            if platform.system() == "Windows":
                local_bin += ".exe"
            if os.path.exists(local_bin):
                return local_bin
            # Try in executable directory itself
            local_bin = os.path.join(exe_dir, name)
            if platform.system() == "Windows":
                local_bin += ".exe"
            if os.path.exists(local_bin):
                return local_bin
        return None

    def _find_espeak(self):
        # Try bundled first
        bundled = self._find_bundled_binary("espeak-ng")
        if bundled:
            return bundled
        bundled = self._find_bundled_binary("espeak")
        if bundled:
            return bundled

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
        # Try bundled first
        bundled = self._find_bundled_binary("ffmpeg")
        if bundled:
            return bundled

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

        try:
            # espeak-ng to WAV
            subprocess.run([self.espeak_path, "-w", wav_path, text], check=True)

            # Convert WAV to Opus
            return self.convert_to_greeting(wav_path)
        finally:
            if os.path.exists(wav_path):
                os.remove(wav_path)

    def convert_to_greeting(self, input_path):
        if not self.has_ffmpeg:
            msg = "ffmpeg is required for audio conversion"
            raise RuntimeError(msg)

        opus_path = os.path.join(self.greetings_dir, "greeting.opus")

        if os.path.exists(opus_path):
            os.remove(opus_path)

        subprocess.run(
            [
                self.ffmpeg_path,
                "-i",
                input_path,
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

    def remove_greeting(self):
        opus_path = os.path.join(self.greetings_dir, "greeting.opus")
        if os.path.exists(opus_path):
            os.remove(opus_path)
        return True

    def handle_incoming_call(self, caller_identity):
        RNS.log(
            f"Voicemail: handle_incoming_call from {RNS.prettyhexrep(caller_identity.hash)}",
            RNS.LOG_DEBUG,
        )
        if not self.config.voicemail_enabled.get():
            RNS.log("Voicemail: Voicemail is disabled", RNS.LOG_DEBUG)
            return

        delay = self.config.voicemail_auto_answer_delay_seconds.get()
        RNS.log(f"Voicemail: Will auto-answer in {delay} seconds", RNS.LOG_DEBUG)

        def voicemail_job():
            RNS.log(
                f"Voicemail: Auto-answer timer started for {RNS.prettyhexrep(caller_identity.hash)}",
                RNS.LOG_DEBUG,
            )
            time.sleep(delay)

            # Check if still ringing and no other active call
            telephone = self.telephone_manager.telephone
            if not telephone:
                RNS.log("Voicemail: No telephone object", RNS.LOG_ERROR)
                return

            RNS.log(
                f"Voicemail: Checking status. Call status: {telephone.call_status}, Active call: {telephone.active_call}",
                RNS.LOG_DEBUG,
            )

            if (
                telephone
                and telephone.active_call
                and telephone.active_call.get_remote_identity().hash
                == caller_identity.hash
                and telephone.call_status == 4  # Ringing
            ):
                RNS.log(
                    f"Auto-answering call from {RNS.prettyhexrep(caller_identity.hash)} for voicemail",
                    RNS.LOG_INFO,
                )
                self.start_voicemail_session(caller_identity)
            else:
                RNS.log(
                    "Voicemail: Auto-answer conditions not met after delay",
                    RNS.LOG_DEBUG,
                )
                if telephone.active_call:
                    RNS.log(
                        f"Voicemail: Active call remote: {RNS.prettyhexrep(telephone.active_call.get_remote_identity().hash)}",
                        RNS.LOG_DEBUG,
                    )

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
            if self.has_espeak and self.has_ffmpeg:
                try:
                    self.generate_greeting(self.config.voicemail_greeting.get())
                except Exception as e:
                    RNS.log(
                        f"Voicemail: Could not generate initial greeting: {e}",
                        RNS.LOG_ERROR,
                    )
            else:
                RNS.log(
                    "Voicemail: espeak-ng or ffmpeg missing, cannot generate greeting",
                    RNS.LOG_WARNING,
                )

        def session_job():
            try:
                # Wait for link to stabilize
                RNS.log(
                    f"Voicemail: Waiting {self.STABILIZATION_DELAY}s for link stabilization...",
                    RNS.LOG_DEBUG,
                )
                time.sleep(self.STABILIZATION_DELAY)

                if not telephone.active_call:
                    RNS.log(
                        "Voicemail: Call ended during stabilization delay",
                        RNS.LOG_DEBUG,
                    )
                    return

                # 1. Play greeting
                if os.path.exists(greeting_path):
                    try:
                        greeting_source = OpusFileSource(
                            greeting_path, target_frame_ms=60
                        )
                        # Attach to transmit mixer
                        greeting_pipeline = Pipeline(
                            source=greeting_source,
                            codec=Null(),
                            sink=telephone.transmit_mixer,
                        )
                        greeting_pipeline.start()

                        # Wait for greeting to finish
                        while greeting_source.running:
                            time.sleep(0.1)
                            if not telephone.active_call:
                                greeting_pipeline.stop()
                                return

                        greeting_pipeline.stop()
                    except Exception as e:
                        RNS.log(
                            f"Voicemail: Could not play greeting (libs missing?): {e}",
                            RNS.LOG_ERROR,
                        )
                else:
                    RNS.log("Voicemail: No greeting available to play", RNS.LOG_WARNING)

                if not telephone.active_call:
                    return

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

                if not telephone.active_call:
                    return

                # 3. Start recording
                self.start_recording(caller_identity)

                # 4. Wait for max recording time or hangup
                max_time = self.config.voicemail_max_recording_seconds.get()
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
            # Ensure samplerate is set to avoid TypeError in LXST Opus codec
            # which expects sink to have a valid samplerate attribute
            self.recording_sink.samplerate = 48000

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
                remote_name = self.get_name_for_identity_hash(
                    self.recording_remote_identity.hash.hex(),
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

                if self.on_new_voicemail_callback:
                    self.on_new_voicemail_callback(
                        self.recording_remote_identity.hash.hex(),
                        remote_name,
                        duration,
                    )
            else:
                # Delete short/empty recording
                filepath = os.path.join(self.recordings_dir, self.recording_filename)
                if os.path.exists(filepath):
                    os.remove(filepath)

            self.is_recording = False
            self.is_greeting_recording = False
            self.recording_start_time = None
            self.recording_remote_identity = None
            self.recording_filename = None

        except Exception as e:
            RNS.log(f"Error stopping recording: {e}", RNS.LOG_ERROR)
            self.is_recording = False

    def start_greeting_recording(self):
        telephone = self.telephone_manager.telephone
        if not telephone:
            return

        # Ensure we have audio input
        if not telephone.audio_input:
            RNS.log(
                "Voicemail: No audio input available for recording greeting",
                RNS.LOG_ERROR,
            )
            return

        temp_wav = os.path.join(self.greetings_dir, "temp_greeting.wav")
        if os.path.exists(temp_wav):
            os.remove(temp_wav)

        try:
            self.greeting_recording_sink = OpusFileSink(
                os.path.join(self.greetings_dir, "greeting.opus")
            )
            self.greeting_recording_sink.samplerate = 48000

            self.greeting_recording_pipeline = Pipeline(
                source=telephone.audio_input,
                codec=Null(),
                sink=self.greeting_recording_sink,
            )
            self.greeting_recording_pipeline.start()
            self.is_greeting_recording = True
            RNS.log("Voicemail: Started recording greeting from mic", RNS.LOG_DEBUG)
        except Exception as e:
            RNS.log(
                f"Voicemail: Failed to start greeting recording: {e}", RNS.LOG_ERROR
            )

    def stop_greeting_recording(self):
        if not self.is_greeting_recording:
            return

        try:
            self.greeting_recording_pipeline.stop()
            self.greeting_recording_sink = None
            self.greeting_recording_pipeline = None
            self.is_greeting_recording = False
            RNS.log("Voicemail: Stopped recording greeting from mic", RNS.LOG_DEBUG)
        except Exception as e:
            RNS.log(f"Voicemail: Error stopping greeting recording: {e}", RNS.LOG_ERROR)
            self.is_greeting_recording = False
