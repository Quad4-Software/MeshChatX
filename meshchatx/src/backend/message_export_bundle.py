# SPDX-License-Identifier: 0BSD
"""Build and restore LXMF message export bundles with contacts and read state."""

from __future__ import annotations

from meshchatx.src.backend.meshchat_utils import (
    normalize_identity_storage_hash,
    parse_lxmf_display_name,
)

MESSAGE_EXPORT_FORMAT = "meshchatx/messages/v2"


def _contacts_for_export(database) -> list[dict]:
    rows = database.contacts.get_contacts(limit=10000, offset=0)
    hashes = [r["remote_identity_hash"] for r in rows if r.get("remote_identity_hash")]
    icons = {}
    if hashes:
        for ir in database.misc.get_user_icons(hashes):
            icons[ir["destination_hash"]] = dict(ir)
    export_data = []
    for row in rows:
        d = dict(row)
        d.pop("id", None)
        h = d.get("remote_identity_hash")
        if h and h in icons:
            d["lxmf_icon"] = icons[h]
        export_data.append(d)
    return export_data


def _display_names_for_export(database, peer_hashes: set[str]) -> list[dict]:
    """Custom names plus announce-derived names for message peers."""
    names: dict[str, str] = {}
    for row in database.announces.get_all_custom_display_names():
        dest = row.get("destination_hash")
        name = row.get("display_name")
        if dest and name:
            names[dest] = name

    for peer_hash in peer_hashes:
        if peer_hash in names:
            continue
        announce = database.announces.get_announce_by_hash(peer_hash)
        if not announce:
            continue
        try:
            app_data = announce["app_data"]
        except (KeyError, IndexError, TypeError):
            continue
        parsed = parse_lxmf_display_name(app_data, default_value=None)
        if parsed:
            names[peer_hash] = parsed

    return [
        {"destination_hash": dest, "display_name": name}
        for dest, name in sorted(names.items())
    ]


def _read_state_for_export(database) -> list[dict]:
    rows = database.messages.get_all_conversation_read_state()
    out = []
    for row in rows:
        d = dict(row)
        d.pop("id", None)
        d.pop("created_at", None)
        d.pop("updated_at", None)
        if d.get("destination_hash") and d.get("last_read_at"):
            out.append(d)
    return out


def _notification_viewed_for_export(database) -> list[dict]:
    rows = database.messages.get_all_notification_viewed_state()
    out = []
    for row in rows:
        d = dict(row)
        d.pop("id", None)
        d.pop("created_at", None)
        d.pop("updated_at", None)
        if d.get("destination_hash") and d.get("last_viewed_at"):
            out.append(d)
    return out


def build_messages_export_bundle(database, messages_list: list[dict]) -> dict:
    peer_hashes: set[str] = set()
    icon_hashes: set[str] = set()
    for m in messages_list:
        h = m.get("peer_hash") or m.get("source_hash")
        if h:
            peer_hashes.add(h)
            icon_hashes.add(h)

    icons = {}
    if icon_hashes:
        for ir in database.misc.get_user_icons(list(icon_hashes)):
            icons[ir["destination_hash"]] = dict(ir)
    for m in messages_list:
        h = m.get("peer_hash") or m.get("source_hash")
        if h and h in icons:
            m["lxmf_icon"] = icons[h]

    return {
        "format": MESSAGE_EXPORT_FORMAT,
        "messages": messages_list,
        "contacts": _contacts_for_export(database),
        "display_names": _display_names_for_export(database, peer_hashes),
        "conversation_read_state": _read_state_for_export(database),
        "notification_viewed_state": _notification_viewed_for_export(database),
    }


def _canonical_dest_hash(value) -> str:
    if not isinstance(value, str):
        return ""
    return normalize_identity_storage_hash(value)


def _optional_dest_hash(value) -> str | None:
    if value is None or value == "":
        return None
    hashed = _canonical_dest_hash(value)
    if not hashed:
        raise ValueError("invalid destination hash")
    return hashed


def import_contacts_list(database, contacts) -> tuple[int, int]:
    """Import contacts from an export list. Skip rows with invalid hashes."""
    if not isinstance(contacts, list):
        return 0, 0
    seen = {}
    no_hash = []
    for c in contacts:
        if not isinstance(c, dict):
            continue
        h = _canonical_dest_hash(c.get("remote_identity_hash"))
        if h:
            seen[h] = c
        else:
            no_hash.append(c)
    unique_contacts = list(seen.values()) + no_hash
    added = 0
    skipped = 0
    for c in unique_contacts:
        name = c.get("name")
        remote_identity_hash = _canonical_dest_hash(c.get("remote_identity_hash"))
        if not name or not remote_identity_hash:
            skipped += 1
            continue
        try:
            lxmf_address = _optional_dest_hash(c.get("lxmf_address"))
            lxst_address = _optional_dest_hash(c.get("lxst_address"))
            database.contacts.add_contact(
                name,
                remote_identity_hash,
                lxmf_address=lxmf_address,
                lxst_address=lxst_address,
                preferred_ringtone_id=c.get("preferred_ringtone_id"),
                custom_image=c.get("custom_image"),
                is_telemetry_trusted=1 if c.get("is_telemetry_trusted") else 0,
            )
            icon = c.get("lxmf_icon")
            if isinstance(icon, dict) and icon.get("icon_name"):
                database.misc.update_lxmf_user_icon(
                    remote_identity_hash,
                    icon.get("icon_name"),
                    icon.get("foreground_colour"),
                    icon.get("background_colour"),
                )
            added += 1
        except Exception:
            skipped += 1
    return added, skipped


def _import_contacts(database, contacts) -> tuple[int, int]:
    return import_contacts_list(database, contacts)


def _import_display_names(database, display_names) -> int:
    if not isinstance(display_names, list):
        return 0
    count = 0
    for row in display_names:
        if not isinstance(row, dict):
            continue
        dest = row.get("destination_hash")
        name = row.get("display_name")
        if not dest or not name:
            continue
        database.announces.upsert_custom_display_name(dest, name)
        count += 1
    return count


def import_messages_export_bundle(database, payload) -> dict:
    """Import messages plus optional contacts, names, and read state.

    Accepts legacy {messages: [...]} / bare arrays and v2 bundles.
    """
    if isinstance(payload, list):
        messages = payload
        contacts = []
        display_names = []
        read_state = []
        viewed_state = []
    elif isinstance(payload, dict):
        messages = payload.get("messages", [])
        if messages is None:
            messages = []
        contacts = payload.get("contacts") or []
        display_names = payload.get("display_names") or []
        read_state = payload.get("conversation_read_state") or []
        viewed_state = payload.get("notification_viewed_state") or []
    else:
        return {
            "ok": False,
            "error": "messages must be an array",
            "imported": 0,
            "skipped": 0,
            "errors": [],
            "contacts_added": 0,
            "contacts_skipped": 0,
            "display_names_imported": 0,
            "read_state_imported": 0,
        }

    if not isinstance(messages, list):
        return {
            "ok": False,
            "error": "messages must be an array",
            "imported": 0,
            "skipped": 0,
            "errors": [],
            "contacts_added": 0,
            "contacts_skipped": 0,
            "display_names_imported": 0,
            "read_state_imported": 0,
        }

    contacts_added, contacts_skipped = _import_contacts(database, contacts)
    display_names_imported = _import_display_names(database, display_names)
    msg_result = database.messages.import_lxmf_messages(messages)
    read_imported = database.messages.import_conversation_read_state(read_state)
    viewed_imported = database.messages.import_notification_viewed_state(viewed_state)

    return {
        "ok": True,
        "imported": msg_result["imported"],
        "skipped": msg_result["skipped"],
        "errors": msg_result["errors"],
        "contacts_added": contacts_added,
        "contacts_skipped": contacts_skipped,
        "display_names_imported": display_names_imported,
        "read_state_imported": read_imported + viewed_imported,
    }
