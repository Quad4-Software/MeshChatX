# SPDX-License-Identifier: 0BSD

import io
import json
import zipfile

import pytest

from meshchatx.src.backend.map_geo_sanitizer import (
    is_allowed_data_image_href,
    is_remote_href,
    sanitize_geo_bytes,
)
from meshchatx.src.backend.map_geo_validator import GeoValidationError

TINY_PNG = (
    b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01"
    b"\x08\x02\x00\x00\x00\x90wS\xde\x00\x00\x00\nIDATx\x9cc\xf8\x0f\x00"
    b"\x00\x01\x01\x00\x05\x18\xd8N\x00\x00\x00\x00IEND\xaeB`\x82"
)

TINY_PNG_DATA = (
    "data:image/png;base64,"
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNkYAAAAAYAAjCB0C8="
)


def _kmz(files: dict[str, bytes]) -> bytes:
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        for name, payload in files.items():
            zf.writestr(name, payload)
    return buf.getvalue()


def test_oracle_remote_href_is_remote():
    assert is_remote_href("https://evil.example/icon.png") is True
    assert is_remote_href("http://evil.example/x") is True
    assert is_remote_href("//cdn.example/x.png") is True
    assert is_remote_href("file:///etc/passwd") is True
    assert is_remote_href("javascript:alert(1)") is True
    assert is_remote_href("vbscript:msgbox(1)") is True
    assert is_remote_href("files/icon.png") is False
    assert is_remote_href(TINY_PNG_DATA) is False


def test_oracle_data_image_allowlist():
    assert is_allowed_data_image_href(TINY_PNG_DATA) is True
    assert is_allowed_data_image_href("data:text/html;base64,PHNjcmlwdD4=") is False
    assert is_allowed_data_image_href("data:image/svg+xml;base64,PHN2Zz4=") is False


def test_sanitize_kml_strips_remote_icon_keeps_placemark():
    kml = b"""<?xml version="1.0"?>
    <kml xmlns="http://www.opengis.net/kml/2.2"><Document>
      <Placemark><name>P</name>
        <Style><IconStyle><Icon><href>https://evil.example/i.png</href></Icon></IconStyle></Style>
        <Point><coordinates>1,2,0</coordinates></Point>
      </Placemark>
    </Document></kml>"""
    result = sanitize_geo_bytes(kml)
    assert result.format == "kml"
    assert result.feature_count == 1
    assert "remote_href" in result.stripped
    assert b"https://evil.example" not in result.data


def test_sanitize_kml_network_link_only_rejected():
    kml = b"""<?xml version="1.0"?>
    <kml xmlns="http://www.opengis.net/kml/2.2"><Document>
      <NetworkLink><Link><href>https://evil.example/layer.kml</href></Link></NetworkLink>
    </Document></kml>"""
    with pytest.raises(GeoValidationError) as exc:
        sanitize_geo_bytes(kml)
    assert exc.value.code == "remote_content"


def test_sanitize_kml_rejects_dtd():
    kml = b"""<?xml version="1.0"?>
    <!DOCTYPE kml [<!ENTITY xxe SYSTEM "file:///etc/passwd">]>
    <kml xmlns="http://www.opengis.net/kml/2.2"><Document>
      <Placemark><name>&xxe;</name>
        <Point><coordinates>1,2,0</coordinates></Point>
      </Placemark>
    </Document></kml>"""
    with pytest.raises(GeoValidationError) as exc:
        sanitize_geo_bytes(kml)
    assert exc.value.code == "dtd_forbidden"


def test_sanitize_kml_keeps_data_png_icon():
    kml = f"""<?xml version="1.0"?>
    <kml xmlns="http://www.opengis.net/kml/2.2"><Document>
      <Placemark><name>P</name>
        <Style><IconStyle><Icon><href>{TINY_PNG_DATA}</href></Icon></IconStyle></Style>
        <Point><coordinates>1,2,0</coordinates></Point>
      </Placemark>
    </Document></kml>""".encode()
    result = sanitize_geo_bytes(kml)
    assert result.feature_count == 1
    assert b"data:image/png" in result.data


def test_sanitize_kml_flattens_cdata_html_description():
    kml = b"""<?xml version="1.0" encoding="utf-8"?>
    <kml xmlns="http://www.opengis.net/kml/2.2"><Document>
      <Placemark><name>Leaking Tanks</name>
        <description><![CDATA[<h2>Hostile</h2><script>alert(1)</script>]]></description>
        <Point><coordinates>-117.99,33.78,0</coordinates></Point>
      </Placemark>
    </Document></kml>"""
    result = sanitize_geo_bytes(kml)
    assert result.feature_count == 1
    assert "html_description" in result.stripped
    lower = result.data.lower()
    assert b"<script" not in lower
    assert b"<h2" not in lower
    assert b"hostile" in lower


def test_sanitize_kmz_skips_unreferenced_svg_keeps_placemark():
    kml = b"""<?xml version="1.0"?>
    <kml xmlns="http://www.opengis.net/kml/2.2"><Document>
      <Placemark><Point><coordinates>1,2,0</coordinates></Point></Placemark>
    </Document></kml>"""
    data = _kmz({"doc.kml": kml, "icon.svg": b"<svg></svg>"})
    result = sanitize_geo_bytes(data)
    assert result.format == "kmz"
    assert result.feature_count == 1
    assert "skipped_kmz_entry" in result.stripped
    with zipfile.ZipFile(io.BytesIO(result.data)) as zf:
        names = [
            n.replace("\\", "/").lower() for n in zf.namelist() if not n.endswith("/")
        ]
        assert "doc.kml" in names
        assert "icon.svg" not in names


def test_sanitize_kmz_skips_arcgis_xsl_sidecar():
    kml = b"""<?xml version="1.0"?>
    <kml xmlns="http://www.opengis.net/kml/2.2"><Document>
      <Style><IconStyle><Icon><href>Layer0_Symbol.png</href></Icon></IconStyle></Style>
      <Placemark><name>ArcGIS Point</name>
        <styleUrl>#s</styleUrl>
        <Point><coordinates>1,2,0</coordinates></Point>
      </Placemark>
    </Document></kml>"""
    data = _kmz(
        {
            "doc.kml": kml,
            "F2E8A9CB2E0A446C9BCA87742DD683E5.xsl": (
                b"<?xml version='1.0'?>"
                b"<xsl:stylesheet xmlns:xsl='http://www.w3.org/1999/XSL/Transform' version='1.0'/>"
            ),
            "Layer0_Symbol.png": TINY_PNG,
        }
    )
    result = sanitize_geo_bytes(data)
    assert result.format == "kmz"
    assert result.feature_count == 1
    assert "skipped_kmz_entry" in result.stripped
    with zipfile.ZipFile(io.BytesIO(result.data)) as zf:
        names = [n.replace("\\", "/") for n in zf.namelist() if not n.endswith("/")]
        assert "doc.kml" in names
        assert "Layer0_Symbol.png" in names
        assert not any(n.lower().endswith(".xsl") for n in names)


def test_sanitize_kmz_keeps_zip_local_png():
    kml = b"""<?xml version="1.0"?>
    <kml xmlns="http://www.opengis.net/kml/2.2"><Document>
      <Placemark><name>Z</name>
        <Style><IconStyle><Icon><href>files/icon.png</href></Icon></IconStyle></Style>
        <Point><coordinates>1,2,0</coordinates></Point>
      </Placemark>
    </Document></kml>"""
    data = _kmz({"doc.kml": kml, "files/icon.png": TINY_PNG})
    result = sanitize_geo_bytes(data)
    assert result.format == "kmz"
    assert result.feature_count == 1
    with zipfile.ZipFile(io.BytesIO(result.data)) as zf:
        names = [n.replace("\\", "/") for n in zf.namelist() if not n.endswith("/")]
        assert "doc.kml" in names
        assert "files/icon.png" in names


def test_sanitize_kmz_path_traversal_rejected():
    data = _kmz({"../evil.kml": b"<kml></kml>"})
    with pytest.raises(GeoValidationError) as exc:
        sanitize_geo_bytes(data)
    assert exc.value.code in ("path_traversal", "kmz_missing_kml")


def test_sanitize_kml_strips_remote_groundoverlay():
    kml = b"""<?xml version="1.0"?>
    <kml xmlns="http://www.opengis.net/kml/2.2"><Document>
      <Placemark><name>P</name>
        <Point><coordinates>1,2,0</coordinates></Point>
      </Placemark>
      <GroundOverlay>
        <Icon><href>https://evil.example/overlay.png</href></Icon>
        <LatLonBox><north>1</north><south>0</south><east>1</east><west>0</west></LatLonBox>
      </GroundOverlay>
    </Document></kml>"""
    result = sanitize_geo_bytes(kml)
    assert result.feature_count == 1
    assert "remote_overlay" in result.stripped
    assert b"https://evil.example" not in result.data


def test_sanitize_geojson_strips_http_icon():
    payload = json.dumps(
        {
            "type": "FeatureCollection",
            "features": [
                {
                    "type": "Feature",
                    "properties": {
                        "name": "A",
                        "href": "https://evil.example/i.png",
                    },
                    "geometry": {"type": "Point", "coordinates": [1.0, 2.0]},
                },
            ],
        },
    ).encode()
    result = sanitize_geo_bytes(payload)
    obj = json.loads(result.data)
    assert "href" not in obj["features"][0]["properties"]
    assert obj["features"][0]["properties"]["name"] == "A"
    assert "remote_href" in result.stripped
