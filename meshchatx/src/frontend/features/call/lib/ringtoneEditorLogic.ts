// SPDX-License-Identifier: 0BSD

export interface RingtoneItem {
    id: number | string;
    filename: string;
    display_name?: string;
    is_primary?: boolean;
    [key: string]: unknown;
}

export function formatRingtoneTime(seconds: number): string {
    const mins = Math.floor(seconds / 60);
    const secs = (seconds % 60).toFixed(2);
    return `${mins}:${secs.padStart(5, "0")}`;
}

export function isDarkMode(): boolean {
    if (typeof document === "undefined") return false;
    return document.documentElement.classList.contains("dark");
}

export function drawWaveformCanvas(
    canvas: HTMLCanvasElement | null,
    audioBuffer: AudioBuffer | null,
    startTime: number,
    endTime: number,
    totalDuration: number
): void {
    if (!canvas || !audioBuffer) return;

    const ctx = canvas.getContext("2d");
    if (!ctx) return;

    const width = canvas.clientWidth;
    const height = canvas.clientHeight;
    if (width === 0 || height === 0) return;

    const dpr = typeof window !== "undefined" ? window.devicePixelRatio || 1 : 1;
    canvas.width = width * dpr;
    canvas.height = height * dpr;
    ctx.scale(dpr, dpr);

    const data = audioBuffer.getChannelData(0);
    const step = Math.ceil(data.length / width);
    const amp = height / 2;

    ctx.clearRect(0, 0, width, height);
    ctx.beginPath();
    ctx.moveTo(0, amp);

    ctx.strokeStyle = isDarkMode() ? "#3f3f46" : "#e4e4e7";
    ctx.lineWidth = 1;

    for (let i = 0; i < width; i++) {
        let min = 1.0;
        let max = -1.0;
        for (let j = 0; j < step; j++) {
            const datum = data[i * step + j];
            if (datum < min) min = datum;
            if (datum > max) max = datum;
        }
        ctx.moveTo(i, amp + min * amp);
        ctx.lineTo(i, amp + max * amp);
    }
    ctx.stroke();

    if (totalDuration > 0) {
        const startX = (startTime / totalDuration) * width;
        const endX = (endTime / totalDuration) * width;

        ctx.beginPath();
        ctx.strokeStyle = "#3b82f6";
        ctx.lineWidth = 1.5;
        for (let i = Math.floor(startX); i < Math.ceil(endX); i++) {
            let min = 1.0;
            let max = -1.0;
            for (let j = 0; j < step; j++) {
                const datum = data[i * step + j];
                if (datum < min) min = datum;
                if (datum > max) max = datum;
            }
            ctx.moveTo(i, amp + min * amp);
            ctx.lineTo(i, amp + max * amp);
        }
        ctx.stroke();
    }
}

export function audioBufferToWav(buffer: AudioBuffer): Blob {
    const numOfChan = buffer.numberOfChannels;
    const length = buffer.length * numOfChan * 2 + 44;
    const bufferArr = new ArrayBuffer(length);
    const view = new DataView(bufferArr);
    const channels: Float32Array[] = [];
    let offset = 0;
    let pos = 0;

    const setUint16 = (data: number) => {
        view.setUint16(pos, data, true);
        pos += 2;
    };

    const setUint32 = (data: number) => {
        view.setUint32(pos, data, true);
        pos += 4;
    };

    const writeString = (str: string) => {
        for (let i = 0; i < str.length; i++) {
            view.setUint8(pos + i, str.charCodeAt(i));
        }
        pos += str.length;
    };

    writeString("RIFF");
    setUint32(length - 8);
    writeString("WAVE");
    writeString("fmt ");
    setUint32(16);
    setUint16(1);
    setUint16(numOfChan);
    setUint32(buffer.sampleRate);
    setUint32(buffer.sampleRate * 2 * numOfChan);
    setUint16(numOfChan * 2);
    setUint16(16);
    writeString("data");
    setUint32(length - pos - 4);

    for (let i = 0; i < buffer.numberOfChannels; i++) {
        channels.push(buffer.getChannelData(i));
    }

    while (pos < length) {
        for (let i = 0; i < numOfChan; i++) {
            let sample = Math.max(-1, Math.min(1, channels[i][offset]));
            sample = (sample < 0 ? sample * 0x8000 : sample * 0x7fff) | 0;
            view.setInt16(pos, sample, true);
            pos += 2;
        }
        offset++;
    }

    return new Blob([bufferArr], { type: "audio/wav" });
}

export function trimAudioBuffer(audioBuffer: AudioBuffer, startTime: number, endTime: number): AudioBuffer {
    const sampleRate = audioBuffer.sampleRate;
    const startSample = Math.floor(startTime * sampleRate);
    const endSample = Math.floor(endTime * sampleRate);
    const frameCount = Math.max(1, endSample - startSample);

    const offlineCtx = new OfflineAudioContext(audioBuffer.numberOfChannels, frameCount, sampleRate);
    const trimmedBuffer = offlineCtx.createBuffer(audioBuffer.numberOfChannels, frameCount, sampleRate);

    for (let channel = 0; channel < audioBuffer.numberOfChannels; channel++) {
        const data = audioBuffer.getChannelData(channel);
        const trimmedData = trimmedBuffer.getChannelData(channel);
        for (let i = 0; i < frameCount; i++) {
            trimmedData[i] = data[startSample + i] || 0;
        }
    }

    return trimmedBuffer;
}

export async function fetchAndDecodeAudio(
    ringtoneId: number | string
): Promise<{ audioContext: AudioContext; audioBuffer: AudioBuffer }> {
    const response = await fetch(`/api/v1/telephone/ringtones/${ringtoneId}/audio`);
    const arrayBuffer = await response.arrayBuffer();

    const AudioContextClass =
        window.AudioContext || (window as unknown as { webkitAudioContext: typeof AudioContext }).webkitAudioContext;
    const audioContext = new AudioContextClass();
    const audioBuffer = await audioContext.decodeAudioData(arrayBuffer);

    return { audioContext, audioBuffer };
}
