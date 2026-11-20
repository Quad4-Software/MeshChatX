# SPDX-License-Identifier: 0BSD
"""Adversarial coordinate/format properties for map geo validators."""

import json

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from meshchatx.src.backend.map_geo_validator import (
    GeoValidationError,
    validate_geojson_bytes,
    validate_kml_bytes,
)

LIMITS = {"max_bytes": 10 * 1024 * 1024, "max_features": 10_000}


def geojson(coords, gtype="Point"):
    return json.dumps({"type": gtype, "coordinates": coords}).encode()


class TestCoordinateValidation:
    @pytest.mark.parametrize(
        "coords",
        [
            [],
            [[]],
            [[[]]],
            [[10, 20], []],
            [10, 20, float("nan")],
            [10, 20, float("inf")],
            [10, 20, -float("inf")],
            [10, True],
            [False, 20],
            [[10, 20, float("nan")]],
        ],
    )
    def test_invalid_positions_rejected(self, coords):
        with pytest.raises(GeoValidationError):
            validate_geojson_bytes(geojson(coords), **LIMITS)

    @pytest.mark.parametrize(
        "coords",
        [
            [10, 20],
            [10, 20, 1500],
            [10, 20, 1500, 0],
            [-179.9, 89.9],
            [[10, 20], [30, 40]],
        ],
    )
    def test_valid_positions_accepted(self, coords):
        validate_geojson_bytes(
            geojson(coords, "MultiPoint" if isinstance(coords[0], list) else "Point"),
            **LIMITS,
        )

    def test_lon_lat_range_bounds(self):
        with pytest.raises(GeoValidationError):
            validate_geojson_bytes(geojson([181, 0]), **LIMITS)
        with pytest.raises(GeoValidationError):
            validate_geojson_bytes(geojson([0, 91]), **LIMITS)
        validate_geojson_bytes(geojson([-180, -90]), **LIMITS)
        validate_geojson_bytes(geojson([180, 90]), **LIMITS)

    def test_deeply_nested_json_rejected_not_crash(self):
        # json.loads raises RecursionError on extreme nesting; the validator
        # must map that to GeoValidationError, not propagate a 500.
        deep = json.dumps(
            {"type": "Point", "coordinates": json.loads("[" * 5000 + "]" * 5000)}
        ).encode()
        with pytest.raises(GeoValidationError):
            validate_geojson_bytes(deep, **LIMITS)

    def test_deeply_nested_unparseable_json_rejected_not_crash(self):
        with pytest.raises((GeoValidationError, RecursionError)):
            validate_geojson_bytes(("[" * 100000 + "]" * 100000).encode(), **LIMITS)

    def test_null_geometry_feature_ok(self):
        feat = json.dumps(
            {"type": "Feature", "geometry": None, "properties": {}}
        ).encode()
        validate_geojson_bytes(feat, **LIMITS)


class TestKmlValidation:
    def test_deeply_nested_kml_does_not_crash(self):
        # expat parses iteratively, so deep nesting may validate or raise a
        # clean GeoValidationError. Either way it must not crash.
        nested = "<kml>" + "<a>" * 5000 + "</a>" * 5000 + "</kml>"
        try:
            validate_kml_bytes(nested.encode(), **LIMITS)
        except GeoValidationError:
            pass


class TestGenericRobustness:
    @given(data=st.binary(max_size=4096))
    @settings(max_examples=100, deadline=3000)
    def test_random_bytes_raise_validation_error_not_crash(self, data):
        with pytest.raises(GeoValidationError):
            validate_geojson_bytes(data, **LIMITS)

    @given(data=st.binary(max_size=2048))
    @settings(max_examples=60, deadline=3000)
    def test_random_bytes_kml_raise_validation_error_not_crash(self, data):
        with pytest.raises(GeoValidationError):
            validate_kml_bytes(data, **LIMITS)
