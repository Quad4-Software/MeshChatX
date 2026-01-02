import base64
import os

import LXMF
import RNS

from .database import Database


class ForwardingManager:
    def __init__(self, db: Database, storage_path: str, delivery_callback, config=None):
        self.db = db
        self.storage_path = storage_path
        self.delivery_callback = delivery_callback
        self.config = config
        self.forwarding_destinations = {}
        self.forwarding_routers = {}

    def load_aliases(self):
        mappings = self.db.messages.get_all_forwarding_mappings()
        for mapping in mappings:
            try:
                private_key_bytes = base64.b64decode(
                    mapping["alias_identity_private_key"],
                )
                alias_identity = RNS.Identity.from_bytes(private_key_bytes)
                alias_hash = mapping["alias_hash"]

                # create temp router for this alias
                router_storage_path = os.path.join(
                    self.storage_path,
                    "forwarding",
                    alias_hash,
                )
                os.makedirs(router_storage_path, exist_ok=True)

                router = LXMF.LXMRouter(
                    identity=alias_identity,
                    storagepath=router_storage_path,
                )
                router.PROCESSING_INTERVAL = 1
                if self.config:
                    router.delivery_per_transfer_limit = (
                        self.config.lxmf_delivery_transfer_limit_in_bytes.get() / 1000
                    )

                router.register_delivery_callback(self.delivery_callback)

                alias_destination = router.register_delivery_identity(
                    identity=alias_identity,
                )

                self.forwarding_destinations[alias_hash] = alias_destination
                self.forwarding_routers[alias_hash] = router

            except Exception as e:
                print(f"Failed to load forwarding alias {mapping['alias_hash']}: {e}")

    def get_or_create_mapping(
        self,
        source_hash,
        final_recipient_hash,
        original_destination_hash,
    ):
        mapping = self.db.messages.get_forwarding_mapping(
            original_sender_hash=source_hash,
            final_recipient_hash=final_recipient_hash,
        )

        if not mapping:
            alias_identity = RNS.Identity()
            alias_hash = alias_identity.hash.hex()

            # create temp router for this alias
            router_storage_path = os.path.join(
                self.storage_path,
                "forwarding",
                alias_hash,
            )
            os.makedirs(router_storage_path, exist_ok=True)

            router = LXMF.LXMRouter(
                identity=alias_identity,
                storagepath=router_storage_path,
            )
            router.PROCESSING_INTERVAL = 1
            if self.config:
                router.delivery_per_transfer_limit = (
                    self.config.lxmf_delivery_transfer_limit_in_bytes.get() / 1000
                )

            router.register_delivery_callback(self.delivery_callback)

            alias_destination = router.register_delivery_identity(
                identity=alias_identity,
            )

            self.forwarding_destinations[alias_hash] = alias_destination
            self.forwarding_routers[alias_hash] = router

            data = {
                "alias_identity_private_key": base64.b64encode(
                    alias_identity.get_private_key(),
                ).decode(),
                "alias_hash": alias_hash,
                "original_sender_hash": source_hash,
                "final_recipient_hash": final_recipient_hash,
                "original_destination_hash": original_destination_hash,
            }
            self.db.messages.create_forwarding_mapping(data)
            return data
        return mapping

    def announce_aliases(self):
        for alias_hash in self.forwarding_destinations:
            destination = self.forwarding_destinations[alias_hash]
            destination.announce()
