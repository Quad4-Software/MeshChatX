# SPDX-License-Identifier: 0BSD

from meshchatx.src.backend import reticulum_config_guard as guard


def test_reticulum_config_has_required_sections(tmp_path):
    config_path = tmp_path / "config"
    config_path.write_text("[reticulum]\n", encoding="utf-8")
    assert guard.reticulum_config_has_required_sections(str(config_path)) is False

    config_path.write_text("[reticulum]\n[interfaces]\n", encoding="utf-8")
    assert guard.reticulum_config_has_required_sections(str(config_path)) is True


def test_reticulum_config_is_parseable_rejects_broken_configobj(tmp_path):
    config_path = tmp_path / "config"
    config_path.write_text(
        "[reticulum]\n[[broken\n[interfaces]\n",
        encoding="utf-8",
    )
    assert guard.reticulum_config_has_required_sections(str(config_path)) is True
    assert guard.reticulum_config_is_parseable(str(config_path)) is False


def test_backup_reticulum_config_file_creates_copy(tmp_path):
    config_path = tmp_path / "config"
    config_path.write_text("broken", encoding="utf-8")

    backup_path = guard.backup_reticulum_config_file(str(config_path))
    assert backup_path is not None
    assert ".corrupt." in backup_path
    assert open(backup_path, encoding="utf-8").read() == "broken"


def test_repair_unparseable_reticulum_config_rewrites_file(tmp_path):
    config_path = tmp_path / "config"
    config_path.write_text(
        "[reticulum]\n[[broken\n[interfaces]\n",
        encoding="utf-8",
    )
    written = []

    def write_default(path: str) -> None:
        written.append(path)
        with open(path, "w", encoding="utf-8") as handle:
            handle.write("[reticulum]\n[interfaces]\nfixed = true\n")

    assert (
        guard.repair_unparseable_reticulum_config(
            str(config_path),
            write_default=write_default,
        )
        is True
    )
    assert written == [str(config_path)]
    assert "fixed = true" in config_path.read_text(encoding="utf-8")


def test_repair_unparseable_reticulum_config_skips_valid_file(tmp_path):
    config_path = tmp_path / "config"
    config_path.write_text(
        """[reticulum]
share_instance = False

[interfaces]
""",
        encoding="utf-8",
    )

    assert (
        guard.repair_unparseable_reticulum_config(
            str(config_path),
            write_default=lambda _path: (_ for _ in ()).throw(
                AssertionError("should not write")
            ),
        )
        is False
    )
