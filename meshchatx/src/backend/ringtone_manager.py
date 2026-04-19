# SPDX-License-Identifier: 0BSD

import os

from .audio_codec import encode_audio_to_ogg_opus


def _ringtone_profile():
    """Stereo 48 kHz Opus ``audio`` profile for music-grade ringtones."""
    from LXST.Codecs import Opus

    return Opus.PROFILE_AUDIO_MAX


class RingtoneManager:
    def __init__(self, config, storage_dir):
        self.config = config
        self.storage_dir = os.path.join(storage_dir, "ringtones")

        os.makedirs(self.storage_dir, exist_ok=True)

    def convert_to_ringtone(self, input_path, ringtone_id=None):
        """Decode ``input_path`` and re-encode it as an OGG/Opus ringtone.

        Accepts any audio container miniaudio can decode (WAV, MP3, FLAC,
        OGG/Vorbis) plus OGG/Opus via LXST. Encoded with the music
        ``audio`` profile so trim edits preserve the original duration
        and stereo image instead of being forced through the low-bitrate
        voice profile. Returns the stored filename.
        """
        import secrets

        filename = f"ringtone_{secrets.token_hex(8)}.opus"
        opus_path = os.path.join(self.storage_dir, filename)
        encode_audio_to_ogg_opus(input_path, opus_path, profile=_ringtone_profile())
        return filename

    def remove_ringtone(self, filename):
        opus_path = os.path.join(self.storage_dir, filename)
        if os.path.exists(opus_path):
            os.remove(opus_path)
        return True

    def get_ringtone_path(self, filename):
        return os.path.join(self.storage_dir, filename)
