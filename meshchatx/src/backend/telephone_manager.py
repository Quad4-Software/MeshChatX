import asyncio
import base64
import os
import time

import RNS
from LXST import Telephone


class Tee:
    def __init__(self, sink):
        self.sinks = [sink]

    def add_sink(self, sink):
        if sink not in self.sinks:
            self.sinks.append(sink)

    def remove_sink(self, sink):
        if sink in self.sinks:
            self.sinks.remove(sink)

    def handle_frame(self, frame, source):
        for sink in self.sinks:
            try:
                sink.handle_frame(frame, source)
            except Exception as e:
                RNS.log(f"Tee: Error in sink handle_frame: {e}", RNS.LOG_ERROR)

    def can_receive(self, from_source=None):
        return any(sink.can_receive(from_source) for sink in self.sinks)


class TelephoneManager:
    # LXST Status Constants for reference:
    # 0: STATUS_BUSY
    # 1: STATUS_REJECTED
    # 2: STATUS_CALLING
    # 3: STATUS_AVAILABLE
    # 4: STATUS_RINGING
    # 5: STATUS_CONNECTING
    # 6: STATUS_ESTABLISHED

    def __init__(
        self,
        identity: RNS.Identity,
        config_manager=None,
        storage_dir=None,
        db=None,
    ):
        self.identity = identity
        self.config_manager = config_manager
        self.storage_dir = storage_dir
        self.db = db
        self.get_name_for_identity_hash = None
        self.recordings_dir = (
            os.path.join(storage_dir, "recordings") if storage_dir else None
        )
        if self.recordings_dir:
            os.makedirs(self.recordings_dir, exist_ok=True)

        self.telephone = None
        self.on_ringing_callback = None
        self.on_established_callback = None
        self.on_ended_callback = None

        self.call_start_time = None
        self.call_status_at_end = None
        self.call_is_incoming = False
        self.call_was_established = False

        # Manual mute overrides in case LXST internal muting is buggy
        self.transmit_muted = False
        self.receive_muted = False

        self.initiation_status = None
        self.initiation_target_hash = None
        self.on_initiation_status_callback = None

    @property
    def is_recording(self):
        # Check if voicemail manager or this manager is recording
        # This is a bit of a hack since we don't have a direct link to voicemail_manager here
        # but we can check if our own recording is active if we had it.
        # For now, we'll just return False and let meshchat.py handle the combined status.
        return False

    def init_telephone(self):
        if self.telephone is not None:
            return

        self.telephone = Telephone(self.identity)
        # Disable busy tone played on caller side when remote side rejects, or doesn't answer
        self.telephone.set_busy_tone_time(0)
        # Increase connection timeout for slower networks
        self.telephone.set_connect_timeout(30)

        # Set initial profile from config
        if self.config_manager:
            profile_id = self.config_manager.telephone_audio_profile_id.get()
            self.telephone.switch_profile(profile_id)

        self.telephone.set_ringing_callback(self.on_telephone_ringing)
        self.telephone.set_established_callback(self.on_telephone_call_established)
        self.telephone.set_ended_callback(self.on_telephone_call_ended)

    def teardown(self):
        if self.telephone is not None:
            self.telephone.teardown()
            self.telephone = None

    def hangup(self):
        if self.telephone:
            try:
                self.telephone.hangup()
            except Exception as e:
                RNS.log(f"TelephoneManager: Error during hangup: {e}", RNS.LOG_ERROR)

        # Always clear initiation status on hangup to prevent "Dialing..." hang
        self._update_initiation_status(None, None)

    def register_ringing_callback(self, callback):
        self.on_ringing_callback = callback

    def register_established_callback(self, callback):
        self.on_established_callback = callback

    def register_ended_callback(self, callback):
        self.on_ended_callback = callback

    def on_telephone_ringing(self, caller_identity: RNS.Identity):
        if self.initiation_status:
            # This is an outgoing call where the remote side is now ringing.
            # We update the initiation status to "Ringing..." for the UI.
            self._update_initiation_status("Ringing...")
            return

        self.call_start_time = time.time()
        self.call_is_incoming = True
        self.call_was_established = False
        if self.on_ringing_callback:
            self.on_ringing_callback(caller_identity)

    def on_telephone_call_established(self, caller_identity: RNS.Identity):
        # Update start time to when it was actually established for duration calculation
        self.call_start_time = time.time()
        self.call_was_established = True

        # Track per-call stats from the active link (uses RNS Link counters)
        link = getattr(self.telephone, "active_call", None)
        self.call_stats = {
            "link": link,
        }

        if self.on_established_callback:
            self.on_established_callback(caller_identity)

    def on_telephone_call_ended(self, caller_identity: RNS.Identity):
        # Capture status just before ending if possible, or use the last known status
        if self.telephone:
            self.call_status_at_end = self.telephone.call_status

        # Ensure initiation status is cleared when call ends
        self._update_initiation_status(None, None)

        if self.on_ended_callback:
            self.on_ended_callback(caller_identity)

    def start_recording(self):
        # Disabled for now as LXST does not have a Tee to use
        pass

    def stop_recording(self):
        # Disabled for now
        pass

    def announce(self, attached_interface=None, display_name=None):
        if self.telephone:
            if display_name:
                import RNS.vendor.umsgpack as msgpack

                # Pack display name in LXMF-compatible app data format
                app_data = msgpack.packb([display_name, None, None])
                self.telephone.destination.announce(
                    app_data=app_data,
                    attached_interface=attached_interface,
                )
                self.telephone.last_announce = time.time()
            else:
                self.telephone.announce(attached_interface=attached_interface)

    def _update_initiation_status(self, status, target_hash=None):
        self.initiation_status = status
        if target_hash is not None or status is None:
            self.initiation_target_hash = target_hash
        if self.on_initiation_status_callback:
            try:
                self.on_initiation_status_callback(
                    self.initiation_status,
                    self.initiation_target_hash,
                )
            except Exception as e:
                RNS.log(
                    f"TelephoneManager: Error in initiation status callback: {e}",
                    RNS.LOG_ERROR,
                )

    async def initiate(self, destination_hash: bytes, timeout_seconds: int = 15):
        if self.telephone is None:
            msg = "Telephone is not initialized"
            raise RuntimeError(msg)

        if self.telephone.busy or self.initiation_status:
            msg = "Telephone is already in use"
            raise RuntimeError(msg)

        destination_hash_hex = destination_hash.hex()
        self._update_initiation_status("Resolving identity...", destination_hash_hex)

        try:

            def resolve_identity(target_hash_hex):
                """Resolve identity from multiple hints: direct recall, destination_hash announce, identity_hash announce, or public key."""
                target_hash = bytes.fromhex(target_hash_hex)

                # 1) Direct recall (identity hash)
                ident = RNS.Identity.recall(target_hash)
                if ident:
                    return ident

                if not self.db:
                    return None

                # 2) By destination_hash (could be lxst.telephony or lxmf.delivery hash)
                announce = self.db.announces.get_announce_by_hash(target_hash_hex)
                if not announce:
                    # 3) By identity_hash field (if user entered identity hash but we missed recall, or other announce types)
                    announces = self.db.announces.get_filtered_announces(
                        identity_hash=target_hash_hex,
                    )
                    if announces:
                        announce = announces[0]

                if not announce:
                    return None

                # Try identity_hash from announce
                identity_hex = announce.get("identity_hash")
                if identity_hex:
                    ident = RNS.Identity.recall(bytes.fromhex(identity_hex))
                    if ident:
                        return ident

                # Try reconstructing from public key
                if announce.get("identity_public_key"):
                    try:
                        return RNS.Identity.from_bytes(
                            base64.b64decode(announce["identity_public_key"]),
                        )
                    except Exception:
                        pass

                return None

            # Find destination identity
            destination_identity = resolve_identity(destination_hash_hex)

            if destination_identity is None:
                self._update_initiation_status("Discovering path/identity...")
                RNS.Transport.request_path(destination_hash)

                # Wait for identity to appear
                start_wait = time.time()
                while time.time() - start_wait < timeout_seconds:
                    if not self.initiation_status:  # Externally cancelled (hangup)
                        return None
                    await asyncio.sleep(0.5)
                    destination_identity = resolve_identity(destination_hash_hex)
                    if destination_identity:
                        break

            if destination_identity is None:
                self._update_initiation_status(None, None)
                msg = "Destination identity not found"
                raise RuntimeError(msg)

            if not RNS.Transport.has_path(destination_hash):
                self._update_initiation_status("Requesting path...")
                RNS.Transport.request_path(destination_hash)

                # Wait up to 10s for path discovery
                path_wait_start = time.time()
                while time.time() - path_wait_start < min(timeout_seconds, 10):
                    if not self.initiation_status:  # Externally cancelled
                        return None
                    if RNS.Transport.has_path(destination_hash):
                        break
                    await asyncio.sleep(0.5)

            self._update_initiation_status("Dialing...")
            self.call_start_time = time.time()
            self.call_is_incoming = False

            # Use a thread for the blocking LXST call, but monitor status for early exit
            # if established elsewhere or timed out/hung up
            call_task = asyncio.create_task(
                asyncio.to_thread(self.telephone.call, destination_identity),
            )

            start_wait = time.time()
            # LXST telephone.call usually returns on establishment or timeout.
            # We wait for it, but if status becomes established or ended, we can stop waiting.
            while not call_task.done():
                if not self.initiation_status:  # Externally cancelled
                    break
                if self.telephone.call_status in [
                    6,
                    0,
                    1,
                ]:  # Established, Busy, Rejected
                    break
                if self.telephone.call_status == 3 and (
                    time.time() - start_wait > 1.0
                ):  # Available (ended/timeout)
                    break
                await asyncio.sleep(0.5)

            # If the task finished but we're still ringing or connecting,
            # wait a bit more for establishment or definitive failure
            if self.initiation_status and self.telephone.call_status in [
                4,
                5,
            ]:  # Ringing, Connecting
                wait_until = time.time() + timeout_seconds
                while time.time() < wait_until:
                    if not self.initiation_status:  # Externally cancelled
                        break
                    if self.telephone.call_status in [
                        6,
                        0,
                        1,
                        3,
                    ]:  # Established, Busy, Rejected, Ended
                        break
                    await asyncio.sleep(0.5)

            return self.telephone.active_call

        except Exception as e:
            self._update_initiation_status(f"Failed: {e!s}")
            await asyncio.sleep(3)
            raise
        finally:
            # If call was successful, keep status for a moment to prevent UI flicker
            # while the frontend picks up the new active_call state
            if (
                self.telephone
                and self.telephone.active_call
                and self.telephone.call_status == 6
            ):
                await asyncio.sleep(1.5)
            self._update_initiation_status(None, None)

    def mute_transmit(self):
        if self.telephone:
            # Manual override as LXST internal muting can be buggy
            if hasattr(self.telephone, "audio_input") and self.telephone.audio_input:
                try:
                    self.telephone.audio_input.stop()
                except Exception as e:
                    RNS.log(f"Failed to stop audio input for mute: {e}", RNS.LOG_ERROR)

            # Still call the internal method just in case it does something useful
            try:
                self.telephone.mute_transmit()
            except Exception:  # noqa: S110
                pass

            self.transmit_muted = True

    def unmute_transmit(self):
        if self.telephone:
            # Manual override as LXST internal muting can be buggy
            if hasattr(self.telephone, "audio_input") and self.telephone.audio_input:
                try:
                    self.telephone.audio_input.start()
                except Exception as e:
                    RNS.log(
                        f"Failed to start audio input for unmute: {e}",
                        RNS.LOG_ERROR,
                    )

            # Still call the internal method just in case
            try:
                self.telephone.unmute_transmit()
            except Exception:  # noqa: S110
                pass

            self.transmit_muted = False

    def mute_receive(self):
        if self.telephone:
            # Manual override as LXST internal muting can be buggy
            if hasattr(self.telephone, "audio_output") and self.telephone.audio_output:
                try:
                    self.telephone.audio_output.stop()
                except Exception as e:
                    RNS.log(f"Failed to stop audio output for mute: {e}", RNS.LOG_ERROR)

            # Still call the internal method just in case
            try:
                self.telephone.mute_receive()
            except Exception:  # noqa: S110
                pass

            self.receive_muted = True

    def unmute_receive(self):
        if self.telephone:
            # Manual override as LXST internal muting can be buggy
            if hasattr(self.telephone, "audio_output") and self.telephone.audio_output:
                try:
                    self.telephone.audio_output.start()
                except Exception as e:
                    RNS.log(
                        f"Failed to start audio output for unmute: {e}",
                        RNS.LOG_ERROR,
                    )

            # Still call the internal method just in case
            try:
                self.telephone.unmute_receive()
            except Exception:  # noqa: S110
                pass

            self.receive_muted = False
