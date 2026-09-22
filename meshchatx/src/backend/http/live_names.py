# SPDX-License-Identifier: 0BSD

"""Live meshchat name bindings for extracted HTTP and WS modules.

Free names in route and dispatch handlers resolve through meshchatx.meshchat
at use time so patch("meshchatx.meshchat.<symbol>") still applies.
"""

from __future__ import annotations

import types
from typing import Any


class LiveMeshchatName:
    """Resolve a meshchat module binding at use time so patches apply."""

    __slots__ = ("_name",)

    def __init__(self, name: str) -> None:
        object.__setattr__(self, "_name", name)

    def _resolve(self) -> Any:
        import meshchatx.meshchat as mc

        return getattr(mc, self._name)

    def __getattr__(self, item: str) -> Any:
        return getattr(self._resolve(), item)

    def __call__(self, *args: Any, **kwargs: Any) -> Any:
        return self._resolve()(*args, **kwargs)


def inject_meshchat_names(module_globals: dict[str, Any]) -> None:
    """Bind meshchat names into a module globals dict for free-variable lookups."""
    import meshchatx.meshchat as mc

    for key, value in mc.__dict__.items():
        if key.startswith("__"):
            continue
        if isinstance(value, type) and issubclass(value, BaseException):
            module_globals[key] = value
        elif (
            isinstance(value, types.ModuleType)
            or isinstance(value, type)
            or callable(value)
        ):
            module_globals[key] = LiveMeshchatName(key)
        else:
            module_globals[key] = value
