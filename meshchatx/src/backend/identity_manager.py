import base64
import contextlib
import json
import os
import shutil

import RNS

from meshchatx.src.backend.database.config import ConfigDAO
from meshchatx.src.backend.database.provider import DatabaseProvider
from meshchatx.src.backend.database.schema import DatabaseSchema


class IdentityManager:
    def __init__(self, storage_dir: str, identity_file_path: str | None = None):
        self.storage_dir = storage_dir
        self.identity_file_path = identity_file_path

    def get_identity_bytes(self, identity: RNS.Identity) -> bytes:
        return identity.get_private_key()

    def backup_identity(self, identity: RNS.Identity) -> dict:
        identity_bytes = self.get_identity_bytes(identity)
        target_path = self.identity_file_path or os.path.join(
            self.storage_dir,
            "identity",
        )
        os.makedirs(os.path.dirname(target_path), exist_ok=True)
        with open(target_path, "wb") as f:
            f.write(identity_bytes)
        return {
            "path": target_path,
            "size": os.path.getsize(target_path),
        }

    def backup_identity_base32(self, identity: RNS.Identity) -> str:
        return base64.b32encode(self.get_identity_bytes(identity)).decode("utf-8")

    def list_identities(self, current_identity_hash: str | None = None):
        identities = []
        identities_base_dir = os.path.join(self.storage_dir, "identities")
        if not os.path.exists(identities_base_dir):
            return identities

        for identity_hash in os.listdir(identities_base_dir):
            identity_path = os.path.join(identities_base_dir, identity_hash)
            if not os.path.isdir(identity_path):
                continue

            metadata_path = os.path.join(identity_path, "metadata.json")
            metadata = None
            if os.path.exists(metadata_path):
                with contextlib.suppress(Exception):
                    with open(metadata_path) as f:
                        metadata = json.load(f)

            if metadata:
                identities.append(
                    {
                        "hash": identity_hash,
                        "display_name": metadata.get("display_name", "Anonymous Peer"),
                        "icon_name": metadata.get("icon_name"),
                        "icon_foreground_colour": metadata.get(
                            "icon_foreground_colour",
                        ),
                        "icon_background_colour": metadata.get(
                            "icon_background_colour",
                        ),
                        "lxmf_address": metadata.get("lxmf_address"),
                        "lxst_address": metadata.get("lxst_address"),
                        "is_current": (
                            current_identity_hash is not None
                            and identity_hash == current_identity_hash
                        ),
                    },
                )
                continue

            # Fallback to DB if metadata.json doesn't exist
            db_path = os.path.join(identity_path, "database.db")
            if not os.path.exists(db_path):
                continue

            display_name = "Anonymous Peer"
            icon_name = None
            icon_foreground_colour = None
            icon_background_colour = None
            lxmf_address = None
            lxst_address = None

            try:
                temp_provider = DatabaseProvider(db_path)
                temp_config_dao = ConfigDAO(temp_provider)
                display_name = temp_config_dao.get("display_name", "Anonymous Peer")
                icon_name = temp_config_dao.get("lxmf_user_icon_name")
                icon_foreground_colour = temp_config_dao.get(
                    "lxmf_user_icon_foreground_colour",
                )
                icon_background_colour = temp_config_dao.get(
                    "lxmf_user_icon_background_colour",
                )
                lxmf_address = temp_config_dao.get("lxmf_address_hash")
                lxst_address = temp_config_dao.get("lxst_address_hash")
                temp_provider.close()

                # Save metadata for next time
                metadata = {
                    "display_name": display_name,
                    "icon_name": icon_name,
                    "icon_foreground_colour": icon_foreground_colour,
                    "icon_background_colour": icon_background_colour,
                    "lxmf_address": lxmf_address,
                    "lxst_address": lxst_address,
                }
                with open(metadata_path, "w") as f:
                    json.dump(metadata, f)
            except Exception as e:
                print(f"Error reading config for {identity_hash}: {e}")

            identities.append(
                {
                    "hash": identity_hash,
                    "display_name": display_name,
                    "icon_name": icon_name,
                    "icon_foreground_colour": icon_foreground_colour,
                    "icon_background_colour": icon_background_colour,
                    "lxmf_address": lxmf_address,
                    "lxst_address": lxst_address,
                    "is_current": (
                        current_identity_hash is not None
                        and identity_hash == current_identity_hash
                    ),
                },
            )
        return identities

    def create_identity(self, display_name=None):
        new_identity = RNS.Identity(create_keys=True)
        return self._save_new_identity(new_identity, display_name or "Anonymous Peer")

    def _save_new_identity(self, identity, display_name):
        identity_hash = identity.hash.hex()

        identity_dir = os.path.join(self.storage_dir, "identities", identity_hash)
        os.makedirs(identity_dir, exist_ok=True)

        identity_file = os.path.join(identity_dir, "identity")
        with open(identity_file, "wb") as f:
            f.write(identity.get_private_key())

        db_path = os.path.join(identity_dir, "database.db")

        new_provider = DatabaseProvider(db_path)
        new_schema = DatabaseSchema(new_provider)
        new_schema.initialize()

        if display_name:
            new_config_dao = ConfigDAO(new_provider)
            new_config_dao.set("display_name", display_name)

        new_provider.close()

        # Save metadata
        metadata = {
            "display_name": display_name,
            "icon_name": None,
            "icon_foreground_colour": None,
            "icon_background_colour": None,
        }
        metadata_path = os.path.join(identity_dir, "metadata.json")
        with open(metadata_path, "w") as f:
            json.dump(metadata, f)

        return {
            "hash": identity_hash,
            "display_name": display_name,
        }

    def update_metadata_cache(self, identity_hash: str, metadata: dict):
        identity_dir = os.path.join(self.storage_dir, "identities", identity_hash)
        if not os.path.exists(identity_dir):
            return

        metadata_path = os.path.join(identity_dir, "metadata.json")

        # Merge with existing metadata if it exists
        existing_metadata = {}
        if os.path.exists(metadata_path):
            with contextlib.suppress(Exception), open(metadata_path) as f:
                existing_metadata = json.load(f)

        existing_metadata.update(metadata)

        with open(metadata_path, "w") as f:
            json.dump(existing_metadata, f)

    def delete_identity(self, identity_hash: str, current_identity_hash: str | None):
        if current_identity_hash and identity_hash == current_identity_hash:
            raise ValueError("Cannot delete the current active identity")

        identity_dir = os.path.join(self.storage_dir, "identities", identity_hash)
        if os.path.exists(identity_dir):
            shutil.rmtree(identity_dir)
            return True
        return False

    def restore_identity_from_bytes(self, identity_bytes: bytes) -> dict:
        try:
            # We use RNS.Identity.from_bytes to validate and get the hash
            identity = RNS.Identity.from_bytes(identity_bytes)
            if not identity:
                raise ValueError("Could not load identity from bytes")

            return self._save_new_identity(identity, "Restored Identity")
        except Exception as exc:
            raise ValueError(f"Failed to restore identity: {exc}")

    def restore_identity_from_base32(self, base32_value: str) -> dict:
        try:
            identity_bytes = base64.b32decode(base32_value, casefold=True)
            return self.restore_identity_from_bytes(identity_bytes)
        except Exception as exc:
            msg = f"Invalid base32 identity: {exc}"
            raise ValueError(msg) from exc
