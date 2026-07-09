# SPDX-License-Identifier: MIT

# https://github.com/markqvist/Sideband/blob/e515889e210037f881c201e0d627a7b09a48eb69/sbapp/sideband/sense.py#L11
class SidebandCommands:
    PLUGIN_COMMAND = 0x00
    TELEMETRY_REQUEST = 0x01
    PING = 0x02
    ECHO = 0x03
    SIGNAL_REPORT = 0x04
