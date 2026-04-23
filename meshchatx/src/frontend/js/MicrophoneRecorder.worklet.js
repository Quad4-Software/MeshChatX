// SPDX-License-Identifier: 0BSD

class MicrophonePcmFloatProcessor extends AudioWorkletProcessor {
    process(inputs) {
        const input = inputs[0];
        if (!input || input.length === 0) {
            return true;
        }
        const ch0 = input[0];
        if (!ch0 || ch0.length === 0) {
            return true;
        }
        const copy = new Float32Array(ch0.length);
        copy.set(ch0);
        this.port.postMessage(copy.buffer, [copy.buffer]);
        return true;
    }
}

registerProcessor("microphone-pcm-float", MicrophonePcmFloatProcessor);
