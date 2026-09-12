// SPDX-License-Identifier: 0BSD

import { afterEach, describe, expect, it, vi } from "vitest";
import { useCallAudioDevices } from "../../meshchatx/src/frontend/js/call/useCallAudioDevices.js";

const mediaDevicesDescriptor = Object.getOwnPropertyDescriptor(navigator, "mediaDevices");

function stubMediaDevices(value) {
    Object.defineProperty(navigator, "mediaDevices", {
        configurable: true,
        value,
    });
}

afterEach(() => {
    if (mediaDevicesDescriptor) {
        Object.defineProperty(navigator, "mediaDevices", mediaDevicesDescriptor);
    } else {
        Reflect.deleteProperty(navigator, "mediaDevices");
    }
    vi.restoreAllMocks();
});

describe("useCallAudioDevices", () => {
    it("returns null mediaDevices api when getUserMedia is unavailable", () => {
        const devices = useCallAudioDevices();
        stubMediaDevices(undefined);
        expect(devices.getMediaDevicesApi()).toBeNull();
        stubMediaDevices({ enumerateDevices: vi.fn() });
        expect(devices.getMediaDevicesApi()).toBeNull();
        const mediaDevices = { getUserMedia: vi.fn() };
        stubMediaDevices(mediaDevices);
        expect(devices.getMediaDevicesApi()).toBe(mediaDevices);
    });

    it("detects the enumerateDevices api", () => {
        const devices = useCallAudioDevices();
        expect(devices.hasEnumerateDevicesApi(null)).toBe(false);
        expect(devices.hasEnumerateDevicesApi({})).toBe(false);
        expect(devices.hasEnumerateDevicesApi({ enumerateDevices: vi.fn() })).toBe(true);
    });

    it("refreshAudioDevices uses default placeholders when mediaDevices is missing", async () => {
        const devices = useCallAudioDevices();
        stubMediaDevices(undefined);
        await devices.refreshAudioDevices();
        expect(devices.audioInputDevices.value).toEqual([
            { deviceId: "__meshchat_default_in__", kind: "audioinput", label: "Default", groupId: "" },
        ]);
        expect(devices.audioOutputDevices.value).toEqual([
            { deviceId: "__meshchat_default_out__", kind: "audiooutput", label: "Default", groupId: "" },
        ]);
    });

    it("refreshAudioDevices uses default placeholders without enumerateDevices", async () => {
        const devices = useCallAudioDevices();
        stubMediaDevices({ getUserMedia: vi.fn() });
        await devices.refreshAudioDevices();
        expect(devices.audioInputDevices.value[0].deviceId).toBe("__meshchat_default_in__");
        expect(devices.audioOutputDevices.value[0].deviceId).toBe("__meshchat_default_out__");
    });

    it("refreshAudioDevices keeps usable lists and valid selections", async () => {
        const devices = useCallAudioDevices();
        devices.selectedAudioInputId.value = "mic-1";
        devices.selectedAudioOutputId.value = "spk-1";
        stubMediaDevices({
            getUserMedia: vi.fn(),
            enumerateDevices: vi.fn().mockResolvedValue([
                { kind: "audioinput", deviceId: "mic-1", label: "Mic One", groupId: "g1" },
                { kind: "audiooutput", deviceId: "spk-1", label: "Speaker One", groupId: "g2" },
            ]),
        });
        await devices.refreshAudioDevices();
        expect(devices.audioInputDevices.value).toHaveLength(1);
        expect(devices.audioInputDevices.value[0].deviceId).toBe("mic-1");
        expect(devices.audioOutputDevices.value[0].deviceId).toBe("spk-1");
        expect(devices.selectedAudioInputId.value).toBe("mic-1");
        expect(devices.selectedAudioOutputId.value).toBe("spk-1");
    });

    it("refreshAudioDevices resets a stale selection to the first device", async () => {
        const devices = useCallAudioDevices();
        devices.selectedAudioInputId.value = "gone";
        devices.selectedAudioOutputId.value = "gone";
        stubMediaDevices({
            getUserMedia: vi.fn(),
            enumerateDevices: vi.fn().mockResolvedValue([
                { kind: "audioinput", deviceId: "mic-9", label: "Mic Nine", groupId: "g1" },
                { kind: "audiooutput", deviceId: "spk-9", label: "Speaker Nine", groupId: "g2" },
            ]),
        });
        await devices.refreshAudioDevices();
        expect(devices.selectedAudioInputId.value).toBe("mic-9");
        expect(devices.selectedAudioOutputId.value).toBe("spk-9");
    });

    it("refreshAudioDevices keeps default placeholders for pre-permission lists", async () => {
        const devices = useCallAudioDevices();
        stubMediaDevices({
            getUserMedia: vi.fn(),
            enumerateDevices: vi
                .fn()
                .mockResolvedValue([
                    { kind: "audioinput", deviceId: "", label: "", groupId: "" },
                    { kind: "audiooutput", deviceId: "", label: "", groupId: "" },
                ]),
        });
        await devices.refreshAudioDevices();
        expect(devices.audioInputDevices.value[0].deviceId).toBe("__meshchat_default_in__");
        expect(devices.audioOutputDevices.value[0].deviceId).toBe("__meshchat_default_out__");
    });

    it("refreshAudioDevices falls back to placeholders and logs on enumerate failure", async () => {
        const consoleError = vi.spyOn(console, "error").mockImplementation(() => {});
        const devices = useCallAudioDevices();
        stubMediaDevices({
            getUserMedia: vi.fn(),
            enumerateDevices: vi.fn().mockRejectedValue(new Error("boom")),
        });
        await devices.refreshAudioDevices();
        expect(devices.audioInputDevices.value[0].deviceId).toBe("__meshchat_default_in__");
        expect(devices.audioOutputDevices.value[0].deviceId).toBe("__meshchat_default_out__");
        expect(consoleError).toHaveBeenCalled();
        expect(consoleError.mock.calls[0][0]).toContain("refresh-devices");
    });

    it("pickWebAudioMicConstraints returns bare audio without a real device id", () => {
        const devices = useCallAudioDevices();
        const mediaDevices = { enumerateDevices: vi.fn() };
        devices.selectedAudioInputId.value = null;
        expect(devices.pickWebAudioMicConstraints(mediaDevices)).toEqual({ audio: true });
        devices.selectedAudioInputId.value = "__meshchat_default_in__";
        expect(devices.pickWebAudioMicConstraints(mediaDevices)).toEqual({ audio: true });
    });

    it("pickWebAudioMicConstraints pins a valid device id with processing hints", () => {
        const devices = useCallAudioDevices();
        devices.selectedAudioInputId.value = "mic-1";
        devices.audioInputDevices.value = [{ kind: "audioinput", deviceId: "mic-1" }];
        const constraints = devices.pickWebAudioMicConstraints({ enumerateDevices: vi.fn() });
        expect(constraints).toEqual({
            audio: {
                echoCancellation: true,
                noiseSuppression: true,
                autoGainControl: true,
                deviceId: { exact: "mic-1" },
            },
        });
    });

    it("pickWebAudioMicConstraints ignores a device id absent from the list", () => {
        const devices = useCallAudioDevices();
        devices.selectedAudioInputId.value = "stale";
        devices.audioInputDevices.value = [{ kind: "audioinput", deviceId: "mic-1" }];
        expect(devices.pickWebAudioMicConstraints({ enumerateDevices: vi.fn() })).toEqual({ audio: true });
    });

    it("getUserMediaWithMicFallback retries wide open on retryable errors", async () => {
        const devices = useCallAudioDevices();
        vi.spyOn(console, "error").mockImplementation(() => {});
        const err = new Error("not found");
        err.name = "NotFoundError";
        const fakeStream = { id: "stream" };
        const getUserMedia = vi.fn().mockRejectedValueOnce(err).mockResolvedValueOnce(fakeStream);
        const mediaDevices = { getUserMedia, enumerateDevices: vi.fn().mockResolvedValue([]) };
        devices.selectedAudioInputId.value = "gone";
        devices.audioInputDevices.value = [{ kind: "audioinput", deviceId: "gone" }];
        const stream = await devices.getUserMediaWithMicFallback(mediaDevices);
        expect(stream).toBe(fakeStream);
        expect(getUserMedia).toHaveBeenCalledTimes(2);
        expect(getUserMedia.mock.calls[1][0]).toEqual({ audio: true });
        expect(devices.selectedAudioInputId.value).toBe("__meshchat_default_in__");
    });

    it("getUserMediaWithMicFallback rethrows non-retryable errors", async () => {
        const devices = useCallAudioDevices();
        const err = new Error("denied");
        err.name = "NotAllowedError";
        const getUserMedia = vi.fn().mockRejectedValue(err);
        await expect(
            devices.getUserMediaWithMicFallback({ getUserMedia, enumerateDevices: vi.fn() })
        ).rejects.toBe(err);
        expect(getUserMedia).toHaveBeenCalledTimes(1);
    });
});
