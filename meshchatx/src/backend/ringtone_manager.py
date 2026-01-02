import os
import shutil
import subprocess

import RNS


class RingtoneManager:
    def __init__(self, config, storage_dir):
        self.config = config
        self.storage_dir = os.path.join(storage_dir, "ringtones")

        # Ensure directory exists
        os.makedirs(self.storage_dir, exist_ok=True)

        # Paths to executables
        self.ffmpeg_path = self._find_ffmpeg()
        self.has_ffmpeg = self.ffmpeg_path is not None

        if self.has_ffmpeg:
            RNS.log(f"Ringtone: Found ffmpeg at {self.ffmpeg_path}", RNS.LOG_DEBUG)
        else:
            RNS.log("Ringtone: ffmpeg not found", RNS.LOG_ERROR)

    def _find_ffmpeg(self):
        path = shutil.which("ffmpeg")
        if path:
            return path
        return None

    def convert_to_ringtone(self, input_path, ringtone_id=None):
        if not self.has_ffmpeg:
            msg = "ffmpeg is required for audio conversion"
            raise RuntimeError(msg)

        import secrets
        filename = f"ringtone_{secrets.token_hex(8)}.opus"
        opus_path = os.path.join(self.storage_dir, filename)

        subprocess.run(
            [
                self.ffmpeg_path,
                "-i",
                input_path,
                "-c:a",
                "libopus",
                "-b:a",
                "32k",
                "-vbr",
                "on",
                opus_path,
            ],
            check=True,
        )

        return filename

    def remove_ringtone(self, filename):
        opus_path = os.path.join(self.storage_dir, filename)
        if os.path.exists(opus_path):
            os.remove(opus_path)
        return True

    def get_ringtone_path(self, filename):
        return os.path.join(self.storage_dir, filename)

