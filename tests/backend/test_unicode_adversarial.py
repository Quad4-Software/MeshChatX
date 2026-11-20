# SPDX-License-Identifier: 0BSD
"""Unicode adversarial: hostile names through contacts DB roundtrip and search."""

import unicodedata

import pytest

HOSTILE_NAMES = [
    "admin",  # baseline
    "\u0430dmin",  # Cyrillic-a homoglyph
    "adm\u0456n",  # Cyrillic-i homoglyph
    "\u202enimda\u202c",  # RLO visually reverses text
    "adm\u200bin",  # zero-width space
    "adm\u200din\u200c",  # ZWNJ/ZWJ
    "a\u0301dmin",  # combining acute (NFD form of á)
    "\U0001f600\U0001f525\U0001f4af",  # emoji only
    "x" * 1000,  # very long name
    "name\x00suffix",  # embedded NUL
    "\U0001d4d0dmin",  # mathematical bold homoglyph
    "adm\u0131n",  # dotless-i homoglyph
    "\u202e\u202d",  # lone directionals
]


class TestContactUnicodeRoundtrip:
    def _add(self, db, name, ident):
        db.contacts.add_contact(name, ident, lxmf_address="ab" * 16)

    def _by_name(self, db, name):
        return [r for r in db.contacts.get_contacts() if r["name"] == name]

    @pytest.mark.parametrize("name", HOSTILE_NAMES)
    def test_roundtrip_exact(self, db, name):
        ident = name.encode("utf-8", errors="ignore").hex().ljust(32, "0")[:32]
        self._add(db, name, ident)
        rows = self._by_name(db, name)
        assert len(rows) == 1
        assert rows[0]["name"] == name  # byte-exact roundtrip

    def test_nfc_nfd_names_are_distinct_rows(self, db):
        nfc = "\u00e1dmin"  # ádmin (composed)
        nfd = "a\u0301dmin"  # ádmin (decomposed)
        assert nfc != nfd
        assert unicodedata.normalize("NFC", nfc) == unicodedata.normalize("NFC", nfd)
        self._add(db, nfc, "a" * 32)
        self._add(db, nfd, "b" * 32)
        names = [r["name"] for r in db.contacts.get_contacts()]
        # DB stores both byte-distinct names; no silent normalization merge.
        assert nfc in names and nfd in names

    def test_search_matches_literal_not_homoglyph(self, db):
        self._add(db, "\u0430dmin", "a" * 32)  # Cyrillic a
        self._add(db, "admin", "b" * 32)  # Latin a
        hits = db.contacts.get_contacts(search="admin")
        names = [r["name"] for r in hits]
        assert "admin" in names
        # Cyrillic- spoof must NOT be returned by a Latin query.
        assert "\u0430dmin" not in names

    def test_surrogate_name_handled(self, db):
        name = "bad\ud800name"  # lone surrogate — cannot encode to UTF-8
        try:
            self._add(db, name, "c" * 32)
        except (UnicodeEncodeError, UnicodeError):
            return  # clean rejection is acceptable
        rows = self._by_name(db, name)
        assert rows == [] or rows[0]["name"] == name
