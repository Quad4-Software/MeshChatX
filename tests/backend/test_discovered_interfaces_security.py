# SPDX-License-Identifier: 0BSD

"""Fuzz and security-style tests for discovered interface filtering and matching."""

import json

import pytest
from hypothesis import HealthCheck, given, settings
from hypothesis import strategies as st

from meshchatx.meshchat import ReticulumMeshChat


def _iface_dict(**kwargs):
    base = {
        "name": "tcp-client",
        "type": "TCPClientInterface",
        "reachable_on": "10.0.0.1",
        "port": 4242,
    }
    base.update(kwargs)
    return base


@pytest.mark.parametrize(
    "name,network_name,ifac_netname",
    [
        ("<script>alert(1)</script>", "n", "k"),
        ("n", "<img src=x onerror=alert(1)>", "k"),
        ("a" * 50_000, "b", "c"),
        ("javascript:void(0)", "x", "y"),
        ("'; DROP TABLE x; --", "1", "2"),
        ("\x00\x01hidden", "v", "w"),
        ("peer-\u202e\u2066evil", "10.0.0.2", "4242"),
    ],
)
def test_discovery_filter_candidates_preserves_strings(
    name, network_name, ifac_netname
):
    iface = _iface_dict(
        name=name,
        network_name=network_name,
        ifac_netname=ifac_netname,
    )
    c = ReticulumMeshChat.discovery_filter_candidates(iface)
    assert isinstance(c, list)
    assert all(isinstance(x, str) for x in c)
    blob = "\n".join(c)
    assert name in blob or network_name in blob or ifac_netname in blob


def test_filter_discovered_interfaces_long_names_and_scripts():
    ifaces = [
        _iface_dict(name="<script>iface</script>", reachable_on="10.0.0.1"),
        _iface_dict(name="ok-peer", reachable_on="10.0.0.2"),
    ]
    out = ReticulumMeshChat.filter_discovered_interfaces(ifaces, "10.0.*", "")
    assert len(out) == 2
    raw = json.dumps(out)
    assert "<script>" in raw


@settings(max_examples=120, deadline=None)
@given(
    name=st.text(max_size=3000),
    typ=st.text(max_size=64),
    host=st.text(max_size=256),
    port=st.one_of(st.integers(min_value=0, max_value=65535), st.text(max_size=8)),
    extra=st.dictionaries(
        keys=st.text(max_size=24, alphabet=st.characters(blacklist_categories=("Cs",))),
        values=st.one_of(
            st.text(max_size=200, alphabet=st.characters(blacklist_categories=("Cs",))),
            st.integers(min_value=-1000, max_value=100_000),
            st.none(),
        ),
        max_size=8,
    ),
)
def test_discovery_filter_candidates_never_raises(name, typ, host, port, extra):
    iface = {"name": name, "type": typ, "reachable_on": host, "port": port, **extra}
    c = ReticulumMeshChat.discovery_filter_candidates(iface)
    assert isinstance(c, list)
    for x in c:
        assert isinstance(x, str)


@settings(
    suppress_health_check=[HealthCheck.filter_too_much, HealthCheck.too_slow],
    max_examples=100,
    deadline=None,
)
@given(
    wl=st.lists(
        st.text(max_size=64, alphabet=st.characters(blacklist_categories=("Cs",))),
        max_size=12,
    ),
    bl=st.lists(
        st.text(max_size=64, alphabet=st.characters(blacklist_categories=("Cs",))),
        max_size=12,
    ),
    iface=st.builds(
        _iface_dict,
        name=st.text(
            max_size=128, alphabet=st.characters(blacklist_categories=("Cs",))
        ),
        reachable_on=st.sampled_from(
            ["10.0.0.1", "192.168.0.1", "peer-abc", "1.2.3.4"]
        ),
        port=st.integers(min_value=1, max_value=65535),
    ),
)
def test_matches_discovery_pattern_fuzzing(wl, bl, iface):
    patterns_wl = ",".join(wl) if wl else ""
    patterns_bl = ",".join(bl) if bl else ""
    ReticulumMeshChat.matches_discovery_pattern(
        ReticulumMeshChat.sanitize_discovery_patterns(patterns_wl),
        iface,
    )
    ReticulumMeshChat.matches_discovery_pattern(
        ReticulumMeshChat.sanitize_discovery_patterns(patterns_bl),
        iface,
    )


@settings(max_examples=80, deadline=None)
@given(
    interfaces=st.lists(
        st.builds(
            _iface_dict,
            name=st.text(
                max_size=500, alphabet=st.characters(blacklist_categories=("Cs",))
            ),
            reachable_on=st.text(
                max_size=80, alphabet=st.characters(blacklist_categories=("Cs",))
            ),
        ),
        max_size=24,
    ),
)
def test_filter_discovered_interfaces_list_fuzzing(interfaces):
    out = ReticulumMeshChat.filter_discovered_interfaces(
        interfaces,
        "",
        "",
    )
    assert isinstance(out, list)
    json.dumps(out)
