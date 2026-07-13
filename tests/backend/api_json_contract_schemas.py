# SPDX-License-Identifier: 0BSD

"""JSON Schema definitions for stable /api/v1 JSON bodies (contract tests)."""

from __future__ import annotations

from jsonschema import Draft202012Validator

_USER_GUIDANCE_ITEM = {
    "type": "object",
    "required": [
        "id",
        "title",
        "description",
        "action_route",
        "action_label",
        "severity",
    ],
    "properties": {
        "id": {"type": "string"},
        "title": {"type": "string"},
        "description": {"type": "string"},
        "action_route": {"type": "string"},
        "action_label": {"type": "string"},
        "severity": {"type": "string"},
    },
    "additionalProperties": True,
}

APP_INFO_BODY_SCHEMA: dict = {
    "type": "object",
    "required": [
        "version",
        "lxmf_version",
        "rns_version",
        "lxst_version",
        "python_version",
        "dependencies",
        "storage_path",
        "database_path",
        "database_file_size",
        "database_files",
        "sqlite",
        "reticulum_config_path",
        "is_connected_to_shared_instance",
        "shared_instance_address",
        "is_transport_enabled",
        "memory_usage",
        "network_stats",
        "reticulum_stats",
        "is_reticulum_running",
        "download_stats",
        "emergency",
        "integrity_issues",
        "database_health_issues",
        "user_guidance",
        "tutorial_seen",
        "changelog_seen_version",
    ],
    "properties": {
        "version": {"type": "string"},
        "lxmf_version": {"type": "string"},
        "rns_version": {"type": "string"},
        "lxst_version": {"type": "string"},
        "python_version": {"type": "string"},
        "dependencies": {
            "type": "object",
            "minProperties": 1,
            "additionalProperties": {"type": "string"},
        },
        "storage_path": {"type": "string"},
        "database_path": {"type": "string"},
        "database_file_size": {"type": "integer"},
        "database_files": {
            "type": "object",
            "required": ["main_bytes", "wal_bytes", "shm_bytes", "total_bytes"],
            "properties": {
                "main_bytes": {"type": "integer"},
                "wal_bytes": {"type": "integer"},
                "shm_bytes": {"type": "integer"},
                "total_bytes": {"type": "integer"},
            },
            "additionalProperties": True,
        },
        "sqlite": {
            "type": "object",
            "required": [
                "journal_mode",
                "synchronous",
                "wal_autocheckpoint",
                "busy_timeout",
            ],
            "additionalProperties": True,
        },
        "reticulum_config_path": {"type": ["string", "null"]},
        "is_connected_to_shared_instance": {"type": "boolean"},
        "shared_instance_address": {"type": ["string", "null"]},
        "is_transport_enabled": {"type": "boolean"},
        "memory_usage": {
            "type": "object",
            "required": ["rss", "vms"],
            "properties": {
                "rss": {"type": "integer"},
                "vms": {"type": "integer"},
            },
            "additionalProperties": True,
        },
        "network_stats": {
            "type": "object",
            "required": [
                "bytes_sent",
                "bytes_recv",
                "packets_sent",
                "packets_recv",
            ],
            "properties": {
                "bytes_sent": {"type": "integer"},
                "bytes_recv": {"type": "integer"},
                "packets_sent": {"type": "integer"},
                "packets_recv": {"type": "integer"},
            },
            "additionalProperties": True,
        },
        "reticulum_stats": {
            "type": "object",
            "required": [
                "total_paths",
                "announces_per_second",
                "announces_per_minute",
                "announces_per_hour",
            ],
            "properties": {
                "total_paths": {"type": "integer"},
                "announces_per_second": {"type": "integer"},
                "announces_per_minute": {"type": "integer"},
                "announces_per_hour": {"type": "integer"},
            },
            "additionalProperties": True,
        },
        "is_reticulum_running": {"type": "boolean"},
        "download_stats": {
            "type": "object",
            "required": ["avg_download_speed_bps"],
            "properties": {
                "avg_download_speed_bps": {"type": ["number", "null"]},
            },
            "additionalProperties": True,
        },
        "emergency": {"type": "boolean"},
        "integrity_issues": {"type": "array"},
        "database_health_issues": {"type": "array"},
        "user_guidance": {
            "type": "array",
            "items": _USER_GUIDANCE_ITEM,
        },
        "tutorial_seen": {"type": "boolean"},
        "changelog_seen_version": {"type": "string"},
        "landlock_kernel_supported": {"type": "boolean"},
        "landlock_requested": {"type": "boolean"},
        "landlock_auto_enabled": {"type": "boolean"},
        "landlock_disabled_by_env": {"type": "boolean"},
        "landlock_active": {"type": "boolean"},
    },
    "additionalProperties": True,
}

_SERVER_BIND_STATUS_SCHEMA: dict = {
    "listen_host": {"type": ["string", "null"]},
    "listen_port": {"type": ["integer", "null"]},
    "https_enabled": {"type": "boolean"},
    "is_loopback_bind": {"type": "boolean"},
    "plugins_enabled": {"type": "boolean"},
    "landlock_kernel_supported": {"type": "boolean"},
    "landlock_requested": {"type": "boolean"},
    "landlock_auto_enabled": {"type": "boolean"},
    "landlock_disabled_by_env": {"type": "boolean"},
    "landlock_active": {"type": "boolean"},
}

API_V1_STATUS_SCHEMA: dict = {
    "type": "object",
    "required": ["status", "stage", "network_ready"],
    "properties": {
        "status": {"type": "string", "enum": ["ok", "starting", "failed"]},
        "stage": {
            "type": "string",
            "enum": ["http", "starting", "rns", "identity", "ready", "failed"],
        },
        "network_ready": {"type": "boolean"},
        "network_degraded": {"type": "boolean"},
        "ui_ready": {"type": "boolean"},
        "error": {"type": "string"},
        **_SERVER_BIND_STATUS_SCHEMA,
    },
    "additionalProperties": False,
}

SELF_TEST_STATUS_ITEM_SCHEMA: dict = {
    "type": "object",
    "required": ["status", "reason"],
    "properties": {
        "status": {"type": "string", "enum": ["ok", "failed"]},
        "reason": {"type": "string"},
    },
    "additionalProperties": False,
}

SELF_TEST_SCHEMA: dict = {
    "type": "object",
    "required": [
        "stack_up",
        "config_good",
        "db_good",
        "read_write_good",
        "identity_good",
        "imports_good",
        "storage_lock_good",
        "temp_fs_good",
        "public_assets_good",
        "lxmf_router_good",
        "subprocess_good",
        "run_module_good",
        "sqlite_roundtrip",
        "identity_roundtrip",
        "loopback_tcp",
        "unicode_path_good",
        "rnode_support_good",
        "bot_launcher_good",
        "http_status_good",
        "http_app_info_good",
        "http_config_good",
        "http_db_health_good",
        "http_auth_csrf_good",
        "http_bots_status_good",
        "http_security_good",
        "http_interfaces_good",
        "http_reticulum_instance_good",
        "http_identities_good",
        "http_favourites_good",
        "http_telephone_good",
        "http_plugins_good",
        "http_plugins_trust_good",
        "http_sideband_plugins_good",
        "http_sideband_config_good",
        "http_rrc_hubs_good",
        "http_rrc_servers_good",
        "plugins_runtime_good",
        "websocket_good",
        "websocket_rns_link_good",
        "bots_lifecycle",
    ],
    "properties": {
        "stack_up": SELF_TEST_STATUS_ITEM_SCHEMA,
        "config_good": SELF_TEST_STATUS_ITEM_SCHEMA,
        "db_good": SELF_TEST_STATUS_ITEM_SCHEMA,
        "read_write_good": SELF_TEST_STATUS_ITEM_SCHEMA,
        "identity_good": SELF_TEST_STATUS_ITEM_SCHEMA,
        "imports_good": SELF_TEST_STATUS_ITEM_SCHEMA,
        "storage_lock_good": SELF_TEST_STATUS_ITEM_SCHEMA,
        "temp_fs_good": SELF_TEST_STATUS_ITEM_SCHEMA,
        "public_assets_good": SELF_TEST_STATUS_ITEM_SCHEMA,
        "lxmf_router_good": SELF_TEST_STATUS_ITEM_SCHEMA,
        "subprocess_good": SELF_TEST_STATUS_ITEM_SCHEMA,
        "run_module_good": SELF_TEST_STATUS_ITEM_SCHEMA,
        "sqlite_roundtrip": SELF_TEST_STATUS_ITEM_SCHEMA,
        "identity_roundtrip": SELF_TEST_STATUS_ITEM_SCHEMA,
        "loopback_tcp": SELF_TEST_STATUS_ITEM_SCHEMA,
        "unicode_path_good": SELF_TEST_STATUS_ITEM_SCHEMA,
        "rnode_support_good": SELF_TEST_STATUS_ITEM_SCHEMA,
        "bot_launcher_good": SELF_TEST_STATUS_ITEM_SCHEMA,
        "http_status_good": SELF_TEST_STATUS_ITEM_SCHEMA,
        "http_app_info_good": SELF_TEST_STATUS_ITEM_SCHEMA,
        "http_config_good": SELF_TEST_STATUS_ITEM_SCHEMA,
        "http_db_health_good": SELF_TEST_STATUS_ITEM_SCHEMA,
        "http_auth_csrf_good": SELF_TEST_STATUS_ITEM_SCHEMA,
        "http_bots_status_good": SELF_TEST_STATUS_ITEM_SCHEMA,
        "http_security_good": SELF_TEST_STATUS_ITEM_SCHEMA,
        "http_interfaces_good": SELF_TEST_STATUS_ITEM_SCHEMA,
        "http_reticulum_instance_good": SELF_TEST_STATUS_ITEM_SCHEMA,
        "http_identities_good": SELF_TEST_STATUS_ITEM_SCHEMA,
        "http_favourites_good": SELF_TEST_STATUS_ITEM_SCHEMA,
        "http_telephone_good": SELF_TEST_STATUS_ITEM_SCHEMA,
        "http_plugins_good": SELF_TEST_STATUS_ITEM_SCHEMA,
        "http_plugins_trust_good": SELF_TEST_STATUS_ITEM_SCHEMA,
        "http_sideband_plugins_good": SELF_TEST_STATUS_ITEM_SCHEMA,
        "http_sideband_config_good": SELF_TEST_STATUS_ITEM_SCHEMA,
        "http_rrc_hubs_good": SELF_TEST_STATUS_ITEM_SCHEMA,
        "http_rrc_servers_good": SELF_TEST_STATUS_ITEM_SCHEMA,
        "plugins_runtime_good": SELF_TEST_STATUS_ITEM_SCHEMA,
        "websocket_good": SELF_TEST_STATUS_ITEM_SCHEMA,
        "websocket_rns_link_good": SELF_TEST_STATUS_ITEM_SCHEMA,
        "bots_lifecycle": SELF_TEST_STATUS_ITEM_SCHEMA,
    },
    "additionalProperties": False,
}

API_V1_APP_INFO_ENVELOPE_SCHEMA: dict = {
    "type": "object",
    "required": ["app_info"],
    "properties": {"app_info": APP_INFO_BODY_SCHEMA},
    "additionalProperties": False,
}

AUTH_STATUS_SCHEMA: dict = {
    "type": "object",
    "required": ["auth_enabled", "password_set", "authenticated"],
    "properties": {
        "auth_enabled": {"type": "boolean"},
        "password_set": {"type": "boolean"},
        "authenticated": {"type": "boolean"},
        "network_ready": {"type": "boolean"},
        "status": {"type": "string", "enum": ["starting", "ok", "failed"]},
        "stage": {
            "type": "string",
            "enum": ["http", "starting", "rns", "identity", "ready", "failed"],
        },
        "error": {"type": "string"},
    },
    "additionalProperties": False,
}

TELEPHONE_VOICEMAIL_STATUS_SCHEMA: dict = {
    "type": "object",
    "required": [
        "has_espeak",
        "is_recording",
        "is_greeting_recording",
        "has_greeting",
    ],
    "properties": {
        "has_espeak": {"type": "boolean"},
        "is_recording": {"type": "boolean"},
        "is_greeting_recording": {"type": "boolean"},
        "has_greeting": {"type": "boolean"},
    },
    "additionalProperties": False,
}

TELEPHONE_VOICEMAILS_ENVELOPE_SCHEMA: dict = {
    "type": "object",
    "required": ["voicemails", "unread_count"],
    "properties": {
        "voicemails": {
            "type": "array",
            "items": {"type": "object", "additionalProperties": True},
        },
        "unread_count": {"type": "integer"},
    },
    "additionalProperties": False,
}

_RINGTONE_ROW_SCHEMA: dict = {
    "type": "object",
    "required": ["id", "filename", "display_name", "is_primary", "created_at"],
    "properties": {
        "id": {"type": "integer"},
        "filename": {"type": "string"},
        "display_name": {"type": "string"},
        "is_primary": {"type": "boolean"},
        "created_at": {"type": ["string", "null"]},
    },
    "additionalProperties": True,
}

TELEPHONE_RINGTONES_LIST_SCHEMA: dict = {
    "type": "array",
    "items": _RINGTONE_ROW_SCHEMA,
}

TELEPHONE_RINGTONE_STATUS_SCHEMA: dict = {
    "type": "object",
    "required": [
        "has_custom_ringtone",
        "enabled",
        "filename",
        "id",
        "volume",
    ],
    "properties": {
        "has_custom_ringtone": {"type": "boolean"},
        "enabled": {"type": "boolean"},
        "filename": {"type": ["string", "null"]},
        "id": {"type": ["integer", "null"]},
        "volume": {"type": "number"},
    },
    "additionalProperties": False,
}

TELEPHONE_CONTACTS_LIST_SCHEMA: dict = {
    "type": "object",
    "required": ["contacts", "total_count"],
    "properties": {
        "contacts": {
            "type": "array",
            "items": {"type": "object", "additionalProperties": True},
        },
        "total_count": {"type": "integer"},
    },
    "additionalProperties": False,
}

TELEPHONE_CONTACT_CHECK_SCHEMA: dict = {
    "type": "object",
    "required": ["is_contact", "contact"],
    "properties": {
        "is_contact": {"type": "boolean"},
        "contact": {
            "oneOf": [
                {"type": "null"},
                {"type": "object", "additionalProperties": True},
            ],
        },
    },
    "additionalProperties": False,
}


def assert_matches_schema(instance: object, schema: dict) -> None:
    Draft202012Validator(schema).validate(instance)
