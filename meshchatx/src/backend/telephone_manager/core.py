# SPDX-License-Identifier: 0BSD

import asyncio
import base64
import contextlib
import os
import sys
import threading
import time

import RNS

from meshchatx.src.backend import reticulum_pathfinding
from meshchatx.src.backend.meshchat_utils import (
    hex_identifier_to_bytes,
    normalize_hex_identifier,
)
from meshchatx.src.backend.path_utils import path_response_window


def __getattr__(name: str):
    # LXST pulls in numpy and audio backends, so Telephone resolves lazily
    # through module __getattr__ instead of a top-level import. Keeping the
    # name module-scoped also keeps tests patching this attribute working.
    if name == "Telephone":
        from LXST import Telephone

        return Telephone
    if name == "Tee":
        return _tee_class()
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


def _telephone_class():
    # Bare Telephone would miss module __getattr__ on a global load, so
    # resolve through the module object, which also picks up test patches.
    return sys.modules[__name__].Telephone


_TEE_CLASS = None


def _tee_class():
    """Build the Tee sink lazily so this module stays LXST-free at import."""
    global _TEE_CLASS
    if _TEE_CLASS is not None:
        return _TEE_CLASS
    from LXST.Sinks import Sink

    class Tee(Sink):
        """Fan-out sink that forwards receive frames to every child sink.

        LXST Pipeline rejects sinks that are not Sink subclasses, and
        Telephony pokes the LineSink buffer surface (buffer_max_height,
        autostart_min, streaming, wait_for_frames) on audio_output. Tee
        mirrors that surface and forwards lifecycle calls to children.
        """

        def __init__(self, sink):
            self.sinks = [sink]
            self.should_run = False
            self._streaming = getattr(sink, "streaming", False)
            self._buffer_max_height = getattr(sink, "buffer_max_height", 3)
            self._autostart_min = getattr(sink, "autostart_min", 1)
            self._channels = getattr(sink, "channels", None) or 1
            self._samplerate = getattr(sink, "samplerate", None) or 48000
            self._bitdepth = getattr(sink, "bitdepth", None) or 16

        def _mirror_attr(self, name, fallback):
            # Codecs read channels/samplerate/bitdepth off their sink. Read the
            # live child values so a sink configured after Tee creation (such
            # as OpusFileSink.samplerate) is still picked up.
            for sink in self.sinks:
                value = getattr(sink, name, None)
                if value is not None:
                    return value
            return fallback

        def _forward_attr(self, name, value):
            for sink in self.sinks:
                if not hasattr(sink, name):
                    continue
                try:
                    setattr(sink, name, value)
                except Exception as e:
                    RNS.log(
                        f"Tee: could not set {name} on {sink}: {e}",
                        RNS.LOG_ERROR,
                    )

        def _forward_call(self, name):
            for sink in self.sinks:
                method = getattr(sink, name, None)
                if not callable(method):
                    continue
                try:
                    method()
                except Exception as e:
                    RNS.log(
                        f"Tee: {name} failed on {sink}: {e}",
                        RNS.LOG_ERROR,
                    )

        @property
        def streaming(self):
            return self._streaming

        @streaming.setter
        def streaming(self, value):
            self._streaming = value
            self._forward_attr("streaming", value)

        @property
        def buffer_max_height(self):
            return self._buffer_max_height

        @buffer_max_height.setter
        def buffer_max_height(self, value):
            self._buffer_max_height = value
            self._forward_attr("buffer_max_height", value)

        @property
        def autostart_min(self):
            return self._autostart_min

        @autostart_min.setter
        def autostart_min(self, value):
            self._autostart_min = value
            self._forward_attr("autostart_min", value)

        @property
        def channels(self):
            return self._mirror_attr("channels", self._channels)

        @channels.setter
        def channels(self, value):
            self._channels = value
            self._forward_attr("channels", value)

        @property
        def samplerate(self):
            return self._mirror_attr("samplerate", self._samplerate)

        @samplerate.setter
        def samplerate(self, value):
            self._samplerate = value
            self._forward_attr("samplerate", value)

        @property
        def bitdepth(self):
            return self._mirror_attr("bitdepth", self._bitdepth)

        @bitdepth.setter
        def bitdepth(self, value):
            self._bitdepth = value
            self._forward_attr("bitdepth", value)

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

        def start(self):
            self.should_run = True
            self._forward_call("start")

        def stop(self):
            self.should_run = False
            self._forward_call("stop")

        def wait_for_frames(self):
            self._forward_call("wait_for_frames")

        def enable_low_latency(self):
            self._forward_call("enable_low_latency")

        def release(self):
            super().release()
            self._forward_call("release")

    _TEE_CLASS = Tee
    return _TEE_CLASS


def _patch_lxst_linksource_samplerate():
    """Give LXST LinkSource the samplerate attribute sinks read.

    LXST 0.5.x LinkSource never sets samplerate, but OpusFileSink and
    Mixer read source.samplerate on the first accepted frame, so every
    incoming packet raised AttributeError and voicemail recordings came
    out silent. Decoded frames run at the codec sink rate, so expose
    that (falling back to the 48 kHz pipeline rate when unset).
    """
    try:
        from LXST.Network import LinkSource
    except Exception:
        return False
    if hasattr(LinkSource, "samplerate"):
        return False

    def _samplerate(self):
        codec = getattr(self, "codec", None)
        sink = getattr(codec, "sink", None) or getattr(self, "sink", None)
        rate = getattr(sink, "samplerate", None)
        return rate or 48000

    def _set_samplerate(self, value):
        # Keep instance overrides possible; the property reads them back.
        self._samplerate_override = value

    def _get_samplerate(self):
        override = getattr(self, "_samplerate_override", None)
        if override:
            return override
        return _samplerate(self)

    LinkSource.samplerate = property(_get_samplerate, _set_samplerate)
    return True


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
        # Once-per-call latch so a duplicated ended event (local hangup plus
        # remote link close) cannot record the same call twice.
        self._call_end_recorded = False

        # Manual mute overrides in case LXST internal muting is buggy
        self.transmit_muted = False
        self.receive_muted = False
        # Half-duplex PTT state. LXST squelches the packetizer when TX is idle.
        self.ptt_active = False
        self.call_stats = {}

        self.initiation_status = None
        self.initiation_target_hash = None
        self.on_initiation_status_callback = None
        self._path_poll_interval_s = 0.05
        self._path_retry_interval_s = 1.5
        self._status_poll_interval_s = 0.1
        # Strong refs to fire-and-forget tasks so the loop cannot GC them.
        self._background_tasks: set[asyncio.Task] = set()
        self.is_voicemail_session_active = False
        self.preferred_profile_id = None
        self.preferred_mode_id = None
        self._caller_allowed = None
        self._blocked_identity_hashes = None
        # When True, LXST must not open PulseAudio LineSource/LineSink (Docker /
        # headless / Android web bridge). Set by ReticulumMeshChat.
        self.web_audio_required = False

    @property
    def is_recording(self):
        return False

    @staticmethod
    def codec2_available() -> bool:
        """Return whether LXST can construct Codec2 codecs (pycodec2 + libcodec2)."""
        try:
            from meshchatx import android_codec2

            if android_codec2._is_chaquopy_android():
                if not android_codec2.ensure_lxst_codec2_binding():
                    return False
        except Exception:
            pass
        try:
            from LXST.Codecs import Codec2

            if Codec2 is None:
                return False
            # Touch a mode constant and construct once to catch dlopen failures early.
            _ = Codec2.CODEC2_1600
            Codec2(mode=Codec2.CODEC2_1600)
            return True
        except Exception:
            return False

    def resolve_audio_profile_id(self, profile_id=None):
        """Return a valid LXST profile id, falling back when Codec2 is unavailable."""
        from LXST.Primitives.Telephony import Profiles

        available = set(Profiles.available_profiles())
        pid = profile_id
        if pid is None and self.config_manager:
            with contextlib.suppress(Exception):
                pid = self.config_manager.telephone_audio_profile_id.get()
        try:
            pid = int(pid) if pid is not None else None
        except (TypeError, ValueError):
            pid = None
        if pid not in available:
            pid = Profiles.DEFAULT_PROFILE

        codec2_profiles = {
            Profiles.BANDWIDTH_ULTRA_LOW,
            Profiles.BANDWIDTH_VERY_LOW,
            Profiles.BANDWIDTH_LOW,
        }
        if pid in codec2_profiles and not self.codec2_available():
            RNS.log(
                "TelephoneManager: Codec2 unavailable, falling back to default Opus profile",
                RNS.LOG_WARNING,
            )
            pid = Profiles.DEFAULT_PROFILE
        return pid

    def apply_preferred_profile(self, profile_id=None):
        """Store preferred profile and apply it if a call is already established."""
        self.preferred_profile_id = self.resolve_audio_profile_id(profile_id)
        if (
            self.telephone
            and self.telephone.active_call
            and self.telephone.call_status == 6
        ):
            with contextlib.suppress(Exception):
                self.telephone.switch_profile(self.preferred_profile_id)
        return self.preferred_profile_id

    def resolve_call_mode_id(self, mode_id=None):
        """Return a valid LXST call mode id (full or half duplex)."""
        from meshchatx.src.backend import lxst_profiles_compat as lxst_modes

        available = set(lxst_modes.available_modes())
        mid = mode_id
        if mid is None and self.config_manager:
            with contextlib.suppress(Exception):
                mid = self.config_manager.telephone_call_mode_id.get()
        try:
            mid = int(mid) if mid is not None else None
        except (TypeError, ValueError):
            mid = None
        if mid not in available:
            mid = lxst_modes.default_mode()
        return mid

    def apply_preferred_mode(self, mode_id=None):
        """Store preferred duplex mode and apply it on an established call."""
        self.preferred_mode_id = self.resolve_call_mode_id(mode_id)
        if (
            self.telephone
            and self.telephone.active_call
            and self.telephone.call_status == 6
        ):
            self.switch_mode(self.preferred_mode_id)
        return self.preferred_mode_id

    def switch_mode(self, mode_id):
        """Switch live call duplex mode via LXST signalling and local squelch."""
        from meshchatx.src.backend import lxst_profiles_compat as lxst_modes

        resolved = self.resolve_call_mode_id(mode_id)
        self.preferred_mode_id = resolved
        if not (
            self.telephone
            and self.telephone.active_call
            and self.telephone.call_status == 6
        ):
            return resolved
        with contextlib.suppress(Exception):
            self.telephone.switch_mode(resolved)
        # Keep local view aligned even when LXST is mocked in tests.
        with contextlib.suppress(Exception):
            self.telephone.active_call.call_mode = resolved
        # Half duplex starts listen-only. Full duplex keeps continuous TX open.
        self.ptt_active = False
        if resolved == lxst_modes.mode_half_duplex():
            with contextlib.suppress(Exception):
                self.telephone.squelch_transmit(True)
        else:
            with contextlib.suppress(Exception):
                self.telephone.unsquelch_transmit(True)
        return resolved

    def get_active_mode_id(self):
        """Return the active call mode, preferred mode, or LXST default."""
        from meshchatx.src.backend import lxst_profiles_compat as lxst_modes

        available = set(lxst_modes.available_modes())
        if self.telephone and self.telephone.active_call:
            link_mode = getattr(self.telephone.active_call, "call_mode", None)
            if link_mode in available:
                return link_mode
            mode = getattr(self.telephone, "active_mode", None)
            if mode in available:
                return mode
        if self.preferred_mode_id in available:
            return self.preferred_mode_id
        return self.resolve_call_mode_id()

    def is_half_duplex(self):
        from meshchatx.src.backend import lxst_profiles_compat as lxst_modes

        return self.get_active_mode_id() == lxst_modes.mode_half_duplex()

    def is_transmit_squelched(self):
        """True when LXST packetizer is squelched (half-duplex idle / PTT up)."""
        if not self.telephone or not self.telephone.active_call:
            return False
        packetizer = getattr(self.telephone.active_call, "packetizer", None)
        if packetizer is not None:
            return bool(getattr(packetizer, "squelched", False))
        return self.is_half_duplex() and not self.ptt_active

    def set_ptt_active(self, active: bool):
        """Push-to-talk gate for half-duplex calls (unsquelch while held)."""
        if not (
            self.telephone
            and self.telephone.active_call
            and self.telephone.call_status == 6
        ):
            self.ptt_active = False
            return False
        if not self.is_half_duplex():
            self.ptt_active = False
            return False
        want_active = bool(active)
        try:
            if want_active:
                self.telephone.unsquelch_transmit(True)
            else:
                self.telephone.squelch_transmit(True)
            self.ptt_active = want_active
            return True
        except Exception as e:
            RNS.log(f"TelephoneManager: PTT squelch failed: {e}", RNS.LOG_ERROR)
            return False

    def _reset_call_audio_controls(self):
        self.transmit_muted = False
        self.receive_muted = False
        self.ptt_active = False
        self.call_stats = {}

    def init_telephone(self):
        if self.telephone is not None:
            return
        if self.config_manager and not self.config_manager.telephone_enabled.get():
            return

        if self.web_audio_required:
            from meshchatx.src.backend.web_audio_bridge import (
                install_hostless_lxst_audio,
            )

            install_hostless_lxst_audio()

        _patch_lxst_linksource_samplerate()

        # Never enable LXST auto_answer. MeshChatX answers only via explicit
        # user action or the separate voicemail timer after RINGING.
        self.telephone = _telephone_class()(self.identity, auto_answer=None)
        self.telephone.auto_answer = None
        # Disable busy tone played on caller side when remote side rejects, or doesn't answer
        self.telephone.set_busy_tone_time(0)
        # Increase connection timeout for slower networks
        self.telephone.set_connect_timeout(30)

        # LXST switch_profile / switch_mode are no-ops without an established call.
        # Remember preferred values and pass them into telephone.call() on dial.
        self.preferred_profile_id = self.resolve_audio_profile_id()
        self.preferred_mode_id = self.resolve_call_mode_id()

        self._install_link_table_cleanup()
        self.refresh_call_policy()

        self.telephone.set_ringing_callback(self.on_telephone_ringing)
        self.telephone.set_established_callback(self.on_telephone_call_established)
        self.telephone.set_ended_callback(self.on_telephone_call_ended)

    def set_call_policy(self, allowed_fn=None, blocked_identity_hashes=None):
        """Install LXST-level allow/block checks used before RINGING.

        allowed_fn receives the caller identity hash as bytes and must return bool.
        blocked_identity_hashes is an optional iterable of identity hash bytes.
        """
        self._caller_allowed = allowed_fn
        if blocked_identity_hashes is None:
            self._blocked_identity_hashes = None
        else:
            self._blocked_identity_hashes = [
                bytes(h) for h in blocked_identity_hashes if h is not None
            ]
        self.refresh_call_policy()

    def refresh_call_policy(self):
        """Push current policy into the live Telephone instance."""
        if self.telephone is None:
            return

        self.telephone.auto_answer = None

        if self._blocked_identity_hashes is not None:
            self.telephone.set_blocked(list(self._blocked_identity_hashes))
        else:
            self.telephone.set_blocked(None)

        if callable(self._caller_allowed):
            self.telephone.set_allowed(self._caller_allowed)
        else:
            # Fail closed until MeshChatX installs sync_telephone_call_policy.
            self.telephone.set_allowed(_telephone_class().ALLOW_NONE)

    def _install_link_table_cleanup(self):
        """Ensure closed inbound links are removed from Telephone.links.

        Older LXST builds never popped self.links on close. Patch the bound
        handler so MeshChatX stays safe even before the LXST bump is installed.
        """
        phone = self.telephone
        if phone is None:
            return
        previous = getattr(phone, "_Telephone__link_closed", None)
        if (
            previous is None
            or getattr(previous, "_meshchatx_link_cleanup", False) is True
        ):
            return

        def _link_closed(link, previous=previous, phone=phone):
            try:
                previous(link)
            finally:
                link_id = getattr(link, "link_id", None)
                if link_id is not None:
                    with contextlib.suppress(Exception):
                        phone.links.pop(link_id, None)

        _link_closed._meshchatx_link_cleanup = True
        phone._Telephone__link_closed = _link_closed

    def teardown(self):
        if self.telephone is not None:
            self.telephone.teardown()
            self.telephone = None
        # Drop per-call state: otherwise a call that was in flight leaves
        # initiation_status set and every later initiate() reports busy, and
        # stale start/stats leak into the next session.
        self.initiation_status = None
        self.initiation_target_hash = None
        self.call_start_time = None
        self.call_status_at_end = None
        self.call_is_incoming = False
        self.call_was_established = False
        self.call_stats = {}
        self.ptt_active = False
        self.is_voicemail_session_active = False
        self._call_end_recorded = True

    def hangup(self):
        self._update_initiation_status(None, None)
        if self.telephone:
            try:
                self.telephone.hangup()
            except Exception as e:
                RNS.log(f"TelephoneManager: Error during hangup: {e}", RNS.LOG_ERROR)

    def request_hangup(self):
        # FIXME: Remove async hangup shim when LXST call() cancellation is non-blocking.
        self._update_initiation_status(None, None)
        if not self.telephone:
            return
        threading.Thread(target=self.hangup, daemon=True).start()

    def register_ringing_callback(self, callback):
        self.on_ringing_callback = callback

    def register_established_callback(self, callback):
        self.on_established_callback = callback

    def register_ended_callback(self, callback):
        self.on_ended_callback = callback

    def set_callbacks(self, ringing=None, established=None, ended=None):
        if ringing:
            self.register_ringing_callback(ringing)
        if established:
            self.register_established_callback(established)
        if ended:
            self.register_ended_callback(ended)

    def on_telephone_ringing(self, caller_identity: RNS.Identity):
        if self.initiation_status:
            self._update_initiation_status("Ringing...")
            return

        self.call_start_time = time.time()
        self.call_is_incoming = True
        self.call_was_established = False
        self._call_end_recorded = False
        if self.on_ringing_callback:
            self.on_ringing_callback(caller_identity)

    def on_telephone_call_established(self, caller_identity: RNS.Identity):
        # Update start time to when it was actually established for duration calculation
        self.call_start_time = time.time()
        self.call_was_established = True
        self.ptt_active = False

        # Track per-call stats from the active link (uses RNS Link counters)
        link = getattr(self.telephone, "active_call", None)
        self.call_stats = {
            "link": link,
            "started_at": self.call_start_time,
        }

        if self.on_established_callback:
            self.on_established_callback(caller_identity)

    def on_telephone_call_ended(self, caller_identity: RNS.Identity):
        if self._call_end_recorded:
            # LXST can emit ended twice for one call (local hangup plus remote
            # link close); only the first may record history/notifications.
            return
        self._call_end_recorded = True
        # Capture status just before ending if possible, or use the last known status
        if self.telephone:
            self.call_status_at_end = self.telephone.call_status

        # Ensure initiation status is cleared when call ends
        self._update_initiation_status(None, None)
        self._reset_call_audio_controls()

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

    def _is_initiation_cancelled(self):
        return not bool(self.initiation_status)

    def _initiation_still_in_flight(self):
        phone = self.telephone
        if phone is None:
            return False
        if getattr(phone, "active_call", None):
            return False
        return phone.call_status in (2, 4, 5)

    async def _await_path(self, destination_hash: bytes, timeout_seconds: float):
        # Reuse shared pathfinding behavior so stale/unresponsive routes are
        # refreshed before we wait, mirroring the faster outbound LXMF path prep.
        with contextlib.suppress(Exception):
            reticulum_pathfinding.prepare_fresh_path_request(None, destination_hash)

        timeout_after = time.monotonic() + max(0.0, timeout_seconds)
        next_request_at = 0.0

        while time.monotonic() < timeout_after:
            if self._is_initiation_cancelled():
                return False

            if RNS.Transport.has_path(destination_hash):
                return True

            now = time.monotonic()
            if now >= next_request_at:
                with contextlib.suppress(Exception):
                    reticulum_pathfinding.nudge_path_request(destination_hash)
                next_request_at = now + self._path_retry_interval_s

            await asyncio.sleep(self._path_poll_interval_s)

        return RNS.Transport.has_path(destination_hash)

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
                target_hash = hex_identifier_to_bytes(target_hash_hex)
                if not target_hash:
                    return None

                # 1) Direct recall (identity hash)
                ident = RNS.Identity.recall(target_hash)
                if ident:
                    return ident

                if not self.db:
                    return None

                th = target_hash_hex.strip()
                canonical = normalize_hex_identifier(th)

                # 2) By destination_hash (could be lxst.telephony or lxmf.delivery hash)
                announce = self.db.announces.get_announce_by_hash(th)
                if not announce and canonical:
                    announce = self.db.announces.get_announce_by_hash(canonical)
                if not announce:
                    # 3) By identity_hash field (if user entered identity hash but we missed recall, or other announce types)
                    id_key = canonical or th
                    announces = self.db.announces.get_filtered_announces(
                        identity_hash=id_key,
                    )
                    if announces:
                        announce = announces[0]

                if not announce:
                    return None

                # Try identity_hash from announce
                identity_hex = announce.get("identity_hash")
                if identity_hex:
                    id_bytes = hex_identifier_to_bytes(identity_hex)
                    if id_bytes:
                        ident = RNS.Identity.recall(id_bytes)
                        if ident:
                            return ident

                # Try reconstructing from public key
                if announce.get("identity_public_key"):
                    with contextlib.suppress(Exception):
                        return RNS.Identity.from_bytes(
                            base64.b64decode(announce["identity_public_key"]),
                        )

                return None

            # Find destination identity
            destination_identity = resolve_identity(destination_hash_hex)

            if destination_identity is None:
                self._update_initiation_status("Discovering path/identity...")
                with contextlib.suppress(Exception):
                    reticulum_pathfinding.prepare_fresh_path_request(
                        None,
                        destination_hash,
                    )
                timeout_after = time.monotonic() + timeout_seconds
                next_request_at = 0.0

                # Wait for identity to appear while also nudging path discovery.
                while time.monotonic() < timeout_after:
                    if self._is_initiation_cancelled():
                        return None

                    now = time.monotonic()
                    if now >= next_request_at:
                        with contextlib.suppress(Exception):
                            reticulum_pathfinding.nudge_path_request(destination_hash)
                        next_request_at = now + self._path_retry_interval_s

                    destination_identity = resolve_identity(destination_hash_hex)
                    if destination_identity:
                        break
                    await asyncio.sleep(self._path_poll_interval_s)

            if destination_identity is None:
                self._update_initiation_status(None, None)
                msg = "Destination identity not found"
                raise RuntimeError(msg)

            # FIXME: Remove telephony-destination pre-path lookup once LXST aligns
            # identity-hash and telephony-destination path handling.
            call_destination_hash: bytes = destination_hash
            with contextlib.suppress(Exception):
                dest = RNS.Destination(
                    destination_identity,
                    RNS.Destination.OUT,
                    RNS.Destination.SINGLE,
                    "lxst",
                    "telephony",
                )
                dest_hash = dest.hash
                if isinstance(dest_hash, bytes):
                    call_destination_hash = dest_hash

            if not RNS.Transport.has_path(call_destination_hash):
                self._update_initiation_status("Requesting path...")
                path_wait = float(timeout_seconds)
                try:
                    path_wait = max(
                        path_wait,
                        path_response_window(call_destination_hash),
                    )
                except Exception:
                    pass
                has_path = await self._await_path(
                    call_destination_hash,
                    timeout_seconds=path_wait,
                )
                if self._is_initiation_cancelled():
                    return None
                if not has_path:
                    msg = "Path not found to destination"
                    raise RuntimeError(msg)

            self._update_initiation_status("Establishing link...", destination_hash_hex)
            self.call_start_time = time.time()
            self.call_is_incoming = False
            self._call_end_recorded = False

            profile_id = self.resolve_audio_profile_id(self.preferred_profile_id)
            self.preferred_profile_id = profile_id
            mode_id = self.resolve_call_mode_id(self.preferred_mode_id)
            self.preferred_mode_id = mode_id

            # Use a thread for the blocking LXST call, but monitor status for early exit
            # if established elsewhere or timed out/hung up. Pass preferred profile and
            # duplex mode so Codec2/Opus and half-duplex actually apply on dial.
            call_task = asyncio.create_task(
                asyncio.to_thread(
                    self.telephone.call,
                    destination_identity,
                    profile_id,
                    mode_id,
                ),
            )

            start_wait = time.time()
            cancel_requested = False
            # LXST telephone.call usually returns on establishment or timeout.
            # We wait for it, but if status becomes established or ended, we can stop waiting.
            while not call_task.done():
                if self._is_initiation_cancelled():
                    cancel_requested = True
                    break

                # Update UI status based on current call state
                if self.telephone.call_status == 2:
                    self._update_initiation_status("Calling...", destination_hash_hex)
                elif self.telephone.call_status == 4:
                    self._update_initiation_status("Ringing...", destination_hash_hex)
                elif self.telephone.call_status == 5:
                    self._update_initiation_status(
                        "Establishing link...",
                        destination_hash_hex,
                    )

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
                await asyncio.sleep(self._status_poll_interval_s)

            if cancel_requested:
                self._update_initiation_status(None, None)
                with contextlib.suppress(Exception):
                    # FIXME: Remove async hangup dispatch when LXST exposes cooperative cancellation.
                    hangup_task = asyncio.create_task(
                        asyncio.to_thread(self.telephone.hangup)
                    )
                    self._background_tasks.add(hangup_task)
                    hangup_task.add_done_callback(self._background_tasks.discard)
                return None

            # If the task finished but we're still ringing or connecting,
            # wait a bit more for establishment or definitive failure
            if self.initiation_status and self.telephone.call_status in [
                2,
                4,
                5,
            ]:  # Calling, Ringing, Connecting
                wait_until = time.time() + timeout_seconds
                while time.time() < wait_until:
                    if not self.initiation_status:  # Externally cancelled
                        break

                    if self.telephone.call_status == 2:
                        self._update_initiation_status(
                            "Calling...",
                            destination_hash_hex,
                        )
                    elif self.telephone.call_status == 4:
                        self._update_initiation_status(
                            "Ringing...",
                            destination_hash_hex,
                        )
                    elif self.telephone.call_status == 5:
                        self._update_initiation_status(
                            "Establishing link...",
                            destination_hash_hex,
                        )

                    if self.telephone.call_status in [
                        6,
                        0,
                        1,
                        3,
                    ]:  # Established, Busy, Rejected, Ended
                        break
                    await asyncio.sleep(self._status_poll_interval_s)

            return self.telephone.active_call

        except Exception as e:
            self._update_initiation_status(f"Failed: {e!s}")
            await asyncio.sleep(3)
            raise
        finally:
            if self._is_initiation_cancelled():
                self._update_initiation_status(None, None)
            elif self._initiation_still_in_flight():
                # Keep the dial overlay while LXST is still calling or ringing
                # without an active_call object the UI can bind to.
                pass
            else:
                # Wait for either establishment, failure, or a timeout
                # to ensure the UI has something to show (either active_call or initiation_status)
                for _ in range(40):  # Max 4 seconds of defensive waiting
                    if self.telephone and (
                        self.telephone.active_call
                        or self.telephone.call_status in [0, 1, 3, 6]
                    ):
                        break
                    await asyncio.sleep(self._status_poll_interval_s)

                # If call was successful, keep status for a moment to prevent UI flicker
                # while the frontend picks up the new active_call state
                if self.telephone and (
                    (self.telephone.active_call and self.telephone.call_status == 6)
                    or self.telephone.call_status in [2, 4, 5]
                ):
                    await asyncio.sleep(1.0)
                self._update_initiation_status(None, None)

    def mute_transmit(self):
        if self.telephone:
            try:
                self.telephone.mute_transmit()
            except Exception:
                pass
            self.transmit_muted = True

    def unmute_transmit(self):
        if self.telephone:
            try:
                self.telephone.unmute_transmit()
            except Exception:
                pass
            self.transmit_muted = False

    def mute_receive(self):
        if self.telephone:
            try:
                self.telephone.mute_receive()
            except Exception:
                pass
            self.receive_muted = True

    def unmute_receive(self):
        if self.telephone:
            try:
                self.telephone.unmute_receive()
            except Exception:
                pass
            self.receive_muted = False
