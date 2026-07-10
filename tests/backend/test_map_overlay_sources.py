# SPDX-License-Identifier: 0BSD

import pytest

from meshchatx.src.backend.map_overlay_sources import (
    OverlaySourceParseError,
    parse_create_payload,
    parse_nomadnet_file_url,
    parse_rngit_repo_url,
)

HASH = "a" * 32


def test_parse_nomadnet_file_url_variants():
    spec = parse_nomadnet_file_url(f"{HASH}:/file/maps/layer.geojson")
    assert spec.kind == "nomadnet_file"
    assert spec.destination_hash == HASH
    assert spec.path_or_repo_path == "/file/maps/layer.geojson"

    spec2 = parse_nomadnet_file_url(f"nomadnet://{HASH}:/file/a.kml")
    assert spec2.path_or_repo_path == "/file/a.kml"


def test_parse_nomadnet_rejects_traversal():
    with pytest.raises(OverlaySourceParseError) as exc:
        parse_nomadnet_file_url(f"{HASH}:/file/../secret.geojson")
    assert exc.value.code == "path_traversal"


def test_parse_nomadnet_requires_file_prefix():
    with pytest.raises(OverlaySourceParseError) as exc:
        parse_nomadnet_file_url(f"{HASH}:/page/index.mu")
    assert exc.value.code == "not_file_path"


def test_parse_rngit_repo_url():
    dest, group, repo = parse_rngit_repo_url(f"rns://{HASH}/public/maps")
    assert dest == HASH
    assert group == "public"
    assert repo == "maps"


def test_parse_create_payload_nomadnet():
    specs = parse_create_payload(
        {
            "kind": "nomadnet_file",
            "url": f"{HASH}:/file/layer.kmz",
            "refresh_interval_seconds": 30,
        },
    )
    assert len(specs) == 1
    assert specs[0].refresh_interval_seconds == 60


def test_parse_create_payload_rngit_multi_path():
    specs = parse_create_payload(
        {
            "kind": "rngit_files",
            "url": f"rns://{HASH}/group/repo",
            "ref": "v1.2.3",
            "paths": ["a.geojson", "b/c.kml"],
        },
    )
    assert len(specs) == 2
    assert specs[0].ref == "v1.2.3"
    assert specs[0].path_or_repo_path == "a.geojson"
    assert specs[1].path_or_repo_path == "b/c.kml"


def test_parse_create_payload_rejects_bad_extension():
    with pytest.raises(OverlaySourceParseError) as exc:
        parse_create_payload(
            {
                "kind": "rngit_files",
                "url": f"rns://{HASH}/group/repo",
                "paths": ["readme.md"],
            },
        )
    assert exc.value.code == "unsupported_extension"


def test_parse_create_payload_rejects_invalid_hash():
    with pytest.raises(OverlaySourceParseError) as exc:
        parse_create_payload(
            {
                "kind": "nomadnet_file",
                "url": "zzzz:/file/a.geojson",
            },
        )
    assert exc.value.code == "invalid_destination_hash"


def test_parse_create_payload_rejects_bad_ref():
    with pytest.raises(OverlaySourceParseError):
        parse_create_payload(
            {
                "kind": "rngit_files",
                "url": f"rns://{HASH}/group/repo",
                "ref": "../evil",
                "paths": ["a.geojson"],
            },
        )
