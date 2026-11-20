# SPDX-License-Identifier: 0BSD
"""Identity-switch None windows for the SQLite-unavailable middleware."""

from types import SimpleNamespace

from meshchatx.src.backend.http.db_availability import (
    exception_looks_like_missing_database,
)


class TestMissingContextDetection:
    def _app(self, database=None, message_handler=None, announce_manager=None):
        return SimpleNamespace(
            database=database,
            message_handler=message_handler,
            announce_manager=announce_manager,
        )

    def test_database_none(self):
        exc = AttributeError("'NoneType' object has no attribute 'announces'")
        assert exception_looks_like_missing_database(exc, self._app()) is True

    def test_message_handler_none(self):
        # Database mounted, message_handler still None during setup(): a
        # route touching app.message_handler.X must also map to retry.
        exc = AttributeError(
            "'NoneType' object has no attribute 'get_conversation_messages'"
        )
        app = self._app(database=object())
        assert exception_looks_like_missing_database(exc, app) is True

    def test_announce_manager_none(self):
        exc = AttributeError(
            "'NoneType' object has no attribute 'get_filtered_announces'"
        )
        app = self._app(database=object(), message_handler=object())
        assert exception_looks_like_missing_database(exc, app) is True

    def test_all_mounted_returns_false(self):
        exc = AttributeError("'NoneType' object has no attribute 'x'")
        app = self._app(
            database=object(), message_handler=object(), announce_manager=object()
        )
        assert exception_looks_like_missing_database(exc, app) is False

    def test_non_attribute_error_returns_false(self):
        assert (
            exception_looks_like_missing_database(
                ValueError("nonetype attribute"), self._app()
            )
            is False
        )
        assert (
            exception_looks_like_missing_database(
                AttributeError("some other bug"),
                self._app(
                    database=object(),
                    message_handler=object(),
                    announce_manager=object(),
                ),
            )
            is False
        )
