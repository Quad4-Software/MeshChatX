# SPDX-License-Identifier: 0BSD

"""Sensitive exports and downloads must be POST so CSRF middleware applies."""


def _handler(app, method: str, path: str):
    for route in app.get_routes():
        if route.method == method and route.path == path:
            return route.handler
    return None


def test_sensitive_exports_are_post_not_get(mock_app):
    mutators = [
        "/api/v1/identities/export-all",
        "/api/v1/identity/backup/download",
        "/api/v1/identity/backup/base32",
        "/api/v1/bots/export",
        "/api/v1/database/backup/download",
        "/api/v1/database/backups/{filename}/download",
        "/api/v1/database/snapshots/{filename}/download",
        "/api/v1/maintenance/messages/export",
    ]
    for path in mutators:
        assert _handler(mock_app, "POST", path) is not None, path
        assert _handler(mock_app, "GET", path) is None, path
