// SPDX-License-Identifier: 0BSD

import { t } from "../../../js/i18n.js";
import ToastUtils from "../../../js/ToastUtils.js";
import {
    classifyGetUserMediaError,
    isBraveBrowser,
    isMeshChatXAndroid as detectMeshChatXAndroid,
    promptMicrophoneAccess,
    queryMicrophonePermissionState,
    WEB_AUDIO_MIC_TOAST_KEY,
} from "../../../js/webAudioMicPermission.js";
import {
    COMPRESSOR_ATTACK,
    COMPRESSOR_KNEE,
    COMPRESSOR_RATIO,
    COMPRESSOR_RELEASE,
    COMPRESSOR_THRESHOLD,
    DEFAULT_AUDIO_INPUT_DEVICE_ID,
    DEFAULT_AUDIO_INPUT_DEVICE_LABEL,
    DEFAULT_AUDIO_OUTPUT_DEVICE_ID,
    DEFAULT_AUDIO_OUTPUT_DEVICE_LABEL,
    HIGHPASS_FILTER_FREQ,
    HIGHPASS_FILTER_Q,
    INT16_SAMPLE_MAX,
    SCRIPT_PROCESSOR_BUFFER_SIZE,
    TELEPHONE_PCM_CAPTURE_WORKLET_URL,
} from "./constants.js";
import { computeSignalLevel, extractInt16Samples } from "./callWebAudioPlayback.js";
import type { AudioDeviceItem } from "./types.js";

declare const window: {
    isSecureContext?: boolean;
    MeshChatXAndroid?: {
        isTelephoneNativeAudioAvailable?: () => boolean;
        isNativePcmAudioAvailable?: () => boolean;
    };
};

/**
 * Converts Float32Array audio channel buffer to 16 bit PCM ArrayBuffer
 */
export function floatChannelToInt16PcmBuffer(ch0: Float32Array): ArrayBuffer {
    const pcm = new Int16Array(ch0.length);
    for (let i = 0; i < ch0.length; i += 1) {
        const s = ch0[i] ?? 0;
        pcm[i] = Math.max(-1, Math.min(1, s)) * INT16_SAMPLE_MAX;
    }
    return pcm.buffer;
}

/**
 * Builds getUserMedia constraints according to selected input device
 */
export function pickMicConstraints(
    selectedAudioInputId: string,
    audioInputDevices: AudioDeviceItem[]
): MediaStreamConstraints {
    const processingHints = {
        echoCancellation: true,
        noiseSuppression: true,
        autoGainControl: true,
    };
    const validIds = new Set(
        (audioInputDevices || []).filter((d) => d.kind === "audioinput" && d.deviceId).map((d) => d.deviceId)
    );
    if (!selectedAudioInputId || selectedAudioInputId === DEFAULT_AUDIO_INPUT_DEVICE_ID) {
        return { audio: true };
    }
    const id = validIds.has(selectedAudioInputId) ? selectedAudioInputId : null;
    return id ? { audio: { ...processingHints, deviceId: { exact: id } } } : { audio: true };
}

/**
 * Enumerates input and output audio devices from navigator.mediaDevices
 */
export async function enumerateAudioDevices(
    selectedInputId: string,
    selectedOutputId: string
): Promise<{
    inputs: AudioDeviceItem[];
    outputs: AudioDeviceItem[];
    resolvedInputId: string;
    resolvedOutputId: string;
}> {
    const defaultIn: AudioDeviceItem = {
        deviceId: DEFAULT_AUDIO_INPUT_DEVICE_ID,
        kind: "audioinput",
        label: DEFAULT_AUDIO_INPUT_DEVICE_LABEL,
        groupId: "",
    };
    const defaultOut: AudioDeviceItem = {
        deviceId: DEFAULT_AUDIO_OUTPUT_DEVICE_ID,
        kind: "audiooutput",
        label: DEFAULT_AUDIO_OUTPUT_DEVICE_LABEL,
        groupId: "",
    };

    const mediaDevices = navigator?.mediaDevices;
    if (!mediaDevices || typeof mediaDevices.enumerateDevices !== "function") {
        return {
            inputs: [defaultIn],
            outputs: [defaultOut],
            resolvedInputId: defaultIn.deviceId,
            resolvedOutputId: defaultOut.deviceId,
        };
    }

    const devices = await mediaDevices.enumerateDevices();
    let inputs: AudioDeviceItem[] = devices
        .filter((d) => d.kind === "audioinput")
        .map((d) => ({ deviceId: d.deviceId, kind: "audioinput", label: d.label, groupId: d.groupId }));
    let outputs: AudioDeviceItem[] = devices
        .filter((d) => d.kind === "audiooutput")
        .map((d) => ({ deviceId: d.deviceId, kind: "audiooutput", label: d.label, groupId: d.groupId }));

    const inputsUsable = inputs.some((d) => d.deviceId && String(d.deviceId).trim() !== "" && d.label);
    if (!inputsUsable) inputs = [defaultIn];

    const outputsUsable = outputs.some((d) => d.deviceId && String(d.deviceId).trim() !== "" && d.label);
    if (!outputsUsable) outputs = [defaultOut];

    const inputValid = inputs.some((d) => d.deviceId === selectedInputId);
    const resolvedInputId = inputValid ? selectedInputId : inputs[0]?.deviceId || defaultIn.deviceId;

    const outputValid = outputs.some((d) => d.deviceId === selectedOutputId);
    const resolvedOutputId = outputValid ? selectedOutputId : outputs[0]?.deviceId || defaultOut.deviceId;

    return { inputs, outputs, resolvedInputId, resolvedOutputId };
}

/**
 * Requests microphone permission
 */
export async function requestMicPermission(): Promise<boolean> {
    try {
        if (detectMeshChatXAndroid()) {
            const tel = window.MeshChatXAndroid?.isTelephoneNativeAudioAvailable;
            if (typeof tel === "function" && tel()) return true;
            if (window.MeshChatXAndroid?.isNativePcmAudioAvailable?.()) return true;
        }
        if (typeof window !== "undefined" && window.isSecureContext === false) {
            ToastUtils.error(t("call.microphone_insecure_context"), 5000, WEB_AUDIO_MIC_TOAST_KEY);
            return false;
        }
        const mediaDevices = navigator?.mediaDevices;
        if (!mediaDevices) {
            throw new Error("navigator.mediaDevices is unavailable");
        }
        await promptMicrophoneAccess(mediaDevices);
        // Wide-open { audio: true } is what opens the permission dialog.
        // Call requestAudioPermission before refreshAudioDevices / enumerateDevices.
        return true;
    } catch (e: any) {
        const permissionState = await queryMicrophonePermissionState();
        const errorKey = classifyGetUserMediaError(e, {
            permissionState,
            isBrave: isBraveBrowser(),
        });
        ToastUtils.error(t(errorKey), 5000, WEB_AUDIO_MIC_TOAST_KEY);
        return false;
    }
}

export interface MicAudioChain {
    audioSourceNode: MediaStreamAudioSourceNode;
    audioNoiseHighpass: BiquadFilterNode | null;
    audioNoiseCompressor: DynamicsCompressorNode | null;
    captureInput: AudioNode;
}

/**
 * Creates media stream source node and noise cleanup filters
 */
export function createMicAudioChain(audioCtx: AudioContext, stream: MediaStream): MicAudioChain {
    const source = audioCtx.createMediaStreamSource(stream);
    let captureInput: AudioNode = source;
    let highpass: BiquadFilterNode | null = null;
    let compressor: DynamicsCompressorNode | null = null;

    if (typeof audioCtx.createBiquadFilter === "function" && typeof audioCtx.createDynamicsCompressor === "function") {
        try {
            highpass = audioCtx.createBiquadFilter();
            highpass.type = "highpass";
            highpass.frequency.value = HIGHPASS_FILTER_FREQ;
            highpass.Q.value = HIGHPASS_FILTER_Q;

            compressor = audioCtx.createDynamicsCompressor();
            compressor.threshold.value = COMPRESSOR_THRESHOLD;
            compressor.knee.value = COMPRESSOR_KNEE;
            compressor.ratio.value = COMPRESSOR_RATIO;
            compressor.attack.value = COMPRESSOR_ATTACK;
            compressor.release.value = COMPRESSOR_RELEASE;

            source.connect(highpass);
            highpass.connect(compressor);
            captureInput = compressor;
        } catch {
            // fallback to direct source
            captureInput = source;
        }
    }

    return { audioSourceNode: source, audioNoiseHighpass: highpass, audioNoiseCompressor: compressor, captureInput };
}

/**
 * Attempts AudioWorklet capture node attachment with fallback to ScriptProcessor
 */
export async function setupMicCaptureNodes(params: {
    audioCtx: AudioContext;
    captureInput: AudioNode;
    onPcmData: (buffer: ArrayBuffer) => void;
    onLocalLevel?: (level: number) => void;
}): Promise<{
    workletNode: AudioWorkletNode | null;
    scriptNode: ScriptProcessorNode | null;
    silentGain: GainNode;
}> {
    const { audioCtx, captureInput, onPcmData, onLocalLevel } = params;
    let micTapNode: AudioNode | null = null;
    let workletNode: AudioWorkletNode | null = null;
    let scriptNode: ScriptProcessorNode | null = null;

    if (globalThis.isSecureContext !== false && audioCtx.audioWorklet) {
        try {
            await audioCtx.audioWorklet.addModule(TELEPHONE_PCM_CAPTURE_WORKLET_URL);
            const processor = new AudioWorkletNode(audioCtx, "telephone-pcm-capture", {
                numberOfInputs: 1,
                numberOfOutputs: 1,
                channelCount: 1,
            });
            processor.port.onmessage = (event) => {
                const pcmBuffer = event.data as ArrayBuffer;
                onPcmData(pcmBuffer);
                if (onLocalLevel) {
                    const samples = extractInt16Samples(pcmBuffer);
                    if (samples && samples.length > 0) {
                        onLocalLevel(computeSignalLevel(samples, INT16_SAMPLE_MAX));
                    }
                }
            };
            captureInput.connect(processor);
            workletNode = processor;
            micTapNode = processor;
        } catch {
            // fallback to script processor
        }
    }

    if (!micTapNode) {
        if (typeof audioCtx.createScriptProcessor !== "function") {
            throw new Error("AudioWorklet and ScriptProcessor capture are unavailable");
        }
        const processor = audioCtx.createScriptProcessor(SCRIPT_PROCESSOR_BUFFER_SIZE, 1, 1);
        processor.onaudioprocess = (e) => {
            const ch0 = e.inputBuffer.getChannelData(0);
            if (!ch0 || ch0.length === 0) return;
            if (onLocalLevel) {
                onLocalLevel(computeSignalLevel(ch0, 1));
            }
            onPcmData(floatChannelToInt16PcmBuffer(ch0));
        };
        captureInput.connect(processor);
        scriptNode = processor;
        micTapNode = processor;
    }

    const silentGain = audioCtx.createGain();
    silentGain.gain.value = 0;
    micTapNode.connect(silentGain);
    silentGain.connect(audioCtx.destination);

    return { workletNode, scriptNode, silentGain };
}
