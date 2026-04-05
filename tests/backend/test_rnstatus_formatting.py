from meshchatx.src.backend.rnstatus_handler import (
    fmt_packet_count,
    fmt_percentage,
    fmt_per_second,
)


def test_fmt_per_second_human_readable():
    assert fmt_per_second(0) == "0"
    assert fmt_per_second(0.4674843123420399) == "0.467"
    assert fmt_per_second(12.3456789) == "12.35"
    assert fmt_per_second(100.2) == "100.2"


def test_fmt_packet_count_integers():
    assert fmt_packet_count(1575.786604215814) == "1,576"
    assert fmt_packet_count(0) == "0"


def test_fmt_percentage():
    assert fmt_percentage(3.14159265) == "3.14"
    assert fmt_percentage(101.2) == "101.2"
    assert fmt_percentage(0.5) == "0.5"
