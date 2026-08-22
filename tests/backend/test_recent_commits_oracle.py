# SPDX-License-Identifier: 0BSD

"""Adversarial oracle and fuzz tests for recent fetch_reticulum_manual and rnstatus changes."""

from __future__ import annotations

import importlib.util
import io
import json
import sys
import zipfile
from pathlib import Path

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

_REPO = Path(__file__).resolve().parents[2]
_FETCH = _REPO / "scripts" / "build" / "fetch_reticulum_manual.py"


def _load_fetch(name: str):
    spec = importlib.util.spec_from_file_location(name, _FETCH)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


@pytest.fixture(scope="module")
def fetch():
    return _load_fetch("fetch_reticulum_manual_oracle")


def test_bootstrap_config_rejects_host_newline_injection(fetch, tmp_path):
    config_path = tmp_path / "config"
    fetch._write_bootstrap_config(
        config_path,
        [fetch.TcpBootstrap(name="x", host="evil.com\nenabled = yes", port=4242)],
    )
    text = config_path.read_text(encoding="utf-8")
    assert "target_host" not in text
    assert "enabled = yes" not in text


@pytest.mark.parametrize(
    "host",
    [
        "good.example.test",
        "200:73eb:2e4:14be:aac7:90b3:784b:71a3",
        "10.0.0.1",
    ],
)
def test_parse_mcx_bootstraps_accepts_valid_hosts(fetch, host):
    rows = fetch._parse_mcx_tcp_bootstraps(
        {
            "interfaces": [
                {
                    "name": "ok",
                    "type": "tcp",
                    "network": "clearnet",
                    "status": "online",
                    "host": host,
                    "port": 4242,
                },
            ],
        },
    )
    assert len(rows) == 1
    assert rows[0].host == host


@pytest.mark.parametrize(
    "host",
    [
        "evil\nfoo",
        "evil\rfoo",
        "evil=foo",
        "evil\tfoo",
        "",
        "   ",
    ],
)
def test_parse_mcx_bootstraps_rejects_host_injection_chars(fetch, host):
    rows = fetch._parse_mcx_tcp_bootstraps(
        {
            "interfaces": [
                {
                    "name": "bad",
                    "type": "tcp",
                    "network": "clearnet",
                    "status": "online",
                    "host": host,
                    "port": 4242,
                },
            ],
        },
    )
    assert rows == []


@pytest.mark.parametrize("port", [-1, 0, 65536, 99999])
def test_parse_mcx_bootstraps_rejects_invalid_ports(fetch, port):
    rows = fetch._parse_mcx_tcp_bootstraps(
        {
            "interfaces": [
                {
                    "name": "bad-port",
                    "type": "tcp",
                    "network": "clearnet",
                    "status": "online",
                    "host": "node.example.test",
                    "port": port,
                },
            ],
        },
    )
    assert rows == []


@settings(max_examples=80, deadline=None)
@given(
    host=st.text(
        min_size=1,
        max_size=64,
        alphabet=st.characters(
            blacklist_characters="\r\n\t=", blacklist_categories=("Cs",)
        ),
    ).filter(lambda value: value.strip()),
    port=st.integers(min_value=1, max_value=65535),
)
def test_parse_mcx_bootstraps_host_port_oracle(fetch, host, port):
    rows = fetch._parse_mcx_tcp_bootstraps(
        {
            "interfaces": [
                {
                    "name": "fuzz",
                    "type": "tcp",
                    "network": "clearnet",
                    "status": "online",
                    "host": host,
                    "port": port,
                },
            ],
        },
    )
    assert len(rows) == 1
    assert rows[0].host == fetch._sanitize_target_host(host)
    assert rows[0].port == port


@settings(
    max_examples=60,
    deadline=None,
    suppress_health_check=[__import__("hypothesis").HealthCheck.filter_too_much],
)
@given(
    host=st.text(min_size=1, max_size=32).filter(
        lambda value: any(ch in value for ch in "\r\n\t=") or not value.strip(),
    ),
    port=st.one_of(
        st.integers(max_value=0),
        st.integers(min_value=65536, max_value=100_000),
    ),
)
def test_parse_mcx_bootstraps_rejects_hostile_rows(fetch, host, port):
    rows = fetch._parse_mcx_tcp_bootstraps(
        {
            "interfaces": [
                {
                    "name": "fuzz",
                    "type": "tcp",
                    "network": "clearnet",
                    "status": "online",
                    "host": host,
                    "port": port,
                },
            ],
        },
    )
    assert rows == []


def test_zip_extract_blocks_parent_traversal(fetch, tmp_path):
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as archive:
        archive.writestr("repo/docs/manual/index.html", b"<html>ok</html>")
        archive.writestr("repo/docs/../../escape.txt", b"pwned")
    buf.seek(0)
    zf, prefix = fetch._resolve_docs_root(buf.read())
    try:
        extracted, _skipped = fetch._extract(zf, prefix, tmp_path)
        assert extracted == 1
        assert not (tmp_path / "escape.txt").exists()
        assert (tmp_path / "manual" / "index.html").is_file()
    finally:
        zf.close()


@pytest.mark.parametrize(
    "url",
    [
        "https://meshchatx.com.evil.com/api",
        "https://evil.com/meshchatx.com",
        "https://meshchatx.com@evil.com/x",
        "http://meshchatx.com/api",
    ],
)
def test_mcx_interfaces_url_rejects_untrusted_origins(fetch, url):
    with pytest.raises(ValueError):
        fetch._validate_mcx_interfaces_url(url)


def test_mcx_interfaces_url_accepts_official_endpoint(fetch):
    assert (
        fetch._validate_mcx_interfaces_url("https://meshchatx.com/api/mcx-interfaces")
        == "https://meshchatx.com/api/mcx-interfaces"
    )


def test_traffic_totals_data_share_oracle():
    from meshchatx.src.backend.rnstatus_handler import _format_traffic_totals

    stats = {
        "rxs": 100,
        "txs": 200,
        "prxs": 10,
        "arxs": 20,
        "ptxs": 30,
        "atxs": 40,
    }
    totals = _format_traffic_totals(stats)
    assert totals is not None
    assert totals["data_rx_pct"] == 70
    assert totals["data_tx_pct"] == 65


@settings(max_examples=80, deadline=None)
@given(
    rxs=st.floats(
        min_value=1.0, max_value=1_000_000.0, allow_nan=False, allow_infinity=False
    ),
    txs=st.floats(
        min_value=1.0, max_value=1_000_000.0, allow_nan=False, allow_infinity=False
    ),
    prxs=st.floats(
        min_value=0.0, max_value=500_000.0, allow_nan=False, allow_infinity=False
    ),
    arxs=st.floats(
        min_value=0.0, max_value=500_000.0, allow_nan=False, allow_infinity=False
    ),
    ptxs=st.floats(
        min_value=0.0, max_value=500_000.0, allow_nan=False, allow_infinity=False
    ),
    atxs=st.floats(
        min_value=0.0, max_value=500_000.0, allow_nan=False, allow_infinity=False
    ),
)
def test_traffic_totals_data_share_fuzz_oracle(rxs, txs, prxs, arxs, ptxs, atxs):
    from meshchatx.src.backend.rnstatus_handler import _format_traffic_totals

    stats = {
        "rxs": rxs,
        "txs": txs,
        "prxs": min(prxs, rxs),
        "arxs": min(arxs, max(0.0, rxs - min(prxs, rxs))),
        "ptxs": min(ptxs, txs),
        "atxs": min(atxs, max(0.0, txs - min(ptxs, txs))),
    }
    totals = _format_traffic_totals(stats)
    assert totals is not None
    expected_rx = int(
        min(
            100.0,
            max(0.0, (rxs - stats["prxs"] - stats["arxs"]) / rxs) * 100.0,
        ),
    )
    expected_tx = int(
        min(
            100.0,
            max(0.0, (txs - stats["ptxs"] - stats["atxs"]) / txs) * 100.0,
        ),
    )
    if expected_rx > 0:
        assert totals["data_rx_pct"] == expected_rx
    else:
        assert "data_rx_pct" not in totals
    if expected_tx > 0:
        assert totals["data_tx_pct"] == expected_tx
    else:
        assert "data_tx_pct" not in totals


@settings(max_examples=60, deadline=None)
@given(
    part=st.floats(
        min_value=0.0, max_value=10_000.0, allow_nan=False, allow_infinity=False
    ),
    total=st.floats(
        min_value=0.0, max_value=10_000.0, allow_nan=False, allow_infinity=False
    ),
)
def test_flow_share_percent_oracle(part, total):
    from meshchatx.src.backend.rnstatus_handler import _flow_share_percent

    result = _flow_share_percent(part, total)
    if total <= 0 or part <= 0:
        assert result is None
    else:
        assert result == int(min(100.0, (part / total) * 100.0))


def test_should_skip_fetch_unknown_source_requires_refresh(fetch, tmp_path):
    dest = tmp_path / "out"
    manual = dest / "manual"
    manual.mkdir(parents=True)
    (manual / "index.html").write_text("<html>m</html>", encoding="utf-8")
    manifest = tmp_path / "manifest.json"
    manifest.write_text(
        json.dumps(
            {
                "source_url": "https://evil.example/reticulum.zip",
                "rns_version": "1.5.0",
            },
        ),
        encoding="utf-8",
    )
    skip, reason = fetch.should_skip_fetch(
        dest=dest,
        manifest_path=manifest,
        source_url=fetch.DEFAULT_RNS_SOURCE,
        pinned_rns="1.5.0",
        force=False,
    )
    assert skip is False
    assert "source changed" in reason
