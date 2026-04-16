# SPDX-License-Identifier: 0BSD

import struct
import time

from RNS.vendor import umsgpack


class Sensor:
    SID_NONE = 0x00
    SID_TIME = 0x01
    SID_LOCATION = 0x02
    SID_PRESSURE = 0x03
    SID_BATTERY = 0x04
    SID_PHYSICAL_LINK = 0x05
    SID_ACCELERATION = 0x06
    SID_TEMPERATURE = 0x07
    SID_HUMIDITY = 0x08
    SID_MAGNETIC_FIELD = 0x09
    SID_AMBIENT_LIGHT = 0x0A
    SID_GRAVITY = 0x0B
    SID_ANGULAR_VELOCITY = 0x0C
    SID_PROXIMITY = 0x0E
    SID_INFORMATION = 0x0F
    SID_RECEIVED = 0x10
    SID_POWER_CONSUMPTION = 0x11
    SID_POWER_PRODUCTION = 0x12
    SID_PROCESSOR = 0x13
    SID_RAM = 0x14
    SID_NVM = 0x15
    SID_TANK = 0x16
    SID_FUEL = 0x17
    SID_RNS_TRANSPORT = 0x19
    SID_LXMF_PROPAGATION = 0x18
    SID_CONNECTION_MAP = 0x1A
    SID_CUSTOM = 0xFF


class Telemeter:
    @staticmethod
    def unpack_location(packed):
        try:
            if packed is None:
                return None
            return {
                "latitude": struct.unpack("!i", packed[0])[0] / 1e6,
                "longitude": struct.unpack("!i", packed[1])[0] / 1e6,
                "altitude": struct.unpack("!i", packed[2])[0] / 1e2,
                "speed": struct.unpack("!I", packed[3])[0] / 1e2,
                "bearing": struct.unpack("!i", packed[4])[0] / 1e2,
                "accuracy": struct.unpack("!H", packed[5])[0] / 1e2,
                "last_update": packed[6],
            }
        except Exception:
            return None

    @staticmethod
    def pack_location(
        latitude,
        longitude,
        altitude=0,
        speed=0,
        bearing=0,
        accuracy=0,
        last_update=None,
    ):
        try:
            return [
                struct.pack("!i", int(round(latitude * 1e6))),
                struct.pack("!i", int(round(longitude * 1e6))),
                struct.pack("!i", int(round(altitude * 1e2))),
                struct.pack("!I", int(round(speed * 1e2))),
                struct.pack("!i", int(round(bearing * 1e2))),
                struct.pack("!H", int(round(accuracy * 1e2))),
                int(last_update) if last_update is not None else int(time.time()),
            ]
        except Exception:
            return None

    @staticmethod
    def from_packed(packed):
        try:
            p = umsgpack.unpackb(packed)
            res = {}
            if Sensor.SID_TIME in p:
                res["time"] = {"utc": p[Sensor.SID_TIME]}
            if Sensor.SID_LOCATION in p:
                res["location"] = Telemeter.unpack_location(p[Sensor.SID_LOCATION])
            if Sensor.SID_PHYSICAL_LINK in p:
                pl = p[Sensor.SID_PHYSICAL_LINK]
                if isinstance(pl, (list, tuple)) and len(pl) >= 3:
                    res["physical_link"] = {"rssi": pl[0], "snr": pl[1], "q": pl[2]}
            if Sensor.SID_BATTERY in p:
                b = p[Sensor.SID_BATTERY]
                if isinstance(b, (list, tuple)) and len(b) >= 2:
                    res["battery"] = {"charge_percent": b[0], "charging": b[1]}
            # Add other sensors as needed
            return res
        except Exception:
            return None

    @staticmethod
    def pack(time_utc=None, location=None, battery=None, physical_link=None):
        p = {}
        p[Sensor.SID_TIME] = int(time_utc if time_utc is not None else time.time())
        if location:
            p[Sensor.SID_LOCATION] = Telemeter.pack_location(**location)
        if battery:
            # battery should be [charge_percent, charging]
            p[Sensor.SID_BATTERY] = [battery["charge_percent"], battery["charging"]]
        if physical_link:
            # physical_link should be [rssi, snr, q]
            p[Sensor.SID_PHYSICAL_LINK] = [
                physical_link["rssi"],
                physical_link["snr"],
                physical_link["q"],
            ]
        return umsgpack.packb(p)
