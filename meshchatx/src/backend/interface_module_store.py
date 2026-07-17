# SPDX-License-Identifier: 0BSD

"""Install custom Reticulum interface modules into configdir/interfaces."""

from __future__ import annotations

import contextlib
import os
import re
import tempfile

_MODULE_NAME_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")
_MAX_MODULE_BYTES = 512 * 1024


def interface_modules_dir(reticulum_config_dir: str | None) -> str:
    """Return the RNS interfacepath directory for this MeshChatX instance."""
    if not reticulum_config_dir:
        raise ValueError("Reticulum config directory is not configured")
    root = os.path.abspath(os.path.expanduser(str(reticulum_config_dir)))
    return os.path.join(root, "interfaces")


def sanitize_interface_module_stem(name: str | None) -> str | None:
    """Return a safe TypeName stem, or None when the name is invalid."""
    if not name or not isinstance(name, str):
        return None
    raw = name.strip()
    if not raw or "/" in raw or "\\" in raw or ".." in raw:
        return None
    stem = os.path.basename(raw)
    if stem.lower().endswith(".py"):
        stem = stem[:-3]
    if not _MODULE_NAME_RE.fullmatch(stem):
        return None
    return stem


def validate_interface_module_source(data: bytes) -> str | None:
    """Return an error message when module bytes are unsafe or incomplete."""
    if not data:
        return "Interface module file is empty"
    if len(data) > _MAX_MODULE_BYTES:
        return f"Interface module is too large (max {_MAX_MODULE_BYTES} bytes)"
    try:
        text = data.decode("utf-8")
    except UnicodeDecodeError:
        return "Interface module must be UTF-8 text"
    if "\x00" in text:
        return "Interface module must be plain text"
    if "interface_class" not in text:
        return (
            "Interface module must define interface_class "
            "(RNS loads TypeName.py and expects that name)"
        )
    return None


def list_interface_modules(reticulum_config_dir: str | None) -> dict:
    """List installed *.py modules under interfacepath."""
    path = interface_modules_dir(reticulum_config_dir)
    modules: list[dict] = []
    if os.path.isdir(path):
        for entry in sorted(os.listdir(path)):
            if not entry.endswith(".py") or entry.startswith("."):
                continue
            stem = sanitize_interface_module_stem(entry)
            if stem is None:
                continue
            full = os.path.join(path, entry)
            if not os.path.isfile(full):
                continue
            try:
                size = os.path.getsize(full)
            except OSError:
                size = 0
            modules.append({"type": stem, "filename": entry, "size": size})
    return {
        "interfacepath": path,
        "modules": modules,
    }


def install_interface_module(
    reticulum_config_dir: str | None,
    *,
    filename: str | None,
    data: bytes,
    overwrite: bool = False,
) -> dict:
    """Write a custom interface module into interfacepath.

    Returns a dict with type, filename, path, and interfacepath.
    Raises ValueError on validation failures.
    """
    err = validate_interface_module_source(data)
    if err:
        raise ValueError(err)
    stem = sanitize_interface_module_stem(filename)
    if stem is None:
        raise ValueError(
            "Filename must be a Python identifier plus .py (example: WeaveInterface.py)"
        )
    target_dir = interface_modules_dir(reticulum_config_dir)
    os.makedirs(target_dir, mode=0o700, exist_ok=True)
    target_name = f"{stem}.py"
    target_path = os.path.join(target_dir, target_name)
    if os.path.exists(target_path) and not overwrite:
        raise ValueError(
            f"{target_name} already exists. Re-upload with overwrite enabled "
            "to replace it."
        )
    fd, tmp_path = tempfile.mkstemp(prefix=".iface_", suffix=".py", dir=target_dir)
    try:
        with os.fdopen(fd, "wb") as handle:
            handle.write(data)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(tmp_path, target_path)
    except Exception:
        with contextlib.suppress(OSError):
            os.remove(tmp_path)
        raise
    with contextlib.suppress(OSError):
        os.chmod(target_path, 0o600)
    return {
        "type": stem,
        "filename": target_name,
        "path": target_path,
        "interfacepath": target_dir,
        "size": len(data),
    }


def delete_interface_module(
    reticulum_config_dir: str | None,
    type_name: str | None,
) -> dict:
    """Delete an installed interface module by type stem."""
    stem = sanitize_interface_module_stem(type_name)
    if stem is None:
        raise ValueError("Invalid interface module type name")
    target_dir = interface_modules_dir(reticulum_config_dir)
    target_path = os.path.join(target_dir, f"{stem}.py")
    if not os.path.isfile(target_path):
        raise FileNotFoundError(f"{stem}.py is not installed")
    os.remove(target_path)
    return {
        "type": stem,
        "filename": f"{stem}.py",
        "interfacepath": target_dir,
    }
