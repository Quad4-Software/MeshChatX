import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import NotificationSoundUtils from "../../meshchatx/src/frontend/js/NotificationSoundUtils";

describe("NotificationSoundUtils", () => {
    let audioInstances;
    let originalAudio;

    beforeEach(() => {
        audioInstances = [];
        originalAudio = globalThis.Audio;
        globalThis.Audio = vi.fn(function (src) {
            const player = {
                src,
                loop: false,
                volume: 1,
                currentTime: 0,
                onended: null,
                play: vi.fn().mockResolvedValue(undefined),
                pause: vi.fn(),
            };
            audioInstances.push(player);
            return player;
        });
        globalThis.window = globalThis.window || {};
        globalThis.window.api = {
            get: vi.fn(),
        };
        NotificationSoundUtils.stop();
        NotificationSoundUtils.autoplayBlocked = false;
    });

    afterEach(() => {
        globalThis.Audio = originalAudio;
        vi.restoreAllMocks();
    });

    it("shouldPlay returns false when disabled", () => {
        expect(NotificationSoundUtils.shouldPlay({ notification_sound_enabled: false })).toBe(false);
        expect(NotificationSoundUtils.shouldPlay({ notification_sound_enabled: true })).toBe(true);
        expect(NotificationSoundUtils.shouldPlay(null)).toBe(false);
    });

    it("play skips when disabled", async () => {
        const result = await NotificationSoundUtils.play({ notification_sound_enabled: false });
        expect(result).toBe(false);
        expect(globalThis.window.api.get).not.toHaveBeenCalled();
    });

    it("play skips when status has no sound", async () => {
        globalThis.window.api.get.mockResolvedValue({
            data: { enabled: true, has_sound: false, id: null },
        });
        const result = await NotificationSoundUtils.play({ notification_sound_enabled: true });
        expect(result).toBe(false);
        expect(globalThis.Audio).not.toHaveBeenCalled();
    });

    it("play creates audio when configured", async () => {
        globalThis.window.api.get.mockResolvedValue({
            data: { enabled: true, has_sound: true, id: 7, volume: 0.5 },
        });
        const result = await NotificationSoundUtils.play({ notification_sound_enabled: true });
        expect(result).toBe(true);
        expect(globalThis.window.api.get).toHaveBeenCalledWith("/api/v1/notification-sounds/status");
        expect(globalThis.Audio).toHaveBeenCalledWith("/api/v1/notification-sounds/7/audio");
        expect(audioInstances[0].volume).toBe(0.5);
        expect(audioInstances[0].loop).toBe(false);
        expect(audioInstances[0].play).toHaveBeenCalled();
    });

    it("play sets autoplayBlocked on NotAllowedError", async () => {
        globalThis.window.api.get.mockResolvedValue({
            data: { enabled: true, has_sound: true, id: 2, volume: 1 },
        });
        globalThis.Audio = vi.fn(function () {
            const player = {
                loop: false,
                volume: 1,
                onended: null,
                play: vi.fn().mockRejectedValue(Object.assign(new Error("blocked"), { name: "NotAllowedError" })),
                pause: vi.fn(),
                currentTime: 0,
            };
            audioInstances.push(player);
            return player;
        });

        const result = await NotificationSoundUtils.play({ notification_sound_enabled: true });
        expect(result).toBe(false);
        expect(NotificationSoundUtils.autoplayBlocked).toBe(true);
    });

    it("play returns false while autoplayBlocked", async () => {
        NotificationSoundUtils.autoplayBlocked = true;
        const result = await NotificationSoundUtils.play({ notification_sound_enabled: true });
        expect(result).toBe(false);
        expect(globalThis.window.api.get).not.toHaveBeenCalled();
    });

    it("unlockAutoplay clears blocked flag", () => {
        NotificationSoundUtils.autoplayBlocked = true;
        NotificationSoundUtils.unlockAutoplay();
        expect(NotificationSoundUtils.autoplayBlocked).toBe(false);
    });

    it("stop pauses active player", async () => {
        globalThis.window.api.get.mockResolvedValue({
            data: { enabled: true, has_sound: true, id: 1, volume: 1 },
        });
        await NotificationSoundUtils.play({ notification_sound_enabled: true });
        NotificationSoundUtils.stop();
        expect(audioInstances[0].pause).toHaveBeenCalled();
    });

    it("preview plays selected sound", async () => {
        const result = await NotificationSoundUtils.preview(9, 80);
        expect(result).toBe(true);
        expect(globalThis.Audio).toHaveBeenCalledWith("/api/v1/notification-sounds/9/audio");
        expect(audioInstances[0].volume).toBeCloseTo(0.8);
    });
});
