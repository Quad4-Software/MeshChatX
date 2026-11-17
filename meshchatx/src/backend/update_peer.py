# SPDX-License-Identifier: 0BSD
"""Opt-in peer relay for update payloads on the meshchatx.update aspect.

A node that has verified a manifest (and optionally artifact files) can
announce a "meshchatx.update" destination and serve manifest probes,
manifests, sizes and byte ranges to other nodes. Peers are untrusted:
clients verify the signed manifest and artifact checksums themselves, so
the server only ever serves bytes it believes are genuine, and refuses
anything whose sha256 is not in a manifest it verified itself.

Server-side limits: per-requester token bucket, bounded concurrency, max
range size, and only artifacts whose sha256 appears in a verified manifest
are served.
"""

from __future__ import annotations

import threading
import time
from pathlib import Path

from meshchatx.src.backend import update_types as T
from meshchatx.src.backend.update_types import (
    MANIFEST_MAX_BYTES,
    RNS_RANGE_MAX_BYTES,
    RNS_UPDATE_APP,
    RNS_UPDATE_ASPECT,
    RNS_UPDATE_SUBASPECT,
    sha256_file,
)

RNS_UPDATE_PATH = "/update"
MAX_SERVED_MANIFESTS = 4
MAX_SERVED_ARTIFACTS = 8
SERVER_RATE_PER_SEC = 8.0
SERVER_RATE_BURST = 16.0
SERVER_MAX_CONCURRENT = 4


def _mp_pack(obj) -> bytes:
    from RNS.vendor import umsgpack as mp

    return mp.packb(obj, use_bin_type=True)


def _mp_unpack(data: bytes):
    from RNS.vendor import umsgpack as mp

    return mp.unpackb(data)


class _RateBucket:
    def __init__(self, rate=SERVER_RATE_PER_SEC, burst=SERVER_RATE_BURST):
        self.rate = rate
        self.burst = burst
        self.tokens = burst
        self.last = time.monotonic()
        self.lock = threading.Lock()

    def allow(self, cost: float = 1.0) -> bool:
        with self.lock:
            now = time.monotonic()
            self.tokens = min(self.burst, self.tokens + (now - self.last) * self.rate)
            self.last = now
            if self.tokens >= cost:
                self.tokens -= cost
                return True
            return False


class PeerUpdateServer:
    """Serves verified update payloads over RNS request/reply.

    verified_manifests: {channel: {"rsm": bytes, "sha256": hex, "manifest": dict}}
    artifact_files: {name: path} restricted to names whose sha256 is in a
    verified manifest. Files are registered via register_artifact().
    """

    def __init__(
        self,
        *,
        rate_per_sec=SERVER_RATE_PER_SEC,
        burst=SERVER_RATE_BURST,
        max_concurrent=SERVER_MAX_CONCURRENT,
    ):
        self._manifests = {}  # channel -> dict
        self._artifacts = {}  # name -> {"path","sha256","size"}
        self._lock = threading.Lock()
        self._sem = threading.BoundedSemaphore(max_concurrent)
        self._buckets = {}
        self._bucket_lock = threading.Lock()
        self._rate = rate_per_sec
        self._burst = burst
        self._destination = None
        self._announce_app_data = None
        self.enabled = False
        self.requests_served = 0

    # -- state ---------------------------------------------------------------

    def set_enabled(self, enabled: bool, app_data: dict | None = None):
        self.enabled = bool(enabled)
        self._announce_app_data = app_data

    @property
    def destination(self):
        return self._destination

    def announce_app_data(self):
        channels = sorted(self._manifests.keys())
        return {"v": 1, "ch": channels, "a": bool(self._artifacts)}

    def register_manifest(self, channel: str, rsm: bytes, manifest: dict):
        """Record a manifest this node verified itself."""
        if not isinstance(rsm, (bytes, bytearray)) or len(rsm) > MANIFEST_MAX_BYTES:
            raise T.UpdateVerifyError("manifest too large to serve")
        sha = T.sha256_hex(bytes(rsm))
        with self._lock:
            self._manifests[channel] = {
                "rsm": bytes(rsm),
                "sha256": sha,
                "manifest": manifest,
                "ts": time.time(),
            }
            # prune
            if len(self._manifests) > MAX_SERVED_MANIFESTS:
                oldest = min(self._manifests, key=lambda c: self._manifests[c]["ts"])
                self._manifests.pop(oldest, None)

    def _verified_shas(self) -> set:
        out = set()
        for m in self._manifests.values():
            man = m.get("manifest") or {}
            for art in man.get("artifacts") or []:
                if isinstance(art, dict) and art.get("sha256"):
                    out.add(str(art["sha256"]).lower())
        return out

    def register_artifact(self, name: str, path, sha256: str, size: int):
        """Register a local file for serving.

        Only allowed when sha256 is in a verified manifest (checked lazily
        on first request too).
        """
        safe = T.safe_artifact_name(name)
        if safe is None:
            raise T.UpdateVerifyError("bad artifact name")
        name = safe
        with self._lock:
            if (
                len(self._artifacts) >= MAX_SERVED_ARTIFACTS
                and name not in self._artifacts
            ):
                oldest = min(
                    self._artifacts, key=lambda n: self._artifacts[n].get("ts", 0)
                )
                self._artifacts.pop(oldest, None)
            self._artifacts[name] = {
                "path": str(path),
                "sha256": sha256.lower(),
                "size": int(size),
                "ts": time.time(),
            }

    def _artifact_ok(self, name: str) -> dict | None:
        with self._lock:
            art = self._artifacts.get(name)
        if not art:
            return None
        # refuse to serve bytes whose hash is not in a verified manifest
        if art["sha256"] not in self._verified_shas():
            return None
        return art

    def _bucket_for(self, key: str) -> _RateBucket:
        with self._bucket_lock:
            b = self._buckets.get(key)
            if b is None:
                b = _RateBucket(self._rate, self._burst)
                self._buckets[key] = b
                if len(self._buckets) > 256:
                    self._buckets.clear()
            return b

    # -- RNS wiring ------------------------------------------------------------

    def start(self, identity=None):
        """Create and announce the destination, register the handler."""
        import RNS

        self._ensure_identity(identity)
        if self._destination is None:
            self._destination = RNS.Destination(
                RNS_UPDATE_APP, RNS_UPDATE_SUBASPECT, RNS_UPDATE_ASPECT
            )
            self._destination.set_link_established_callback(lambda _l: None)
        self._destination.register_request_handler(
            RNS_UPDATE_PATH,
            response_generator=self._responder,
            allow=RNS.Destination.ALLOW_ALL,
        )
        self.enabled = True
        try:
            self._destination.announce(self.announce_app_data())
        except Exception:
            pass

    def stop(self):
        dest = self._destination
        self._destination = None
        self.enabled = False
        if dest is not None:
            try:
                dest.deregister_request_handler(RNS_UPDATE_PATH)
            except Exception:
                pass
            try:
                import RNS

                RNS.Transport.deregister_destination(dest)
            except Exception:
                pass
            try:
                dest.close()
            except Exception:
                pass

    def _ensure_identity(self, identity=None):
        # The announcing identity is the peer's own choice; for the embedded
        # relay we use a dedicated identity passed in or a throwaway one so
        # the user's main LXMF identity is not exposed as an update source.
        if identity is not None:
            return identity
        try:
            import RNS

            return RNS.Identity()
        except Exception:
            return None

    # -- request handling -------------------------------------------------------

    def _responder(
        self, path, data, request_id, link_id, remote_identity, requested_at
    ):
        """Response generator for RNS.Destination.register_request_handler."""
        if not self.enabled:
            return None
        key = (
            remote_identity.hex()
            if hasattr(remote_identity, "hex")
            else str(remote_identity)
        )
        bucket = self._bucket_for(key)
        if not bucket.allow(1.0):
            return _mp_pack({"s": "none"})
        if not self._sem.acquire(blocking=False):
            return _mp_pack({"s": "none"})
        try:
            return self._handle(data)
        except Exception:
            return _mp_pack({"s": "none"})
        finally:
            self._sem.release()

    def _handle(self, data) -> bytes:
        try:
            req = _mp_unpack(data)
        except Exception:
            return _mp_pack({"s": "none"})
        if not isinstance(req, dict):
            return _mp_pack({"s": "none"})
        op = req.get("op")
        try:
            if op == "probe":
                return self._op_probe(req)
            if op == "manifest":
                return self._op_manifest(req)
            if op == "head":
                return self._op_head(req)
            if op == "range":
                return self._op_range(req)
        except Exception:
            return _mp_pack({"s": "none"})
        return _mp_pack({"s": "none"})

    def _op_probe(self, req) -> bytes:
        channel = req.get("channel")
        m = self._manifests.get(channel)
        if not m:
            return _mp_pack({"s": "none"})
        want = (req.get("sha256") or "").lower()
        if want and want == m["sha256"]:
            return _mp_pack({"s": "same"})
        return _mp_pack({"s": "ok", "d": m["rsm"]})

    def _op_manifest(self, req) -> bytes:
        m = self._manifests.get(req.get("channel"))
        if not m:
            return _mp_pack({"s": "none"})
        return _mp_pack({"s": "ok", "d": m["rsm"]})

    def _op_head(self, req) -> bytes:
        name = T.safe_artifact_name(req.get("name"))
        if name is None:
            return _mp_pack({"s": "none"})
        art = self._artifact_ok(name)
        if not art:
            return _mp_pack({"s": "none"})
        return _mp_pack({"s": "ok", "size": art["size"]})

    def _op_range(self, req) -> bytes:
        name = T.safe_artifact_name(req.get("name"))
        if name is None:
            return _mp_pack({"s": "none"})
        art = self._artifact_ok(name)
        if not art:
            return _mp_pack({"s": "none"})
        try:
            off = int(req.get("o"))
            length = int(req.get("l"))
        except (TypeError, ValueError):
            return _mp_pack({"s": "none"})
        if off < 0 or length <= 0 or length > RNS_RANGE_MAX_BYTES:
            return _mp_pack({"s": "none"})
        off = min(off, art["size"])
        length = min(length, art["size"] - off)
        if length <= 0:
            return _mp_pack({"s": "ok", "d": b""})
        try:
            with open(art["path"], "rb") as fh:
                fh.seek(off)
                chunk = fh.read(length)
        except OSError:
            return _mp_pack({"s": "none"})
        self.requests_served += 1
        return _mp_pack({"s": "ok", "d": chunk})

    # -- seed dir scanning (sneakernet / filesync imports) ---------------------

    def scan_seed_dir(self, seed_dir) -> int:
        """Index files dropped into the seed dir.

        Only files whose sha256 is in a verified manifest are served.
        Returns count indexed.
        """
        root = Path(seed_dir)
        if not root.is_dir():
            return 0
        verified = self._verified_shas()
        count = 0
        for p in sorted(root.iterdir()):
            if not p.is_file():
                continue
            name = T.safe_artifact_name(p.name)
            if name is None or name.endswith(".blockmap"):
                continue
            try:
                sha = sha256_file(p)
            except OSError:
                continue
            if sha not in verified:
                continue
            size = p.stat().st_size
            self.register_artifact(name, p, sha, size)
            count += 1
        return count


def announce_handler_for(server: PeerUpdateServer):
    """Return an AnnounceHandler-compatible object feeding the transport."""
    from meshchatx.src.backend.announce_handler import AnnounceHandler

    def cb(aspect, destination_hash, announced_identity, app_data, packet_hash):
        # The transport learns destinations itself; the server announces its
        # own destination. Nothing needed here beyond keeping the handler
        # registered so announces flow.
        return None

    return AnnounceHandler(RNS_UPDATE_ASPECT, cb)
