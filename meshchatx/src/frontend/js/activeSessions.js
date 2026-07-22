// SPDX-License-Identifier: 0BSD

/**
 * Predict whether the multi-session warning toast should fire.
 * Mirrors meshchatx.src.backend.active_sessions.should_warn_multi_session.
 */
export function shouldWarnMultiSession(count, warningEnabled) {
    const active = Number(count);
    if (!Number.isFinite(active)) {
        return false;
    }
    return warningEnabled !== false && active >= 2;
}

/**
 * Fire at most once per multi-session episode (count rises to 2+).
 * Resets when the count drops below 2 so a later episode can warn again.
 */
export function shouldShowMultiSessionToast(count, warningEnabled, alreadyWarned) {
    const shouldWarn = shouldWarnMultiSession(count, warningEnabled);
    if (!shouldWarn) {
        return { show: false, warned: false };
    }
    if (alreadyWarned) {
        return { show: false, warned: true };
    }
    return { show: true, warned: true };
}
