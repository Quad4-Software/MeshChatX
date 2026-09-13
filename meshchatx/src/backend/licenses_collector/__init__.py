# SPDX-License-Identifier: 0BSD
"""licenses_collector public API."""

from __future__ import annotations

# ruff: noqa: F401, F403, F405

from meshchatx.src.backend.licenses_collector.core import *  # noqa: F403

from meshchatx.src.backend.licenses_collector import core as _core

_repo_root = _core._repo_root
_license_from_metadata = _core._license_from_metadata
_author_from_metadata = _core._author_from_metadata
_dist_for_requirement_name = _core._dist_for_requirement_name
_collect_python_transitive = _core._collect_python_transitive
_python_roots_from_pyproject = _core._python_roots_from_pyproject
_bundled_vendor_license_row = _core._bundled_vendor_license_row
_bundled_lxmfy_license_row = _core._bundled_lxmfy_license_row
_bundled_rns_filesync_license_row = _core._bundled_rns_filesync_license_row
_bundled_embed_rows = _core._bundled_embed_rows
_merge_bundled_vendor_rows = _core._merge_bundled_vendor_rows
_merge_bundled_lxmfy = _core._merge_bundled_lxmfy
_collect_backend_licenses_live = _core._collect_backend_licenses_live
_load_embedded_backend_licenses = _core._load_embedded_backend_licenses
_license_from_package_json = _core._license_from_package_json
_author_from_package_json = _core._author_from_package_json
_workspace_root_npm_identity = _core._workspace_root_npm_identity
_filter_out_workspace_root_package = _core._filter_out_workspace_root_package
_try_pnpm_licenses = _core._try_pnpm_licenses
_flatten_pnpm_licenses_json = _core._flatten_pnpm_licenses_json
_embedded_data_paths = _core._embedded_data_paths
_load_embedded_frontend_licenses = _core._load_embedded_frontend_licenses
_ROOT_DIST_CANDIDATES = _core._ROOT_DIST_CANDIDATES
_DATA_SUBPATH = _core._DATA_SUBPATH
_FRONTEND_LICENSES_FILENAME = _core._FRONTEND_LICENSES_FILENAME
_BACKEND_LICENSES_FILENAME = _core._BACKEND_LICENSES_FILENAME
_THIRD_PARTY_NOTICES_FILENAME = _core._THIRD_PARTY_NOTICES_FILENAME
