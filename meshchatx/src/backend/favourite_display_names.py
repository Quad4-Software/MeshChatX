"""Shared favourite display-name sentinels that must not clobber stored names."""

# Keep in sync with meshchatx/src/frontend/js/nomadUnknownNodeName.js
UNKNOWN_FAVOURITE_NAMES = frozenset(
    {
        "",
        "Unknown Node",
        "Anonymous Node",
        "Unbekannter Knoten",
        "Nodo desconocido",
        "Tuntematon solmu",
        "Noeud inconnu",
        "Nodo Sconosciuto",
        "Onbekende knoop",
        "Неизвестный узел",
        "未知节点",
    },
)


def is_unknown_favourite_display_name(name) -> bool:
    """Return True when ``name`` is empty or a known unknown-node placeholder."""
    if not isinstance(name, str):
        return True
    return name.strip() in UNKNOWN_FAVOURITE_NAMES
