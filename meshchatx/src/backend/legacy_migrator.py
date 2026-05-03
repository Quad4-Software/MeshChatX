# SPDX-License-Identifier: 0BSD

import os
import shutil

import RNS

LEGACY_DIR = ".reticulum-meshchat"
CURRENT_DIR = ".reticulum-meshchatx"


def _basename_norm(p: str) -> str:
    return os.path.basename(os.path.normpath(p))


def paired_legacy_from_new(new_storage_path: str) -> str | None:
    if _basename_norm(new_storage_path) != CURRENT_DIR:
        return None
    parent = os.path.dirname(os.path.normpath(new_storage_path))
    return os.path.join(parent, LEGACY_DIR)


def paired_new_from_legacy(legacy_storage_path: str) -> str | None:
    if _basename_norm(legacy_storage_path) != LEGACY_DIR:
        return None
    parent = os.path.dirname(os.path.normpath(legacy_storage_path))
    return os.path.join(parent, CURRENT_DIR)


def storage_has_meshchat_data(storage_dir: str) -> bool:
    if not storage_dir or not os.path.isdir(storage_dir):
        return False
    ident = os.path.join(storage_dir, "identity")
    if os.path.isfile(ident) and os.path.getsize(ident) > 0:
        return True
    ids = os.path.join(storage_dir, "identities")
    if not os.path.isdir(ids):
        return False
    try:
        for sub in os.listdir(ids):
            dbp = os.path.join(ids, sub, "database.db")
            if os.path.isfile(dbp):
                return True
    except OSError:
        return False
    return False


def resolve_startup_storage(request_dir: str) -> tuple[str, dict]:
    planned = os.path.abspath(os.path.expanduser(request_dir))
    empty_ctx: dict = {"show_choice": False}
    skip = os.environ.get("MESHCHAT_SKIP_LEGACY_MIGRATION_UI", "").strip().lower() in (
        "1",
        "true",
        "yes",
    )
    if skip:
        return planned, empty_ctx

    base = _basename_norm(planned)
    if base == CURRENT_DIR and not storage_has_meshchat_data(planned):
        legacy = paired_legacy_from_new(planned)
        if legacy and storage_has_meshchat_data(legacy):
            return legacy, {
                "show_choice": True,
                "legacy_path": legacy,
                "target_path": planned,
                "mode": "redirect_to_legacy",
            }
    if base == LEGACY_DIR and storage_has_meshchat_data(planned):
        target = paired_new_from_legacy(planned)
        if target:
            return planned, {
                "show_choice": True,
                "legacy_path": planned,
                "target_path": target,
                "mode": "on_legacy_path",
            }
    return planned, empty_ctx


def _copy_file(src: str, dst: str) -> None:
    os.makedirs(os.path.dirname(dst), exist_ok=True)
    shutil.copy2(src, dst, follow_symlinks=False)


def copy_legacy_storage_tree(src_root: str, dst_root: str) -> None:
    src_root = os.path.realpath(src_root)
    dst_root = os.path.realpath(dst_root)
    if src_root == dst_root:
        raise ValueError("same path")
    if not os.path.isdir(src_root):
        raise ValueError("missing source")
    os.makedirs(dst_root, exist_ok=True)
    for root, dirs, files in os.walk(src_root, topdown=True, followlinks=False):
        dirs[:] = [d for d in dirs if d != "__pycache__"]
        rel = os.path.relpath(root, src_root)
        dest_dir = dst_root if rel == "." else os.path.join(dst_root, rel)
        os.makedirs(dest_dir, exist_ok=True)
        for name in files:
            if name.endswith((".pyc",)):
                continue
            sp = os.path.join(root, name)
            dp = os.path.join(dest_dir, name)
            if os.path.islink(sp):
                link = os.readlink(sp)
                if os.path.exists(dp):
                    os.unlink(dp)
                os.symlink(link, dp)
            else:
                _copy_file(sp, dp)


def migrate_legacy_to_target(legacy_path: str, target_path: str) -> None:
    if storage_has_meshchat_data(target_path):
        raise ValueError("target already has data")
    copy_legacy_storage_tree(legacy_path, target_path)


def fresh_storage_at_target(target_path: str) -> None:
    if storage_has_meshchat_data(target_path):
        raise ValueError("target not empty")
    os.makedirs(target_path, exist_ok=True)
    ident = RNS.Identity(create_keys=True)
    with open(os.path.join(target_path, "identity"), "wb") as f:
        f.write(ident.get_private_key())


def assert_migration_context_paths(ctx: dict, legacy: str, target: str) -> None:
    if not ctx.get("show_choice"):
        raise ValueError("invalid context")
    if os.path.realpath(legacy) != os.path.realpath(ctx["legacy_path"]):
        raise ValueError("legacy mismatch")
    if os.path.realpath(target) != os.path.realpath(ctx["target_path"]):
        raise ValueError("target mismatch")
