import random

from hypothesis import given, settings, strategies as st

from HTTPInterface import HDLC


def test_frame_wraps_with_flags():
    framed = HDLC.frame(b"abc")
    assert framed[0] == HDLC.FLAG
    assert framed[-1] == HDLC.FLAG
    assert bytes([HDLC.FLAG]) not in framed[1:-1]


def test_escape_flag_and_esc_inside_payload():
    payload = bytes([0x01, HDLC.FLAG, 0x02, HDLC.ESC, 0x03])
    framed = HDLC.frame(payload)
    assert bytes([HDLC.ESC, HDLC.FLAG ^ HDLC.ESC_MASK]) in framed
    assert bytes([HDLC.ESC, HDLC.ESC ^ HDLC.ESC_MASK]) in framed
    packets, rem = HDLC.deframe(framed, 4096)
    assert rem == b""
    assert packets == [payload]


def test_deframe_multiple_packets():
    wire = HDLC.frame(b"one") + HDLC.frame(b"two") + HDLC.frame(b"three")
    packets, rem = HDLC.deframe(wire, 4096)
    assert rem == b""
    assert packets == [b"one", b"two", b"three"]


def test_deframe_incomplete_returns_remainder():
    partial = HDLC.frame(b"complete") + bytes([HDLC.FLAG]) + b"incomplete"
    packets, rem = HDLC.deframe(partial, 4096)
    assert packets == [b"complete"]
    assert rem.startswith(bytes([HDLC.FLAG]))
    assert b"incomplete" in rem


def test_deframe_split_across_chunks():
    wire = HDLC.frame(b"split-me")
    mid = len(wire) // 2
    first, rem1 = HDLC.deframe(wire[:mid], 4096)
    assert first == []
    assert rem1 != b""
    second, rem2 = HDLC.deframe(rem1 + wire[mid:], 4096)
    assert second == [b"split-me"]
    assert rem2 == b""


def test_empty_frame_yields_empty_packet():
    packets, rem = HDLC.deframe(bytes([HDLC.FLAG, HDLC.FLAG]), 4096)
    assert packets == [b""]
    assert rem == b""


@given(st.binary(min_size=0, max_size=512))
@settings(max_examples=200, deadline=None)
def test_fuzz_roundtrip_single_packet(data):
    framed = HDLC.frame(data)
    packets, rem = HDLC.deframe(framed, max(len(data) + 16, 64))
    assert rem == b""
    assert packets == [data]


@given(st.lists(st.binary(min_size=0, max_size=128), min_size=1, max_size=20))
@settings(max_examples=100, deadline=None)
def test_fuzz_roundtrip_batch(packets_in):
    wire = b"".join(HDLC.frame(p) for p in packets_in)
    packets, rem = HDLC.deframe(wire, 4096)
    assert rem == b""
    assert packets == packets_in


@given(st.binary(min_size=1, max_size=256), st.integers(min_value=1, max_value=8))
@settings(max_examples=100, deadline=None)
def test_fuzz_chunked_reassembly(data, chunks):
    wire = HDLC.frame(data)
    remainder = b""
    out = []
    step = max(1, len(wire) // chunks)
    for i in range(0, len(wire), step):
        piece = remainder + wire[i : i + step]
        pkts, remainder = HDLC.deframe(piece, 4096)
        out.extend(pkts)
    if remainder:
        pkts, remainder = HDLC.deframe(remainder, 4096)
        out.extend(pkts)
    assert remainder == b""
    assert out == [data]


def test_random_noise_without_flags_still_recovers_frame():
    rng = random.Random(42)
    for _ in range(50):
        noise = bytearray()
        while len(noise) < rng.randint(0, 64):
            b = rng.getrandbits(8)
            if b not in (HDLC.FLAG, HDLC.ESC):
                noise.append(b)
        payload = bytes(rng.getrandbits(8) for _ in range(rng.randint(1, 80)))
        wire = bytes(noise) + HDLC.frame(payload)
        packets, rem = HDLC.deframe(wire, 4096)
        assert rem == b""
        assert packets == [payload]


def test_pipe_compatible_escape_constants():
    assert HDLC.FLAG == 0x7E
    assert HDLC.ESC == 0x7D
    assert HDLC.ESC_MASK == 0x20
