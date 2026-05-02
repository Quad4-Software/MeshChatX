# SPDX-License-Identifier: 0BSD

"""RNGit explorer: resolve paths and run ``/git/list`` for candidate repo names."""

from __future__ import annotations

import asyncio
import base64
import contextlib
import re
from typing import Any

import RNS

RNGIT_ANNOUNCE_ASPECT = "git.repositories"

RNGIT_APP_NAME = "git"
RNGIT_ASPECT = "repositories"
RNGIT_PATH_LIST = "/git/list"
RNGIT_IDX_REPOSITORY = 0x00

_MAX_PROBE_NAMES = 64
_MAX_REFS_PREVIEW_CHARS = 8000

_MAX_RNGIT_PATH_TIMEOUT_S = 600.0
_MAX_RNGIT_LINK_TIMEOUT_S = 180.0
_MAX_RNGIT_LIST_TIMEOUT_S = 600.0


def _clamp_timeout(
    value: float | None,
    *,
    default: float,
    minimum: float,
    maximum: float,
) -> float:
    if value is None:
        return default
    try:
        v = float(value)
    except (TypeError, ValueError):
        return default
    if v < minimum:
        return minimum
    return min(v, maximum)


def display_name_from_rngit_app_data(app_data_b64: str | None) -> str | None:
    """Decode optional rngit announce app_data (often a short node label)."""
    if not app_data_b64:
        return None
    try:
        raw = base64.b64decode(app_data_b64)
    except Exception:
        return None
    if not raw:
        return None
    text = raw.decode("utf-8", errors="replace").strip()
    if not text:
        return None
    line = text.splitlines()[0].strip()
    if not line:
        return None
    return line[:120]


def normalize_destination_hash_hex(value: str) -> str | None:
    raw = value.strip().lower().replace(":", "")
    if len(raw) != RNS.Reticulum.TRUNCATED_HASHLENGTH // 4:
        return None
    try:
        bytes.fromhex(raw)
    except ValueError:
        return None
    return raw


def slug_segment(name: str) -> str | None:
    s = name.strip()
    if not s or len(s) > 256:
        return None
    if not re.fullmatch(r"[A-Za-z0-9._-]+", s):
        return None
    return s


def parse_repository_name_lines(
    text: str, *, limit: int = _MAX_PROBE_NAMES
) -> list[str]:
    out: list[str] = []
    for line in text.splitlines():
        s = line.strip()
        if not s or s.startswith("#"):
            continue
        if len(out) >= limit:
            break
        out.append(s)
    return out


def clone_command(destination_hash_hex: str, group: str, repository: str) -> str:
    return f"git clone rns://{destination_hash_hex}/{group}/{repository}"


async def list_remote_git_refs(
    identity: RNS.Identity,
    destination_hash_hex: str,
    group_name: str,
    repository_name: str,
    *,
    path_timeout: float | None = None,
    link_timeout: float | None = None,
    list_timeout: float | None = None,
    for_push: bool = False,
) -> dict[str, Any]:
    """Open an rngit link and perform ``/git/list`` for ``group_name/repository_name``."""
    norm_hash = normalize_destination_hash_hex(destination_hash_hex)
    if not norm_hash:
        return {"ok": False, "error": "invalid_destination_hash"}
    group = slug_segment(group_name)
    repo = slug_segment(repository_name)
    if not group:
        return {"ok": False, "error": "invalid_group_name"}
    if not repo:
        return {"ok": False, "error": "invalid_repository_name"}

    path_timeout = _clamp_timeout(
        path_timeout,
        default=float(RNS.Transport.PATH_REQUEST_TIMEOUT),
        minimum=1.0,
        maximum=_MAX_RNGIT_PATH_TIMEOUT_S,
    )
    link_timeout = _clamp_timeout(
        link_timeout,
        default=30.0,
        minimum=1.0,
        maximum=_MAX_RNGIT_LINK_TIMEOUT_S,
    )
    list_timeout = _clamp_timeout(
        list_timeout,
        default=120.0,
        minimum=1.0,
        maximum=_MAX_RNGIT_LIST_TIMEOUT_S,
    )

    destination_hash = bytes.fromhex(norm_hash)

    loop = asyncio.get_running_loop()
    if not RNS.Transport.has_path(destination_hash):
        RNS.Transport.request_path(destination_hash)

    deadline = loop.time() + path_timeout
    while not RNS.Transport.has_path(destination_hash) and loop.time() < deadline:
        await asyncio.sleep(0.1)

    if not RNS.Transport.has_path(destination_hash):
        return {"ok": False, "error": "path_not_found"}

    remote_identity = RNS.Identity.recall(destination_hash)
    if not remote_identity:
        return {"ok": False, "error": "identity_not_found"}

    destination = RNS.Destination(
        remote_identity,
        RNS.Destination.OUT,
        RNS.Destination.SINGLE,
        RNGIT_APP_NAME,
        RNGIT_ASPECT,
    )
    link = RNS.Link(destination)

    link_ready = False
    link_failed = False
    done_event = asyncio.Event()
    response_holder: dict[str, Any] = {}

    def on_established(lnk: RNS.Link):
        nonlocal link_ready, link_failed
        try:
            lnk.identify(identity)
            link_ready = True
        except Exception:
            link_failed = True

    def on_closed(_lnk: RNS.Link):
        nonlocal link_failed
        if not link_ready:
            link_failed = True

    link.set_link_established_callback(on_established)
    link.set_link_closed_callback(on_closed)

    try:
        deadline = loop.time() + link_timeout
        while not link_ready and not link_failed and loop.time() < deadline:
            await asyncio.sleep(0.1)

        if not link_ready or link_failed:
            return {"ok": False, "error": "link_failed"}

        repo_path = f"{group}/{repo}"
        request_data: dict[str, Any] = {
            RNGIT_IDX_REPOSITORY: repo_path,
            "for_push": bool(for_push),
        }

        def on_response(request_receipt):
            response_holder["response"] = getattr(request_receipt, "response", None)
            loop.call_soon_threadsafe(done_event.set)

        def on_failed(_request_receipt=None):
            response_holder["response"] = None
            loop.call_soon_threadsafe(done_event.set)

        receipt = link.request(
            RNGIT_PATH_LIST,
            request_data,
            response_callback=on_response,
            failed_callback=on_failed,
            timeout=list_timeout,
        )
        if receipt is False:
            return {"ok": False, "error": "request_not_sent"}

        try:
            await asyncio.wait_for(done_event.wait(), timeout=list_timeout + 5.0)
        except TimeoutError:
            return {"ok": False, "error": "list_timeout"}

        response = response_holder.get("response")
        if response is None or not isinstance(response, (bytes, bytearray)):
            return {"ok": False, "error": "invalid_response"}

        body = bytes(response)
        if len(body) < 1:
            return {"ok": False, "error": "empty_response"}

        status_byte = body[0]
        payload = body[1:]
        if status_byte != 0:
            return {
                "ok": False,
                "error": payload.decode("utf-8", errors="replace").strip()
                or "server_refused",
            }

        return {"ok": True, "refs": payload.decode("utf-8", errors="replace")}
    finally:
        with contextlib.suppress(Exception):
            link.teardown()


async def probe_repositories(
    identity: RNS.Identity,
    destination_hash_hex: str,
    group_name: str,
    repository_names: list[str],
    *,
    path_timeout: float | None = None,
    link_timeout: float | None = None,
    list_timeout: float | None = None,
    for_push: bool = False,
    max_preview_chars: int = _MAX_REFS_PREVIEW_CHARS,
) -> dict[str, Any]:
    """Try ``/git/list`` for each repository name; used when rngit has no index endpoint."""
    norm = normalize_destination_hash_hex(destination_hash_hex)
    if not norm:
        return {"ok": False, "error": "invalid_destination_hash", "results": []}
    group = slug_segment(group_name)
    if not group:
        return {"ok": False, "error": "invalid_group_name", "results": []}

    trimmed = [n.strip() for n in repository_names if n.strip()][:_MAX_PROBE_NAMES]
    if not trimmed:
        return {"ok": False, "error": "no_repository_names", "results": []}

    results: list[dict[str, Any]] = []
    for raw in trimmed:
        repo = slug_segment(raw)
        if not repo:
            results.append(
                {
                    "repository": raw,
                    "reachable": False,
                    "error": "invalid_repository_name",
                    "clone_command": None,
                },
            )
            continue

        listed = await list_remote_git_refs(
            identity,
            norm,
            group,
            repo,
            path_timeout=path_timeout,
            link_timeout=link_timeout,
            list_timeout=list_timeout,
            for_push=for_push,
        )
        cmd = clone_command(norm, group, repo)
        if listed.get("ok"):
            refs = listed.get("refs") or ""
            results.append(
                {
                    "repository": repo,
                    "reachable": True,
                    "refs_preview": refs[:max_preview_chars],
                    "refs_truncated": len(refs) > max_preview_chars,
                    "clone_command": cmd,
                    "error": None,
                },
            )
        else:
            results.append(
                {
                    "repository": repo,
                    "reachable": False,
                    "refs_preview": None,
                    "refs_truncated": False,
                    "clone_command": cmd,
                    "error": listed.get("error"),
                },
            )

    return {
        "ok": True,
        "destination_hash": norm,
        "group_name": group,
        "results": results,
    }
