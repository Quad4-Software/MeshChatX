"""Normalize and validate NomadNet favourite section layout blobs."""

NOMADNET_FAVOURITES_LAYOUT_KEY = "nomadnet_favourites_layout"

# Hard caps keep PUT payloads cheap to parse/store and avoid pathological layouts.
MAX_SECTIONS = 64
MAX_SECTION_ID_LEN = 64
MAX_SECTION_NAME_LEN = 128
MAX_HASHES_PER_SECTION = 2000
MAX_TOTAL_HASHES = 4000
MAX_HASH_LEN = 64
MAX_LAYOUT_JSON_BYTES = 256 * 1024

_FORBIDDEN_SECTION_IDS = frozenset({"__proto__", "constructor", "prototype"})


def _clip_str(value, max_len):
    if not isinstance(value, str):
        return ""
    if len(value) <= max_len:
        return value
    return value[:max_len]


def normalize_favourites_layout(layout):
    """Return a sanitized layout dict, or None when the shape is invalid."""
    if not isinstance(layout, dict) or not isinstance(layout.get("sections"), list):
        return None

    raw_by_section = layout.get("favouritesBySection")
    favourites_by_section = raw_by_section if isinstance(raw_by_section, dict) else {}

    sections = []
    section_ids = set()
    for section in layout.get("sections") or []:
        if len(sections) >= MAX_SECTIONS:
            break
        if not isinstance(section, dict):
            continue
        section_id = section.get("id")
        if not isinstance(section_id, str):
            continue
        section_id = section_id.strip()
        if (
            not section_id
            or len(section_id) > MAX_SECTION_ID_LEN
            or section_id in section_ids
            or section_id in _FORBIDDEN_SECTION_IDS
        ):
            continue
        section_ids.add(section_id)
        name = _clip_str(section.get("name"), MAX_SECTION_NAME_LEN)
        sections.append(
            {
                "id": section_id,
                "name": name,
                "collapsed": section.get("collapsed") is True,
            },
        )

    if not sections:
        return None

    raw_order = layout.get("sectionOrder")
    if isinstance(raw_order, list):
        section_order = []
        for sid in raw_order:
            if not isinstance(sid, str):
                continue
            sid = sid.strip()
            if sid in section_ids and sid not in section_order:
                section_order.append(sid)
            if len(section_order) >= MAX_SECTIONS:
                break
    else:
        section_order = [section["id"] for section in sections]
    for section in sections:
        if section["id"] not in section_order:
            section_order.append(section["id"])

    sanitized_map = {}
    total_hashes = 0
    for key, value in favourites_by_section.items():
        if not isinstance(key, str):
            continue
        key = key.strip()
        if key not in section_ids or key in _FORBIDDEN_SECTION_IDS:
            continue
        if not isinstance(value, list):
            continue
        hashes = []
        seen = set()
        for item in value:
            if (
                total_hashes >= MAX_TOTAL_HASHES
                or len(hashes) >= MAX_HASHES_PER_SECTION
            ):
                break
            if not isinstance(item, str):
                continue
            h = item.strip()
            if not h or len(h) > MAX_HASH_LEN or h in seen:
                continue
            seen.add(h)
            hashes.append(h)
            total_hashes += 1
        sanitized_map[key] = hashes

    for section in sections:
        sanitized_map.setdefault(section["id"], [])

    return {
        "sections": sections,
        "sectionOrder": section_order,
        "favouritesBySection": sanitized_map,
    }


def layout_payload_too_large(raw_body_len):
    """Return True when a raw request body exceeds the layout size budget."""
    try:
        size = int(raw_body_len)
    except (TypeError, ValueError):
        return False
    return size > MAX_LAYOUT_JSON_BYTES
