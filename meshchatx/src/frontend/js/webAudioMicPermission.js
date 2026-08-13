// SPDX-License-Identifier: 0BSD

/**
 * Browser microphone permission helpers for the LXST web audio bridge.
 *
 * Chromium and Brave only show a getUserMedia prompt from a user gesture,
 * on a secure context, and with unconstrained { audio: true } as the first
 * call. Processing flags or deviceId.exact before permission often yield
 * NotFoundError with no dialog, especially on Brave Shields and on
 * self-signed HTTPS origins the user clicked through.
 */

export const WEB_AUDIO_MIC_TOAST_KEY = "call-web-audio-mic";

export function isSecureMediaContext(win = globalThis) {
    return win?.isSecureContext !== false;
}

export function isBraveBrowser(nav = globalThis.navigator) {
    return Boolean(nav?.brave) || /Brave/i.test(nav?.userAgent || "");
}

export function isMeshChatXAndroid(win = globalThis) {
    return (
        Boolean(win?.MeshChatXAndroid) &&
        typeof win.MeshChatXAndroid.getPlatform === "function" &&
        win.MeshChatXAndroid.getPlatform() === "android"
    );
}

export async function queryMicrophonePermissionState(nav = globalThis.navigator) {
    try {
        const perms = nav?.permissions;
        if (!perms || typeof perms.query !== "function") {
            return null;
        }
        const status = await perms.query({ name: "microphone" });
        return status?.state || null;
    } catch {
        return null;
    }
}

export function classifyGetUserMediaError(error, { permissionState = null, isBrave = false } = {}) {
    const name = error?.name;
    if (name === "NotAllowedError" || name === "SecurityError") {
        return "call.microphone_permission_denied";
    }
    if (name === "NotFoundError" || name === "OverconstrainedError") {
        if (permissionState === "denied") {
            return "call.microphone_permission_denied";
        }
        if (permissionState === "granted") {
            return "call.no_audio_input_found";
        }
        if (isBrave) {
            return "call.microphone_prompt_blocked";
        }
        return "call.microphone_permission_needed";
    }
    return "call.web_audio_not_available";
}

export async function promptMicrophoneAccess(mediaDevices) {
    if (!mediaDevices || typeof mediaDevices.getUserMedia !== "function") {
        const err = new Error("navigator.mediaDevices is unavailable");
        err.name = "NotSupportedError";
        throw err;
    }
    const stream = await mediaDevices.getUserMedia({ audio: true });
    const tracks = typeof stream?.getTracks === "function" ? stream.getTracks() : [];
    tracks.forEach((track) => {
        try {
            track.stop();
        } catch {
            // ignore
        }
    });
    return true;
}

export async function promptMicrophoneAccessFromWindow(win = globalThis) {
    if (isMeshChatXAndroid(win)) {
        return true;
    }
    if (!isSecureMediaContext(win)) {
        const err = new Error("insecure context");
        err.name = "SecurityError";
        throw err;
    }
    const mediaDevices = win?.navigator?.mediaDevices;
    return promptMicrophoneAccess(mediaDevices);
}
