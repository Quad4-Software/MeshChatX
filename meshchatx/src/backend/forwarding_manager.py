import base64

import RNS

from .database import Database


class ForwardingManager:
    def __init__(self, db: Database, message_router):
        self.db = db
        self.message_router = message_router
        self.forwarding_destinations = {}

    def load_aliases(self):
        mappings = self.db.messages.get_all_forwarding_mappings()
        for mapping in mappings:
            try:
                private_key_bytes = base64.b64decode(mapping["alias_identity_private_key"])
                alias_identity = RNS.Identity.from_bytes(private_key_bytes)
                alias_destination = self.message_router.register_delivery_identity(identity=alias_identity)
                self.forwarding_destinations[mapping["alias_hash"]] = alias_destination
            except Exception as e:
                print(f"Failed to load forwarding alias {mapping['alias_hash']}: {e}")

    def get_or_create_mapping(self, source_hash, final_recipient_hash, original_destination_hash):
        mapping = self.db.messages.get_forwarding_mapping(
            original_sender_hash=source_hash,
            final_recipient_hash=final_recipient_hash,
        )

        if not mapping:
            alias_identity = RNS.Identity()
            alias_hash = alias_identity.hash.hex()

            alias_destination = self.message_router.register_delivery_identity(alias_identity)
            self.forwarding_destinations[alias_hash] = alias_destination

            data = {
                "alias_identity_private_key": base64.b64encode(alias_identity.get_private_key()).decode(),
                "alias_hash": alias_hash,
                "original_sender_hash": source_hash,
                "final_recipient_hash": final_recipient_hash,
                "original_destination_hash": original_destination_hash,
            }
            self.db.messages.create_forwarding_mapping(data)
            return data
        return mapping

