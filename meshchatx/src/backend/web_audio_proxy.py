# SPDX-License-Identifier: 0BSD

"""Lazy, fault-isolated wrapper around WebAudioBridge.

web_audio_bridge imports LXST, numpy, and OpenBLAS at module load. That
costs tens of MB of RSS plus a pool of OpenBLAS worker threads even on
installs that never use voice. This proxy defers the import and
construction until a call actually needs the bridge.

It also converts failures into a degraded state: if construction or a
bridge call raises, the proxy marks itself failed and every later call
becomes a safe no-op, so audio problems cannot take down messaging. A
native crash inside LXST or its codecs still kills the process, which is
why keeping the import lazy matters: on hosts where audio backends were
historically unstable, never-used audio code now never runs.
"""

import asyncio
import contextlib
import json
import logging
import threading

logger = logging.getLogger(__name__)

_MAX_CALL_FAILURES = 3
_EMPTY_CLIENTS = frozenset()


def _build_bridge(telephone_manager, config_manager, force_enabled):
    from meshchatx.src.backend.web_audio_bridge import WebAudioBridge

    return WebAudioBridge(
        telephone_manager,
        config_manager,
        force_enabled=force_enabled,
    )


class LazyWebAudioBridge:
    """Drop-in stand-in that constructs WebAudioBridge on first real use.

    config_enabled(), allow_fallback(), clients, and get_diagnostics()
    answer from stored configuration without constructing the bridge.
    send_status() and attach_client() are the natural first-use points
    and do construct. detach_client(), push_client_frame(), and
    on_call_ended() never construct: with no live bridge there is
    nothing to detach, feed, or clean up.
    """

    def __init__(self, bridge_factory=None):
        self._bridge_factory = bridge_factory or _build_bridge
        self._telephone_manager = None
        self._config_manager = None
        self._force_enabled = False
        self._bridge = None
        self._failed = False
        self._failure_count = 0
        self._last_error = None
        self._construct_lock = threading.Lock()

    def configure(self, telephone_manager, config_manager, force_enabled=False):
        """Set the construction args, typically on identity (re)bind.

        Tears down a previously built bridge and clears the failure
        state so a new context gets a fresh attempt.
        """
        with self._construct_lock:
            bridge, self._bridge = self._bridge, None
            self._telephone_manager = telephone_manager
            self._config_manager = config_manager
            self._force_enabled = bool(force_enabled)
            self._failed = False
            self._failure_count = 0
            self._last_error = None
        if bridge is not None:
            with contextlib.suppress(Exception):
                bridge.on_call_ended()

    @property
    def initialized(self):
        return self._bridge is not None

    @property
    def failed(self):
        return self._failed

    @property
    def last_error(self):
        return self._last_error

    @property
    def telephone_manager(self):
        bridge = self._bridge
        return bridge.telephone_manager if bridge else self._telephone_manager

    @property
    def config_manager(self):
        bridge = self._bridge
        return bridge.config_manager if bridge else self._config_manager

    @property
    def force_enabled(self):
        return self._force_enabled

    @property
    def clients(self):
        bridge = self._bridge
        return bridge.clients if bridge is not None else _EMPTY_CLIENTS

    def config_enabled(self):
        if self._force_enabled:
            return True
        config = self._config_manager
        return bool(
            config
            and hasattr(config, "telephone_web_audio_enabled")
            and config.telephone_web_audio_enabled.get()
        )

    def allow_fallback(self):
        if self._force_enabled:
            return False
        config = self._config_manager
        return bool(
            config
            and hasattr(config, "telephone_web_audio_allow_fallback")
            and config.telephone_web_audio_allow_fallback.get()
        )

    def get_diagnostics(self):
        base = {
            "initialized": self._bridge is not None,
            "failed": self._failed,
            "last_error": str(self._last_error) if self._last_error else None,
            "force_enabled": self._force_enabled,
            "config_enabled": bool(self.config_enabled()),
            "client_count": len(self.clients),
        }
        bridge = self._bridge
        if bridge is None:
            return base
        try:
            base.update(bridge.get_diagnostics())
            base["initialized"] = True
            self._reset_failures()
        except Exception as exc:
            self._note_call_failure("get_diagnostics", exc)
        return base

    def _ensure_bridge(self):
        if self._bridge is not None or self._failed:
            return self._bridge
        with self._construct_lock:
            if self._bridge is not None or self._failed:
                return self._bridge
            try:
                self._bridge = self._bridge_factory(
                    self._telephone_manager,
                    self._config_manager,
                    self._force_enabled,
                )
                logger.info("Web audio bridge initialized on first use")
            except Exception as exc:
                self._failed = True
                self._last_error = exc
                logger.error(
                    "Web audio bridge failed to initialize, audio disabled: %s",
                    exc,
                )
                return None
        return self._bridge

    def _note_call_failure(self, method, exc):
        self._failure_count += 1
        self._last_error = exc
        logger.error("Web audio bridge %s failed: %s", method, exc)
        if self._failure_count >= _MAX_CALL_FAILURES:
            self._failed = True
            logger.error(
                "Web audio bridge disabled after %d consecutive failures",
                self._failure_count,
            )
            bridge, self._bridge = self._bridge, None
            if bridge is not None:
                with contextlib.suppress(Exception):
                    bridge.on_call_ended()

    def _reset_failures(self):
        self._failure_count = 0

    async def send_status(self, client):
        # Construction imports LXST and numpy and can take a second, so
        # run it off the event loop.
        bridge = await asyncio.to_thread(self._ensure_bridge)
        if bridge is not None:
            try:
                await bridge.send_status(client)
                self._reset_failures()
                return
            except Exception as exc:
                self._note_call_failure("send_status", exc)
        await client.send_str(
            json.dumps(
                {
                    "type": "web_audio.ready",
                    "frame_ms": 60,
                    "required": self._force_enabled,
                    "degraded": True,
                },
            ),
        )

    def attach_client(self, client):
        bridge = self._ensure_bridge()
        if bridge is None:
            return False
        try:
            result = bridge.attach_client(client)
        except Exception as exc:
            self._note_call_failure("attach_client", exc)
            return False
        self._reset_failures()
        return result

    def detach_client(self, client):
        bridge = self._bridge
        if bridge is None:
            return
        try:
            bridge.detach_client(client)
            self._reset_failures()
        except Exception as exc:
            self._note_call_failure("detach_client", exc)

    def push_client_frame(self, pcm_bytes):
        bridge = self._bridge
        if bridge is None:
            return
        try:
            bridge.push_client_frame(pcm_bytes)
            self._reset_failures()
        except Exception as exc:
            self._note_call_failure("push_client_frame", exc)

    def on_call_ended(self):
        bridge = self._bridge
        if bridge is None:
            return
        try:
            bridge.on_call_ended()
            self._reset_failures()
        except Exception as exc:
            self._note_call_failure("on_call_ended", exc)

    def shutdown(self):
        with self._construct_lock:
            bridge, self._bridge = self._bridge, None
        if bridge is not None:
            with contextlib.suppress(Exception):
                bridge.on_call_ended()

    def __getattr__(self, name):
        # Delegate unknown attributes to a live bridge only. Probing an
        # attribute must never trigger construction.
        bridge = self.__dict__.get("_bridge")
        if bridge is not None:
            return getattr(bridge, name)
        raise AttributeError(name)
