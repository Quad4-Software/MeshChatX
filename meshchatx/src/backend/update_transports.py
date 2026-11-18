# SPDX-License-Identifier: 0BSD
"""Update transports: clearnet HTTP mirrors and RNS request/reply.

Every transport is untrusted. The signed manifest is the only trust
anchor; transports only move bytes. HttpTransport tries an ordered mirror
list with ETag conditional fetches, redirect host allowlisting and HTTP
Range support. RnsTransport speaks a small msgpack request/reply protocol
on the "meshchatx.update" destination using an ephemeral identity and a
pluggable link session so tests can run without a network.
"""

from __future__ import annotations

import json
import threading
import time
import urllib.error
import urllib.request

from meshchatx.src.backend import update_types as T
from meshchatx.src.backend.privacy_mode import (
    OutboundHttpBlockedError,
    ensure_outbound_http_allowed,
)
from meshchatx.src.backend.update_types import (
    ARTIFACT_MAX_BYTES,
    HTTP_MAX_REDIRECTS,
    MANIFEST_MAX_BYTES,
    RNS_RANGE_MAX_BYTES,
    USER_AGENT,
    UpdateError,
    UpdateUnavailable,
    UpdateVerifyError,
    env_mirrors_override,
    mirror_asset_name,
)


class FetchNotFound(UpdateError):
    """Mirror answered 404 for the requested object."""


class FetchFailed(UpdateError):
    """Transport-level failure (network, timeout, bad status)."""


# --------------------------------------------------------------------------
# HTTP transport
# --------------------------------------------------------------------------


class _RedirectAllowlist(urllib.request.HTTPRedirectHandler):
    """Follow redirects only to hosts already in the allowlist, max hops."""

    def __init__(self, allowed_hosts):
        self.allowed_hosts = set(allowed_hosts)

    def redirect_request(self, req, fp, code, msg, headers, newurl):
        hops = getattr(req, "_redirect_allowlist_hops", 0) + 1
        if hops > HTTP_MAX_REDIRECTS:
            raise FetchFailed("too many redirects")
        host = urllib.request.urlparse(newurl).hostname or ""
        if host not in self.allowed_hosts:
            raise FetchFailed(f"redirect to disallowed host {host}")
        new_req = super().redirect_request(req, fp, code, msg, headers, newurl)
        if new_req is not None:
            new_req._redirect_allowlist_hops = hops
        return new_req


def _mirror_hosts(mirrors) -> set:
    hosts = set()
    for m in mirrors:
        try:
            h = urllib.request.urlparse(m["base"]).hostname
            if h:
                hosts.add(h)
        except Exception:
            continue
    return hosts


class _NoCookieProcessor(urllib.request.HTTPCookieProcessor):
    def http_response(self, request, response):
        return response

    https_response = http_response


class HttpResponse:
    def __init__(self, status, headers, body):
        self.status = status
        self.headers = headers
        self.body = body


class HttpTransport:
    """Ordered-mirror clearnet transport.

    Mirrors: {"name","kind","base"} where kind is "static" (plain file
    layout), "github" or "forgejo" (release API resolution). All are
    untrusted; callers verify everything they receive.
    """

    def __init__(self, mirrors=None, timeout: float = 30.0, config=None):
        self._config = config
        self.mirrors = list(mirrors) if mirrors else T.default_mirrors()
        env = env_mirrors_override()
        if env:
            self.mirrors = env + [m for m in self.mirrors if m["name"] != "env"]
        self.timeout = timeout
        self._release_cache = {}  # (mirror_name, channel) -> dict
        self._release_lock = threading.Lock()
        self._etags = {}  # (mirror_name, channel) -> etag
        self._opener = self._build_opener()

    def _build_opener(self):
        hosts = _mirror_hosts(self.mirrors)
        # release API hosts for github/forgejo mirrors
        for m in self.mirrors:
            try:
                h = urllib.request.urlparse(m["base"]).hostname
                if h:
                    hosts.add(h)
            except Exception:
                pass
        hosts.add("api.github.com")
        hosts.add("git.quad4.io")
        return urllib.request.build_opener(
            _RedirectAllowlist(hosts),
            urllib.request.HTTPHandler(),
            urllib.request.HTTPSHandler(),
        )

    # -- low level ---------------------------------------------------------

    def _request(self, url, headers=None, method="GET", data=None):
        ensure_outbound_http_allowed(self._config, feature="update transport")
        req = urllib.request.Request(url, data=data, method=method)  # noqa: S310 - mirror URLs validated to https or loopback
        req.add_header("User-Agent", USER_AGENT)
        req.add_header("Accept", "*/*")
        for k, v in (headers or {}).items():
            req.add_header(k, v)
        try:
            with self._opener.open(req, timeout=self.timeout) as resp:
                return HttpResponse(resp.status, resp.headers, resp.read())
        except urllib.error.HTTPError as e:
            body = b""
            try:
                body = e.read() or b""
            except Exception:
                pass
            return HttpResponse(e.code, e.headers or {}, body)
        except Exception as e:
            raise FetchFailed(f"{url}: {e}") from e

    # -- release resolution (github/forgejo) --------------------------------

    def _release_for(self, mirror, channel: str, max_age: float = 300.0):
        """Resolve the newest release carrying update-manifest-{channel}.rsm.

        Returns {"tag","assets":{name:url},"published"} or None.
        """
        key = (mirror["name"], channel)
        with self._release_lock:
            cached = self._release_cache.get(key)
            if cached and time.time() - cached["ts"] < max_age:
                return cached["release"]
        release = self._fetch_release(mirror, channel)
        with self._release_lock:
            self._release_cache[key] = {"ts": time.time(), "release": release}
        return release

    def _fetch_release(self, mirror, channel):
        base = mirror["base"].rstrip("/")
        kind = mirror.get("kind", "static")
        if kind == "github":
            path = base.split("github.com/", 1)[-1]
            api = f"https://api.github.com/repos/{path}/releases?per_page=30"
        elif kind == "forgejo":
            rest = base.split("://", 1)[-1]
            host = rest.split("/", 1)[0]
            path = rest.split("/", 1)[1] if "/" in rest else ""
            api = f"https://{host}/api/v1/repos/{path}/releases?limit=30"
        else:
            return None
        resp = self._request(api, headers={"Accept": "application/vnd.github+json"})
        if resp.status != 200:
            return None
        try:
            releases = json.loads(resp.body.decode("utf-8"))
        except Exception:
            return None
        if not isinstance(releases, list):
            return None
        want = mirror_asset_name(channel)
        for rel in releases:
            if not isinstance(rel, dict) or rel.get("draft"):
                continue
            assets = rel.get("assets") or []
            asset_map = {}
            for a in assets:
                name = a.get("name")
                url = a.get("browser_download_url") or a.get("url")
                if name and url:
                    asset_map[name] = url
            if want in asset_map:
                return {
                    "tag": rel.get("tag_name") or "",
                    "assets": asset_map,
                    "published": rel.get("published_at") or "",
                }
        return None

    # -- manifest -----------------------------------------------------------

    def fetch_manifest(self, channel: str, etag: str | None = None):
        """Fetch the signed manifest, trying mirrors in order.

        Returns a dict with status ok, unchanged or none, the manifest
        bytes when ok, the ETag when known, and the mirror name.
        """
        for mirror in self.mirrors:
            mkey = (mirror["name"], channel)
            eff_etag = self._etags.get(mkey) or etag
            headers = {}
            if eff_etag:
                headers["If-None-Match"] = eff_etag
            kind = mirror.get("kind", "static")
            try:
                if kind in ("github", "forgejo"):
                    rel = self._release_for(mirror, channel)
                    if not rel:
                        continue
                    url = rel["assets"].get(mirror_asset_name(channel))
                    if not url:
                        continue
                    ok, etag_out, body = self._get_conditional(url, headers)
                    if ok == "unchanged":
                        return {
                            "status": "unchanged",
                            "data": None,
                            "etag": eff_etag,
                            "source": mirror["name"],
                        }
                    if ok == "ok" and body is not None:
                        if len(body) > MANIFEST_MAX_BYTES:
                            raise UpdateVerifyError("manifest exceeds size cap")
                        if etag_out:
                            self._etags[mkey] = etag_out
                        return {
                            "status": "ok",
                            "data": body,
                            "etag": etag_out,
                            "source": mirror["name"],
                        }
                    continue
                # static mirror
                url = f"{mirror['base'].rstrip('/')}/updates/{channel}/manifest.rsm"
                ok, etag_out, body = self._get_conditional(url, headers)
                if ok == "unchanged":
                    return {
                        "status": "unchanged",
                        "data": None,
                        "etag": eff_etag,
                        "source": mirror["name"],
                    }
                if ok == "ok" and body is not None:
                    if len(body) > MANIFEST_MAX_BYTES:
                        raise UpdateVerifyError("manifest exceeds size cap")
                    if etag_out:
                        self._etags[mkey] = etag_out
                    return {
                        "status": "ok",
                        "data": body,
                        "etag": etag_out,
                        "source": mirror["name"],
                    }
            except FetchNotFound:
                continue
            except UpdateVerifyError:
                raise
            except OutboundHttpBlockedError:
                raise
            except Exception:
                continue
        return {"status": "none", "data": None, "etag": None, "source": None}

    def _get_conditional(self, url, headers):
        resp = self._request(url, headers=headers)
        if resp.status == 304:
            return "unchanged", headers.get("If-None-Match"), None
        if resp.status == 404:
            raise FetchNotFound(url)
        if resp.status != 200:
            raise FetchFailed(f"{url}: HTTP {resp.status}")
        etag = resp.headers.get("ETag") if resp.headers else None
        return "ok", etag, resp.body

    # -- artifacts -----------------------------------------------------------

    def fetch_file(
        self,
        channel: str,
        name: str,
        version: str | None = None,
        start: int | None = None,
        end: int | None = None,
    ):
        """Fetch an artifact (or range) trying mirrors in order.

        Returns bytes. Raises FetchNotFound if no mirror has it, FetchFailed
        on transport errors.
        """
        safe = T.safe_artifact_name(name)
        if safe is None:
            raise UpdateVerifyError(f"bad artifact name {name!r}")
        name = safe
        last_err = None
        for mirror in self.mirrors:
            kind = mirror.get("kind", "static")
            try:
                if kind in ("github", "forgejo"):
                    rel = self._release_for(mirror, channel)
                    if not rel:
                        continue
                    url = rel["assets"].get(name)
                    if not url:
                        continue
                    return self._get_range(url, start, end)
                if not version:
                    continue
                url = f"{mirror['base'].rstrip('/')}/updates/{channel}/{version}/{name}"
                return self._get_range(url, start, end)
            except FetchNotFound:
                continue
            except OutboundHttpBlockedError:
                raise
            except Exception as e:
                last_err = e
                continue
        if last_err is not None and not isinstance(last_err, FetchNotFound):
            raise FetchFailed(str(last_err))
        raise FetchNotFound(name)

    def _get_range(self, url, start, end):
        headers = {}
        if start is not None:
            headers["Range"] = f"bytes={start}-{end if end is not None else ''}"
        resp = self._request(url, headers=headers)
        if resp.status == 404:
            raise FetchNotFound(url)
        if resp.status == 304:
            raise FetchFailed("unexpected 304 on artifact fetch")
        if resp.status == 206:
            return resp.body
        if resp.status == 200:
            if start is None:
                return resp.body
            # server ignored Range; slice if the full body is present
            if end is None:
                return resp.body[start:]
            return resp.body[start : end + 1]
        raise FetchFailed(f"{url}: HTTP {resp.status}")

    def fetch_blockmap(self, channel, artifact_name, version=None):
        return self.fetch_file(channel, artifact_name + ".blockmap", version=version)


# --------------------------------------------------------------------------
# RNS transport
# --------------------------------------------------------------------------

RNS_UPDATE_PATH = "/update"


def _mp_pack(obj) -> bytes:
    from RNS.vendor import umsgpack as mp

    return mp.packb(obj, use_bin_type=True)


def _mp_unpack(data: bytes):
    from RNS.vendor import umsgpack as mp

    return mp.unpackb(data)


class RnsSession:
    """One request/reply round trip over an RNS link.

    session_factory(destination_hash) -> session; session.request(path,
    data, timeout) -> response bytes. Injectable for tests.
    """

    def __init__(self, link_manager=None, identity=None):
        self._lm = link_manager
        self._identity = identity  # ephemeral RNS.Identity or None
        self._links = {}
        self._lock = threading.Lock()

    def _ensure_identity(self):
        if self._identity is None:
            import RNS

            self._identity = RNS.Identity()  # throwaway, never announced
        return self._identity

    @property
    def identity(self):
        return self._ensure_identity()

    def request(
        self, destination_hash: bytes, path: str, data: bytes, timeout: float = 60.0
    ) -> bytes:
        """Synchronous request/reply. Raises UpdateError on failure."""
        if self._lm is None:
            raise UpdateUnavailable("no RNS link manager available")
        result = {}
        done = threading.Event()

        def on_response(receipt):
            try:
                result["data"] = _receipt_data(receipt)
            except Exception as e:
                result["error"] = e
            done.set()

        def on_failed(receipt=None):
            result["error"] = UpdateError("rns request failed")
            done.set()

        try:
            self._lm.request(
                destination_hash,
                T.RNS_UPDATE_ASPECT,
                path,
                data,
                on_response,
                on_failed,
                lambda _r: None,
                timeout=timeout,
            )
        except RuntimeError as e:
            raise UpdateUnavailable(f"no RNS link: {e}") from e
        except Exception as e:
            raise UpdateError(f"rns request error: {e}") from e
        if not done.wait(timeout + 5.0):
            raise UpdateError("rns request timed out")
        if "error" in result:
            raise result["error"]
        data_out = result.get("data")
        if data_out is None:
            raise UpdateError("rns empty response")
        return data_out

    def open_link(self, destination_hash: bytes, timeout: float = 60.0):
        """Ensure a link exists (path lookup + establishment)."""
        if self._lm is None:
            raise UpdateUnavailable("no RNS link manager available")
        import asyncio

        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            loop = None
        if loop is not None:
            # caller is async; run in a thread to avoid nested-loop issues
            import concurrent.futures

            with concurrent.futures.ThreadPoolExecutor(1) as ex:
                return ex.submit(
                    asyncio.run,
                    self._lm.open_link(
                        destination_hash,
                        T.RNS_UPDATE_ASPECT,
                        auto_identify=False,
                        path_lookup_timeout=timeout,
                        link_establishment_timeout=timeout,
                    ),
                ).result(timeout + 10)
        return asyncio.run(
            self._lm.open_link(
                destination_hash,
                T.RNS_UPDATE_ASPECT,
                auto_identify=False,
                path_lookup_timeout=timeout,
                link_establishment_timeout=timeout,
            )
        )


def _receipt_data(receipt):
    """Extract response bytes from a RequestReceipt, defensively."""
    for attr in ("data", "packet_data"):
        v = getattr(receipt, attr, None)
        if isinstance(v, (bytes, bytearray)):
            return bytes(v)
    pr = getattr(receipt, "packet_receipt", None)
    if pr is not None:
        v = getattr(pr, "data", None)
        if isinstance(v, (bytes, bytearray)):
            return bytes(v)
    res = getattr(receipt, "resource", None)
    if res is not None:
        for meth in ("get_data", "read", "data"):
            fn = getattr(res, meth, None)
            try:
                if callable(fn):
                    out = fn()
                else:
                    out = fn
            except Exception:
                out = None
            if isinstance(out, (bytes, bytearray)):
                return bytes(out)
    raise UpdateError("unrecognized rns response receipt")


class RnsTransport:
    """RNS request/reply transport for the meshchatx.update destination.

    Protocol (all payloads umsgpack dicts on path "/update"):
      {"op":"probe","channel":c,"sha256":hex} -> {"s":"same"|"ok"|"none", ...}
      {"op":"manifest","channel":c}         -> {"s":"ok","d":rsm}|{"s":"none"}
      {"op":"head","name":n}                -> {"s":"ok","size":N}|{"s":"none"}
      {"op":"range","name":n,"o":off,"l":len} -> {"s":"ok","d":bytes}|{"s":"none"}

    Destinations are learned from announces (learn_destination) plus
    configured seeds. An ephemeral RNS.Identity is used; the user's main
    identity is never used for update links.
    """

    def __init__(
        self,
        session=None,
        link_manager=None,
        seeds=None,
        timeout: float = 60.0,
        rate_kbps: float = 256.0,
    ):
        self._session = session or RnsSession(link_manager=link_manager)
        self.timeout = timeout
        self.rate_kbps = rate_kbps
        self._destinations = []
        self._seen = set()
        self._lock = threading.Lock()
        for h in seeds or []:
            self.add_seed(h)
        self._manifest_sha = {}  # channel -> last accepted rsm sha256
        # rate limiter state
        self._rate_lock = threading.Lock()
        self._rate_tokens = rate_kbps * 125.0  # bytes per second
        self._rate_last = time.monotonic()

    @property
    def identity(self):
        return self._session.identity

    def add_seed(self, hexhash: str):
        try:
            raw = bytes.fromhex(hexhash)
        except (ValueError, TypeError):
            return
        if len(raw) == 16:
            self._add_destination(raw)

    def learn_destination(self, destination_hash: bytes):
        """Called by the announce handler when a peer announces."""
        if (
            isinstance(destination_hash, (bytes, bytearray))
            and len(destination_hash) == 16
        ):
            self._add_destination(bytes(destination_hash))

    def _add_destination(self, dh: bytes):
        with self._lock:
            if dh in self._seen:
                return
            if len(self._destinations) >= 32:
                self._seen.discard(self._destinations.pop(0))
            self._seen.add(dh)
            self._destinations.append(dh)

    def destinations(self):
        with self._lock:
            return list(self._destinations)

    # -- rate limiting --------------------------------------------------------

    def _throttle(self, nbytes: int):
        """=Sleep to keep transfer under rate_kbps. Modest and best-effort."""
        if self.rate_kbps <= 0 or nbytes <= 0:
            return
        bps = self.rate_kbps * 1000.0 / 8.0
        with self._rate_lock:
            now = time.monotonic()
            self._rate_tokens = min(
                self._rate_tokens + (now - self._rate_last) * bps,
                bps * 30.0,
            )
            self._rate_last = now
            if self._rate_tokens >= nbytes:
                self._rate_tokens -= nbytes
                return
            deficit = nbytes - self._rate_tokens
            self._rate_tokens = 0.0
        time.sleep(deficit / bps)

    # -- protocol --------------------------------------------------------------

    def _roundtrip(self, request: dict, timeout=None):
        """Try each known destination until one answers."""
        data = _mp_pack(request)
        dests = self.destinations()
        if not dests:
            raise UpdateUnavailable("no known RNS update destinations")
        last_err = None
        for dh in dests:
            try:
                # ensure path exists; abort cleanly when unknown
                self._session.open_link(dh, timeout=timeout or self.timeout)
                raw = self._session.request(
                    dh, RNS_UPDATE_PATH, data, timeout=timeout or self.timeout
                )
                resp = _mp_unpack(raw)
                if isinstance(resp, dict):
                    return resp
                raise UpdateError("bad rns response")
            except UpdateUnavailable:
                raise
            except Exception as e:
                last_err = e
                continue
        raise UpdateError(f"all RNS update destinations failed: {last_err}")

    # -- public API matching HttpTransport -------------------------------------

    def fetch_manifest(self, channel: str, etag: str | None = None):
        """Etag is the sha256 of the last accepted manifest rsm."""
        known = (etag or self._manifest_sha.get(channel) or "").lower() or None
        req = {"op": "probe", "channel": channel, "sha256": known}
        try:
            resp = self._roundtrip(req)
        except UpdateUnavailable:
            return {"status": "none", "data": None, "etag": None, "source": "rns"}
        s = resp.get("s")
        if s == "same":
            return {"status": "unchanged", "data": None, "etag": etag, "source": "rns"}
        if s == "ok" and isinstance(resp.get("d"), (bytes, bytearray)):
            body = bytes(resp["d"])
            if len(body) > MANIFEST_MAX_BYTES:
                raise UpdateVerifyError("manifest exceeds size cap")
            fp = T.manifest_fingerprint(body)
            self._manifest_sha[channel] = fp
            return {"status": "ok", "data": body, "etag": fp, "source": "rns"}
        return {"status": "none", "data": None, "etag": None, "source": "rns"}

    def fetch_file(
        self,
        channel: str,
        name: str,
        version: str | None = None,
        start: int | None = None,
        end: int | None = None,
    ):
        safe = T.safe_artifact_name(name)
        if safe is None:
            raise UpdateVerifyError(f"bad artifact name {name!r}")
        name = safe
        if start is None and end is None:
            # whole file: ask for size then pull ranges
            resp = self._roundtrip({"op": "head", "name": name})
            if resp.get("s") != "ok":
                raise FetchNotFound(name)
            size = int(resp.get("size") or 0)
            if size <= 0:
                raise FetchFailed("bad size from rns peer")
            if size > ARTIFACT_MAX_BYTES:
                raise UpdateVerifyError("artifact exceeds size cap")
            out = bytearray()
            off = 0
            while off < size:
                length = min(RNS_RANGE_MAX_BYTES, size - off)
                chunk = self._range(name, off, off + length - 1)
                if not chunk:
                    raise FetchFailed("rns peer returned empty range")
                self._throttle(len(chunk))
                out += chunk
                off += len(chunk)
                if len(out) > ARTIFACT_MAX_BYTES:
                    raise UpdateVerifyError("artifact exceeds size cap")
            return bytes(out)
        start = int(start) if start is not None else 0
        if start < 0 or (end is not None and int(end) < start):
            raise UpdateError("bad range")
        length = (
            min(int(end) - start + 1, RNS_RANGE_MAX_BYTES)
            if end is not None
            else RNS_RANGE_MAX_BYTES
        )
        return self._range(name, start, end, length=length)

    def _range(self, name, start, end, length=None):
        length = length or (
            min(end - start + 1, RNS_RANGE_MAX_BYTES)
            if end is not None
            else RNS_RANGE_MAX_BYTES
        )
        req = {"op": "range", "name": name, "o": int(start), "l": int(length)}
        last_err = None
        for _attempt in range(T.RNS_MAX_RANGE_RETRIES + 1):
            try:
                resp = self._roundtrip(req)
                if resp.get("s") == "ok" and isinstance(
                    resp.get("d"), (bytes, bytearray)
                ):
                    data = bytes(resp["d"])
                    if len(data) > length:
                        raise UpdateError("rns peer sent oversized range")
                    return data
                if resp.get("s") == "none":
                    raise FetchNotFound(name)
                raise UpdateError(f"bad rns range response: {resp.get('s')}")
            except (FetchNotFound, UpdateUnavailable):
                raise
            except Exception as e:
                last_err = e
                time.sleep(0.5 * (_attempt + 1) + T.random.uniform(0, 0.5))
        raise UpdateError(f"rns range failed: {last_err}")

    def fetch_blockmap(self, channel, artifact_name, version=None):
        return self.fetch_file(channel, artifact_name + ".blockmap", version=version)


# --------------------------------------------------------------------------
# Transport selection
# --------------------------------------------------------------------------


def build_transports(
    settings, *, link_manager=None, rns_session=None, storage_dir=None, config=None
):
    """Return ordered list of transports per settings.transport.

    auto -> [clearnet, rns]; clearnet -> [clearnet]; rns -> [rns].
    """
    http = HttpTransport(mirrors=_mirrors_for(settings), config=config)
    rns = RnsTransport(
        session=rns_session,
        link_manager=link_manager,
        seeds=list(settings.rns_seeds) + T.env_rns_seeds(),
        rate_kbps=settings.rns_rate_kbps,
    )
    pref = settings.transport
    if pref == "clearnet":
        return [http], rns
    if pref == "rns":
        return [rns], rns
    return [http, rns], rns


def _mirrors_for(settings):
    if settings.custom_mirrors:
        return [
            {"name": "custom", "kind": "static", "base": m["base"]}
            for m in settings.custom_mirrors
        ]
    return T.default_mirrors()


def transport_kind(t) -> str:
    return "rns" if isinstance(t, RnsTransport) else "clearnet"
