// SPDX-License-Identifier: 0BSD

import { beforeEach, describe, expect, it, vi } from "vitest";
import { useAudioAttachment } from "../../meshchatx/src/frontend/js/messages/useAudioAttachment.js";

vi.mock("../../meshchatx/src/frontend/js/DialogUtils.js", () => ({
    default: { confirm: vi.fn(async () => true), alert: vi.fn() },
}));

vi.mock("../../meshchatx/src/frontend/js/MicrophoneRecorder.js", () => ({
    default: vi.fn(function () {
        return {
            start: vi.fn(async () => true),
            stop: vi.fn(async () => new Blob(["audio"], { type: "audio/ogg" })),
        };
    }),
}));

import DialogUtils from "../../meshchatx/src/frontend/js/DialogUtils.js";
import MicrophoneRecorder from "../../meshchatx/src/frontend/js/MicrophoneRecorder.js";

describe("useAudioAttachment", () => {
    beforeEach(() => {
        vi.clearAllMocks();
    });

    it("records opus and attaches the blob with a preview url", async () => {
        const a = useAudioAttachment();
        await a.startRecordingAudioAttachment({ codec: "opus" });
        expect(a.isRecordingAudioAttachment.value).toBe(true);
        expect(MicrophoneRecorder).toHaveBeenCalled();
        const inst = MicrophoneRecorder.mock.results[0].value;
        await a.stopRecordingAudioAttachment();
        expect(inst.stop).toHaveBeenCalled();
        expect(a.newMessageAudio.value.audio_mode).toBe(0x10);
        expect(a.newMessageAudio.value.audio_preview_url).toBeTruthy();
    });

    it("asks before replacing an existing attachment", async () => {
        const a = useAudioAttachment();
        a.newMessageAudio.value = { audio_mode: 0x10, audio_blob: new Blob([]) };
        DialogUtils.confirm.mockResolvedValueOnce(false);
        await a.startRecordingAudioAttachment({ codec: "opus" });
        expect(MicrophoneRecorder).not.toHaveBeenCalled();
        expect(DialogUtils.confirm).toHaveBeenCalled();
    });

    it("stop without recording is a no-op after clearing the timer", async () => {
        const a = useAudioAttachment();
        await a.stopRecordingAudioAttachment();
        expect(a.newMessageAudio.value).toBeNull();
    });

    it("removeAudioAttachment clears state and revokes the preview", async () => {
        const a = useAudioAttachment();
        const url = "blob:preview";
        a.newMessageAudio.value = { audio_mode: 0x10, audio_blob: new Blob([]), audio_preview_url: url };
        const revokeSpy = vi.spyOn(URL, "revokeObjectURL").mockImplementation(() => {});
        await a.removeAudioAttachment();
        expect(revokeSpy).toHaveBeenCalledWith(url);
        expect(a.newMessageAudio.value).toBeNull();
        revokeSpy.mockRestore();
    });

    it("failure message depends on mediaDevices availability", () => {
        const a = useAudioAttachment({ t: (k) => k });
        const msg = a.buildAudioRecordingFailureMessage();
        expect(msg).toContain("messages.failed_start_recording");
    });
});
