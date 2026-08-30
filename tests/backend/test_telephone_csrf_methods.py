# SPDX-License-Identifier: 0BSD

"""Telephone call control mutators must be POST so CSRF middleware applies."""


def _handler(app, method: str, path: str):
    for route in app.get_routes():
        if route.method == method and route.path == path:
            return route.handler
    return None


def test_telephone_call_mutators_are_post_not_get(mock_app):
    mutators = [
        "/api/v1/telephone/answer",
        "/api/v1/telephone/hangup",
        "/api/v1/telephone/send-to-voicemail",
        "/api/v1/telephone/mute-transmit",
        "/api/v1/telephone/unmute-transmit",
        "/api/v1/telephone/mute-receive",
        "/api/v1/telephone/unmute-receive",
        "/api/v1/telephone/ptt",
    ]
    for path in mutators:
        assert _handler(mock_app, "POST", path) is not None, path
        assert _handler(mock_app, "GET", path) is None, path

    assert (
        _handler(mock_app, "POST", "/api/v1/telephone/call/{identity_hash}") is not None
    )
    assert _handler(mock_app, "GET", "/api/v1/telephone/call/{identity_hash}") is None
    assert (
        _handler(
            mock_app,
            "POST",
            "/api/v1/telephone/switch-audio-profile/{profile_id}",
        )
        is not None
    )
    assert (
        _handler(mock_app, "GET", "/api/v1/telephone/switch-audio-profile/{profile_id}")
        is None
    )
    assert (
        _handler(mock_app, "POST", "/api/v1/telephone/switch-call-mode/{mode_id}")
        is not None
    )
    assert (
        _handler(mock_app, "GET", "/api/v1/telephone/switch-call-mode/{mode_id}")
        is None
    )
    assert _handler(mock_app, "GET", "/api/v1/telephone/call-modes") is not None
    assert _handler(mock_app, "POST", "/api/v1/telephone/call-modes") is None
