/**
 * Records microphone input as 16-bit PCM and returns a WAV Blob.
 *
 * Produces a self-contained WAV/PCM payload (Float32 samples captured via
 * Web Audio, downmixed to mono and quantised to int16) so the backend can
 * encode the audio to OGG/Opus using LXST's OpusFileSink without relying
 * on ffmpeg or any browser MediaRecorder container output.
 */
class MicrophoneRecorder {
    constructor() {
        this.microphoneMediaStream = null;
        this.audioContext = null;
        this.sourceNode = null;
        this.processorNode = null;
        this.pcmChunks = [];
        this.sampleRate = 0;
        this.channels = 1;
    }

    cleanupMediaStream() {
        if (!this.microphoneMediaStream) {
            return;
        }
        this.microphoneMediaStream.getTracks().forEach((track) => {
            try {
                track.stop();
            } catch {
                // ignore track stop failures
            }
        });
        this.microphoneMediaStream = null;
    }

    teardownAudioGraph() {
        try {
            this.processorNode?.disconnect?.();
        } catch {
            // ignore disconnect failures
        }
        try {
            this.sourceNode?.disconnect?.();
        } catch {
            // ignore disconnect failures
        }
        if (this.audioContext && typeof this.audioContext.close === "function") {
            try {
                const closeResult = this.audioContext.close();
                if (closeResult && typeof closeResult.catch === "function") {
                    closeResult.catch(() => {});
                }
            } catch {
                // ignore close failures
            }
        }
        this.processorNode = null;
        this.sourceNode = null;
        this.audioContext = null;
    }

    async start() {
        try {
            this.pcmChunks = [];

            if (!navigator?.mediaDevices || typeof navigator.mediaDevices.getUserMedia !== "function") {
                return false;
            }

            const AudioContextCtor = globalThis.AudioContext || globalThis.webkitAudioContext;
            if (typeof AudioContextCtor !== "function") {
                return false;
            }

            this.microphoneMediaStream = await navigator.mediaDevices.getUserMedia({
                audio: true,
            });

            this.audioContext = new AudioContextCtor();
            if (typeof this.audioContext.resume === "function") {
                try {
                    await this.audioContext.resume();
                } catch {
                    // ignore resume failures
                }
            }

            this.sampleRate = this.audioContext.sampleRate || 48000;
            this.channels = 1;

            this.sourceNode = this.audioContext.createMediaStreamSource(this.microphoneMediaStream);

            if (typeof this.audioContext.createScriptProcessor !== "function") {
                this.cleanupMediaStream();
                this.teardownAudioGraph();
                return false;
            }

            const bufferSize = 4096;
            this.processorNode = this.audioContext.createScriptProcessor(bufferSize, 1, 1);
            this.processorNode.onaudioprocess = (event) => {
                const input = event?.inputBuffer?.getChannelData(0);
                if (!input || input.length === 0) {
                    return;
                }
                this.pcmChunks.push(new Float32Array(input));
            };

            this.sourceNode.connect(this.processorNode);
            this.processorNode.connect(this.audioContext.destination);

            return true;
        } catch {
            this.cleanupMediaStream();
            this.teardownAudioGraph();
            return false;
        }
    }

    async stop() {
        if (!this.audioContext || !this.processorNode) {
            throw new Error("Cannot stop recording before start()");
        }

        const sampleRate = this.sampleRate;
        const channels = this.channels;
        const chunks = this.pcmChunks;

        this.teardownAudioGraph();
        this.cleanupMediaStream();
        this.pcmChunks = [];

        const samples = MicrophoneRecorder._mergeFloat32Chunks(chunks);
        const wav = MicrophoneRecorder._encodeWavPcm16(samples, sampleRate, channels);
        return new Blob([wav], { type: "audio/wav" });
    }

    static _mergeFloat32Chunks(chunks) {
        let total = 0;
        for (const c of chunks) {
            total += c.length;
        }
        const merged = new Float32Array(total);
        let offset = 0;
        for (const c of chunks) {
            merged.set(c, offset);
            offset += c.length;
        }
        return merged;
    }

    static _encodeWavPcm16(samples, sampleRate, channels) {
        const dataBytes = samples.length * 2;
        const buffer = new ArrayBuffer(44 + dataBytes);
        const view = new DataView(buffer);
        let p = 0;

        const writeString = (s) => {
            for (let i = 0; i < s.length; i++) {
                view.setUint8(p + i, s.charCodeAt(i));
            }
            p += s.length;
        };
        const writeUint32 = (n) => {
            view.setUint32(p, n, true);
            p += 4;
        };
        const writeUint16 = (n) => {
            view.setUint16(p, n, true);
            p += 2;
        };

        writeString("RIFF");
        writeUint32(36 + dataBytes);
        writeString("WAVE");
        writeString("fmt ");
        writeUint32(16);
        writeUint16(1);
        writeUint16(channels);
        writeUint32(sampleRate);
        writeUint32(sampleRate * channels * 2);
        writeUint16(channels * 2);
        writeUint16(16);
        writeString("data");
        writeUint32(dataBytes);

        for (let i = 0; i < samples.length; i++, p += 2) {
            let s = samples[i];
            if (s > 1) s = 1;
            else if (s < -1) s = -1;
            view.setInt16(p, s < 0 ? Math.round(s * 0x8000) : Math.round(s * 0x7fff), true);
        }

        return buffer;
    }
}

export default MicrophoneRecorder;
