# SPDX-License-Identifier: 0BSD

"""Strip remote images, NetworkLinks, and unsafe KMZ entries from map overlays."""

from __future__ import annotations

import json
import zipfile
from dataclasses import dataclass, field
from io import BytesIO
from xml.etree import ElementTree as ET

from meshchatx.src.backend.map_geo_validator import (
    GeoValidationError,
    ZIP_LOCAL_HEADER,
    sniff_format,
)


def _strip_ns(tag: str) -> str:
    if "}" in tag:
        return tag.rsplit("}", 1)[-1]
    return tag


ALLOWED_DATA_IMAGE_PREFIXES = (
    "data:image/png;base64,",
    "data:image/jpeg;base64,",
    "data:image/jpg;base64,",
    "data:image/gif;base64,",
    "data:image/webp;base64,",
)

ALLOWED_KMZ_EXTS = frozenset({".kml", ".png", ".jpg", ".jpeg", ".gif", ".webp"})
REMOTE_HREF_SCHEMES = (
    "http:",
    "https:",
    "file:",
    "ftp:",
    "javascript:",
    "vbscript:",
)
OVERLAY_TAGS = frozenset({"groundoverlay", "photooverlay", "screenoverlay"})
DROP_TAGS = frozenset({"networklink", "networklinkcontrol"})
ICON_URL_KEYS = (
    "href",
    "url",
    "icon",
    "image",
    "iconurl",
    "mcx_icon_href",
    "marker-symbol",
)


@dataclass
class SanitizeResult:
    data: bytes
    format: str
    stripped: list[str] = field(default_factory=list)
    feature_count: int = 0


def _looks_like_dtd(text: str) -> bool:
    head = text[:4096].upper()
    return "<!DOCTYPE" in head or "<!ENTITY" in head


def is_remote_href(href: str) -> bool:
    h = (href or "").strip()
    if not h:
        return False
    lower = h.lower()
    if lower.startswith("//"):
        return True
    return any(lower.startswith(s) for s in REMOTE_HREF_SCHEMES)


def is_allowed_data_image_href(href: str) -> bool:
    h = (href or "").strip()
    if not h.lower().startswith("data:"):
        return False
    lower = h.lower()
    if ";" in lower[:64] and "base64," not in lower[:96]:
        return False
    return any(lower.startswith(p) for p in ALLOWED_DATA_IMAGE_PREFIXES)


def _href_from_element(el: ET.Element) -> str | None:
    tag = _strip_ns(el.tag).lower()
    if tag in ("href", "hrefhref"):
        text = (el.text or "").strip()
        return text or None
    for key, val in el.attrib.items():
        attr = _strip_ns(key).lower()
        if attr in ("href", "xlink:href") or attr.endswith("href"):
            s = str(val).strip()
            if s:
                return s
    return None


def _set_href_on_element(el: ET.Element, value: str | None) -> None:
    tag = _strip_ns(el.tag).lower()
    if tag == "href":
        el.text = value
        return
    for key in list(el.attrib.keys()):
        attr = _strip_ns(key).lower()
        if attr in ("href", "xlink:href") or attr.endswith("href"):
            if value is None:
                del el.attrib[key]
            else:
                el.attrib[key] = value


def _strip_description_html(el: ET.Element) -> bool:
    tag = _strip_ns(el.tag).lower()
    if tag != "description":
        return False
    texts = []
    if el.text and el.text.strip():
        texts.append(el.text.strip())
    had_children = False
    for child in list(el):
        had_children = True
        if child.text and child.text.strip():
            texts.append(child.text.strip())
        if child.tail and child.tail.strip():
            texts.append(child.tail.strip())
        el.remove(child)
    el.text = " ".join(texts) if texts else None
    return had_children


def _walk_strip_kml(
    el: ET.Element,
    stripped: list[str],
    *,
    zip_local_ok: bool,
) -> None:
    for child in list(el):
        tag = _strip_ns(child.tag).lower()
        if tag in DROP_TAGS:
            stripped.append("network_link")
            el.remove(child)
            continue
        if tag in OVERLAY_TAGS:
            hrefs = []
            for sub in child.iter():
                h = _href_from_element(sub)
                if h:
                    hrefs.append(h)
            if any(
                is_remote_href(h)
                or (
                    h.strip().lower().startswith("data:")
                    and not is_allowed_data_image_href(h)
                )
                for h in hrefs
            ):
                stripped.append("remote_overlay")
                el.remove(child)
                continue
            if any(is_remote_href(h) for h in hrefs):
                stripped.append("remote_overlay")
                el.remove(child)
                continue
            if not zip_local_ok:
                non_data = [h for h in hrefs if h and not is_allowed_data_image_href(h)]
                if non_data:
                    stripped.append("remote_overlay")
                    el.remove(child)
                    continue
        if _strip_description_html(child):
            stripped.append("html_description")
        href = _href_from_element(child)
        if href is not None:
            if is_allowed_data_image_href(href):
                pass
            elif is_remote_href(href) or href.strip().lower().startswith("data:"):
                stripped.append("remote_href")
                if _strip_ns(child.tag).lower() == "href":
                    el.remove(child)
                    continue
                _set_href_on_element(child, None)
            elif not zip_local_ok:
                stripped.append("remote_href")
                if _strip_ns(child.tag).lower() == "href":
                    el.remove(child)
                    continue
                _set_href_on_element(child, None)
        _walk_strip_kml(child, stripped, zip_local_ok=zip_local_ok)


def _count_placemarks(root: ET.Element) -> int:
    return sum(1 for el in root.iter() if _strip_ns(el.tag).lower() == "placemark")


def sanitize_kml_bytes(data: bytes, *, zip_local_ok: bool = False) -> SanitizeResult:
    try:
        text = data.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise GeoValidationError("invalid_encoding") from exc
    if _looks_like_dtd(text):
        raise GeoValidationError("dtd_forbidden")
    try:
        root = ET.fromstring(text)
    except ET.ParseError as exc:
        raise GeoValidationError("invalid_kml") from exc
    if _strip_ns(root.tag).lower() != "kml":
        raise GeoValidationError("invalid_kml")
    stripped: list[str] = []
    _walk_strip_kml(root, stripped, zip_local_ok=zip_local_ok)
    count = _count_placemarks(root)
    if count == 0 and "network_link" in stripped:
        raise GeoValidationError("remote_content")
    out = ET.tostring(root, encoding="utf-8", xml_declaration=True)
    return SanitizeResult(
        data=out, format="kml", stripped=stripped, feature_count=count
    )


def _retain_kmz_local_hrefs(
    el: ET.Element,
    kml_name: str,
    kept: dict[str, bytes],
    referenced: set[str],
    stripped: list[str],
) -> None:
    for child in list(el):
        href = _href_from_element(child)
        if href and not is_allowed_data_image_href(href) and not is_remote_href(href):
            resolved = _resolve_zip_href(kml_name, href)
            ext = _zip_entry_ext(resolved) if resolved else ""
            if (
                resolved is None
                or resolved not in kept
                or ext not in (ALLOWED_KMZ_EXTS - {".kml"})
            ):
                stripped.append(
                    "unsafe_kmz_entry"
                    if resolved and resolved in kept
                    else "remote_href"
                )
                if _strip_ns(child.tag).lower() == "href":
                    el.remove(child)
                    continue
                _set_href_on_element(child, None)
            else:
                referenced.add(resolved)
        _retain_kmz_local_hrefs(child, kml_name, kept, referenced, stripped)


def _zip_entry_ext(name: str) -> str:
    lower = name.replace("\\", "/").lower()
    if "." not in lower.rsplit("/", 1)[-1]:
        return ""
    return "." + lower.rsplit(".", 1)[-1]


def sanitize_kmz_bytes(data: bytes) -> SanitizeResult:
    if not data.startswith(ZIP_LOCAL_HEADER):
        raise GeoValidationError("invalid_kmz")
    try:
        zf = zipfile.ZipFile(BytesIO(data))
    except zipfile.BadZipFile as exc:
        raise GeoValidationError("invalid_kmz") from exc
    stripped: list[str] = []
    with zf:
        infos = [i for i in zf.infolist() if not i.is_dir()]
        kml_name = None
        kept: dict[str, bytes] = {}
        for info in infos:
            name = info.filename.replace("\\", "/")
            if ".." in name.split("/"):
                raise GeoValidationError("path_traversal")
            ext = _zip_entry_ext(name)
            if ext not in ALLOWED_KMZ_EXTS:
                raise GeoValidationError("unsafe_kmz_entry")
            payload = zf.read(info.filename)
            kept[name] = payload
            lower = name.lower()
            if lower.endswith(".kml"):
                if kml_name is None or lower.endswith("doc.kml") or lower == "doc.kml":
                    if (
                        lower == "doc.kml"
                        or lower.endswith("/doc.kml")
                        or kml_name is None
                    ):
                        kml_name = name
        if not kml_name:
            raise GeoValidationError("kmz_missing_kml")
        kml_result = sanitize_kml_bytes(kept[kml_name], zip_local_ok=True)
        stripped.extend(kml_result.stripped)
        root = ET.fromstring(kml_result.data)
        referenced: set[str] = set()
        _retain_kmz_local_hrefs(
            root,
            kml_name,
            kept,
            referenced,
            stripped,
        )
        kml_bytes = ET.tostring(root, encoding="utf-8", xml_declaration=True)
        out_buf = BytesIO()
        with zipfile.ZipFile(out_buf, "w", compression=zipfile.ZIP_DEFLATED) as out_zf:
            out_zf.writestr("doc.kml", kml_bytes)
            for path in sorted(referenced):
                out_zf.writestr(path, kept[path])
    return SanitizeResult(
        data=out_buf.getvalue(),
        format="kmz",
        stripped=stripped,
        feature_count=kml_result.feature_count,
    )


def _resolve_zip_href(kml_path: str, href: str) -> str | None:
    h = (href or "").strip().replace("\\", "/")
    if not h or is_remote_href(h) or h.lower().startswith("data:"):
        return None
    base = kml_path.rsplit("/", 1)[0] + "/" if "/" in kml_path else ""
    combined = (base + h).replace("\\", "/")
    parts = [p for p in combined.split("/") if p and p != "."]
    out: list[str] = []
    for p in parts:
        if p == "..":
            if not out:
                return None
            out.pop()
        else:
            out.append(p)
    return "/".join(out)


def _strip_geojson_remote_urls(obj, stripped: list[str]) -> None:
    if isinstance(obj, dict):
        props = obj.get("properties")
        if isinstance(props, dict):
            for key, val in list(props.items()):
                if not isinstance(val, str):
                    continue
                key_l = str(key).lower()
                if not any(tok in key_l for tok in ICON_URL_KEYS):
                    continue
                if is_allowed_data_image_href(val):
                    continue
                if is_remote_href(val) or val.strip().lower().startswith("data:"):
                    stripped.append("remote_href")
                    del props[key]
        for v in obj.values():
            _strip_geojson_remote_urls(v, stripped)
    elif isinstance(obj, list):
        for item in obj:
            _strip_geojson_remote_urls(item, stripped)


def sanitize_geojson_bytes(data: bytes) -> SanitizeResult:
    try:
        text = data.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise GeoValidationError("invalid_encoding") from exc
    try:
        obj = json.loads(text)
    except json.JSONDecodeError as exc:
        raise GeoValidationError("invalid_geojson") from exc
    stripped: list[str] = []
    _strip_geojson_remote_urls(obj, stripped)
    count = 0
    if isinstance(obj, dict):
        t = obj.get("type")
        if t == "FeatureCollection":
            feats = obj.get("features")
            count = len(feats) if isinstance(feats, list) else 0
        else:
            count = 1
    if not stripped:
        return SanitizeResult(
            data=data, format="geojson", stripped=[], feature_count=count
        )
    out = json.dumps(obj, separators=(",", ":")).encode("utf-8")
    return SanitizeResult(
        data=out, format="geojson", stripped=stripped, feature_count=count
    )


def sanitize_geo_bytes(
    data: bytes,
    *,
    hinted_format: str | None = None,
) -> SanitizeResult:
    if not data:
        raise GeoValidationError("empty_file")
    fmt = sniff_format(data, hinted_format)
    if fmt == "geojson":
        return sanitize_geojson_bytes(data)
    if fmt == "kml":
        return sanitize_kml_bytes(data, zip_local_ok=False)
    if fmt == "kmz":
        return sanitize_kmz_bytes(data)
    raise GeoValidationError("unknown_format")
