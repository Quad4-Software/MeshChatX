/**
 * A simple class for recording microphone input and returning the audio encoded in codec2
 */
class Codec2MicrophoneRecorder {
    constructor() {
        this.sampleRate = 8000;
        this.codec2Mode = "1200";
        this.audioChunks = [];

        this.audioContext = null;
        this.audioWorkletNode = null;
        this.microphoneMediaStream = null;
        this.mediaStreamSource = null;
    }

    static _downsampleBuffer(buffer, sourceSampleRate, targetSampleRate) {
        if (targetSampleRate === sourceSampleRate) {
            return new Float32Array(buffer);
        }
        const sampleRateRatio = sourceSampleRate / targetSampleRate;
        const newLength = Math.round(buffer.length / sampleRateRatio);
        const result = new Float32Array(newLength);
        let offsetResult = 0;
        let offsetBuffer = 0;
        while (offsetResult < result.length) {
            const nextOffsetBuffer = Math.round((offsetResult + 1) * sampleRateRatio);
            let accum = 0;
            let count = 0;
            for (let i = offsetBuffer; i < nextOffsetBuffer && i < buffer.length; i++) {
                accum += buffer[i];
                count++;
            }
            result[offsetResult] = count ? accum / count : 0;
            offsetResult++;
            offsetBuffer = nextOffsetBuffer;
        }
        return result;
    }

    async start() {
        try {
            this.audioChunks = [];
            this.audioContext = new AudioContext({ sampleRate: this.sampleRate });

            let tap = null;

            if (
                globalThis.isSecureContext !== false &&
                this.audioContext.audioWorklet &&
                typeof this.audioContext.audioWorklet.addModule === "function" &&
                typeof globalThis.AudioWorkletNode === "function"
            ) {
                try {
                    await this.audioContext.audioWorklet.addModule("assets/js/codec2-emscripten/processor.js");
                    const wn = new AudioWorkletNode(this.audioContext, "audio-processor");
                    wn.port.onmessage = async (event) => {
                        this.audioChunks.push(event.data);
                    };
                    tap = wn;
                } catch (e) {
                    console.log(e);
                }
            }

            if (!tap) {
                if (typeof this.audioContext.createScriptProcessor !== "function") {
                    await this.audioContext.close().catch(() => {});
                    this.audioContext = null;
                    return false;
                }
                try {
                    const bufferSize = 4096;
                    const acc = { bufferIndex: 0, inputBuffer: new Float32Array(bufferSize) };
                    const sp = this.audioContext.createScriptProcessor(bufferSize, 1, 1);
                    sp.onaudioprocess = (e) => {
                        const inputData = e.inputBuffer.getChannelData(0);
                        for (let i = 0; i < inputData.length; i += 1) {
                            if (acc.bufferIndex < bufferSize) {
                                acc.inputBuffer[acc.bufferIndex++] = inputData[i];
                            }
                            if (acc.bufferIndex === bufferSize) {
                                const downsampledBuffer = Codec2MicrophoneRecorder._downsampleBuffer(
                                    acc.inputBuffer,
                                    this.sampleRate,
                                    this.sampleRate
                                );
                                this.audioChunks.push(downsampledBuffer);
                                acc.bufferIndex = 0;
                            }
                        }
                    };
                    tap = sp;
                } catch (e2) {
                    console.log(e2);
                    await this.audioContext.close().catch(() => {});
                    this.audioContext = null;
                    return false;
                }
            }

            this.audioWorkletNode = tap;

            this.microphoneMediaStream = await navigator.mediaDevices.getUserMedia({
                audio: true,
            });

            this.mediaStreamSource = this.audioContext.createMediaStreamSource(this.microphoneMediaStream);
            this.mediaStreamSource.connect(this.audioWorkletNode);
            this._silentTap = this.audioContext.createGain();
            this._silentTap.gain.value = 0;
            this.audioWorkletNode.connect(this._silentTap);
            this._silentTap.connect(this.audioContext.destination);

            if (typeof this.audioContext.resume === "function") {
                try {
                    await this.audioContext.resume();
                } catch {
                    // ignore
                }
            }

            return true;
        } catch (e) {
            console.log(e);
            try {
                this.mediaStreamSource?.disconnect?.();
            } catch {
                // ignore
            }
            this.mediaStreamSource = null;
            if (this.microphoneMediaStream) {
                this.microphoneMediaStream.getTracks().forEach((track) => track.stop());
            }
            this.microphoneMediaStream = null;
            try {
                if (this.audioWorkletNode) {
                    if (this.audioWorkletNode.port) {
                        this.audioWorkletNode.port.onmessage = null;
                    }
                    this.audioWorkletNode.onaudioprocess = null;
                    this.audioWorkletNode.disconnect();
                }
            } catch {
                // ignore
            }
            this.audioWorkletNode = null;
            try {
                this._silentTap?.disconnect?.();
            } catch {
                // ignore
            }
            this._silentTap = null;
            if (this.audioContext && this.audioContext.state !== "closed") {
                await this.audioContext.close().catch(() => {});
            }
            this.audioContext = null;
            return false;
        }
    }

    async stop() {
        if (this.mediaStreamSource) {
            this.mediaStreamSource.disconnect();
        }

        if (this.microphoneMediaStream) {
            this.microphoneMediaStream.getTracks().forEach((track) => track.stop());
        }

        if (this.audioWorkletNode) {
            try {
                if (this.audioWorkletNode.port) {
                    this.audioWorkletNode.port.onmessage = null;
                }
            } catch {
                // ignore
            }
            try {
                this.audioWorkletNode.onaudioprocess = null;
            } catch {
                // ignore
            }
            try {
                this.audioWorkletNode.disconnect();
            } catch {
                // ignore
            }
            this.audioWorkletNode = null;
        }

        if (this._silentTap) {
            try {
                this._silentTap.disconnect();
            } catch {
                // ignore
            }
            this._silentTap = null;
        }

        if (this.audioContext && this.audioContext.state !== "closed") {
            this.audioContext.close();
        }
        this.audioContext = null;

        var fullAudio = [];
        for (const chunk of this.audioChunks) {
            fullAudio = [...fullAudio, ...chunk];
        }

        const buffer = WavEncoder.encodeWAV(fullAudio, this.sampleRate);

        const rawBuffer = await Codec2Lib.audioFileToRaw(buffer, "audio.wav");
        const encoded = await Codec2Lib.runEncode(this.codec2Mode, rawBuffer);

        return encoded;
    }
}
