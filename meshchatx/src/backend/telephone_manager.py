import asyncio
import time

import RNS
from LXST import Telephone


class TelephoneManager:
    def __init__(self, identity: RNS.Identity, config_manager=None):
        self.identity = identity
        self.config_manager = config_manager
        self.telephone = None
        self.on_ringing_callback = None
        self.on_established_callback = None
        self.on_ended_callback = None

        self.call_start_time = None
        self.call_status_at_end = None
        self.call_is_incoming = False

    def init_telephone(self):
        if self.telephone is not None:
            return

        self.telephone = Telephone(self.identity)
        # Disable busy tone played on caller side when remote side rejects, or doesn't answer
        self.telephone.set_busy_tone_time(0)
        self.telephone.set_ringing_callback(self.on_telephone_ringing)
        self.telephone.set_established_callback(self.on_telephone_call_established)
        self.telephone.set_ended_callback(self.on_telephone_call_ended)

    def teardown(self):
        if self.telephone is not None:
            self.telephone.teardown()
            self.telephone = None

    def register_ringing_callback(self, callback):
        self.on_ringing_callback = callback

    def register_established_callback(self, callback):
        self.on_established_callback = callback

    def register_ended_callback(self, callback):
        self.on_ended_callback = callback

    def on_telephone_ringing(self, caller_identity: RNS.Identity):
        self.call_start_time = time.time()
        self.call_is_incoming = True
        if self.on_ringing_callback:
            self.on_ringing_callback(caller_identity)

    def on_telephone_call_established(self, caller_identity: RNS.Identity):
        # Update start time to when it was actually established for duration calculation
        self.call_start_time = time.time()
        if self.on_established_callback:
            self.on_established_callback(caller_identity)

    def on_telephone_call_ended(self, caller_identity: RNS.Identity):
        # Capture status just before ending if possible, or use the last known status
        if self.telephone:
            self.call_status_at_end = self.telephone.call_status

        if self.on_ended_callback:
            self.on_ended_callback(caller_identity)

    def announce(self, attached_interface=None):
        if self.telephone:
            self.telephone.announce(attached_interface=attached_interface)

    async def initiate(self, destination_hash: bytes, timeout_seconds: int = 15):
        if self.telephone is None:
            msg = "Telephone is not initialized"
            raise RuntimeError(msg)

        # Find destination identity
        destination_identity = RNS.Identity.recall(destination_hash)
        if destination_identity is None:
            # If not found by identity hash, try as destination hash
            destination_identity = RNS.Identity.recall(
                destination_hash
            )  # Identity.recall takes identity hash

        if destination_identity is None:
            msg = "Destination identity not found"
            raise RuntimeError(msg)

        # In LXST, we just call the identity. Telephone class handles path requests.
        # But we might want to ensure a path exists first for better UX,
        # similar to how the old MeshChat did it.

        # For now, let's just use the telephone.call method which is threaded.
        # We need to run it in a thread since it might block.
        self.call_start_time = time.time()
        self.call_is_incoming = False
        await asyncio.to_thread(self.telephone.call, destination_identity)
        return self.telephone.active_call
