// SPDX-License-Identifier: 0BSD

import { describe, expect, it, vi } from "vitest";
import {
    classifyGetUserMediaError,
    isBraveBrowser,
    isMeshChatXAndroid,
    isSecureMediaContext,
    promptMicrophoneAccess,
    queryMicrophonePermissionState,
} from "@/js/webAudioMicPermission";

describe("webAudioMicPermission", () => {
    it("treats undefined isSecureContext as allowed", () => {
        expect(isSecureMediaContext({})).toBe(true);
        expect(isSecureMediaContext({ isSecureContext: false })).toBe(false);
        expect(isSecureMediaContext({ isSecureContext: true })).toBe(true);
    });

    it("detects Android only when MeshChatXAndroid reports android", () => {
        expect(isMeshChatXAndroid({})).toBe(false);
        expect(isMeshChatXAndroid(null)).toBe(false);
        expect(
            isMeshChatXAndroid({
                MeshChatXAndroid: { getPlatform: () => "android" },
            })
        ).toBe(true);
        expect(
            isMeshChatXAndroid({
                MeshChatXAndroid: { getPlatform: () => "desktop" },
            })
        ).toBe(false);
    });

    it("detects Brave via navigator.brave or UA", () => {
        expect(isBraveBrowser({ brave: {} })).toBe(true);
        expect(isBraveBrowser({ userAgent: "Mozilla/5.0 Brave/1.70" })).toBe(true);
        expect(isBraveBrowser({ userAgent: "Mozilla/5.0 Chrome/120" })).toBe(false);
    });

    it("maps NotFoundError to prompt-blocked on Brave when permission is still prompt", () => {
        const err = new Error("missing");
        err.name = "NotFoundError";
        expect(classifyGetUserMediaError(err, { permissionState: "prompt", isBrave: true })).toBe(
            "call.microphone_prompt_blocked"
        );
        expect(classifyGetUserMediaError(err, { permissionState: "prompt", isBrave: false })).toBe(
            "call.microphone_permission_needed"
        );
        expect(classifyGetUserMediaError(err, { permissionState: "granted", isBrave: true })).toBe(
            "call.no_audio_input_found"
        );
        expect(classifyGetUserMediaError(err, { permissionState: null, isBrave: false })).toBe(
            "call.microphone_permission_needed"
        );
    });

    it("maps NotAllowedError to denied", () => {
        const err = new Error("no");
        err.name = "NotAllowedError";
        expect(classifyGetUserMediaError(err)).toBe("call.microphone_permission_denied");
    });

    it("promptMicrophoneAccess uses bare audio true then stops tracks", async () => {
        const stop = vi.fn();
        const getUserMedia = vi.fn().mockResolvedValue({ getTracks: () => [{ stop }] });
        await expect(promptMicrophoneAccess({ getUserMedia })).resolves.toBe(true);
        expect(getUserMedia).toHaveBeenCalledTimes(1);
        expect(getUserMedia.mock.calls[0][0]).toEqual({ audio: true });
        expect(stop).toHaveBeenCalled();
    });

    it("queryMicrophonePermissionState returns null when the API throws", async () => {
        const nav = {
            permissions: {
                query: vi.fn().mockRejectedValue(new TypeError("unsupported")),
            },
        };
        await expect(queryMicrophonePermissionState(nav)).resolves.toBe(null);
    });
});
