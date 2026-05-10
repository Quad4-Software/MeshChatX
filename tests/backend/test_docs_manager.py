# SPDX-License-Identifier: 0BSD

import os
import shutil
import zipfile
from unittest.mock import MagicMock

import pytest
from hypothesis import HealthCheck, given, settings
from hypothesis import strategies as st

from meshchatx.src.backend.docs_manager import DocsManager


@pytest.fixture
def temp_dirs(tmp_path):
    public_dir = tmp_path / "public"
    public_dir.mkdir()
    docs_dir = public_dir / "reticulum-docs"
    docs_dir.mkdir()
    return str(public_dir), str(docs_dir)


@pytest.fixture
def docs_manager(temp_dirs):
    public_dir, _ = temp_dirs
    config = MagicMock()
    return DocsManager(config, public_dir)


def test_docs_manager_initialization(docs_manager, temp_dirs):
    _, docs_dir = temp_dirs
    assert docs_manager.docs_dir == os.path.join(docs_dir, "current")
    assert os.path.exists(docs_dir)
    assert docs_manager.upload_status == "idle"


def test_docs_manager_storage_dir_fallback(tmp_path):
    public_dir = tmp_path / "public"
    public_dir.mkdir()
    storage_dir = tmp_path / "storage"
    storage_dir.mkdir()

    config = MagicMock()
    dm = DocsManager(config, str(public_dir), storage_dir=str(storage_dir))

    assert dm.docs_dir == os.path.join(str(storage_dir), "reticulum-docs", "current")
    assert dm.meshchatx_docs_dir == os.path.join(str(storage_dir), "meshchatx-docs")
    assert dm.bundled_docs_dir == os.path.join(
        str(public_dir),
        "reticulum-docs-bundled",
        "current",
    )
    assert os.path.exists(dm.docs_base_dir)
    assert os.path.exists(dm.meshchatx_docs_dir)


def test_has_bundled_docs_falls_back_to_public(tmp_path):
    public_dir = tmp_path / "public"
    public_dir.mkdir()
    storage_dir = tmp_path / "storage"
    storage_dir.mkdir()
    bundled = public_dir / "reticulum-docs-bundled" / "current"
    bundled.mkdir(parents=True)
    (bundled / "index.html").write_text("<html></html>")

    config = MagicMock()
    dm = DocsManager(config, str(public_dir), storage_dir=str(storage_dir))

    assert dm.has_bundled_docs() is True
    assert dm.has_user_docs() is False
    assert dm.has_docs() is True

    resolved = dm.find_docs_file("index.html")
    assert resolved == os.path.realpath(str(bundled / "index.html"))


def test_user_docs_take_precedence_over_bundled(tmp_path):
    public_dir = tmp_path / "public"
    public_dir.mkdir()
    storage_dir = tmp_path / "storage"
    storage_dir.mkdir()
    bundled = public_dir / "reticulum-docs-bundled" / "current"
    bundled.mkdir(parents=True)
    (bundled / "index.html").write_text("<html>bundled</html>")

    config = MagicMock()
    dm = DocsManager(config, str(public_dir), storage_dir=str(storage_dir))
    user_index = os.path.join(dm.docs_dir, "index.html")
    os.makedirs(dm.docs_dir, exist_ok=True)
    with open(user_index, "w") as f:
        f.write("<html>user</html>")

    resolved = dm.find_docs_file("index.html")
    assert resolved == os.path.realpath(user_index)


def test_find_docs_file_rejects_traversal(tmp_path):
    public_dir = tmp_path / "public"
    public_dir.mkdir()
    bundled = public_dir / "reticulum-docs-bundled" / "current"
    bundled.mkdir(parents=True)
    (bundled / "index.html").write_text("<html></html>")
    (tmp_path / "secret.txt").write_text("nope")

    config = MagicMock()
    dm = DocsManager(config, str(public_dir))

    assert dm.find_docs_file("../../secret.txt") is None
    assert dm.find_docs_file("..") is None
    assert dm.find_docs_file("missing.html") is None


def test_docs_manager_readonly_public_dir_handling(tmp_path):
    public_dir = tmp_path / "readonly_public"
    public_dir.mkdir()

    os.chmod(public_dir, 0o555)  # noqa: S103

    config = MagicMock()
    from unittest.mock import patch

    with patch("os.makedirs", side_effect=OSError("Read-only file system")):
        dm = DocsManager(config, str(public_dir))
        assert dm.last_error is not None
        assert (
            "Read-only file system" in dm.last_error
            or "Permission denied" in dm.last_error
        )

    os.chmod(public_dir, 0o755)  # noqa: S103


def test_has_docs(docs_manager, temp_dirs):
    _, docs_dir = temp_dirs
    assert docs_manager.has_docs() is False

    current_dir = os.path.join(docs_dir, "current")
    os.makedirs(current_dir, exist_ok=True)
    index_path = os.path.join(current_dir, "index.html")
    with open(index_path, "w") as f:
        f.write("<html></html>")

    assert docs_manager.has_docs() is True


def test_get_status_reports_bundled_and_user_flags(docs_manager):
    status = docs_manager.get_status()
    assert status["status"] == "idle"
    assert status["progress"] == 0
    assert status["has_docs"] is False
    assert status["has_bundled_docs"] is False
    assert status["has_user_docs"] is False


def test_upload_zip_extracts_and_switches_version(docs_manager):
    payload = _make_docs_zip(
        files={
            "reticulum_website-main/docs/index.html": "<html>uploaded</html>",
            "reticulum_website-main/docs/manual.html": "<html>manual</html>",
        },
    )

    assert docs_manager.upload_zip(payload, "v-test") is True
    assert docs_manager.upload_status == "completed"
    assert "v-test" in docs_manager.get_available_versions()
    resolved = docs_manager.find_docs_file("index.html")
    assert resolved is not None
    with open(resolved) as fh:
        assert "uploaded" in fh.read()


def test_clear_reticulum_docs_does_not_touch_bundled(tmp_path):
    public_dir = tmp_path / "public"
    public_dir.mkdir()
    storage_dir = tmp_path / "storage"
    storage_dir.mkdir()
    bundled = public_dir / "reticulum-docs-bundled" / "current"
    bundled.mkdir(parents=True)
    (bundled / "index.html").write_text("<html>bundled</html>")

    config = MagicMock()
    dm = DocsManager(config, str(public_dir), storage_dir=str(storage_dir))

    payload = _make_docs_zip(
        files={"reticulum_website-main/docs/index.html": "<html>uploaded</html>"},
    )
    dm.upload_zip(payload, "v1")
    assert dm.has_user_docs() is True

    assert dm.clear_reticulum_docs() is True
    assert dm.has_bundled_docs() is True


def test_export_reticulum_docs_returns_none_when_empty(tmp_path):
    public_dir = tmp_path / "public"
    public_dir.mkdir()
    config = MagicMock()
    dm = DocsManager(config, str(public_dir), storage_dir=str(tmp_path / "storage"))
    assert dm.export_reticulum_docs() is None


def test_export_reticulum_docs_uses_upload_compatible_layout(tmp_path):
    public_dir = tmp_path / "public"
    public_dir.mkdir()
    bundled = public_dir / "reticulum-docs-bundled" / "current"
    bundled.mkdir(parents=True)
    (bundled / "index.html").write_text("<html>bundled</html>")
    (bundled / "manual").mkdir()
    (bundled / "manual" / "index.html").write_text("<html>chapter</html>")

    config = MagicMock()
    dm = DocsManager(config, str(public_dir), storage_dir=str(tmp_path / "storage"))

    payload = dm.export_reticulum_docs(root_folder="reticulum_manual")
    assert payload is not None

    import io as _io

    with zipfile.ZipFile(_io.BytesIO(payload)) as zf:
        names = sorted(zf.namelist())
    assert "reticulum_manual/docs/index.html" in names
    assert "reticulum_manual/docs/manual/index.html" in names
    for n in names:
        assert n.startswith("reticulum_manual/docs/")


def test_export_reticulum_docs_round_trips_through_upload(tmp_path):
    public_dir = tmp_path / "public"
    public_dir.mkdir()
    bundled = public_dir / "reticulum-docs-bundled" / "current"
    bundled.mkdir(parents=True)
    (bundled / "index.html").write_text("<html>shared</html>")

    config = MagicMock()
    src = DocsManager(config, str(public_dir), storage_dir=str(tmp_path / "src"))
    payload = src.export_reticulum_docs()
    assert payload is not None

    other_public = tmp_path / "other_public"
    other_public.mkdir()
    other = DocsManager(
        config,
        str(other_public),
        storage_dir=str(tmp_path / "other_storage"),
    )
    assert other.upload_zip(payload, "shared-from-peer") is True
    assert "shared-from-peer" in other.get_available_versions()
    resolved = other.find_docs_file("index.html")
    assert resolved is not None
    with open(resolved) as fh:
        assert "shared" in fh.read()


def _make_docs_zip(files: dict[str, str]) -> bytes:
    import io

    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        for path, content in files.items():
            zf.writestr(path, content)
    return buf.getvalue()


def create_mock_zip(zip_path, file_list):
    with zipfile.ZipFile(zip_path, "w") as zf:
        for file_path in file_list:
            zf.writestr(file_path, "test content")


@settings(
    deadline=None,
    suppress_health_check=[
        HealthCheck.filter_too_much,
        HealthCheck.function_scoped_fixture,
    ],
)
@given(
    root_folder_name=st.text(min_size=1, max_size=50).filter(
        lambda x: "/" not in x and "\x00" not in x and x not in [".", ".."],
    ),
    docs_file=st.text(min_size=1, max_size=50).filter(
        lambda x: "/" not in x and "\x00" not in x,
    ),
)
def test_extract_docs_fuzzing(docs_manager, temp_dirs, root_folder_name, docs_file):
    _, docs_dir = temp_dirs
    zip_path = os.path.join(docs_dir, "test.zip")

    zip_files = [
        f"{root_folder_name}/",
        f"{root_folder_name}/docs/",
        f"{root_folder_name}/docs/{docs_file}",
    ]

    create_mock_zip(zip_path, zip_files)

    try:
        docs_manager._extract_docs(zip_path, "fuzz")
    except Exception:
        pass
    finally:
        if os.path.exists(zip_path):
            os.remove(zip_path)
        for item in os.listdir(docs_dir):
            item_path = os.path.join(docs_dir, item)
            if os.path.isdir(item_path):
                shutil.rmtree(item_path)
            else:
                os.remove(item_path)


def test_extract_docs_malformed_zip(docs_manager, temp_dirs):
    _, docs_dir = temp_dirs
    zip_path = os.path.join(docs_dir, "malformed.zip")

    create_mock_zip(zip_path, ["file_at_root.txt"])
    try:
        docs_manager._extract_docs(zip_path, "malformed-1")
    except (IndexError, Exception):
        pass
    finally:
        if os.path.exists(zip_path):
            os.remove(zip_path)

    create_mock_zip(zip_path, ["root/not_docs/file.txt"])
    try:
        docs_manager._extract_docs(zip_path, "malformed-2")
    except Exception:
        pass
    finally:
        if os.path.exists(zip_path):
            os.remove(zip_path)


def test_populate_meshchatx_docs_generates_index_html(tmp_path):
    public_dir = tmp_path / "public"
    public_dir.mkdir()
    docs_dir = tmp_path / "docs"
    docs_dir.mkdir()
    (docs_dir / "README.md").write_text("# Hello\nWorld")
    (docs_dir / "FAQ.md").write_text("# FAQ\nQ&A")

    config = MagicMock()
    dm = DocsManager(config, str(public_dir), project_root=str(tmp_path))
    dm.populate_meshchatx_docs()

    index_path = os.path.join(dm.meshchatx_docs_dir, "index.html")
    assert os.path.exists(index_path)
    content = open(index_path, encoding="utf-8").read()
    assert "MeshChatX Documentation" in content
    assert "README.html" in content
    assert "FAQ.html" in content


def test_get_doc_content_rejects_directory_path(tmp_path):
    public_dir = tmp_path / "public"
    public_dir.mkdir()
    config = MagicMock()
    dm = DocsManager(config, str(public_dir))

    # Ensure meshchatx_docs_dir exists as a directory
    os.makedirs(dm.meshchatx_docs_dir, exist_ok=True)

    # Passing "." should resolve to the directory itself, not a file
    assert dm.get_doc_content(".") is None
    assert dm.get_doc_content("..") is None
    assert dm.get_doc_content("") is None
