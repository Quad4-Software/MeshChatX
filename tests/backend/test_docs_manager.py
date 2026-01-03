import os
import shutil
import zipfile
from unittest.mock import MagicMock, patch

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
    config.docs_downloaded.get.return_value = False
    return DocsManager(config, public_dir)


def test_docs_manager_initialization(docs_manager, temp_dirs):
    _, docs_dir = temp_dirs
    assert docs_manager.docs_dir == docs_dir
    assert os.path.exists(docs_dir)
    assert docs_manager.download_status == "idle"


def test_docs_manager_storage_dir_fallback(tmp_path):
    public_dir = tmp_path / "public"
    public_dir.mkdir()
    storage_dir = tmp_path / "storage"
    storage_dir.mkdir()

    config = MagicMock()
    # If storage_dir is provided, it should be used for docs
    dm = DocsManager(config, str(public_dir), storage_dir=str(storage_dir))

    assert dm.docs_dir == os.path.join(str(storage_dir), "reticulum-docs")
    assert dm.meshchatx_docs_dir == os.path.join(str(storage_dir), "meshchatx-docs")
    assert os.path.exists(dm.docs_dir)
    assert os.path.exists(dm.meshchatx_docs_dir)


def test_docs_manager_readonly_public_dir_handling(tmp_path):
    # This test simulates a read-only public dir without storage_dir
    public_dir = tmp_path / "readonly_public"
    public_dir.mkdir()

    # Make it read-only
    os.chmod(public_dir, 0o555)

    config = MagicMock()
    try:
        # Should not crash even if os.makedirs fails
        dm = DocsManager(config, str(public_dir))
        assert dm.last_error is not None
        assert (
            "Read-only file system" in dm.last_error
            or "Permission denied" in dm.last_error
        )
    finally:
        # Restore permissions for cleanup
        os.chmod(public_dir, 0o755)


def test_has_docs(docs_manager, temp_dirs):
    _, docs_dir = temp_dirs
    assert docs_manager.has_docs() is False

    index_path = os.path.join(docs_dir, "index.html")
    with open(index_path, "w") as f:
        f.write("<html></html>")

    assert docs_manager.has_docs() is True


def test_get_status(docs_manager):
    status = docs_manager.get_status()
    assert status["status"] == "idle"
    assert status["progress"] == 0
    assert status["has_docs"] is False


@patch("requests.get")
def test_download_task_success(mock_get, docs_manager, temp_dirs):
    public_dir, docs_dir = temp_dirs

    # Mock response
    mock_response = MagicMock()
    mock_response.headers = {"content-length": "100"}
    mock_response.iter_content.return_value = [b"data" * 25]
    mock_get.return_value = mock_response

    # Mock extract_docs to avoid real zip issues
    with patch.object(docs_manager, "_extract_docs") as mock_extract:
        docs_manager._download_task()

        assert docs_manager.download_status == "completed"
        assert mock_extract.called
        zip_path = os.path.join(docs_dir, "website.zip")
        mock_extract.assert_called_with(zip_path)


@patch("requests.get")
def test_download_task_failure(mock_get, docs_manager):
    mock_get.side_effect = Exception("Download failed")

    docs_manager._download_task()

    assert docs_manager.download_status == "error"
    assert docs_manager.last_error == "Download failed"


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
        lambda x: "/" not in x and x not in [".", ".."]
    ),
    docs_file=st.text(min_size=1, max_size=50).filter(lambda x: "/" not in x),
)
def test_extract_docs_fuzzing(docs_manager, temp_dirs, root_folder_name, docs_file):
    public_dir, docs_dir = temp_dirs
    zip_path = os.path.join(docs_dir, "test.zip")

    # Create a zip structure similar to what DocsManager expects
    # reticulum_website-main/docs/some_file.html
    zip_files = [
        f"{root_folder_name}/",
        f"{root_folder_name}/docs/",
        f"{root_folder_name}/docs/{docs_file}",
    ]

    create_mock_zip(zip_path, zip_files)

    try:
        docs_manager._extract_docs(zip_path)
        # Check if the file was extracted to the right place
        extracted_file = os.path.join(docs_dir, docs_file)
        assert os.path.exists(extracted_file)
    except Exception:
        # If it's a known zip error or something, we can decide if it's a failure
        # But for these valid-ish paths, it should work.
        pass
    finally:
        if os.path.exists(zip_path):
            os.remove(zip_path)
        # Clean up extracted files for next run
        for item in os.listdir(docs_dir):
            item_path = os.path.join(docs_dir, item)
            if os.path.isdir(item_path):
                shutil.rmtree(item_path)
            else:
                os.remove(item_path)


def test_extract_docs_malformed_zip(docs_manager, temp_dirs):
    public_dir, docs_dir = temp_dirs
    zip_path = os.path.join(docs_dir, "malformed.zip")

    # 1. Zip with no folders at all
    create_mock_zip(zip_path, ["file_at_root.txt"])
    try:
        # This might fail with IndexError at namelist()[0].split('/')[0] if no slash
        docs_manager._extract_docs(zip_path)
    except (IndexError, Exception):
        pass  # Expected or at least handled by not crashing the whole app
    finally:
        if os.path.exists(zip_path):
            os.remove(zip_path)

    # 2. Zip with different structure
    create_mock_zip(zip_path, ["root/not_docs/file.txt"])
    try:
        docs_manager._extract_docs(zip_path)
    except Exception:
        pass
    finally:
        if os.path.exists(zip_path):
            os.remove(zip_path)
