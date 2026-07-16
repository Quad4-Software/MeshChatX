# SPDX-License-Identifier: 0BSD

"""JSON Schema definitions for WebSocket message bodies (contract tests)."""

from __future__ import annotations

from tests.backend.api_json_contract_schemas import assert_matches_schema


def _ws_type(
    msg_type: str,
    *,
    required: list[str] | None = None,
    properties: dict | None = None,
    additional_properties: bool = True,
) -> dict:
    props: dict = {"type": {"type": "string", "const": msg_type}}
    if properties:
        props.update(properties)
    return {
        "type": "object",
        "required": ["type", *(required or [])],
        "properties": props,
        "additionalProperties": additional_properties,
    }


_WS_OBJECT = {"type": "object", "additionalProperties": True}
_WS_STRING = {"type": "string"}
_WS_INTEGER = {"type": "integer"}
_WS_BOOL = {"type": "boolean"}

WS_MESSAGE_SCHEMAS: dict[str, dict] = {
    "ping": _ws_type("ping"),
    "pong": _ws_type("pong"),
    "error": _ws_type(
        "error",
        required=["message"],
        properties={"message": _WS_STRING},
    ),
    "startup_status": _ws_type(
        "startup_status",
        required=["status"],
        properties={
            "status": _WS_STRING,
            "stage": _WS_STRING,
            "network_ready": _WS_BOOL,
            "error": _WS_STRING,
        },
    ),
    "config.set": _ws_type(
        "config.set",
        required=["config"],
        properties={"config": _WS_OBJECT},
    ),
    "config": _ws_type(
        "config",
        required=["config"],
        properties={"config": _WS_OBJECT},
    ),
    "announced": _ws_type("announced"),
    "blocked_destinations": _ws_type(
        "blocked_destinations",
        required=["blocked_destinations"],
        properties={"blocked_destinations": {"type": "array", "items": _WS_OBJECT}},
    ),
    "keyboard_shortcuts.get": _ws_type("keyboard_shortcuts.get"),
    "keyboard_shortcuts.set": _ws_type(
        "keyboard_shortcuts.set",
        required=["shortcuts"],
        properties={"shortcuts": _WS_OBJECT},
    ),
    "keyboard_shortcuts.delete": _ws_type("keyboard_shortcuts.delete", required=["id"]),
    "keyboard_shortcuts": _ws_type(
        "keyboard_shortcuts",
        required=["shortcuts"],
        properties={"shortcuts": _WS_OBJECT},
    ),
    "nomadnet.download.cancel": _ws_type(
        "nomadnet.download.cancel",
        required=["download_id"],
        properties={"download_id": _WS_INTEGER},
    ),
    "nomadnet.download.cancelled": _ws_type(
        "nomadnet.download.cancelled",
        required=["download_id"],
        properties={"download_id": _WS_INTEGER},
    ),
    "nomadnet.page.archives.get": _ws_type(
        "nomadnet.page.archives.get",
        required=["destination_hash", "page_path"],
    ),
    "nomadnet.page.archives": _ws_type(
        "nomadnet.page.archives",
        required=["destination_hash", "page_path", "archives"],
        properties={"archives": {"type": "array", "items": _WS_OBJECT}},
    ),
    "nomadnet.page.archive.load": _ws_type(
        "nomadnet.page.archive.load",
        required=["archive_id"],
    ),
    "nomadnet.page.archive.flush": _ws_type("nomadnet.page.archive.flush"),
    "nomadnet.page.archive.add": _ws_type(
        "nomadnet.page.archive.add",
        required=["destination_hash", "page_path", "content"],
    ),
    "nomadnet.page.archive.added": _ws_type(
        "nomadnet.page.archive.added",
        required=["destination_hash", "page_path"],
    ),
    "nomadnet.file.download": _ws_type(
        "nomadnet.file.download",
        required=["download_id", "nomadnet_file_download"],
        properties={"nomadnet_file_download": _WS_OBJECT},
    ),
    "nomadnet.page.download": _ws_type(
        "nomadnet.page.download",
        required=["download_id", "nomadnet_page_download"],
        properties={"nomadnet_page_download": _WS_OBJECT},
    ),
    "lxmf.forwarding.rules.get": _ws_type("lxmf.forwarding.rules.get"),
    "lxmf.forwarding.rules": _ws_type(
        "lxmf.forwarding.rules",
        required=["rules"],
        properties={"rules": {"type": "array", "items": _WS_OBJECT}},
    ),
    "lxmf.forwarding.rule.add": _ws_type(
        "lxmf.forwarding.rule.add",
        required=["rule"],
        properties={"rule": _WS_OBJECT},
    ),
    "lxmf.forwarding.rule.delete": _ws_type(
        "lxmf.forwarding.rule.delete",
        required=["rule_id"],
    ),
    "lxmf.forwarding.rule.toggle": _ws_type(
        "lxmf.forwarding.rule.toggle",
        required=["rule_id", "enabled"],
        properties={"enabled": _WS_BOOL},
    ),
    "lxm.ingest_uri": _ws_type("lxm.ingest_uri", required=["uri"]),
    "lxm.ingest_uri.result": _ws_type(
        "lxm.ingest_uri.result",
        required=["success"],
        properties={"success": _WS_BOOL},
    ),
    "lxm.generate_paper_uri": _ws_type("lxm.generate_paper_uri"),
    "lxm.generate_paper_uri.result": _ws_type(
        "lxm.generate_paper_uri.result",
        required=["success"],
        properties={"success": _WS_BOOL},
    ),
    "announce": _ws_type(
        "announce",
        required=["announce"],
        properties={"announce": _WS_OBJECT},
    ),
    "lxmf.delivery": _ws_type("lxmf.delivery"),
    "lxmf_message_created": _ws_type(
        "lxmf_message_created",
        required=["lxmf_message"],
        properties={"lxmf_message": _WS_OBJECT},
    ),
    "lxmf_message_state_updated": _ws_type(
        "lxmf_message_state_updated",
        required=["lxmf_message"],
        properties={"lxmf_message": _WS_OBJECT},
    ),
    "lxmf_message_deleted": _ws_type("lxmf_message_deleted"),
    "lxmf.telemetry": _ws_type("lxmf.telemetry", required=["destination_hash"]),
    "identity_switched": _ws_type("identity_switched"),
    "reticulum_reload_status": _ws_type("reticulum_reload_status", required=["status"]),
    "new_voicemail": _ws_type("new_voicemail"),
    "telephone_ringing": _ws_type("telephone_ringing"),
    "telephone_call_established": _ws_type("telephone_call_established"),
    "telephone_missed_call": _ws_type("telephone_missed_call"),
    "telephone_call_ended": _ws_type("telephone_call_ended"),
    "telephone_initiation_status": _ws_type(
        "telephone_initiation_status",
        required=["status"],
    ),
    "rrc.change": _ws_type("rrc.change"),
    "rrc.message": _ws_type(
        "rrc.message",
        required=["message"],
        properties={"message": _WS_OBJECT},
    ),
    "rrc.server.change": _ws_type("rrc.server.change"),
    "rnsh.session.change": _ws_type("rnsh.session.change"),
    "rnsh.output": _ws_type("rnsh.output"),
    "rnx.session.change": _ws_type("rnx.session.change"),
    "rnx.output": _ws_type("rnx.output"),
    "rncp.transfer.progress": _ws_type("rncp.transfer.progress"),
    "rncp.send.completed": _ws_type("rncp.send.completed"),
    "rncp.fetch.completed": _ws_type("rncp.fetch.completed"),
    "rns.link.open": _ws_type(
        "rns.link.open",
        required=["request_id"],
        properties={
            "request_id": _WS_STRING,
            "destination_hash": _WS_STRING,
            "aspect": _WS_STRING,
            "status": _WS_STRING,
            "phase": _WS_STRING,
            "identified": _WS_BOOL,
            "failure_reason": {"type": ["string", "null"]},
            "auto_identify": _WS_BOOL,
        },
    ),
    "rns.link.identify": _ws_type(
        "rns.link.identify",
        required=["request_id"],
        properties={
            "request_id": _WS_STRING,
            "destination_hash": _WS_STRING,
            "aspect": _WS_STRING,
            "status": _WS_STRING,
            "failure_reason": {"type": ["string", "null"]},
        },
    ),
    "rns.link.request": _ws_type(
        "rns.link.request",
        required=["request_id"],
        properties={
            "request_id": _WS_STRING,
            "destination_hash": _WS_STRING,
            "aspect": _WS_STRING,
            "path": _WS_STRING,
            "data_b64": _WS_STRING,
            "body_b64": _WS_STRING,
            "status": _WS_STRING,
            "phase": _WS_STRING,
            "progress": {"type": "number"},
            "failure_reason": {"type": ["string", "null"]},
            "timeout": {"type": "number"},
        },
    ),
    "rns.link.send": _ws_type(
        "rns.link.send",
        required=["request_id"],
        properties={
            "request_id": _WS_STRING,
            "destination_hash": _WS_STRING,
            "aspect": _WS_STRING,
            "payload_b64": _WS_STRING,
            "status": _WS_STRING,
            "failure_reason": {"type": ["string", "null"]},
        },
    ),
    "rns.link.close": _ws_type(
        "rns.link.close",
        required=["request_id"],
        properties={
            "request_id": _WS_STRING,
            "destination_hash": _WS_STRING,
            "aspect": _WS_STRING,
            "status": _WS_STRING,
            "failure_reason": {"type": ["string", "null"]},
        },
    ),
    "rns.link.event": _ws_type(
        "rns.link.event",
        required=["event", "destination_hash", "aspect"],
        properties={
            "event": _WS_STRING,
            "destination_hash": _WS_STRING,
            "aspect": _WS_STRING,
            "payload_b64": _WS_STRING,
        },
    ),
}

WS_MESSAGE_SAMPLES: dict[str, dict] = {
    "ping": {"type": "ping"},
    "pong": {"type": "pong"},
    "error": {"type": "error", "message": "Authentication required"},
    "startup_status": {
        "type": "startup_status",
        "status": "ok",
        "stage": "ready",
        "network_ready": True,
    },
    "config.set": {"type": "config.set", "config": {"display_name": "Test"}},
    "config": {"type": "config", "config": {"display_name": "Test"}},
    "announced": {"type": "announced"},
    "blocked_destinations": {
        "type": "blocked_destinations",
        "blocked_destinations": [],
    },
    "keyboard_shortcuts.get": {"type": "keyboard_shortcuts.get"},
    "keyboard_shortcuts.set": {"type": "keyboard_shortcuts.set", "shortcuts": {}},
    "keyboard_shortcuts.delete": {
        "type": "keyboard_shortcuts.delete",
        "id": "nav_messages",
    },
    "keyboard_shortcuts": {"type": "keyboard_shortcuts", "shortcuts": {}},
    "nomadnet.download.cancel": {"type": "nomadnet.download.cancel", "download_id": 1},
    "nomadnet.download.cancelled": {
        "type": "nomadnet.download.cancelled",
        "download_id": 1,
    },
    "nomadnet.page.archives.get": {
        "type": "nomadnet.page.archives.get",
        "destination_hash": "aa" * 16,
        "page_path": "/page/index.mu",
    },
    "nomadnet.page.archives": {
        "type": "nomadnet.page.archives",
        "destination_hash": "aa" * 16,
        "page_path": "/page/index.mu",
        "archives": [],
    },
    "nomadnet.page.archive.load": {
        "type": "nomadnet.page.archive.load",
        "archive_id": 1,
    },
    "nomadnet.page.archive.flush": {"type": "nomadnet.page.archive.flush"},
    "nomadnet.page.archive.add": {
        "type": "nomadnet.page.archive.add",
        "destination_hash": "aa" * 16,
        "page_path": "/page/index.mu",
        "content": "body",
    },
    "nomadnet.page.archive.added": {
        "type": "nomadnet.page.archive.added",
        "destination_hash": "aa" * 16,
        "page_path": "/page/index.mu",
    },
    "nomadnet.file.download": {
        "type": "nomadnet.file.download",
        "download_id": 1,
        "nomadnet_file_download": {"status": "success"},
    },
    "nomadnet.page.download": {
        "type": "nomadnet.page.download",
        "download_id": 1,
        "nomadnet_page_download": {"status": "success"},
    },
    "lxmf.forwarding.rules.get": {"type": "lxmf.forwarding.rules.get"},
    "lxmf.forwarding.rules": {"type": "lxmf.forwarding.rules", "rules": []},
    "lxmf.forwarding.rule.add": {"type": "lxmf.forwarding.rule.add", "rule": {"id": 1}},
    "lxmf.forwarding.rule.delete": {
        "type": "lxmf.forwarding.rule.delete",
        "rule_id": 1,
    },
    "lxmf.forwarding.rule.toggle": {
        "type": "lxmf.forwarding.rule.toggle",
        "rule_id": 1,
        "enabled": True,
    },
    "lxm.ingest_uri": {"type": "lxm.ingest_uri", "uri": "meshchatx://map"},
    "lxm.ingest_uri.result": {"type": "lxm.ingest_uri.result", "success": True},
    "lxm.generate_paper_uri": {"type": "lxm.generate_paper_uri"},
    "lxm.generate_paper_uri.result": {
        "type": "lxm.generate_paper_uri.result",
        "success": True,
        "uri": "lxm://paper",
    },
    "announce": {"type": "announce", "announce": {"aspect": "lxmf.delivery"}},
    "lxmf.delivery": {"type": "lxmf.delivery"},
    "lxmf_message_created": {
        "type": "lxmf_message_created",
        "lxmf_message": {"hash": "cc" * 16},
    },
    "lxmf_message_state_updated": {
        "type": "lxmf_message_state_updated",
        "lxmf_message": {"hash": "cc" * 16, "state": "sent"},
    },
    "lxmf_message_deleted": {"type": "lxmf_message_deleted", "hash": "cc" * 16},
    "lxmf.telemetry": {"type": "lxmf.telemetry", "destination_hash": "aa" * 16},
    "identity_switched": {"type": "identity_switched"},
    "reticulum_reload_status": {"type": "reticulum_reload_status", "status": "ok"},
    "new_voicemail": {"type": "new_voicemail", "id": 1},
    "telephone_ringing": {
        "type": "telephone_ringing",
        "remote_identity_hash": "aa" * 16,
    },
    "telephone_call_established": {"type": "telephone_call_established"},
    "telephone_missed_call": {"type": "telephone_missed_call"},
    "telephone_call_ended": {"type": "telephone_call_ended"},
    "telephone_initiation_status": {
        "type": "telephone_initiation_status",
        "status": "ringing",
    },
    "rrc.change": {"type": "rrc.change"},
    "rrc.message": {"type": "rrc.message", "message": {"kind": "msg"}},
    "rrc.server.change": {"type": "rrc.server.change"},
    "rnsh.session.change": {"type": "rnsh.session.change"},
    "rnsh.output": {"type": "rnsh.output", "data": "ok"},
    "rnx.session.change": {"type": "rnx.session.change"},
    "rnx.output": {"type": "rnx.output", "data": "ok"},
    "rncp.transfer.progress": {"type": "rncp.transfer.progress", "percent": 50},
    "rncp.send.completed": {"type": "rncp.send.completed"},
    "rncp.fetch.completed": {"type": "rncp.fetch.completed"},
    "rns.link.open": {
        "type": "rns.link.open",
        "request_id": "req-1",
        "destination_hash": "aa" * 16,
        "aspect": "microrn.mgmt",
        "status": "success",
        "identified": False,
    },
    "rns.link.identify": {
        "type": "rns.link.identify",
        "request_id": "req-2",
        "destination_hash": "aa" * 16,
        "aspect": "microrn.mgmt",
        "status": "success",
    },
    "rns.link.request": {
        "type": "rns.link.request",
        "request_id": "req-3",
        "destination_hash": "aa" * 16,
        "aspect": "microrn.mgmt",
        "path": "/status",
        "status": "success",
        "body_b64": "",
    },
    "rns.link.send": {
        "type": "rns.link.send",
        "request_id": "req-4",
        "destination_hash": "aa" * 16,
        "aspect": "microrn.mgmt",
        "payload_b64": "",
        "status": "success",
    },
    "rns.link.close": {
        "type": "rns.link.close",
        "request_id": "req-5",
        "destination_hash": "aa" * 16,
        "aspect": "microrn.mgmt",
        "status": "success",
    },
    "rns.link.event": {
        "type": "rns.link.event",
        "event": "link_closed",
        "destination_hash": "aa" * 16,
        "aspect": "microrn.mgmt",
    },
}


def all_ws_message_types() -> set[str]:
    return set(WS_MESSAGE_SCHEMAS)


def assert_ws_message_matches_schema(message: dict) -> None:
    msg_type = message.get("type")
    if not isinstance(msg_type, str):
        raise AssertionError("WebSocket message missing string type")
    schema = WS_MESSAGE_SCHEMAS.get(msg_type)
    if schema is None:
        raise AssertionError(f"No WebSocket schema registered for type {msg_type!r}")
    assert_matches_schema(message, schema)
