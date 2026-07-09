from meshchatx.src.backend.favourite_display_names import (
    UNKNOWN_FAVOURITE_NAMES,
    is_unknown_favourite_display_name,
)


def test_unknown_favourite_names_include_localized_placeholders():
    assert "" in UNKNOWN_FAVOURITE_NAMES
    assert "Unknown Node" in UNKNOWN_FAVOURITE_NAMES
    assert "Anonymous Node" in UNKNOWN_FAVOURITE_NAMES
    assert "Unbekannter Knoten" in UNKNOWN_FAVOURITE_NAMES
    assert "未知节点" in UNKNOWN_FAVOURITE_NAMES


def test_is_unknown_favourite_display_name():
    assert is_unknown_favourite_display_name(None) is True
    assert is_unknown_favourite_display_name("") is True
    assert is_unknown_favourite_display_name("  ") is True
    assert is_unknown_favourite_display_name("Unknown Node") is True
    assert is_unknown_favourite_display_name("Неизвестный узел") is True
    assert is_unknown_favourite_display_name("Real Node") is False
