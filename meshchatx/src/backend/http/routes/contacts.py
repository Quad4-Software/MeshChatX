# SPDX-License-Identifier: 0BSD
"""HTTP routes: contacts."""

from __future__ import annotations

import logging

from aiohttp import web

from meshchatx.src.backend.constants import API_V1_PREFIX
from meshchatx.src.backend.http.db_availability import (
    http_for_database_exception,
    require_database,
)
from meshchatx.src.backend.http.errors import (
    http_bad_request,
    http_payload_too_large,
    http_unexpected,
)
from meshchatx.src.backend.http.uploads import (
    PayloadTooLargeError,
    read_json_limited,
)

logger = logging.getLogger(__name__)

CONTACTS_DEFAULT_LIMIT = 100
CONTACTS_MAX_LIMIT = 500


def parse_contacts_pagination(query, default_limit=CONTACTS_DEFAULT_LIMIT):
    """Parse limit/offset from a MultiDict-like query.

    Returns (limit, offset) with limit clamped to [1, CONTACTS_MAX_LIMIT]
    and offset >= 0. Returns None when limit or offset is not an integer.
    """
    try:
        limit = int(query.get("limit", default_limit))
        offset = int(query.get("offset", 0))
    except (TypeError, ValueError):
        return None
    if limit < 1:
        limit = 1
    elif limit > CONTACTS_MAX_LIMIT:
        limit = CONTACTS_MAX_LIMIT
    if offset < 0:
        offset = 0
    return limit, offset


def enrich_contact_row(app, row):
    """Copy a contacts DAO row and attach LXMF/LXST hashes plus icon when known.

    Enrichment failures for one peer must not fail the whole list.
    """
    d = dict(row)
    remote_identity_hash = d.get("remote_identity_hash")
    if not remote_identity_hash:
        return d
    try:
        lxmf_hash = app.get_lxmf_destination_hash_for_identity_hash(
            remote_identity_hash,
        )
        tele_hash = app.get_lxst_telephony_hash_for_identity_hash(
            remote_identity_hash,
        )
        if lxmf_hash:
            d["remote_destination_hash"] = lxmf_hash
            try:
                icon = app.database.misc.get_user_icon(lxmf_hash)
            except Exception:
                icon = None
            if icon:
                d["remote_icon"] = dict(icon)
        if tele_hash:
            d["remote_telephony_hash"] = tele_hash
    except Exception:
        logger.debug(
            "Contact enrichment skipped for %s",
            remote_identity_hash,
            exc_info=True,
        )
    return d


def register_contacts_routes(routes, app):
    # contacts routes
    @routes.get(API_V1_PREFIX + "/telephone/contacts")
    async def telephone_contacts_get(request):
        pagination = parse_contacts_pagination(request.query)
        if pagination is None:
            return http_bad_request("limit and offset must be integers")
        limit, offset = pagination
        search = request.query.get("search")

        unavailable = require_database(app)
        if unavailable is not None:
            return unavailable

        try:
            contacts_rows = app.database.contacts.get_contacts(
                search=search,
                limit=limit,
                offset=offset,
            )
            total_count = app.database.contacts.get_contacts_count(search=search)
            contacts = [enrich_contact_row(app, row) for row in contacts_rows]
            return web.json_response(
                {"contacts": contacts, "total_count": total_count},
            )
        except Exception as e:
            logger.exception("telephone_contacts_get failed")
            return http_for_database_exception(e)

    @routes.post(API_V1_PREFIX + "/telephone/contacts")
    async def telephone_contacts_post(request):
        try:
            data = await read_json_limited(request)
        except PayloadTooLargeError:
            return http_payload_too_large()
        name = data.get("name")
        remote_identity_hash = data.get("remote_identity_hash")
        lxmf_address = data.get("lxmf_address")
        lxst_address = data.get("lxst_address")
        preferred_ringtone_id = data.get("preferred_ringtone_id")
        custom_image = data.get("custom_image")
        is_telemetry_trusted = data.get("is_telemetry_trusted", 0)

        if not name:
            return http_bad_request("Name is required")

        # Normalize: chat UI often posts an LXMF destination hash as
        # remote_identity_hash. Prefer the real identity hash when known so
        # incoming-call policy (identity hash) matches saved contacts.
        provided_hash = remote_identity_hash
        lookup_hash = remote_identity_hash or lxmf_address or lxst_address
        if lookup_hash:
            announce = app.database.announces.get_announce_by_hash(lookup_hash)
            if announce and announce.get("identity_hash"):
                remote_identity_hash = announce.get("identity_hash")
                if not lxmf_address and announce.get("aspect") == "lxmf.delivery":
                    lxmf_address = announce.get("destination_hash") or lookup_hash
                if not lxst_address and announce.get("aspect") == "lxst.telephony":
                    lxst_address = announce.get("destination_hash") or lookup_hash
            else:
                ident = app.recall_identity(lookup_hash)
                if ident:
                    remote_identity_hash = ident.hash.hex()

        if not remote_identity_hash:
            remote_identity_hash = lxmf_address or lxst_address or provided_hash
        if not remote_identity_hash:
            return http_bad_request(
                "Identity hash is required or could not be derived",
            )

        # If the client only supplied a destination hash, keep it on the
        # matching address field so lookups by either form succeed.
        if provided_hash and provided_hash != remote_identity_hash:
            if not lxmf_address:
                lxmf_announce = app.database.announces.get_announce_by_hash(
                    provided_hash,
                )
                if lxmf_announce and lxmf_announce.get("aspect") == "lxmf.delivery":
                    lxmf_address = provided_hash
                elif not lxst_address:
                    lxst_announce = app.database.announces.get_announce_by_hash(
                        provided_hash,
                    )
                    if (
                        lxst_announce
                        and lxst_announce.get("aspect") == "lxst.telephony"
                    ):
                        lxst_address = provided_hash
                    else:
                        # Default: treat unknown destination-shaped hashes as LXMF
                        lxmf_address = lxmf_address or provided_hash

        if not lxmf_address:
            try:
                lxmf_address = app.get_lxmf_destination_hash_for_identity_hash(
                    remote_identity_hash,
                )
            except Exception:
                pass
        if not lxst_address:
            try:
                lxst_address = app.get_lxst_telephony_hash_for_identity_hash(
                    remote_identity_hash,
                )
            except Exception:
                pass

        app.database.contacts.add_contact(
            name,
            remote_identity_hash,
            lxmf_address=lxmf_address,
            lxst_address=lxst_address,
            preferred_ringtone_id=preferred_ringtone_id,
            custom_image=custom_image,
            is_telemetry_trusted=is_telemetry_trusted,
        )
        app.sync_telephone_call_policy()
        return web.json_response({"message": "Contact added"})

    @routes.patch(API_V1_PREFIX + "/telephone/contacts/{id}")
    async def telephone_contacts_patch(request):
        contact_id = int(request.match_info["id"])
        try:
            data = await read_json_limited(request)
        except PayloadTooLargeError:
            return http_payload_too_large()
        name = data.get("name")
        remote_identity_hash = data.get("remote_identity_hash")
        lxmf_address = data.get("lxmf_address")
        lxst_address = data.get("lxst_address")
        preferred_ringtone_id = data.get("preferred_ringtone_id")
        custom_image = data.get("custom_image")
        clear_image = data.get("clear_image", False)
        is_telemetry_trusted = data.get("is_telemetry_trusted")

        app.database.contacts.update_contact(
            contact_id,
            name=name,
            remote_identity_hash=remote_identity_hash,
            lxmf_address=lxmf_address,
            lxst_address=lxst_address,
            preferred_ringtone_id=preferred_ringtone_id,
            custom_image=custom_image,
            clear_image=clear_image,
            is_telemetry_trusted=is_telemetry_trusted,
        )
        app.sync_telephone_call_policy()
        return web.json_response({"message": "Contact updated"})

    @routes.delete(API_V1_PREFIX + "/telephone/contacts/{id}")
    async def telephone_contacts_delete(request):
        contact_id = int(request.match_info["id"])
        app.database.contacts.delete_contact(contact_id)
        app.sync_telephone_call_policy()
        return web.json_response({"message": "Contact deleted"})

    @routes.get(API_V1_PREFIX + "/telephone/contacts/check/{identity_hash}")
    async def telephone_contacts_check(request):
        unavailable = require_database(app)
        if unavailable is not None:
            return unavailable
        identity_hash = request.match_info["identity_hash"]
        try:
            contact = app._resolve_contact_for_hash(identity_hash)
            return web.json_response(
                {
                    "is_contact": contact is not None,
                    "contact": dict(contact) if contact else None,
                },
            )
        except Exception as e:
            logger.exception("telephone_contacts_check failed")
            return http_for_database_exception(e)

    @routes.get(API_V1_PREFIX + "/telephone/contacts/export")
    async def telephone_contacts_export(request):
        unavailable = require_database(app)
        if unavailable is not None:
            return unavailable
        try:
            rows = app.database.contacts.get_contacts(limit=10000, offset=0)
            hashes = [
                r["remote_identity_hash"] for r in rows if r.get("remote_identity_hash")
            ]
            icons = {}
            if hashes:
                icon_rows = app.database.misc.get_user_icons(hashes)
                for ir in icon_rows:
                    icons[ir["destination_hash"]] = dict(ir)
            export_data = []
            for row in rows:
                d = dict(row)
                d.pop("id", None)
                h = d.get("remote_identity_hash")
                if h and h in icons:
                    d["lxmf_icon"] = icons[h]
                export_data.append(d)
            return web.json_response({"contacts": export_data})
        except Exception as e:
            retryable = http_for_database_exception(e)
            if retryable.status == 503:
                return retryable
            return http_unexpected(f"Failed to export contacts: {e!s}")

    @routes.post(API_V1_PREFIX + "/telephone/contacts/import")
    async def telephone_contacts_import(request):
        try:
            data = await read_json_limited(request)
            contacts = data.get("contacts", [])
            if not isinstance(contacts, list):
                return http_bad_request(
                    "Invalid import format: contacts must be an array",
                )
            from meshchatx.src.backend.message_export_bundle import import_contacts_list

            added, skipped = import_contacts_list(app.database, contacts)
            app.sync_telephone_call_policy()
            return web.json_response(
                {"message": "Import complete", "added": added, "skipped": skipped},
            )
        except PayloadTooLargeError:
            return http_payload_too_large()
        except Exception as e:
            return http_unexpected(f"Failed to import contacts: {e!s}")

    # announce
