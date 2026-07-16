# SPDX-License-Identifier: 0BSD

import os

import pytest

from meshchatx.src.backend.interface_module_store import (
    delete_interface_module,
    install_interface_module,
    list_interface_modules,
    sanitize_interface_module_stem,
    validate_interface_module_source,
)

_VALID_SRC = b"""# example
class ExampleInterface:
    pass

interface_class = ExampleInterface
"""


def test_sanitize_interface_module_stem():
    assert sanitize_interface_module_stem("WeaveInterface.py") == "WeaveInterface"
    assert sanitize_interface_module_stem("WeaveInterface") == "WeaveInterface"
    assert sanitize_interface_module_stem("../evil.py") is None
    assert sanitize_interface_module_stem("bad-name.py") is None
    assert sanitize_interface_module_stem("") is None


def test_validate_interface_module_source_requires_interface_class():
    assert validate_interface_module_source(b"class Foo: pass") is not None
    assert validate_interface_module_source(_VALID_SRC) is None
    assert validate_interface_module_source(b"") is not None
    assert validate_interface_module_source(b"\x00interface_class") is not None


def test_install_list_delete_interface_module(tmp_path):
    config_dir = tmp_path / "reticulum"
    config_dir.mkdir()
    result = install_interface_module(
        str(config_dir),
        filename="ExampleInterface.py",
        data=_VALID_SRC,
    )
    assert result["type"] == "ExampleInterface"
    assert os.path.isfile(result["path"])
    listed = list_interface_modules(str(config_dir))
    assert listed["interfacepath"].endswith("interfaces")
    assert any(m["type"] == "ExampleInterface" for m in listed["modules"])
    with pytest.raises(ValueError, match="already exists"):
        install_interface_module(
            str(config_dir),
            filename="ExampleInterface.py",
            data=_VALID_SRC,
            overwrite=False,
        )
    install_interface_module(
        str(config_dir),
        filename="ExampleInterface.py",
        data=_VALID_SRC + b"\n# updated\n",
        overwrite=True,
    )
    deleted = delete_interface_module(str(config_dir), "ExampleInterface")
    assert deleted["filename"] == "ExampleInterface.py"
    assert not os.path.exists(os.path.join(str(config_dir), "interfaces", "ExampleInterface.py"))
