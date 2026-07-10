# SPDX-License-Identifier: 0BSD

import io
import json
import zipfile

import pytest

from meshchatx.src.backend.map_geo_validator import (
    GeoValidationError,
    validate_geo_bytes,
)


def _kmz_with_kml(kml: bytes) -> bytes:
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        zf.writestr("doc.kml", kml)
    return buf.getvalue()


def test_validate_geojson_ok():
    data = json.dumps(
        {
            "type": "FeatureCollection",
            "features": [
                {
                    "type": "Feature",
                    "properties": {},
                    "geometry": {"type": "Point", "coordinates": [1.0, 2.0]},
                },
            ],
        },
    ).encode()
    result = validate_geo_bytes(
        data,
        max_bytes=1024 * 1024,
        max_features=100,
        max_kmz_uncompressed_bytes=1024 * 1024,
    )
    assert result.format == "geojson"
    assert result.feature_count == 1


def test_validate_geojson_rejects_html():
    with pytest.raises(GeoValidationError) as exc:
        validate_geo_bytes(
            b"<!DOCTYPE html><html></html>",
            max_bytes=1024,
            max_features=10,
            max_kmz_uncompressed_bytes=1024,
        )
    assert exc.value.code in ("not_geo_content", "unknown_format", "invalid_geojson")


def test_validate_geojson_too_large():
    data = b'{"type":"Point","coordinates":[0,0]}'
    with pytest.raises(GeoValidationError) as exc:
        validate_geo_bytes(
            data,
            hinted_format="geojson",
            max_bytes=5,
            max_features=10,
            max_kmz_uncompressed_bytes=1024,
        )
    assert exc.value.code == "file_too_large"


def test_validate_geojson_coords_out_of_range():
    data = json.dumps(
        {"type": "Point", "coordinates": [200.0, 2.0]},
    ).encode()
    with pytest.raises(GeoValidationError) as exc:
        validate_geo_bytes(
            data,
            max_bytes=1024,
            max_features=10,
            max_kmz_uncompressed_bytes=1024,
        )
    assert exc.value.code == "coordinates_out_of_range"


def test_validate_kml_ok():
    kml = b"""<?xml version="1.0"?>
    <kml xmlns="http://www.opengis.net/kml/2.2">
      <Document><Placemark><name>x</name>
        <Point><coordinates>1,2,0</coordinates></Point>
      </Placemark></Document>
    </kml>"""
    result = validate_geo_bytes(
        kml,
        max_bytes=1024 * 1024,
        max_features=100,
        max_kmz_uncompressed_bytes=1024 * 1024,
    )
    assert result.format == "kml"
    assert result.feature_count == 1


def test_validate_kmz_ok():
    kml = b"""<?xml version="1.0"?>
    <kml xmlns="http://www.opengis.net/kml/2.2">
      <Document><Placemark><Point><coordinates>1,2,0</coordinates></Point></Placemark></Document>
    </kml>"""
    data = _kmz_with_kml(kml)
    result = validate_geo_bytes(
        data,
        max_bytes=1024 * 1024,
        max_features=100,
        max_kmz_uncompressed_bytes=1024 * 1024,
    )
    assert result.format == "kmz"


def test_validate_kmz_missing_kml():
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        zf.writestr("readme.txt", b"nope")
    with pytest.raises(GeoValidationError) as exc:
        validate_geo_bytes(
            buf.getvalue(),
            max_bytes=1024 * 1024,
            max_features=100,
            max_kmz_uncompressed_bytes=1024 * 1024,
        )
    assert exc.value.code == "kmz_missing_kml"


def test_validate_kmz_path_traversal_entry():
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        zf.writestr("../evil.kml", b"<kml></kml>")
    with pytest.raises(GeoValidationError) as exc:
        validate_geo_bytes(
            buf.getvalue(),
            max_bytes=1024 * 1024,
            max_features=100,
            max_kmz_uncompressed_bytes=1024 * 1024,
        )
    assert exc.value.code == "path_traversal"
