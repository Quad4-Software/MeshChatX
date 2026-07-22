"""Reticulum config discovery and shared-instance collision avoidance."""

from __future__ import annotations

import logging
import os
import re
from pathlib import Path

logger = logging.getLogger(__name__)

_SHARE_INSTANCE_RE = re.compile(
    r"(?im)^([ \t]*share_instance[ \t]*=[ \t]*)(\S+)([ \t]*)$",
)


def discover_user_reticulum_config_dir(
    home: str | None = None,
    *,
    system_dir: str = "/etc/reticulum",
) -> str | None:
    """Return an existing user/system Reticulum config dir, matching RNS order.

    Order:
    1. ``system_dir`` (default ``/etc/reticulum``) when ``config`` exists
    2. ``~/.config/reticulum`` when ``config`` exists
    3. ``~/.reticulum`` when ``config`` exists
    """
    user_home = home if home is not None else os.path.expanduser("~")
    candidates = [
        system_dir,
        os.path.join(user_home, ".config", "reticulum"),
        os.path.join(user_home, ".reticulum"),
    ]
    for path in candidates:
        if os.path.isdir(path) and os.path.isfile(os.path.join(path, "config")):
            return os.path.abspath(path)
    return None


def resolve_reticulum_config_dir(
    explicit: str | None,
    bot_config_path: str,
    *,
    environ: dict[str, str] | None = None,
    home: str | None = None,
    system_dir: str = "/etc/reticulum",
) -> str:
    """Resolve the Reticulum config directory for an LXMFy bot.

    Prefer an explicit path or ``LXMFY_RETICULUM_CONFIG_DIR``, then an existing
    user/system Reticulum config. Fall back to the bot config directory only
    when nothing else is available.
    """
    env = environ if environ is not None else os.environ
    if explicit:
        return os.path.abspath(os.path.expanduser(explicit))
    env_dir = env.get("LXMFY_RETICULUM_CONFIG_DIR")
    if env_dir:
        return os.path.abspath(os.path.expanduser(env_dir))
    discovered = discover_user_reticulum_config_dir(
        home=home,
        system_dir=system_dir,
    )
    if discovered:
        return discovered
    return os.path.abspath(bot_config_path)


def is_isolated_reticulum_dir(reticulum_config_dir: str, bot_config_path: str) -> bool:
    """True when the bot uses its own config path as the Reticulum config dir."""
    return os.path.abspath(reticulum_config_dir) == os.path.abspath(bot_config_path)


def ensure_isolated_share_instance_disabled(reticulum_config_dir: str) -> bool:
    """Ensure an isolated Reticulum config does not join the default shared instance.

    Different config directories derive different RPC authkeys. Sharing the default
    instance ports/sockets then fails with ``AuthenticationError: digest sent was
    rejected`` (the failure NomadNet/Columba show when an LXMFy bot collides with
    them). Isolated bot configs must set ``share_instance = No``.

    Returns:
        True if the config file was created or modified.
    """
    config_path = Path(reticulum_config_dir) / "config"
    os.makedirs(reticulum_config_dir, exist_ok=True)

    if not config_path.is_file():
        config_path.write_text(
            "[reticulum]\n"
            "enable_transport = Yes\n"
            "share_instance = No\n"
            "\n"
            "[logging]\n"
            "loglevel = 4\n"
            "\n"
            "[interfaces]\n",
            encoding="utf-8",
        )
        logger.info(
            "Created isolated Reticulum config with share_instance=No at %s",
            config_path,
        )
        return True

    text = config_path.read_text(encoding="utf-8")
    match = _SHARE_INSTANCE_RE.search(text)
    if match:
        current = match.group(2).strip().lower()
        if current in {"no", "false", "0"}:
            return False
        updated = _SHARE_INSTANCE_RE.sub(
            lambda m: f"{m.group(1)}No{m.group(3)}",
            text,
            count=1,
        )
        config_path.write_text(updated, encoding="utf-8")
        logger.warning(
            "Forced share_instance=No in %s to avoid RNS shared-instance "
            "RPC digest rejection with other apps (NomadNet, Columba, rnsd)",
            config_path,
        )
        return True

    if re.search(r"(?im)^\[reticulum\]\s*$", text):
        updated = re.sub(
            r"(?im)^(\[reticulum\]\s*)$",
            r"\1\nshare_instance = No",
            text,
            count=1,
        )
    else:
        updated = "[reticulum]\nshare_instance = No\n\n" + text
    config_path.write_text(updated, encoding="utf-8")
    logger.warning(
        "Added share_instance=No to %s to avoid RNS shared-instance "
        "RPC digest rejection with other apps (NomadNet, Columba, rnsd)",
        config_path,
    )
    return True
