"""Environment variable parsing helpers."""

import os


def env_bool(env_name, default=False):
    val = os.environ.get(env_name)
    if val is None:
        return default
    return val.lower() in ("true", "1", "yes", "on")
