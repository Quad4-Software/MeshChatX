# SPDX-License-Identifier: 0BSD

import json

from meshchatx.src.backend.map_overlay_export import (
    convert_overlay_bytes,
    geojson_to_kml,
    kml_to_geojson,
    merge_geojson_bytes,
)


def test_geojson_kml_roundtrip_point():
    geo = json.dumps(
        {
            "type": "FeatureCollection",
            "features": [
                {
                    "type": "Feature",
                    "properties": {"name": "n"},
                    "geometry": {"type": "Point", "coordinates": [10.5, -20.25]},
                },
            ],
        },
    ).encode()
    kml = geojson_to_kml(geo)
    assert b"<kml" in kml
    back = json.loads(kml_to_geojson(kml).decode())
    assert back["type"] == "FeatureCollection"
    assert len(back["features"]) == 1
    coords = back["features"][0]["geometry"]["coordinates"]
    assert abs(coords[0] - 10.5) < 1e-6
    assert abs(coords[1] + 20.25) < 1e-6


def test_convert_passthrough_and_kmz():
    geo = b'{"type":"Point","coordinates":[1,2]}'
    out = convert_overlay_bytes(
        geo,
        source_format="geojson",
        target_format="geojson",
        max_bytes=1024 * 1024,
        max_features=100,
        max_kmz_uncompressed_bytes=1024 * 1024,
    )
    assert out == geo
    kmz = convert_overlay_bytes(
        geo,
        source_format="geojson",
        target_format="kmz",
        max_bytes=1024 * 1024,
        max_features=100,
        max_kmz_uncompressed_bytes=1024 * 1024,
    )
    assert kmz[:4] == b"PK\x03\x04"


def test_merge_geojson_bytes():
    a = b'{"type":"FeatureCollection","features":[{"type":"Feature","properties":{},"geometry":{"type":"Point","coordinates":[1,2]}}]}'
    b = b'{"type":"Feature","properties":{},"geometry":{"type":"Point","coordinates":[3,4]}}'
    merged = json.loads(merge_geojson_bytes([a, b]).decode())
    assert len(merged["features"]) == 2
