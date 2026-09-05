# SPDX-License-Identifier: 0BSD

"""Lifecycle helper: announce_convert."""

from __future__ import annotations

import base64
from typing import Any

# ruff: noqa: F821


def batch_convert_announces_to_api_dicts(
    app: Any,
    results,
    aspect=None,
    include_hops=True,
):
    """Batch-convert announce rows using prefetched icons and custom names."""
    mc = __import__("meshchatx.meshchat", fromlist=["*"])
    for _k, _v in mc.__dict__.items():
        if not _k.startswith("__"):
            globals()[_k] = _v

    if not results:
        return []

    other_user_hashes = [r["destination_hash"] for r in results]
    user_icons = {}
    if other_user_hashes:
        db_icons = app.database.misc.get_user_icons(other_user_hashes)
        for icon in db_icons:
            user_icons[icon["destination_hash"]] = {
                "icon_name": icon["icon_name"],
                "foreground_colour": icon["foreground_colour"],
                "background_colour": icon["background_colour"],
            }

    custom_names = {}
    lxmf_names_for_telephony = {}
    if other_user_hashes:
        db_custom_names = app.database.provider.fetchall(
            f"SELECT destination_hash, display_name FROM custom_destination_display_names WHERE destination_hash IN ({','.join(['?'] * len(other_user_hashes))})",
            other_user_hashes,
        )
        for row in db_custom_names:
            custom_names[row["destination_hash"]] = row["display_name"]

        if aspect == "lxst.telephony":
            identity_hashes = list(
                {r["identity_hash"] for r in results if r.get("identity_hash")},
            )
            if identity_hashes:
                lxmf_results = app.database.announces.provider.fetchall(
                    f"SELECT identity_hash, app_data FROM announces WHERE aspect = 'lxmf.delivery' AND identity_hash IN ({','.join(['?'] * len(identity_hashes))})",
                    identity_hashes,
                )
                for row in lxmf_results:
                    lxmf_names_for_telephony[row["identity_hash"]] = (
                        parse_lxmf_display_name(row["app_data"])
                    )

    all_announces = []
    for announce in results:
        if not isinstance(announce, dict):
            announce = dict(announce)

        display_name = None
        is_local = (
            app.current_context
            and announce["identity_hash"] == app.current_context.identity_hash
        )

        if announce["aspect"] == "lxmf.delivery":
            display_name = parse_lxmf_display_name(announce["app_data"])
        elif announce["aspect"] == "nomadnetwork.node":
            display_name = parse_nomadnetwork_node_display_name(
                announce["app_data"],
            )
        elif announce["aspect"] == "lxst.telephony":
            display_name = parse_lxmf_display_name(announce["app_data"])
            if not display_name or display_name == "Anonymous Peer":
                display_name = lxmf_names_for_telephony.get(
                    announce["identity_hash"],
                )
        elif announce["aspect"] == "rrc.hub":
            display_name = rrc_protocol.display_name_from_hub_app_data(
                announce.get("app_data"),
            )

        if not display_name or display_name == "Anonymous Peer":
            if is_local and app.current_context:
                display_name = app.current_context.config.display_name.get()
            else:
                display_name = (
                    app.get_name_for_identity_hash(announce["identity_hash"])
                    or "Anonymous Peer"
                )

        hops = None
        if include_hops:
            hops = RNS.Transport.hops_to(
                bytes.fromhex(announce["destination_hash"]),
            )

        created_at = str(announce["created_at"])
        if created_at and "+" not in created_at and "Z" not in created_at:
            created_at += "Z"
        updated_at = str(announce["updated_at"])
        if updated_at and "+" not in updated_at and "Z" not in updated_at:
            updated_at += "Z"

        all_announces.append(
            {
                "id": announce["id"],
                "destination_hash": announce["destination_hash"],
                "aspect": announce["aspect"],
                "identity_hash": announce["identity_hash"],
                "identity_public_key": announce["identity_public_key"],
                "app_data": announce["app_data"],
                "hops": hops,
                "rssi": announce["rssi"],
                "snr": announce["snr"],
                "quality": announce["quality"],
                "created_at": created_at,
                "updated_at": updated_at,
                "display_name": display_name,
                "custom_display_name": custom_names.get(
                    announce["destination_hash"],
                ),
                "lxmf_user_icon": user_icons.get(announce["destination_hash"]),
                "contact_image": announce.get("contact_image"),
            },
        )
    return all_announces


def convert_db_announce_to_dict(app: Any, announce):
    mc = __import__("meshchatx.meshchat", fromlist=["*"])
    for _k, _v in mc.__dict__.items():
        if not _k.startswith("__"):
            globals()[_k] = _v

    # convert to dict if it is a sqlite3.Row
    if not isinstance(announce, dict):
        announce = dict(announce)

    # parse display name from announce
    display_name = None
    if announce["aspect"] == "lxmf.delivery":
        display_name = parse_lxmf_display_name(announce["app_data"])
    elif announce["aspect"] == "nomadnetwork.node":
        display_name = parse_nomadnetwork_node_display_name(
            announce["app_data"],
        )
    elif announce["aspect"] == "lxst.telephony":
        display_name = parse_lxmf_display_name(announce["app_data"])
    elif announce["aspect"] == "rrc.hub":
        display_name = rrc_protocol.display_name_from_hub_app_data(
            announce.get("app_data"),
        )

    # Try to find associated LXMF destination hash if this is a telephony announce
    lxmf_destination_hash = None
    if announce["aspect"] == "lxst.telephony" and announce.get("identity_hash"):
        # 1. Check if we already have an LXMF announce for this identity
        lxmf_announces = app.database.announces.get_filtered_announces(
            aspect="lxmf.delivery",
            search_term=announce["identity_hash"],
        )
        if lxmf_announces:
            for lxmf_a in lxmf_announces:
                if lxmf_a["identity_hash"] == announce["identity_hash"]:
                    lxmf_destination_hash = lxmf_a["destination_hash"]
                    # Also update display name if telephony one was empty
                    if not display_name or display_name == "Anonymous Peer":
                        display_name = parse_lxmf_display_name(
                            lxmf_a["app_data"],
                        )
                    break

        # 2. If not found in announces, try to recall identity and calculate LXMF hash
        if not lxmf_destination_hash:
            try:
                identity_hash_bytes = bytes.fromhex(announce["identity_hash"])
                identity = RNS.Identity.recall(identity_hash_bytes)
                if not identity and announce.get("identity_public_key"):
                    # Try to load from public key if recall failed
                    public_key = base64.b64decode(announce["identity_public_key"])
                    identity = app._identity_from_public_key_bytes(public_key)

                if identity:
                    try:
                        lxmf_destination_hash = RNS.Destination.hash(
                            identity,
                            "lxmf",
                            "delivery",
                        ).hex()
                    except Exception:
                        pass
            except Exception:
                pass

    if not display_name or display_name == "Anonymous Peer":
        is_local = (
            app.current_context
            and announce.get("identity_hash") == app.current_context.identity_hash
        )
        if is_local and app.current_context:
            display_name = app.current_context.config.display_name.get()
        elif announce.get("identity_hash"):
            display_name = (
                app.get_name_for_identity_hash(announce["identity_hash"])
                or "Anonymous Peer"
            )
        else:
            display_name = "Anonymous Peer"

    # find lxmf user icon from database
    lxmf_user_icon = None
    # Try multiple potential hashes for the icon
    icon_hashes_to_check = []
    if lxmf_destination_hash:
        icon_hashes_to_check.append(lxmf_destination_hash)
    icon_hashes_to_check.append(announce["destination_hash"])

    # ensure we don't return the user's own icon for peers
    local_hash = None
    if app.current_context and app.current_context.local_lxmf_destination:
        local_hash = app.current_context.local_lxmf_destination.hexhash

    db_lxmf_user_icon = None
    for icon_hash in icon_hashes_to_check:
        # skip if this is the user's own hash: do not return user's icon for peers
        if local_hash and icon_hash == local_hash:
            continue
        db_lxmf_user_icon = app.database.misc.get_user_icon(icon_hash)
        if db_lxmf_user_icon:
            break

    if db_lxmf_user_icon:
        lxmf_user_icon = {
            "icon_name": db_lxmf_user_icon["icon_name"],
            "foreground_colour": db_lxmf_user_icon["foreground_colour"],
            "background_colour": db_lxmf_user_icon["background_colour"],
        }

    # get current hops away
    hops = RNS.Transport.hops_to(bytes.fromhex(announce["destination_hash"]))

    # ensure created_at and updated_at have Z suffix for UTC if they don't have a timezone
    created_at = str(announce["created_at"])
    if created_at and "+" not in created_at and "Z" not in created_at:
        created_at += "Z"

    updated_at = str(announce["updated_at"])
    if updated_at and "+" not in updated_at and "Z" not in updated_at:
        updated_at += "Z"

    return {
        "id": announce["id"],
        "destination_hash": announce["destination_hash"],
        "aspect": announce["aspect"],
        "identity_hash": announce["identity_hash"],
        "identity_public_key": announce["identity_public_key"],
        "app_data": announce["app_data"],
        "hops": hops,
        "rssi": announce["rssi"],
        "snr": announce["snr"],
        "quality": announce["quality"],
        "display_name": display_name,
        "lxmf_destination_hash": lxmf_destination_hash,
        "custom_display_name": app.get_custom_destination_display_name(
            announce["destination_hash"],
        ),
        "lxmf_user_icon": lxmf_user_icon,
        "created_at": created_at,
        "updated_at": updated_at,
    }
