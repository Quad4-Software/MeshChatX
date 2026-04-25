# SPDX-License-Identifier: 0BSD

import re

import meshchatx


def test_meshchatx_version_is_semver_like():
    assert isinstance(meshchatx.__version__, str)
    assert re.match(r"^\d+\.\d+\.\d+", meshchatx.__version__)
