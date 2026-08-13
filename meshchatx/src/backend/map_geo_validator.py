# SPDX-License-Identifier: 0BSD

"""Validate GeoJSON / KML / KMZ bytes for map overlay import."""

from __future__ import annotations

import json
import zipfile
from dataclasses import dataclass
from io import BytesIO
from xml.etree import ElementTree as ET

ZIP_LOCAL_HEADER = b"PK\x03\x04"
MAX_KMZ_ENTRIES = 512
MAX_COMPRESSION_RATIO = 100.0


class GeoValidationError(ValueError):
    def __init__(self, code: str, message: str | None = None):
        self.code = code
        super().__init__(message or code)


@dataclass
class GeoValidationResult:
    format: str
    feature_count: int
    byte_size: int


def _looks_like_html(text: str) -> bool:
    head = text.lstrip()[:200].lower()
    return head.startswith("<!doctype html") or head.startswith("<html")


def _count_geojson_features(obj) -> int:
    if not isinstance(obj, dict):
        raise GeoValidationError("invalid_geojson")
    t = obj.get("type")
    if t == "FeatureCollection":
        feats = obj.get("features")
        if not isinstance(feats, list):
            raise GeoValidationError("invalid_geojson")
        return len(feats)
    if t == "Feature":
        return 1
    if t in (
        "Point",
        "MultiPoint",
        "LineString",
        "MultiLineString",
        "Polygon",
        "MultiPolygon",
        "GeometryCollection",
    ):
        return 1
    raise GeoValidationError("invalid_geojson")


def _validate_coords_finite(obj, *, depth: int = 0) -> None:
    if depth > 32:
        raise GeoValidationError("geometry_too_deep")
    if isinstance(obj, dict):
        if "coordinates" in obj:
            _walk_coords(obj["coordinates"], depth=0)
        if "geometries" in obj and isinstance(obj["geometries"], list):
            for g in obj["geometries"]:
                _validate_coords_finite(g, depth=depth + 1)
        if "geometry" in obj and obj["geometry"] is not None:
            _validate_coords_finite(obj["geometry"], depth=depth + 1)
        if "features" in obj and isinstance(obj["features"], list):
            for f in obj["features"]:
                _validate_coords_finite(f, depth=depth + 1)


def _walk_coords(node, *, depth: int) -> None:
    if depth > 16:
        raise GeoValidationError("geometry_too_deep")
    if isinstance(node, (int, float)):
        if node != node or node in (float("inf"), float("-inf")):
            raise GeoValidationError("invalid_coordinates")
        return
    if isinstance(node, list):
        if node and all(isinstance(x, (int, float)) for x in node):
            if len(node) < 2:
                raise GeoValidationError("invalid_coordinates")
            lon, lat = float(node[0]), float(node[1])
            if lon != lon or lat != lat:
                raise GeoValidationError("invalid_coordinates")
            if lon < -180.0 or lon > 180.0 or lat < -90.0 or lat > 90.0:
                raise GeoValidationError("coordinates_out_of_range")
            return
        for item in node:
            _walk_coords(item, depth=depth + 1)
        return
    raise GeoValidationError("invalid_coordinates")


def validate_geojson_bytes(
    data: bytes,
    *,
    max_bytes: int,
    max_features: int,
) -> GeoValidationResult:
    if len(data) > max_bytes:
        raise GeoValidationError("file_too_large")
    try:
        text = data.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise GeoValidationError("invalid_encoding") from exc
    if _looks_like_html(text):
        raise GeoValidationError("not_geo_content")
    try:
        obj = json.loads(text)
    except json.JSONDecodeError as exc:
        raise GeoValidationError("invalid_geojson") from exc
    count = _count_geojson_features(obj)
    if count > max_features:
        raise GeoValidationError("too_many_features")
    _validate_coords_finite(obj)
    return GeoValidationResult(
        format="geojson",
        feature_count=count,
        byte_size=len(data),
    )


def _strip_ns(tag: str) -> str:
    if "}" in tag:
        return tag.rsplit("}", 1)[-1]
    return tag


def validate_kml_bytes(
    data: bytes,
    *,
    max_bytes: int,
    max_features: int,
) -> GeoValidationResult:
    if len(data) > max_bytes:
        raise GeoValidationError("file_too_large")
    try:
        text = data.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise GeoValidationError("invalid_encoding") from exc
    if _looks_like_html(text):
        raise GeoValidationError("not_geo_content")
    head = text[:4096].upper()
    if "<!DOCTYPE" in head or "<!ENTITY" in head:
        raise GeoValidationError("dtd_forbidden")
    try:
        root = ET.fromstring(text)
    except ET.ParseError as exc:
        raise GeoValidationError("invalid_kml") from exc
    if _strip_ns(root.tag).lower() != "kml":
        raise GeoValidationError("invalid_kml")
    placemarks = [el for el in root.iter() if _strip_ns(el.tag).lower() == "placemark"]
    count = len(placemarks)
    if count > max_features:
        raise GeoValidationError("too_many_features")
    return GeoValidationResult(format="kml", feature_count=count, byte_size=len(data))


def validate_kmz_bytes(
    data: bytes,
    *,
    max_bytes: int,
    max_uncompressed_bytes: int,
    max_features: int,
) -> GeoValidationResult:
    if len(data) > max_bytes:
        raise GeoValidationError("file_too_large")
    if not data.startswith(ZIP_LOCAL_HEADER):
        raise GeoValidationError("invalid_kmz")
    try:
        zf = zipfile.ZipFile(BytesIO(data))
    except zipfile.BadZipFile as exc:
        raise GeoValidationError("invalid_kmz") from exc
    with zf:
        infos = [i for i in zf.infolist() if not i.is_dir()]
        if len(infos) > MAX_KMZ_ENTRIES:
            raise GeoValidationError("kmz_too_many_entries")
        total_uncomp = 0
        kml_name = None
        for info in infos:
            name = info.filename.replace("\\", "/")
            if ".." in name.split("/"):
                raise GeoValidationError("path_traversal")
            total_uncomp += int(info.file_size)
            if total_uncomp > max_uncompressed_bytes:
                raise GeoValidationError("kmz_uncompressed_too_large")
            if info.compress_size > 0:
                ratio = float(info.file_size) / float(info.compress_size)
                if ratio > MAX_COMPRESSION_RATIO and info.file_size > 1024 * 1024:
                    raise GeoValidationError("kmz_compression_ratio")
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
        kml_bytes = zf.read(kml_name)
        kml_result = validate_kml_bytes(
            kml_bytes,
            max_bytes=max_uncompressed_bytes,
            max_features=max_features,
        )
    return GeoValidationResult(
        format="kmz",
        feature_count=kml_result.feature_count,
        byte_size=len(data),
    )


def sniff_format(data: bytes, hinted: str | None = None) -> str:
    if hinted in ("geojson", "kml", "kmz"):
        return hinted
    if data.startswith(ZIP_LOCAL_HEADER):
        return "kmz"
    sample = data[:256].lstrip()
    if sample.startswith(b"{") or sample.startswith(b"["):
        return "geojson"
    lower = sample.lower()
    if lower.startswith(b"<kml") or b"<kml" in lower[:64]:
        return "kml"
    if lower.startswith(b"<?xml"):
        return "kml"
    raise GeoValidationError("unknown_format")


def validate_geo_bytes(
    data: bytes,
    *,
    hinted_format: str | None = None,
    max_bytes: int,
    max_features: int,
    max_kmz_uncompressed_bytes: int,
) -> GeoValidationResult:
    if not data:
        raise GeoValidationError("empty_file")
    fmt = sniff_format(data, hinted_format)
    if fmt == "geojson":
        return validate_geojson_bytes(
            data,
            max_bytes=max_bytes,
            max_features=max_features,
        )
    if fmt == "kml":
        return validate_kml_bytes(
            data,
            max_bytes=max_bytes,
            max_features=max_features,
        )
    if fmt == "kmz":
        return validate_kmz_bytes(
            data,
            max_bytes=max_bytes,
            max_uncompressed_bytes=max_kmz_uncompressed_bytes,
            max_features=max_features,
        )
    raise GeoValidationError("unknown_format")
