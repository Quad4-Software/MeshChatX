# SPDX-License-Identifier: 0BSD

import base64
import contextlib
import os
import threading

import RNS

from .database import Database
from .meshchat_utils import create_lxmf_router


class ForwardingManager:
    def __init__(
        self,
        db: Database,
        storage_path: str,
        delivery_callback,
        config=None,
        inbound_policy_installer=None,
    ):
        self.db = db
        self.storage_path = storage_path
        self.delivery_callback = delivery_callback
        self.config = config
        self.inbound_policy_installer = inbound_policy_installer
        self.forwarding_destinations = {}
        self.forwarding_routers = {}
        # Guards forwarding_destinations/forwarding_routers: RNS delivery
        # callbacks mutate them while announce/teardown iterate them.
        self._lock = threading.Lock()

    def _install_inbound_policy(self, router):
        if self.inbound_policy_installer is not None:
            self.inbound_policy_installer(router)

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

                router = create_lxmf_router(
                    identity=alias_identity,
                    storagepath=router_storage_path,
                )
                router.PROCESSING_INTERVAL = 1
                if self.config:
                    router.delivery_per_transfer_limit = (
                        self.config.lxmf_delivery_transfer_limit_in_bytes.get() / 1000
                    )

                router.register_delivery_callback(self.delivery_callback)
                self._install_inbound_policy(router)

                alias_destination = router.register_delivery_identity(
                    identity=alias_identity,
                )

                with self._lock:
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
        # Read-then-create must be atomic: concurrent deliveries for the
        # same sender/recipient pair would otherwise create duplicate
        # alias routers and mappings.
        with self._lock:
            mapping = self.db.messages.get_forwarding_mapping(
                original_sender_hash=source_hash,
                final_recipient_hash=final_recipient_hash,
            )

            if mapping:
                return mapping

            alias_identity = RNS.Identity()
            alias_hash = alias_identity.hash.hex()

            # create temp router for this alias
            router_storage_path = os.path.join(
                self.storage_path,
                "forwarding",
                alias_hash,
            )
            os.makedirs(router_storage_path, exist_ok=True)

            router = create_lxmf_router(
                identity=alias_identity,
                storagepath=router_storage_path,
            )
            router.PROCESSING_INTERVAL = 1
            if self.config:
                router.delivery_per_transfer_limit = (
                    self.config.lxmf_delivery_transfer_limit_in_bytes.get() / 1000
                )

            router.register_delivery_callback(self.delivery_callback)
            self._install_inbound_policy(router)

            alias_destination = router.register_delivery_identity(
                identity=alias_identity,
            )

            private_key = alias_identity.get_private_key()
            if not private_key:
                msg = "alias identity has no private key"
                raise ValueError(msg)

            data = {
                "alias_identity_private_key": base64.b64encode(
                    private_key,
                ).decode(),
                "alias_hash": alias_hash,
                "original_sender_hash": source_hash,
                "final_recipient_hash": final_recipient_hash,
                "original_destination_hash": original_destination_hash,
            }
            try:
                self.db.messages.create_forwarding_mapping(data)
            except Exception:
                # The destination is already registered with RNS, so undo
                # the registration before propagating the failure.
                self._stop_router(alias_hash, router)
                raise
            self.forwarding_destinations[alias_hash] = alias_destination
            self.forwarding_routers[alias_hash] = router
            return data

    def announce_aliases(self):
        with self._lock:
            destinations = list(self.forwarding_destinations.values())
        for destination in destinations:
            destination.announce()

    def _stop_router(self, alias_hash, router):
        """Best-effort stop of one alias router and its RNS destinations."""
        try:
            if hasattr(router, "register_delivery_callback"):
                with contextlib.suppress(Exception):
                    router.register_delivery_callback(None)
            if hasattr(router, "delivery_destinations"):
                for dest_hash in list(router.delivery_destinations.keys()):
                    dest = router.delivery_destinations[dest_hash]
                    with contextlib.suppress(Exception):
                        RNS.Transport.deregister_destination(dest)
            if getattr(router, "propagation_destination", None):
                with contextlib.suppress(Exception):
                    RNS.Transport.deregister_destination(
                        router.propagation_destination,
                    )
        except Exception as e:
            print(f"Error deregistering forwarding destinations {alias_hash}: {e}")
        try:
            if hasattr(router, "identity") and router.identity:
                ih = router.identity.hash
                for link in list(RNS.Transport.active_links):
                    match = False
                    if hasattr(link, "destination") and link.destination:
                        if (
                            hasattr(link.destination, "identity")
                            and link.destination.identity
                        ):
                            if link.destination.identity.hash == ih:
                                match = True
                    if match:
                        with contextlib.suppress(Exception):
                            link.teardown()
        except Exception as e:
            print(f"Error cleaning forwarding links {alias_hash}: {e}")
        try:
            router.jobs = lambda: None
            if hasattr(router, "exit_handler"):
                router.exit_handler()
        except Exception as e:
            print(f"Error stopping forwarding LXMF router {alias_hash}: {e}")

    def teardown(self):
        """Stop alias LXMF routers and deregister their RNS destinations."""
        with self._lock:
            routers = list(self.forwarding_routers.items())
            self.forwarding_destinations.clear()
            self.forwarding_routers.clear()
        for alias_hash, router in routers:
            self._stop_router(alias_hash, router)
