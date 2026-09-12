# SPDX-License-Identifier: 0BSD

"""Central JSON file persistence with corruption fallback.

Backend features historically each hand-rolled open+json.load wrapped in
slightly different except clauses, so a corrupt or oversized state file
could raise through startup or silently reset state depending on the
call site. load_json makes the safe default uniform; save_json writes
atomically via meshchatx.src.path_utils.atomic_write_text so a crash
mid-write cannot leave a truncated file behind.
"""

from __future__ import annotations

import json
import os
from typing import Any

from meshchatx.src.path_utils import atomic_write_text

# Upper bound for a state file that is not an explicitly large store.
DEFAULT_MAX_JSON_BYTES = 8 * 1024 * 1024


def load_json(
    path: str | os.PathLike[str],
    default=None,
    *,
    max_bytes: int | None = DEFAULT_MAX_JSON_BYTES,
    expect: type | tuple[type, ...] | None = None,
) -> Any:
    """Read and parse the JSON file at path; return default on any failure.

    default covers missing files, read errors, files larger than
    max_bytes, undecodable or malformed JSON, and (when expect is given)
    a top-level value of the wrong type. Pass max_bytes=None only for
    stores that legitimately grow without bound.
    """
    try:
        with open(path, "rb") as handle:
            if max_bytes is not None:
                raw = handle.read(max_bytes + 1)
                if len(raw) > max_bytes:
                    return default
            else:
                raw = handle.read()
        data = json.loads(raw.decode("utf-8"))
    except (OSError, ValueError, UnicodeDecodeError):
        return default
    if expect is not None and not isinstance(data, expect):
        return default
    return data


def load_json_required(
    path: str | os.PathLike[str],
    *,
    max_bytes: int | None = DEFAULT_MAX_JSON_BYTES,
    expect: type | tuple[type, ...] | None = None,
) -> Any:
    """load_json variant that raises ValueError instead of returning default.

    For files whose absence or corruption is itself an error (signed
    manifests, integrity stores) so callers fail closed with a generic
    message rather than echoing parse internals.
    """
    sentinel = object()
    data = load_json(path, sentinel, max_bytes=max_bytes, expect=expect)
    if data is sentinel:
        raise ValueError(f"Unreadable JSON file: {os.path.basename(os.fspath(path))}")
    return data


def save_json(
    path: str | os.PathLike[str],
    obj,
    *,
    indent: int | None = 2,
    sort_keys: bool = False,
    mode: int = 0o644,
    newline: bool = True,
    fsync_dir: bool = True,
) -> None:
    """Serialize obj and write it atomically to path.

    Raises TypeError/ValueError from json.dumps for non-serializable
    objects and OSError for write failures.
    """
    text = json.dumps(obj, indent=indent, sort_keys=sort_keys)
    if newline:
        text += "\n"
    atomic_write_text(path, text, mode=mode, fsync_dir=fsync_dir)
