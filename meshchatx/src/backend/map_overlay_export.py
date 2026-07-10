# SPDX-License-Identifier: 0BSD

"""Export / transcode cached map overlays between GeoJSON, KML, and KMZ."""

from __future__ import annotations

import json
import zipfile
from io import BytesIO
from xml.etree import ElementTree as ET
from xml.sax.saxutils import escape

from meshchatx.src.backend.map_geo_validator import (
    GeoValidationError,
    sniff_format,
    validate_geo_bytes,
)


class OverlayExportError(ValueError):
    def __init__(self, code: str, message: str | None = None):
        self.code = code
        super().__init__(message or code)


def _strip_ns(tag: str) -> str:
    if "}" in tag:
        return tag.rsplit("}", 1)[-1]
    return tag


def _coords_to_kml(coords, geom_type: str) -> str:
    if geom_type == "Point":
        lon, lat = coords[0], coords[1]
        alt = coords[2] if len(coords) > 2 else 0
        return f"{lon},{lat},{alt}"
    if geom_type in ("LineString", "MultiPoint"):
        parts = []
        for c in coords:
            lon, lat = c[0], c[1]
            alt = c[2] if len(c) > 2 else 0
            parts.append(f"{lon},{lat},{alt}")
        return " ".join(parts)
    if geom_type == "Polygon":
        # outer ring only for simple export
        ring = coords[0] if coords else []
        return _coords_to_kml(ring, "LineString")
    return ""


def geojson_to_kml(data: bytes) -> bytes:
    obj = json.loads(data.decode("utf-8"))
    features = []
    if obj.get("type") == "FeatureCollection":
        features = obj.get("features") or []
    elif obj.get("type") == "Feature":
        features = [obj]
    else:
        features = [{"type": "Feature", "properties": {}, "geometry": obj}]

    parts = [
        '<?xml version="1.0" encoding="UTF-8"?>',
        '<kml xmlns="http://www.opengis.net/kml/2.2"><Document>',
    ]
    for feat in features:
        if not isinstance(feat, dict):
            continue
        props = feat.get("properties") or {}
        name = escape(str(props.get("name") or props.get("title") or "feature"))
        geom = feat.get("geometry") or {}
        gtype = geom.get("type")
        coords = geom.get("coordinates")
        if not gtype or coords is None:
            continue
        parts.append("<Placemark>")
        parts.append(f"<name>{name}</name>")
        if gtype == "Point":
            parts.append(
                f"<Point><coordinates>{_coords_to_kml(coords, 'Point')}</coordinates></Point>",
            )
        elif gtype == "LineString":
            parts.append(
                f"<LineString><coordinates>{_coords_to_kml(coords, 'LineString')}</coordinates></LineString>",
            )
        elif gtype == "Polygon":
            parts.append(
                "<Polygon><outerBoundaryIs><LinearRing>"
                f"<coordinates>{_coords_to_kml(coords, 'Polygon')}</coordinates>"
                "</LinearRing></outerBoundaryIs></Polygon>",
            )
        else:
            # Skip complex geometries in simple transcoder
            parts.append("</Placemark>")
            continue
        parts.append("</Placemark>")
    parts.append("</Document></kml>")
    return "\n".join(parts).encode("utf-8")


def kml_to_geojson(data: bytes) -> bytes:
    root = ET.fromstring(data.decode("utf-8"))
    features = []
    for pm in root.iter():
        if _strip_ns(pm.tag).lower() != "placemark":
            continue
        name = None
        geom = None
        for child in list(pm):
            tag = _strip_ns(child.tag).lower()
            if tag == "name":
                name = (child.text or "").strip()
            elif tag == "point":
                coords_el = next(
                    (
                        c
                        for c in child.iter()
                        if _strip_ns(c.tag).lower() == "coordinates"
                    ),
                    None,
                )
                if coords_el is not None and coords_el.text:
                    parts = coords_el.text.strip().split(",")
                    if len(parts) >= 2:
                        geom = {
                            "type": "Point",
                            "coordinates": [float(parts[0]), float(parts[1])],
                        }
            elif tag == "linestring":
                coords_el = next(
                    (
                        c
                        for c in child.iter()
                        if _strip_ns(c.tag).lower() == "coordinates"
                    ),
                    None,
                )
                if coords_el is not None and coords_el.text:
                    line = []
                    for token in coords_el.text.strip().split():
                        bits = token.split(",")
                        if len(bits) >= 2:
                            line.append([float(bits[0]), float(bits[1])])
                    if line:
                        geom = {"type": "LineString", "coordinates": line}
            elif tag == "polygon":
                coords_el = next(
                    (
                        c
                        for c in child.iter()
                        if _strip_ns(c.tag).lower() == "coordinates"
                    ),
                    None,
                )
                if coords_el is not None and coords_el.text:
                    ring = []
                    for token in coords_el.text.strip().split():
                        bits = token.split(",")
                        if len(bits) >= 2:
                            ring.append([float(bits[0]), float(bits[1])])
                    if ring:
                        geom = {"type": "Polygon", "coordinates": [ring]}
        if geom is None:
            continue
        features.append(
            {
                "type": "Feature",
                "properties": {"name": name} if name else {},
                "geometry": geom,
            },
        )
    return json.dumps(
        {"type": "FeatureCollection", "features": features},
        separators=(",", ":"),
    ).encode("utf-8")


def kmz_to_kml(data: bytes) -> bytes:
    with zipfile.ZipFile(BytesIO(data)) as zf:
        names = [n for n in zf.namelist() if not n.endswith("/")]
        kml_name = None
        for n in names:
            lower = n.replace("\\", "/").lower()
            if lower == "doc.kml" or lower.endswith("/doc.kml"):
                kml_name = n
                break
        if kml_name is None:
            for n in names:
                if n.lower().endswith(".kml"):
                    kml_name = n
                    break
        if kml_name is None:
            raise OverlayExportError("kmz_missing_kml")
        return zf.read(kml_name)


def kml_to_kmz(kml_bytes: bytes) -> bytes:
    buf = BytesIO()
    with zipfile.ZipFile(buf, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("doc.kml", kml_bytes)
    return buf.getvalue()


def merge_geojson_bytes(chunks: list[bytes]) -> bytes:
    features = []
    for chunk in chunks:
        obj = json.loads(chunk.decode("utf-8"))
        if obj.get("type") == "FeatureCollection":
            features.extend(obj.get("features") or [])
        elif obj.get("type") == "Feature":
            features.append(obj)
        else:
            features.append(
                {"type": "Feature", "properties": {}, "geometry": obj},
            )
    return json.dumps(
        {"type": "FeatureCollection", "features": features},
        separators=(",", ":"),
    ).encode("utf-8")


def to_geojson(data: bytes, source_format: str | None = None) -> bytes:
    fmt = source_format or sniff_format(data)
    if fmt == "geojson":
        return data
    if fmt == "kml":
        return kml_to_geojson(data)
    if fmt == "kmz":
        return kml_to_geojson(kmz_to_kml(data))
    raise OverlayExportError("unknown_format")


def from_geojson(geojson_bytes: bytes, target_format: str) -> bytes:
    if target_format == "geojson":
        return geojson_bytes
    if target_format == "kml":
        return geojson_to_kml(geojson_bytes)
    if target_format == "kmz":
        return kml_to_kmz(geojson_to_kml(geojson_bytes))
    raise OverlayExportError("unknown_format")


def convert_overlay_bytes(
    data: bytes,
    *,
    source_format: str | None,
    target_format: str,
    max_bytes: int,
    max_features: int,
    max_kmz_uncompressed_bytes: int,
) -> bytes:
    if target_format not in ("geojson", "kml", "kmz"):
        raise OverlayExportError("invalid_export_format")
    src = source_format or sniff_format(data)
    if src == target_format:
        out = data
    else:
        gj = to_geojson(data, src)
        out = from_geojson(gj, target_format)
    try:
        validate_geo_bytes(
            out,
            hinted_format=target_format,
            max_bytes=max_bytes,
            max_features=max_features,
            max_kmz_uncompressed_bytes=max_kmz_uncompressed_bytes,
        )
    except GeoValidationError as exc:
        raise OverlayExportError(exc.code) from exc
    return out


CONTENT_TYPES = {
    "geojson": "application/geo+json",
    "kml": "application/vnd.google-earth.kml+xml",
    "kmz": "application/vnd.google-earth.kmz",
}

EXTENSIONS = {
    "geojson": ".geojson",
    "kml": ".kml",
    "kmz": ".kmz",
}
