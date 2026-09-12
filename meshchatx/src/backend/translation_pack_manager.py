# SPDX-License-Identifier: 0BSD

"""Local offline translation pack storage, import, validation, and serving.

Packs are user-imported archives. The app never downloads them from the network.
Imported packs live under <storage_dir>/translation-packs/ and are served
same-origin to the Bergamot WASM worker.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import shutil
import tarfile
import tempfile
import zipfile

import RNS

from meshchatx.src.path_utils import (
    PathJailError,
    is_path_within_dir,
    resolve_path_under_dir,
    resolve_under_root,
    safe_path_under_dir,
)

_ALLOWED_FILE_NAME_RE = re.compile(r"^[A-Za-z0-9@\-][A-Za-z0-9_.@\- ]*$")
_PAIR_CODE_RE = re.compile(r"^[a-zA-Z]{4}$")
_FILE_TYPE_RE = re.compile(
    r"^(model|lex|vocab|qualityModel|srcvocab|trgvocab)[^A-Za-z0-9]", re.IGNORECASE
)
_REQUIRED_PARTS = frozenset({"model", "lex", "vocab"})


class TranslationPackError(ValueError):
    """Raised when a pack archive or file fails validation."""


class TranslationPackManager:
    def __init__(self, storage_dir: str) -> None:
        self.storage_dir = storage_dir
        self.packs_dir = os.path.join(storage_dir, "translation-packs")
        self.incoming_dir = os.path.join(self.packs_dir, "incoming")
        self.registry_path = os.path.join(self.packs_dir, "registry.json")
        self._registry_cache: dict | None = None
        os.makedirs(self.packs_dir, exist_ok=True)
        os.makedirs(self.incoming_dir, exist_ok=True)
        self._rebuild_registry()

    def packs_root(self) -> str:
        return self.packs_dir

    def list_installed(self) -> list[dict]:
        """Return installed packs with pair, from, to, size, and version."""
        registry = self._load_registry()
        packs: list[dict] = []
        for pair, entry in sorted(registry.items()):
            if not _PAIR_CODE_RE.match(pair):
                continue
            from_lang = entry.get("from", pair[:2])
            to_lang = entry.get("to", pair[2:4])
            files = entry.get("files", {})
            total_size = sum(
                f.get("size", 0) for f in files.values() if isinstance(f, dict)
            )
            packs.append(
                {
                    "pair": pair,
                    "from": from_lang,
                    "to": to_lang,
                    "version": entry.get("version", ""),
                    "size": total_size,
                    "files": list(files.keys()),
                }
            )
        return packs

    def import_archive(self, archive_path: str) -> list[str]:
        """Extract an archive into incoming, validate, and install each pack."""
        tmp_dir = tempfile.mkdtemp(dir=self.incoming_dir)
        try:
            if tarfile.is_tarfile(archive_path):
                with tarfile.open(archive_path, "r:*") as tf:
                    for member in tf.getmembers():
                        if not member.isreg() and not member.isdir():
                            continue
                        if member.issym() or member.islnk():
                            continue
                        if member.name.startswith(("/", "\\")) or os.path.isabs(
                            member.name
                        ):
                            continue
                        target = resolve_path_under_dir(tmp_dir, member.name)
                        if not target or not is_path_within_dir(target, tmp_dir):
                            continue
                        if member.isdir():
                            os.makedirs(target, exist_ok=True)
                        else:
                            os.makedirs(os.path.dirname(target), exist_ok=True)
                            with open(target, "wb") as f:
                                f.write(tf.extractfile(member).read())
            elif zipfile.is_zipfile(archive_path):
                with zipfile.ZipFile(archive_path, "r") as zf:
                    for info in zf.infolist():
                        if info.is_dir():
                            continue
                        if info.filename.startswith(("/", "\\")) or os.path.isabs(
                            info.filename
                        ):
                            continue
                        target = resolve_path_under_dir(tmp_dir, info.filename)
                        if not target or not is_path_within_dir(target, tmp_dir):
                            continue
                        os.makedirs(os.path.dirname(target), exist_ok=True)
                        with open(target, "wb") as f:
                            f.write(zf.read(info))
            else:
                raise TranslationPackError("Unsupported archive format")

            pairs = self._install_from_directory(tmp_dir)
            self._rebuild_registry()
            return pairs
        finally:
            shutil.rmtree(tmp_dir, ignore_errors=True)
            try:
                os.remove(archive_path)
            except OSError:
                pass

    def remove_pack(self, pair: str) -> bool:
        if not _PAIR_CODE_RE.match(pair):
            return False
        pair_dir = os.path.join(self.packs_dir, pair)
        if not os.path.isdir(pair_dir):
            return False
        shutil.rmtree(pair_dir, ignore_errors=True)
        self._rebuild_registry()
        return True

    def safe_file_path(self, requested: str) -> str | None:
        """Return the absolute path to a pack file, or None if outside packs_dir."""
        if not isinstance(requested, str) or not requested or "\x00" in requested:
            return None
        try:
            return resolve_under_root(
                self.packs_dir,
                requested,
                strict=True,
                must_be_file=True,
            )
        except PathJailError:
            return None

    def _install_from_directory(self, source_dir: str) -> list[str]:
        registry_path = os.path.join(source_dir, "registry.json")

        if os.path.isfile(registry_path):
            with open(registry_path, encoding="utf-8") as f:
                registry = json.load(f)
            return self._install_registry(source_dir, registry)

        # Single-pair archive: look for pack.json or a single pair directory.
        pack_json_path = os.path.join(source_dir, "pack.json")
        if os.path.isfile(pack_json_path):
            with open(pack_json_path, encoding="utf-8") as f:
                pack = json.load(f)
            return self._install_pack(source_dir, pack)

        dirs = sorted(
            e
            for e in os.listdir(source_dir)
            if os.path.isdir(os.path.join(source_dir, e))
        )
        if len(dirs) == 1 and _PAIR_CODE_RE.match(dirs[0]):
            pair = dirs[0].lower()
            pack = self._infer_pack_from_directory(os.path.join(source_dir, pair), pair)
            return self._install_pack(source_dir, pack)

        raise TranslationPackError(
            "No registry.json, pack.json, or single pair directory found"
        )

    def _install_registry(self, source_dir: str, registry: dict) -> list[str]:
        installed: list[str] = []
        for pair, entry in registry.items():
            pair = str(pair).lower()
            if not _PAIR_CODE_RE.match(pair):
                continue
            pair_dir = os.path.join(source_dir, pair)
            if not os.path.isdir(pair_dir):
                raise TranslationPackError(f"Pair {pair} missing directory")
            pack = {
                "id": pair,
                "from": entry.get("from", pair[:2]),
                "to": entry.get("to", pair[2:4]),
                "version": entry.get("version", ""),
                "files": self._normalise_files(entry.get("files", {}), pair),
            }
            # If files were not declared by type, try to infer from the directory.
            if not pack["files"]:
                pack["files"] = self._infer_files_from_directory(pair_dir, pair)
            installed.extend(self._install_pack(source_dir, pack))
        return installed

    def _install_pack(self, source_dir: str, pack: dict) -> list[str]:
        pair = str(pack.get("id", pack.get("from", "") + pack.get("to", ""))).lower()
        if not _PAIR_CODE_RE.match(pair):
            raise TranslationPackError(f"Invalid pack id: {pair}")

        source_pair_dir = os.path.join(source_dir, pair)
        if not os.path.isdir(source_pair_dir):
            raise TranslationPackError(f"Pack directory missing: {pair}")

        files = pack.get("files", {})
        if not files:
            files = self._infer_files_from_directory(source_pair_dir, pair)
            pack["files"] = files

        self._validate_pack_metadata(source_pair_dir, files)

        dest_dir = os.path.join(self.packs_dir, pair)
        if os.path.exists(dest_dir):
            shutil.rmtree(dest_dir, ignore_errors=True)
        os.makedirs(dest_dir, exist_ok=True)
        allowed_basenames = {
            os.path.basename(meta.get("name", "")) for meta in files.values()
        }
        for filename in os.listdir(source_pair_dir):
            if filename not in allowed_basenames:
                continue
            src = os.path.join(source_pair_dir, filename)
            if not os.path.isfile(src):
                continue
            shutil.copy2(src, os.path.join(dest_dir, filename))

        # Write a normalised pack.json for future registry rebuilds.
        pack["id"] = pair
        pack.setdefault("from", pair[:2])
        pack.setdefault("to", pair[2:4])
        pack.setdefault("version", "")
        with open(os.path.join(dest_dir, "pack.json"), "w", encoding="utf-8") as f:
            json.dump(pack, f, indent=2)

        return [pair]

    def _validate_pack_metadata(self, pair_dir: str, files: dict) -> None:
        parts = set(files.keys())
        missing_required = _REQUIRED_PARTS - parts
        if missing_required:
            raise TranslationPackError(
                f"Missing required model parts: {', '.join(sorted(missing_required))}"
            )

        for part, meta in files.items():
            if not isinstance(meta, dict):
                raise TranslationPackError(f"File entry for {part} is not an object")
            filename = os.path.basename(meta.get("name", ""))
            if not filename:
                raise TranslationPackError(f"File entry for {part} has no name")
            if not _ALLOWED_FILE_NAME_RE.match(filename):
                raise TranslationPackError(f"Disallowed file name: {filename}")
            file_path = safe_path_under_dir(pair_dir, filename)
            if not file_path or not os.path.isfile(file_path):
                raise TranslationPackError(f"File missing in pack: {filename}")
            stat = os.stat(file_path)
            meta["size"] = stat.st_size
            checksum = meta.get("expectedSha256Hash")
            if checksum:
                actual = self._sha256_file(file_path)
                if actual.lower() != str(checksum).lower():
                    raise TranslationPackError(f"Checksum mismatch for {filename}")

    def _infer_pack_from_directory(self, pair_dir: str, pair: str) -> dict:
        return {
            "id": pair,
            "from": pair[:2],
            "to": pair[2:4],
            "files": self._infer_files_from_directory(pair_dir, pair),
        }

    def _infer_files_from_directory(self, pair_dir: str, pair: str) -> dict:
        files: dict = {}
        for filename in sorted(os.listdir(pair_dir)):
            if not _ALLOWED_FILE_NAME_RE.match(filename):
                continue
            file_path = os.path.join(pair_dir, filename)
            if not os.path.isfile(file_path):
                continue
            match = _FILE_TYPE_RE.match(filename)
            part = match.group(1).lower() if match else None
            if part == "qualitymodel":
                part = "qualityModel"
            if not part:
                continue
            stat = os.stat(file_path)
            files[part] = {
                "name": f"/translation-packs/{pair}/{filename}",
                "size": stat.st_size,
            }
        return files

    def _normalise_files(self, declared: dict, pair: str) -> dict:
        """Rewrite declared file entries to local same-origin paths and add sizes."""
        normalised: dict = {}
        for part, meta in declared.items():
            if not isinstance(meta, dict):
                continue
            filename = os.path.basename(meta.get("name", ""))
            if not filename:
                continue
            if part == "qualityModel" or part == "qualitymodel":
                part = "qualityModel"
            entry = dict(meta)
            entry["name"] = f"/translation-packs/{pair}/{filename}"
            if "size" not in entry:
                entry["size"] = 0
            normalised[part] = entry
        return normalised

    def _rebuild_registry(self) -> None:
        registry: dict = {}
        for pair in sorted(os.listdir(self.packs_dir)):
            pair_dir = os.path.join(self.packs_dir, pair)
            if not os.path.isdir(pair_dir) or pair == "incoming":
                continue
            if not _PAIR_CODE_RE.match(pair):
                continue
            pack_json = os.path.join(pair_dir, "pack.json")
            pack: dict = {"from": pair[:2], "to": pair[2:4], "files": {}}
            if os.path.isfile(pack_json):
                try:
                    with open(pack_json, encoding="utf-8") as f:
                        pack = json.load(f)
                except (OSError, json.JSONDecodeError):
                    pass
            pack.setdefault("from", pair[:2])
            pack.setdefault("to", pair[2:4])
            pack["files"] = self._normalise_files(pack.get("files", {}), pair)
            try:
                self._validate_pack_metadata(pair_dir, pack["files"])
            except TranslationPackError as e:
                RNS.log(
                    f"Skipping invalid translation pack {pair}: {e}", RNS.LOG_WARNING
                )
                continue
            if pack["files"]:
                registry[pair] = pack

        with open(self.registry_path, "w", encoding="utf-8") as f:
            json.dump(registry, f, indent=2)
        self._registry_cache = registry

    def _load_registry(self) -> dict:
        if self._registry_cache is not None:
            return self._registry_cache
        if not os.path.isfile(self.registry_path):
            self._registry_cache = {}
            return self._registry_cache
        registry = {}
        try:
            with open(self.registry_path, encoding="utf-8") as f:
                registry = json.load(f)
        except (OSError, json.JSONDecodeError):
            RNS.log("Failed to load translation pack registry", RNS.LOG_ERROR)
        self._registry_cache = registry
        return registry

    @staticmethod
    def _sha256_file(file_path: str) -> str:
        h = hashlib.sha256()
        with open(file_path, "rb") as f:
            for chunk in iter(lambda: f.read(65536), b""):
                h.update(chunk)
        return h.hexdigest()
