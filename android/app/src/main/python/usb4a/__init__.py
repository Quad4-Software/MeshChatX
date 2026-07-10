# SPDX-License-Identifier: MIT
"""USB helpers for Android (Chaquopy build of usb4a).

Upstream usb4a expects Kivy ``PythonActivity`` via pyjnius. MeshChatX injects
the Activity context at startup and uses the Chaquopy jnius shim instead.
"""

__version__ = "0.3.0-meshchatx"
