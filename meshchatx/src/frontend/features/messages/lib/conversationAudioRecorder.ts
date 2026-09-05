// SPDX-License-Identifier: 0BSD

import DialogUtils from "../../../js/DialogUtils.js";
import ToastUtils from "../../../js/ToastUtils.js";
import MicrophoneRecorder from "../../../js/MicrophoneRecorder.js";
import { t } from "../../../js/i18n.js";
import type { ComposeAudio } from "./conversationViewerSend.js";

type AudioRecorderInstance = {
    start: () => Promise<boolean>;
    stop: () => Promise<Blob | ArrayBuffer>;
    codec2Mode?: string;
};

export type ActiveAudioRecording = {
    recorder: AudioRecorderInstance;
    codec: "opus" | "codec2";
    startedAt: number;
};

export function formatRecordingDuration(milliseconds: number): string {
    const seconds = Math.max(0, Math.floor(milliseconds / 1000));
    return `${Math.floor(seconds / 60)}:${String(seconds % 60).padStart(2, "0")}`;
}

export async function startAudioRecordingSession(args: {
    codec: string;
    mode?: string;
    hasExistingAudio?: boolean;
}): Promise<ActiveAudioRecording | null> {
    if (args.hasExistingAudio) {
        const confirm = await DialogUtils.confirm(
            "An audio recording is already attached. A new recording will replace it."
        );
        if (!confirm) return null;
    }
    let recorder: AudioRecorderInstance | null = null;
    let codec: "opus" | "codec2" | null = null;
    try {
        if (args.codec === "codec2") {
            const Recorder = (
                globalThis as typeof globalThis & {
                    Codec2MicrophoneRecorder: new () => {
                        codec2Mode: string;
                        start: () => Promise<boolean>;
                        stop: () => Promise<ArrayBuffer>;
                    };
                }
            ).Codec2MicrophoneRecorder;
            const rec = new Recorder();
            rec.codec2Mode = args.mode || "1200";
            recorder = rec;
            codec = "codec2";
        } else {
            recorder = new MicrophoneRecorder();
            codec = "opus";
        }
        const started = await recorder.start();
        if (!started) throw new Error(t("messages.failed_start_recording"));
        return {
            recorder,
            codec,
            startedAt: Date.now(),
        };
    } catch (error) {
        ToastUtils.error((error as Error).message);
        return null;
    }
}

export async function stopAudioRecordingSession(active: ActiveAudioRecording): Promise<ComposeAudio | null> {
    try {
        const audio = await active.recorder.stop();
        if (active.codec === "codec2") {
            const encoded = new Uint8Array(audio as ArrayBuffer);
            const mode = active.recorder.codec2Mode || "1200";
            const Codec2Lib = (
                globalThis as typeof globalThis & {
                    Codec2Lib: {
                        runDecode: (mode: string, bytes: Uint8Array) => Promise<ArrayBuffer>;
                        rawToWav: (bytes: ArrayBuffer) => Promise<ArrayBuffer>;
                    };
                }
            ).Codec2Lib;
            const decoded = await Codec2Lib.runDecode(mode, encoded);
            const wav = await Codec2Lib.rawToWav(decoded);
            const preview = new Blob([wav], { type: "audio/wav" });
            return {
                audio_mode: mode === "3200" ? 0x09 : 0x04,
                audio_blob: new Blob([encoded]),
                audio_preview_url: URL.createObjectURL(preview),
            };
        } else {
            const blob = audio as Blob;
            if (blob.size > 0) {
                return {
                    audio_mode: 0x10,
                    audio_blob: blob,
                    audio_preview_url: URL.createObjectURL(blob),
                };
            }
        }
    } catch (error) {
        ToastUtils.error((error as Error).message);
    }
    return null;
}
