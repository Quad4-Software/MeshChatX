# SPDX-License-Identifier: MIT
"""Advertisement and GATT service helpers (from able)."""

from __future__ import annotations

import re
from collections import namedtuple


class Advertisement:
    AD = namedtuple("AD", ["ad_type", "data"])

    class ad_types:
        flags = 0x01
        complete_local_name = 0x09
        service_data = 0x16
        manufacturer_specific_data = 0xFF

    def __init__(self, data):
        self.data = data

    def __iter__(self):
        return Advertisement.parse(self.data)

    @classmethod
    def parse(cls, data):
        pos = 0
        while pos < len(data):
            length = data[pos]
            if length < 2:
                return
            try:
                ad_type = data[pos + 1]
            except IndexError:
                return
            next_pos = pos + length + 1
            if ad_type:
                segment = slice(pos + 2, next_pos)
                yield Advertisement.AD(ad_type, bytearray(data[segment]))
            pos = next_pos


class Services(dict):
    def search(self, pattern, flags=re.IGNORECASE):
        for characteristics in self.values():
            for uuid, characteristic in characteristics.items():
                if re.search(pattern, uuid, flags):
                    return characteristic
        return None
