# SPDX-License-Identifier: 0BSD
"""PyJNIus-compatible facade over Chaquopy's java module.

RNS, usb4a, and related Android serial/Bluetooth code import jnius.
Chaquopy does not ship pyjnius. Map the small surface those libraries need
onto Chaquopy's native Java bridge so RNode USB and classic Bluetooth work.
"""

from __future__ import annotations

JavaException = Exception

try:
    from java import cast as _java_cast
    from java import dynamic_proxy, jclass
except ImportError as exc:  # pragma: no cover - desktop import path
    raise ImportError("jnius Chaquopy shim requires the Chaquopy java module") from exc


def autoclass(class_name: str):
    """Return a Java class, matching pyjnius autoclass."""
    return jclass(class_name)


def cast(cls, obj):
    """Cast obj to cls, accepting a class name string like pyjnius."""
    if isinstance(cls, str):
        cls = jclass(cls)
    return _java_cast(cls, obj)


def java_method(_signature):
    """No-op decorator. Chaquopy dynamic proxies do not need JNI signatures."""

    def decorator(fn):
        return fn

    return decorator


class PythonJavaClass:
    """Base that rebinds subclasses onto java.dynamic_proxy interfaces.

    Subclasses set __javainterfaces__ to a list of Java interface names
    (dot or slash form). Instantiation switches the instance class bases so
    method implementations are visible to Java callers.
    """

    __javainterfaces__: list[str] = []
    __javacontext__ = "app"

    def __init__(self, *args, **kwargs):
        interfaces = list(getattr(self, "__javainterfaces__", []) or [])
        if not interfaces:
            return
        resolved = []
        for name in interfaces:
            jni_name = name.replace("/", ".")
            resolved.append(jclass(jni_name))
        proxy_base = dynamic_proxy(*resolved)
        self.__class__.__bases__ = (proxy_base, object)


__all__ = [
    "JavaException",
    "PythonJavaClass",
    "autoclass",
    "cast",
    "dynamic_proxy",
    "java_method",
    "jclass",
]
