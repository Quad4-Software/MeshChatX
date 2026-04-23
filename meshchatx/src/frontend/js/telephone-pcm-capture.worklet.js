// SPDX-License-Identifier: 0BSD

class TelephonePcmCaptureProcessor extends AudioWorkletProcessor {
    process(inputs) {
        const input = inputs[0];
        if (!input || input.length === 0) {
            return true;
        }
        const ch0 = input[0];
        if (!ch0 || ch0.length === 0) {
            return true;
        }
        const pcm = new Int16Array(ch0.length);
        for (let i = 0; i < ch0.length; i += 1) {
            const s = ch0[i];
            pcm[i] = Math.max(-1, Math.min(1, s)) * 0x7fff;
        }
        this.port.postMessage(pcm.buffer, [pcm.buffer]);
        return true;
    }
}

registerProcessor("telephone-pcm-capture", TelephonePcmCaptureProcessor);
