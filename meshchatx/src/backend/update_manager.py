# SPDX-License-Identifier: 0BSD
"""Update manager: opt-in, signature-verified update check/download/stage.

Everything is off by default. With default settings the manager makes zero
network requests and registers no destinations. When the user enables
updates, checks run only on demand or on the configured jittered interval,
all transports are untrusted, and the signed manifest (schema 2, msgpack
payload in an RSG envelope) is the only trust anchor.

Flow: check -> verify signed manifest -> validate (channel, expiry,
downgrade, high-water mark) -> pick artifact -> optional block reuse ->
verify sha256+size -> atomic stage -> pending.json -> apply per policy.
"""

from __future__ import annotations

import itertools
import os
import threading
import time
from pathlib import Path

from meshchatx.src import update_rsm
from meshchatx.src.backend import update_types as T
from meshchatx.src.backend.update_blockmap import (
    BlockMatcher,
    blockmap_name,
    missing_ranges,
    plan_is_viable,
    verify_blockmap_entry,
)
from meshchatx.src.backend.update_peer import PeerUpdateServer
from meshchatx.src.backend.update_transports import (
    FetchFailed,
    FetchNotFound,
    build_transports,
    transport_kind,
)
from meshchatx.src.backend.update_types import (
    ARTIFACT_MAX_BYTES,
    UpdateError,
    UpdateSettings,
    UpdateUnavailable,
    UpdateVerifyError,
    app_version,
    artifact_cap_bytes,
    atomic_write_bytes,
    atomic_write_json,
    auto_download_allowed,
    build_channel,
    current_artifact_path,
    disclosure_for,
    ensure_private_dir,
    host_platform,
    install_kind,
    jittered_interval_hours,
    normalize_arch,
    now_iso,
    pending_dir,
    pending_marker_path,
    pinned_signer_hashes,
    read_json_file,
    safe_artifact_name,
    seed_dir,
    sha256_file,
    state_path,
    updates_root,
    validate_manifest,
    version_newer,
)

CHECK_BACKOFF_MAX_S = 3600.0
MAX_MISSING_RANGES = 512
_EXTERNAL_KINDS = {
    "oci": "pull the new image with your container runtime",
    "flatpak": "run flatpak update",
}


class UpdateManager:
    def __init__(
        self,
        storage_dir,
        config_getter=None,
        *,
        link_manager=None,
        rns_session=None,
        identity_hashes=None,
        build_meta=None,
    ):
        self.storage_dir = Path(storage_dir)
        self._config_getter = config_getter
        self._link_manager = link_manager
        self._rns_session = rns_session
        self._identity_hashes = identity_hashes or {}
        self._build_meta = build_meta or {}
        self._lock = threading.RLock()
        self._check_lock = threading.Lock()
        self._download_lock = threading.Lock()
        self._stop = threading.Event()
        self._scheduler = None
        self._peer = None
        self._announce_handler = None
        self._transports = None
        self._rns_transport = None
        self._last_manifest = {}  # channel -> {"rsm","manifest","entry","ts"}
        self._progress = {"phase": "idle"}
        self._consecutive_failures = 0

    # ------------------------------------------------------------------
    # config / settings
    # ------------------------------------------------------------------

    def _config(self):
        if self._config_getter is None:
            return None
        try:
            return self._config_getter()
        except Exception:
            return None

    def settings(self) -> UpdateSettings:
        return UpdateSettings.from_config(self._config())

    def _channel(self, settings: UpdateSettings) -> str:
        if settings.channel:
            return settings.channel
        return build_channel(self._build_meta)

    def _current_version(self) -> str:
        try:
            ih = self._identity_hashes or {}
            v = ih.get("version") or ih.get("app_version")
            if v:
                return str(v)
        except Exception:
            pass
        return app_version()

    # ------------------------------------------------------------------
    # state persistence
    # ------------------------------------------------------------------

    def _load_state(self) -> dict:
        st = read_json_file(state_path(self.storage_dir), {})
        if not isinstance(st, dict):
            st = {}
        st.setdefault("last_check", None)
        st.setdefault("high_water", {})
        st.setdefault("pending_relay", {})
        return st

    def _save_state(self, st: dict):
        ensure_private_dir(updates_root(self.storage_dir))
        atomic_write_json(state_path(self.storage_dir), st)

    def _high_water(self, st: dict, channel: str):
        return (st.get("high_water") or {}).get(channel) or {}

    def _record_high_water(self, st: dict, channel: str, manifest: dict):
        hw = st.setdefault("high_water", {})
        cur = hw.get(channel) or {}
        issued = float(manifest.get("issued_at") or 0)
        ver = str(manifest.get("version") or "")
        if issued > float(cur.get("issued_at") or 0) or (
            issued == float(cur.get("issued_at") or 0)
            and version_newer(ver, str(cur.get("version") or "0"))
        ):
            hw[channel] = {"issued_at": issued, "version": ver}

    # ------------------------------------------------------------------
    # lifecycle
    # ------------------------------------------------------------------

    def start(self):
        """Start scheduler and peer relay when settings allow.

        Safe to call when disabled: registers nothing and touches no
        transport.
        """
        settings = self.settings()
        if T.updates_disabled() or not settings.enabled:
            return
        self._ensure_peer(settings)
        if settings.auto_check and self._scheduler is None:
            self._scheduler = threading.Thread(
                target=self._scheduler_loop,
                name="meshchatx-update-scheduler",
                daemon=True,
            )
            self._scheduler.start()

    def stop(self):
        self._stop.set()
        if self._scheduler is not None:
            self._scheduler.join(timeout=5)
            self._scheduler = None
        self._teardown_peer()

    def refresh(self):
        """Re-evaluate settings after a settings change."""
        self.stop()
        self._stop.clear()
        self.start()

    def _ensure_peer(self, settings: UpdateSettings):
        if self._peer is not None or not settings.peer_relay:
            return
        self._peer = PeerUpdateServer()
        try:
            self._peer.start()
        except Exception:
            self._peer = None
            return
        # serve manifests/artifacts we have already verified
        for channel, cached in list(self._last_manifest.items()):
            self._peer.register_manifest(channel, cached["rsm"], cached["manifest"])
        self._scan_seeds()

    def _teardown_peer(self):
        if self._peer is not None:
            try:
                self._peer.stop()
            except Exception:
                pass
            self._peer = None

    def _scan_seeds(self):
        if self._peer is None:
            return
        seed = seed_dir(self.storage_dir)
        try:
            self._peer.scan_seed_dir(seed)
        except Exception:
            pass
        # also index the pending dir so staged artifacts can be relayed
        pend = pending_dir(self.storage_dir)
        try:
            for p in pend.iterdir():
                if p.is_file() and not p.name.endswith(".json"):
                    st = read_json_file(pending_marker_path(self.storage_dir), {})
                    for art in st.get("artifacts") or []:
                        if art.get("file") == p.name and art.get("sha256"):
                            self._peer.register_artifact(
                                p.name,
                                p,
                                art["sha256"],
                                art.get("size", p.stat().st_size),
                            )
        except Exception:
            pass

    # ------------------------------------------------------------------
    # scheduler
    # ------------------------------------------------------------------

    def _scheduler_loop(self):
        settings = self.settings()
        interval = jittered_interval_hours(settings.check_interval_hours)
        # first check after one jittered interval, not at startup
        if self._stop.wait(interval * 3600.0):
            return
        while not self._stop.is_set():
            try:
                self._auto_cycle()
            except Exception:
                pass
            settings = self.settings()
            interval = jittered_interval_hours(settings.check_interval_hours)
            # failure backoff with jitter
            if self._consecutive_failures > 0:
                interval *= min(8.0, 2.0 ** min(self._consecutive_failures, 3))
            if self._stop.wait(interval * 3600.0):
                return

    def _auto_cycle(self):
        settings = self.settings()
        if T.updates_disabled() or not settings.enabled or not settings.auto_check:
            return
        result = self.check_now(manual=False)
        update = (result or {}).get("update")
        if not update:
            return
        ok, reason = auto_download_allowed(settings, self._config())
        if not ok:
            self._record_last_check(
                {
                    "at": now_iso(),
                    "result": "skipped",
                    "detail": f"auto download skipped: {reason}",
                }
            )
            return
        self.download(update.get("artifact"), auto=True)

    # ------------------------------------------------------------------
    # last check record
    # ------------------------------------------------------------------

    def _record_last_check(self, record: dict):
        st = self._load_state()
        st["last_check"] = record
        self._save_state(st)

    def _last_check(self) -> dict | None:
        return self._load_state().get("last_check")

    # ------------------------------------------------------------------
    # transports
    # ------------------------------------------------------------------

    def _get_transports(self):
        settings = self.settings()
        if self._transports is None:
            self._transports, self._rns_transport = build_transports(
                settings,
                link_manager=self._link_manager,
                rns_session=self._rns_session,
                storage_dir=self.storage_dir,
                config=self._config(),
            )
        return self._transports

    def _reset_transports(self):
        self._transports = None
        self._rns_transport = None

    # ------------------------------------------------------------------
    # check
    # ------------------------------------------------------------------

    def check_now(self, manual: bool = True, allow_downgrade: bool = False) -> dict:
        """Run one update check across transports. Returns a result dict."""
        if T.updates_disabled():
            return {"status": "disabled", "update": None}
        settings = self.settings()
        if not settings.enabled:
            return {"status": "disabled", "update": None}
        if not self._check_lock.acquire(blocking=False):
            return {"status": "busy", "update": None}
        try:
            return self._check_inner(settings, manual, allow_downgrade)
        finally:
            self._check_lock.release()

    def _check_inner(self, settings, manual, allow_downgrade) -> dict:
        channel = self._channel(settings)
        current = self._current_version()
        st = self._load_state()
        signers = pinned_signer_hashes(settings.signer_hashes)
        errors = []
        transports = self._get_transports()
        for transport in transports:
            kind = transport_kind(transport)
            try:
                res = transport.fetch_manifest(channel)
            except Exception as e:
                errors.append(f"{kind}: {e}")
                continue
            if res.get("status") == "unchanged":
                cached = self._last_manifest.get(channel)
                self._consecutive_failures = 0
                self._record_last_check(
                    {
                        "at": now_iso(),
                        "result": "up_to_date",
                        "channel": channel,
                        "transport": kind,
                        "detail": "manifest unchanged",
                    }
                )
                return {
                    "status": "up_to_date",
                    "update": None,
                    "manifest": cached["manifest"] if cached else None,
                }
            if res.get("status") != "ok" or not res.get("data"):
                continue
            rsm = res["data"]
            try:
                manifest = update_rsm.verify_rsm(rsm, required_signer_hashes=signers)
            except Exception as e:
                errors.append(f"{kind}: verify failed: {e}")
                continue
            # persist verified manifest for peer relay + offline verify
            self._store_manifest(channel, rsm, manifest)
            try:
                artifacts = validate_manifest(
                    manifest,
                    channel=channel,
                    current_version=current,
                    enforce_newer=not allow_downgrade,
                )
            except UpdateUnavailable as e:
                self._consecutive_failures = 0
                self._record_last_check(
                    {
                        "at": now_iso(),
                        "result": "up_to_date",
                        "channel": channel,
                        "transport": kind,
                        "detail": str(e),
                    }
                )
                return {"status": "up_to_date", "update": None, "manifest": manifest}
            except UpdateVerifyError as e:
                errors.append(f"{kind}: {e}")
                continue
            # high-water mark: reject manifests older than last accepted
            hw = self._high_water(st, channel)
            issued = float(manifest.get("issued_at") or 0)
            if hw and issued < float(hw.get("issued_at") or 0):
                errors.append(f"{kind}: manifest older than accepted high-water mark")
                continue
            if not artifacts:
                self._consecutive_failures = 0
                self._record_last_check(
                    {
                        "at": now_iso(),
                        "result": "up_to_date",
                        "channel": channel,
                        "transport": kind,
                        "detail": "no artifact for this platform",
                    }
                )
                return {"status": "up_to_date", "update": None, "manifest": manifest}
            # size cap
            cap = artifact_cap_bytes(settings)
            artifacts = [a for a in artifacts if a["size"] <= cap]
            if not artifacts:
                self._record_last_check(
                    {
                        "at": now_iso(),
                        "result": "error",
                        "channel": channel,
                        "transport": kind,
                        "detail": "artifact exceeds max_download_mb",
                    }
                )
                return {"status": "too_large", "update": None, "manifest": manifest}
            self._record_high_water(st, channel, manifest)
            self._save_state(st)
            entry = self._pick_artifact(artifacts)
            self._consecutive_failures = 0
            update = {
                "version": manifest.get("version"),
                "channel": channel,
                "issued_at": manifest.get("issued_at"),
                "artifact": entry,
                "current_version": current,
                "transport": kind,
            }
            self._last_manifest[channel] = {
                "rsm": rsm,
                "manifest": manifest,
                "entry": entry,
                "ts": time.time(),
            }
            if self._peer is not None:
                try:
                    self._peer.register_manifest(channel, rsm, manifest)
                except Exception:
                    pass
            self._record_last_check(
                {
                    "at": now_iso(),
                    "result": "update_available",
                    "channel": channel,
                    "transport": kind,
                    "version": manifest.get("version"),
                    "artifact": entry["name"],
                    "size": entry["size"],
                }
            )
            return {
                "status": "update_available",
                "update": update,
                "manifest": manifest,
            }
        self._consecutive_failures += 1
        detail = "; ".join(errors) if errors else "no manifest found"
        self._record_last_check(
            {
                "at": now_iso(),
                "result": "error",
                "channel": channel,
                "detail": detail[:400],
            }
        )
        return {"status": "error", "update": None, "error": detail[:400]}

    def _pick_artifact(self, artifacts: list) -> dict:
        """Prefer the artifact matching this host kind.

        appimage on linux, wheel/pyz for python installs.
        """
        kind = install_kind()
        if kind == "python":
            install_pref = ("pyz", "wheel", "tarball")
        elif kind == "portable":
            install_pref = ("zip", "tarball", "other")
        else:
            install_pref = (kind,)
        plat = host_platform()
        kind_pref = install_pref + {
            "linux": ("appimage", "deb", "rpm", "flatpak", "tarball"),
            "windows": ("exe", "msi"),
            "macos": ("dmg", "tarball"),
            "android": ("apk",),
        }.get(plat, ("pyz", "wheel", "tarball"))
        for k in kind_pref:
            for a in artifacts:
                if a["kind"] == k:
                    return a
        return artifacts[0]

    def _store_manifest(self, channel: str, rsm: bytes, manifest: dict):
        self._last_manifest[channel] = {
            "rsm": rsm,
            "manifest": manifest,
            "entry": None,
            "ts": time.time(),
        }
        try:
            mdir = T.manifest_store_dir(self.storage_dir)
            ensure_private_dir(mdir)
            atomic_write_bytes(mdir / f"{channel}.rsm", rsm)
        except Exception:
            pass

    def stored_manifest(self, channel: str) -> dict | None:
        cached = self._last_manifest.get(channel)
        if cached:
            return cached
        rsm_path = T.manifest_store_dir(self.storage_dir) / f"{channel}.rsm"
        try:
            rsm = rsm_path.read_bytes()
        except OSError:
            return None
        settings = self.settings()
        signers = pinned_signer_hashes(settings.signer_hashes)
        try:
            manifest = update_rsm.verify_rsm(rsm, required_signer_hashes=signers)
        except Exception:
            return None
        cached = {"rsm": rsm, "manifest": manifest, "entry": None, "ts": time.time()}
        self._last_manifest[channel] = cached
        return cached

    # ------------------------------------------------------------------
    # download
    # ------------------------------------------------------------------

    def _set_progress(self, **kw):
        with self._lock:
            self._progress.update(kw)
            self._progress["updated_at"] = time.time()

    def get_progress(self) -> dict:
        with self._lock:
            return dict(self._progress)

    def download(
        self, artifact: dict, *, auto: bool = False, allow_downgrade: bool = False
    ) -> dict:
        """Download, verify and stage an artifact. Returns result dict."""
        if T.updates_disabled():
            raise UpdateUnavailable("updates disabled")
        settings = self.settings()
        if not settings.enabled:
            raise UpdateUnavailable("updates are not enabled")
        kind = artifact.get("kind") or "other"
        if kind in _EXTERNAL_KINDS:
            return {
                "status": "external",
                "artifact": artifact.get("name"),
                "kind": kind,
                "detail": f"update externally: {_EXTERNAL_KINDS[kind]}",
            }
        if not self._download_lock.acquire(blocking=False):
            raise UpdateError("a download is already in progress")
        try:
            return self._download_inner(artifact, settings, auto, allow_downgrade)
        finally:
            self._download_lock.release()

    def _download_inner(self, artifact, settings, auto, allow_downgrade) -> dict:
        name = safe_artifact_name(artifact.get("name"))
        if name is None:
            raise UpdateVerifyError("bad artifact name")
        size = int(artifact.get("size") or 0)
        sha = str(artifact.get("sha256") or "").lower()
        if size <= 0 or size > ARTIFACT_MAX_BYTES:
            raise UpdateVerifyError("artifact size invalid")
        cap = artifact_cap_bytes(settings)
        if size > cap:
            raise UpdateError(
                f"artifact is {size // (1024 * 1024)} MB, over the "
                f"{settings.max_download_mb} MB cap"
            )
        channel = self._channel(settings)
        version = str(artifact.get("version") or "")
        transports = self._get_transports()
        target_dir = pending_dir(self.storage_dir)
        ensure_private_dir(target_dir)
        out_path = target_dir / name
        # sha-suffixed partial name: a kept .part only ever resumes bytes
        # for the exact artifact it was fetched for
        tmp_path = target_dir / (name + "." + sha[:12] + ".part")

        self._set_progress(
            phase="prepare", artifact=name, size=size, downloaded=0, reused=0
        )

        # locate the verified manifest for this artifact (needed for version
        # and blockmap metadata)
        manifest_version = version or self._manifest_version_for(name)

        # block reuse plan
        plan = None
        blockmap = None
        old_path = current_artifact_path()
        if artifact.get("blockmap_sha256") and old_path and os.path.isfile(old_path):
            try:
                bm_bytes = self._fetch_via_transports(
                    transports,
                    channel,
                    blockmap_name(name),
                    version=manifest_version,
                )
                blockmap = verify_blockmap_entry(artifact, bm_bytes)
                matcher = BlockMatcher(blockmap)
                plan = matcher.plan(old_path)
                if not plan_is_viable(plan, size):
                    plan = None
            except Exception:
                plan = None
                blockmap = None

        fetched_bytes = 0
        reused_bytes = 0
        incomplete_download = False
        try:
            if plan is not None:
                self._assemble_with_reuse(
                    plan,
                    old_path,
                    tmp_path,
                    size,
                    transports,
                    channel,
                    name,
                    manifest_version,
                )
                fetched_bytes = plan["missing_bytes"]
                reused_bytes = plan["matched_bytes"]
            else:
                try:
                    self._full_download(
                        tmp_path,
                        size,
                        transports,
                        channel,
                        name,
                        manifest_version,
                    )
                except Exception:
                    # keep the partial file so a later attempt resumes it
                    incomplete_download = True
                    raise
                fetched_bytes = size
            # verify whole-file hash+size
            if tmp_path.stat().st_size != size or sha256_file(tmp_path) != sha:
                # retry once as a full download
                self._set_progress(phase="verify_retry", artifact=name)
                tmp_path.unlink(missing_ok=True)
                try:
                    self._full_download(
                        tmp_path,
                        size,
                        transports,
                        channel,
                        name,
                        manifest_version,
                    )
                except Exception:
                    incomplete_download = True
                    raise
                if tmp_path.stat().st_size != size or sha256_file(tmp_path) != sha:
                    raise UpdateVerifyError(
                        "downloaded artifact failed sha256/size verification"
                    )
            os.replace(tmp_path, out_path)
        except Exception:
            if not incomplete_download:
                try:
                    tmp_path.unlink(missing_ok=True)
                except OSError:
                    pass
            raise

        # stage marker atomically
        primary = {
            "file": name,
            "sha256": sha,
            "size": size,
            "kind": artifact.get("kind") or "other",
            "platform": artifact.get("platform"),
            "arch": artifact.get("arch"),
            "version": manifest_version or artifact.get("version"),
            "bytes_fetched": fetched_bytes,
            "bytes_reused": reused_bytes,
        }
        marker = {
            "version": 1,
            "staged_at": now_iso(),
            "channel": channel,
            "apply_policy": settings.apply_policy,
            # top-level fields kept for desktop/internal/updateapply
            "file": name,
            "sha256": sha,
            "kind": primary["kind"],
            "platform": primary["platform"],
            "artifacts": [primary],
        }
        atomic_write_json(pending_marker_path(self.storage_dir), marker)
        self._set_progress(
            phase="staged",
            artifact=name,
            size=size,
            downloaded=size,
            reused=reused_bytes,
            fetched=fetched_bytes,
        )
        # feed peer relay
        if self._peer is not None:
            try:
                cached = self._last_manifest.get(channel)
                if cached:
                    self._peer.register_manifest(
                        channel, cached["rsm"], cached["manifest"]
                    )
                self._peer.register_artifact(name, out_path, sha, size)
            except Exception:
                pass
        self._record_last_check(
            {
                "at": now_iso(),
                "result": "staged",
                "channel": channel,
                "artifact": name,
                "version": manifest_version,
                "bytes_fetched": fetched_bytes,
                "bytes_reused": reused_bytes,
            }
        )
        return {
            "status": "staged",
            "artifact": name,
            "path": str(out_path),
            "size": size,
            "sha256": sha,
            "bytes_fetched": fetched_bytes,
            "bytes_reused": reused_bytes,
        }

    def _manifest_version_for(self, name: str) -> str:
        for cached in self._last_manifest.values():
            entry = cached.get("entry") or {}
            if entry.get("name") == name:
                return str(cached["manifest"].get("version") or "")
        return ""

    def _fetch_via_transports(self, transports, channel, name, version=None) -> bytes:
        errors = []
        for t in transports:
            try:
                return t.fetch_file(channel, name, version=version)
            except FetchNotFound:
                continue
            except Exception as e:
                errors.append(str(e))
        if errors:
            raise FetchFailed("; ".join(errors))
        raise FetchNotFound(name)

    def _fetch_range_via_transports(
        self, transports, channel, name, version, start, end
    ) -> bytes:
        errors = []
        for t in transports:
            try:
                return t.fetch_file(
                    channel, name, version=version, start=start, end=end
                )
            except FetchNotFound:
                continue
            except Exception as e:
                errors.append(str(e))
        if errors:
            raise FetchFailed("; ".join(errors))
        raise FetchNotFound(name)

    def _full_download(self, out_path, size, transports, channel, name, version):
        """Whole-file download with resume via Range on retry."""
        done = out_path.stat().st_size if out_path.exists() else 0
        mode = "r+b" if done else "wb"
        if done > size:
            done = 0
        with open(out_path, mode) as fh:
            if done:
                fh.truncate(done)
            while done < size:
                chunk = self._fetch_range_via_transports(
                    transports, channel, name, version, done, size - 1
                )
                if not chunk:
                    raise FetchFailed("empty range response")
                fh.seek(done)
                fh.write(chunk)
                fh.flush()
                done += len(chunk)
                os.fsync(fh.fileno())
                self._set_progress(
                    phase="download", artifact=name, downloaded=done, size=size
                )

    def _assemble_with_reuse(
        self, plan, old_path, out_path, size, transports, channel, name, version
    ):
        """Write matched blocks from old file, fetch missing ranges."""
        bs = int(plan.get("block_size") or self._block_size_for(plan, size))
        fetch_ranges = missing_ranges(plan["missing"], bs, size)
        if len(fetch_ranges) > MAX_MISSING_RANGES:
            raise UpdateError("too many missing ranges; falling back")
        # preallocate
        with open(out_path, "wb") as fh:
            fh.truncate(size)
        # copy matched blocks
        with open(old_path, "rb") as src, open(out_path, "r+b") as dst:
            for old_off, new_off, length in plan["copy_ranges"]:
                src.seek(old_off)
                data = src.read(length)
                if len(data) != length:
                    raise UpdateError("short read on reuse source")
                dst.seek(new_off)
                dst.write(data)
            dst.flush()
            os.fsync(dst.fileno())
        # fetch missing ranges (bounded concurrency)
        results = {}
        errors = []
        lock = threading.Lock()

        def work(rng):
            s, e = rng
            try:
                data = self._fetch_range_via_transports(
                    transports, channel, name, version, s, e - 1
                )
                with lock:
                    results[rng] = data
            except Exception as ex:
                with lock:
                    errors.append(ex)

        threads = []
        for rng in fetch_ranges:
            th = threading.Thread(target=work, args=(rng,), daemon=True)
            th.start()
            threads.append(th)
            while sum(1 for t in threads if t.is_alive()) >= 4:
                time.sleep(0.01)
        for th in threads:
            th.join()
        if errors:
            raise FetchFailed(f"range fetch failed: {errors[0]}")
        with open(out_path, "r+b") as dst:
            got = 0
            for (s, e), data in results.items():
                if len(data) != e - s:
                    raise UpdateError("short range response")
                dst.seek(s)
                dst.write(data)
                got += len(data)
            dst.flush()
            os.fsync(dst.fileno())
        self._set_progress(
            phase="assemble",
            artifact=name,
            downloaded=size - plan["matched_bytes"],
            reused=plan["matched_bytes"],
            size=size,
        )

    def _block_size_for(self, plan, size) -> int:
        # block size = distance between consecutive matched new offsets
        offs = sorted(n for _o, n, _l in plan["copy_ranges"])
        for a, b in itertools.pairwise(offs):
            if b > a:
                return b - a
        return size or 512 * 1024

    # ------------------------------------------------------------------
    # manual verify (sneakernet / filesync import)
    # ------------------------------------------------------------------

    def apply_file(self, path, *, channel: str | None = None) -> dict:
        """Verify a user-supplied artifact against a stored signed manifest.

        Works fully offline: the manifest must already be stored (from a
        previous check) or supplied alongside as <file>.manifest.rsm.
        """
        settings = self.settings()
        p = Path(path)
        if not p.is_file():
            raise UpdateError("file not found")
        name = safe_artifact_name(p.name)
        if name is None:
            raise UpdateVerifyError("bad artifact name")
        size = p.stat().st_size
        if size <= 0 or size > artifact_cap_bytes(settings):
            raise UpdateVerifyError("artifact size invalid or over cap")
        # find manifest: prefer stored, else sidecar file
        manifest = None
        rsm = None
        chan = channel or self._channel(settings)
        stored = self.stored_manifest(chan)
        sidecar = p.with_name(p.name + ".manifest.rsm")
        if sidecar.is_file():
            try:
                rsm = sidecar.read_bytes()
                signers = pinned_signer_hashes(settings.signer_hashes)
                manifest = update_rsm.verify_rsm(rsm, required_signer_hashes=signers)
            except Exception:
                manifest = None
        if manifest is None and stored:
            manifest = stored["manifest"]
            rsm = stored["rsm"]
        if manifest is None:
            raise UpdateUnavailable(
                "no verified manifest available; run a check first or "
                "place <file>.manifest.rsm next to the file"
            )
        # find matching artifact entry
        artifacts = validate_manifest(
            manifest,
            channel=chan,
            current_version=self._current_version(),
            enforce_newer=False,
        )
        entry = None
        for a in artifacts:
            if a["name"] == name:
                entry = a
                break
        if entry is None:
            # allow name-agnostic match on hash after hashing the file
            sha = sha256_file(p)
            for a in artifacts:
                if a["sha256"] == sha:
                    entry = dict(a)
                    entry["name"] = name
                    break
        if entry is None:
            raise UpdateVerifyError("file does not match any manifest artifact")
        if entry["size"] != size:
            raise UpdateVerifyError("file size does not match manifest")
        sha = sha256_file(p)
        if sha != entry["sha256"]:
            raise UpdateVerifyError("file sha256 does not match manifest")
        # stage it
        target_dir = pending_dir(self.storage_dir)
        ensure_private_dir(target_dir)
        out_path = target_dir / name
        if out_path.resolve() != p.resolve():
            import shutil

            tmp = target_dir / (name + ".part")
            shutil.copyfile(p, tmp)
            os.replace(tmp, out_path)
        primary = {
            "file": name,
            "sha256": sha,
            "size": size,
            "kind": entry.get("kind") or "other",
            "platform": entry.get("platform"),
            "arch": entry.get("arch"),
            "version": str(manifest.get("version") or ""),
            "bytes_fetched": 0,
            "bytes_reused": 0,
            "source": "local",
        }
        marker = {
            "version": 1,
            "staged_at": now_iso(),
            "channel": chan,
            "apply_policy": settings.apply_policy,
            "file": name,
            "sha256": sha,
            "kind": primary["kind"],
            "platform": primary["platform"],
            "artifacts": [primary],
        }
        atomic_write_json(pending_marker_path(self.storage_dir), marker)
        self._record_last_check(
            {
                "at": now_iso(),
                "result": "staged",
                "channel": chan,
                "artifact": name,
                "version": str(manifest.get("version") or ""),
                "detail": "verified local file",
            }
        )
        return {
            "status": "staged",
            "artifact": name,
            "path": str(out_path),
            "size": size,
            "sha256": sha,
        }

    # ------------------------------------------------------------------
    # pending / discard
    # ------------------------------------------------------------------

    def get_pending(self) -> dict:
        marker = read_json_file(pending_marker_path(self.storage_dir))
        if not marker:
            return {"pending": None}
        arts = []
        for a in marker.get("artifacts") or []:
            p = pending_dir(self.storage_dir) / str(a.get("file"))
            arts.append({**a, "exists": p.is_file()})
        return {"pending": {**marker, "artifacts": arts}}

    def discard(self) -> dict:
        try:
            pending_marker_path(self.storage_dir).unlink(missing_ok=True)
        except OSError:
            pass
        try:
            for p in pending_dir(self.storage_dir).iterdir():
                if p.is_file():
                    p.unlink(missing_ok=True)
        except OSError:
            pass
        return {"status": "discarded"}

    # ------------------------------------------------------------------
    # status / settings
    # ------------------------------------------------------------------

    def status(self) -> dict:
        settings = self.settings()
        channel = self._channel(settings)
        pending = self.get_pending().get("pending")
        return {
            "enabled": bool(settings.enabled and not T.updates_disabled()),
            "disabled_by_env": T.updates_disabled(),
            "current_version": self._current_version(),
            "channel": channel,
            "settings": settings.as_dict(),
            "disclosure": disclosure_for(settings, channel),
            "last_check": self._last_check(),
            "progress": self.get_progress(),
            "pending": pending,
            "peer_relay_active": bool(self._peer is not None and self._peer.enabled),
            "platform": host_platform(),
            "arch": normalize_arch(),
        }

    def update_settings(self, patch: dict) -> dict:
        settings = self.settings()
        clean = settings.validate_patch(patch or {})
        config = self._config()
        if config is None:
            raise UpdateError("no config store available")
        for key, value in clean.items():
            if isinstance(value, bool):
                value = "true" if value else "false"
            elif value is not None and not isinstance(value, str):
                value = str(value)
            setter = getattr(config, "set", None)
            if setter is None:
                # ConfigManager exposes attribute configs; fall back to .value
                cfg = getattr(config, key, None)
                if cfg is not None and hasattr(cfg, "set"):
                    cfg.set(value)
                elif cfg is not None and hasattr(cfg, "value"):
                    cfg.value = value
                else:
                    raise UpdateError(f"unknown setting {key}")
            else:
                setter(key, value)
        self._reset_transports()
        self.refresh()
        return self.status()
