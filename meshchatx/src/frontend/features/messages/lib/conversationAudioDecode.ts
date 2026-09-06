// SPDX-License-Identifier: 0BSD

import {
    assertByteLengthAtMost,
    MAX_CODEC2_DECODED_RAW_BYTES,
    MAX_CODEC2_ENCODED_BYTES,
    MAX_CODEC2_WAV_BYTES,
    MAX_OPUS_ATTACHMENT_BYTES,
} from "../../../js/codec2DecodeLimits.js";
import { MAX_CACHED_AUDIO_ATTACHMENTS } from "./constants.js";

const MAX_CACHED_AUDIO = MAX_CACHED_AUDIO_ATTACHMENTS;

const LXMF_AUDIO_MODE_TO_CODEC2: Record<number, string> = {
    0x01: "450PWB",
    0x02: "450",
    0x03: "700C",
    0x04: "1200",
    0x05: "1300",
    0x06: "1400",
    0x07: "1600",
    0x08: "2400",
    0x09: "3200",
};

export type AudioCacheEntry = { hash: string; objectUrl: string };

export type LxmfAudioField = {
    audio_mode?: number;
    audio_bytes?: string | ArrayBuffer | Uint8Array;
};

type ApiClient = {
    get: (url: string, config?: Record<string, unknown>) => Promise<{ data?: unknown }>;
};

function base64ToUint8Array(base64: string): Uint8Array {
    return Uint8Array.from(atob(base64), (c) => c.charCodeAt(0));
}

function toUint8Array(audioBytes: string | ArrayBuffer | Uint8Array): Uint8Array {
    if (typeof audioBytes === "string") {
        return base64ToUint8Array(audioBytes);
    }
    return audioBytes instanceof Uint8Array ? audioBytes : new Uint8Array(audioBytes);
}

function toArrayBuffer(bytes: Uint8Array): ArrayBuffer {
    return bytes.buffer.slice(bytes.byteOffset, bytes.byteOffset + bytes.byteLength) as ArrayBuffer;
}

async function decodeOpusAudioToBlobUrl(audioBytes: string | ArrayBuffer | Uint8Array): Promise<string | null> {
    try {
        const opusAudioBytes = assertByteLengthAtMost(toUint8Array(audioBytes), MAX_OPUS_ATTACHMENT_BYTES);
        const blob = new Blob([toArrayBuffer(opusAudioBytes)], { type: "audio/ogg" });
        return URL.createObjectURL(blob);
    } catch (error) {
        console.error(error);
        return null;
    }
}

export async function decodeLxmfAudioFieldToBlobUrl(
    audioField: LxmfAudioField | null | undefined
): Promise<string | null> {
    if (!audioField || audioField.audio_bytes == null) {
        return null;
    }
    try {
        const audioMode = audioField.audio_mode;
        if (audioMode === 0x10) {
            return decodeOpusAudioToBlobUrl(audioField.audio_bytes);
        }
        const codecMode = typeof audioMode === "number" ? LXMF_AUDIO_MODE_TO_CODEC2[audioMode] : undefined;
        if (!codecMode) {
            console.error("unsupported audio mode:", audioMode);
            return null;
        }
        const encoded = assertByteLengthAtMost(toUint8Array(audioField.audio_bytes), MAX_CODEC2_ENCODED_BYTES);
        const Codec2Lib = (
            globalThis as typeof globalThis & {
                Codec2Lib: {
                    runDecode: (mode: string, bytes: Uint8Array) => Promise<ArrayBuffer>;
                    rawToWav: (bytes: ArrayBuffer) => Promise<ArrayBuffer>;
                };
            }
        ).Codec2Lib;
        const decoded = assertByteLengthAtMost(
            await Codec2Lib.runDecode(codecMode, encoded),
            MAX_CODEC2_DECODED_RAW_BYTES
        );
        const wavAudio = assertByteLengthAtMost(await Codec2Lib.rawToWav(toArrayBuffer(decoded)), MAX_CODEC2_WAV_BYTES);
        const blob = new Blob([toArrayBuffer(wavAudio)], { type: "audio/wav" });
        return URL.createObjectURL(blob);
    } catch (error) {
        console.error(error);
        return null;
    }
}

export function rememberAudioAttachment(
    order: string[],
    cache: Record<string, string>,
    hash: string,
    objectUrl: string
): { order: string[]; cache: Record<string, string> } {
    const nextCache = { ...cache, [hash]: objectUrl };
    const nextOrder = order.filter((h) => h !== hash).concat(hash);
    while (nextOrder.length > MAX_CACHED_AUDIO) {
        const drop = nextOrder.shift();
        if (drop && nextCache[drop]) {
            try {
                URL.revokeObjectURL(nextCache[drop]);
            } catch {
                /* ignore */
            }
            delete nextCache[drop];
        }
    }
    return { order: nextOrder, cache: nextCache };
}

export function clearAudioAttachmentCache(order: string[], cache: Record<string, string>): void {
    for (const hash of order) {
        const url = cache[hash];
        if (url) {
            try {
                URL.revokeObjectURL(url);
            } catch {
                /* ignore */
            }
        }
    }
}

export async function downloadAndDecodeMessageAudio(
    api: ApiClient,
    messageHash: string,
    audioField: LxmfAudioField
): Promise<string | null> {
    try {
        if (audioField.audio_bytes) {
            return decodeLxmfAudioFieldToBlobUrl(audioField);
        }
        const response = await api.get(`/api/v1/lxmf-messages/attachment/${messageHash}/audio`, {
            responseType: "arraybuffer",
        });
        const audioBytes = response.data;
        if (!audioBytes) {
            return null;
        }
        return decodeLxmfAudioFieldToBlobUrl({
            audio_mode: audioField.audio_mode,
            audio_bytes: audioBytes as ArrayBuffer,
        });
    } catch (error) {
        console.error("Failed to download or decode audio:", error);
        return null;
    }
}
