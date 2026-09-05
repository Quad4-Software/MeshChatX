// SPDX-License-Identifier: 0BSD

/** Caps for Codec2 decode expansion (voice notes). Encoded LXMF audio is small; PCM/WAV is not. */
export const MAX_CODEC2_ENCODED_BYTES = 512 * 1024;
/** ~8 minutes of 8 kHz mono 16-bit PCM before WAV wrap. */
export const MAX_CODEC2_DECODED_RAW_BYTES = 8 * 1024 * 1024;
/** WAV header + PCM. Slightly above raw cap. */
export const MAX_CODEC2_WAV_BYTES = MAX_CODEC2_DECODED_RAW_BYTES + 44;
/** Opus attachments are stored compressed; still bound blob URL creation. */
export const MAX_OPUS_ATTACHMENT_BYTES = 2 * 1024 * 1024;

/**
 * @param {ArrayBuffer | Uint8Array | null | undefined} data
 * @param {number} maxBytes
 * @returns {Uint8Array}
 */
export function assertByteLengthAtMost(data, maxBytes) {
    if (data == null) {
        throw new Error("Missing audio data");
    }
    const bytes = data instanceof Uint8Array ? data : new Uint8Array(data);
    if (bytes.byteLength > maxBytes) {
        throw new Error(`Audio exceeds size limit (${bytes.byteLength} > ${maxBytes})`);
    }
    return bytes;
}
