# SPDX-License-Identifier: 0BSD

"""Template-level oracles for CustomBotTemplate and icon appearance fields."""

from unittest.mock import MagicMock

import LXMF
import pytest

FIELD_ICON_APPEARANCE = LXMF.FIELD_ICON_APPEARANCE

from meshchatx.src.backend.bot_templates import (
    CustomBotTemplate,
    EchoBotTemplate,
    _pack_icon_field,
)


@pytest.fixture
def template_dirs(tmp_path):
    storage = tmp_path / "storage"
    cfg = tmp_path / "config"
    rns = tmp_path / "reticulum"
    for d in (storage, cfg, rns):
        d.mkdir()
    return str(storage), str(cfg), str(rns)


def test_pack_icon_field_normalizes_hex():
    field = _pack_icon_field(
        {"icon_name": "robot", "fg_color": "#aabbcc", "bg_color": "112233"}
    )
    assert FIELD_ICON_APPEARANCE in field
    icon_name, fg, bg = field[FIELD_ICON_APPEARANCE]
    assert icon_name == "robot"
    assert fg == b"\xaa\xbb\xcc"
    assert bg == b"\x11\x22\x33"


def test_pack_icon_field_rejects_malformed():
    assert _pack_icon_field(None) is None
    assert _pack_icon_field("robot") is None
    assert _pack_icon_field({"icon_name": "x", "fg_color": "zz"}) is None
    assert _pack_icon_field({"icon_name": "x"}) is None


def test_custom_bot_registers_commands_and_help(template_dirs):
    storage, cfg, rns = template_dirs
    bot = CustomBotTemplate(
        name="Custom",
        storage_path=storage,
        test_mode=True,
        config_path=cfg,
        reticulum_config_dir=rns,
        custom={
            "commands": [
                {"name": "joke", "response": "ha!"},
                {"name": "mood", "response": "good", "description": "d"},
            ],
            "welcome": "hello",
        },
        icon={"icon_name": "robot", "fg_color": "#aabbcc", "bg_color": "#112233"},
    )
    assert set(bot.bot.commands) >= {"joke", "mood", "help"}
    assert bot.icon_lxmf_field[FIELD_ICON_APPEARANCE][0] == "robot"


def test_custom_bot_command_replies_with_canned_text_and_icon(template_dirs):
    storage, cfg, rns = template_dirs
    bot = CustomBotTemplate(
        name="Custom",
        storage_path=storage,
        test_mode=True,
        config_path=cfg,
        reticulum_config_dir=rns,
        custom={"commands": [{"name": "joke", "response": "ha!"}]},
    )
    ctx = MagicMock()
    bot.bot.commands["joke"].callback(ctx)
    ctx.reply.assert_called_once_with("ha!", lxmf_fields=bot.icon_lxmf_field)

    ctx2 = MagicMock()
    bot.bot.commands["help"].callback(ctx2)
    text = ctx2.reply.call_args.args[0]
    assert "joke" in text


def test_custom_bot_help_listing_includes_user_defined_help(template_dirs):
    storage, cfg, rns = template_dirs
    bot = CustomBotTemplate(
        name="Custom",
        storage_path=storage,
        test_mode=True,
        config_path=cfg,
        reticulum_config_dir=rns,
        custom={"commands": [{"name": "help", "response": "ask me"}]},
    )
    ctx = MagicMock()
    bot.bot.commands["help"].callback(ctx)
    ctx.reply.assert_called_once_with("ask me", lxmf_fields=bot.icon_lxmf_field)


def test_echo_template_default_and_cleared_icon(template_dirs):
    storage, cfg, rns = template_dirs
    bot = EchoBotTemplate(
        name="E",
        storage_path=storage,
        test_mode=True,
        config_path=cfg,
        reticulum_config_dir=rns,
    )
    assert bot.icon_lxmf_field[FIELD_ICON_APPEARANCE][0] == "forum"

    storage2, cfg2, rns2 = template_dirs
    cleared = EchoBotTemplate(
        name="E2",
        storage_path=storage2,
        test_mode=True,
        config_path=cfg2,
        reticulum_config_dir=rns2,
        icon=None,
    )
    assert cleared.icon_lxmf_field is None

    custom = EchoBotTemplate(
        name="E3",
        storage_path=storage,
        test_mode=True,
        config_path=cfg,
        reticulum_config_dir=rns,
        icon={"icon_name": "alien", "fg_color": "#00ff00", "bg_color": "#000000"},
    )
    assert custom.icon_lxmf_field[FIELD_ICON_APPEARANCE][0] == "alien"
