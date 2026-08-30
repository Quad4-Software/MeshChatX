# SPDX-License-Identifier: 0BSD

import contextlib
import socket

import pytest

from meshchatx.src.backend.interface_port_check import (
    describe_port_conflict,
    is_port_in_use,
)


def _free_port(kind="tcp"):
    sock_type = socket.SOCK_STREAM if kind == "tcp" else socket.SOCK_DGRAM
    with contextlib.closing(socket.socket(socket.AF_INET, sock_type)) as sock:
        sock.bind(("127.0.0.1", 0))
        return sock.getsockname()[1]


def test_is_port_in_use_returns_false_for_unbound_port():
    port = _free_port("tcp")
    assert is_port_in_use("127.0.0.1", port, kind="tcp") is False


def test_is_port_in_use_returns_true_when_tcp_port_held():
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.bind(("127.0.0.1", 0))
    sock.listen(1)
    port = sock.getsockname()[1]
    try:
        assert is_port_in_use("127.0.0.1", port, kind="tcp") is True
    finally:
        sock.close()


def test_is_port_in_use_returns_true_when_udp_port_held():
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.bind(("127.0.0.1", 0))
    port = sock.getsockname()[1]
    try:
        assert is_port_in_use("127.0.0.1", port, kind="udp") is True
    finally:
        sock.close()


@pytest.mark.parametrize("port", [None, "", 0, "abc", -1, 70000])
def test_is_port_in_use_rejects_invalid_inputs(port):
    assert is_port_in_use("127.0.0.1", port) is False


def test_is_port_in_use_handles_wildcard_host():
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.bind(("0.0.0.0", 0))
    sock.listen(1)
    port = sock.getsockname()[1]
    try:
        assert is_port_in_use(None, port, kind="tcp") is True
        assert is_port_in_use("0.0.0.0", port, kind="tcp") is True
    finally:
        sock.close()


def test_is_port_in_use_handles_unresolvable_host():
    assert is_port_in_use("not-a-real-host-12345.invalid", 12345) is False


def test_describe_port_conflict_includes_port_and_host():
    msg = describe_port_conflict(
        "127.0.0.1",
        4242,
        kind="tcp",
        interface_name="MyIface",
    )
    assert "4242" in msg
    assert "127.0.0.1" in msg
    assert "MyIface" in msg
    assert "TCP" in msg


def test_describe_port_conflict_handles_invalid_port():
    msg = describe_port_conflict(None, "bogus", kind="udp")
    assert "invalid" in msg.lower()
    assert "UDP" in msg
