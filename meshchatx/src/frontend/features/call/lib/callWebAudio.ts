// SPDX-License-Identifier: 0BSD

import { t } from "../../../js/i18n.js";
import ToastUtils from "../../../js/ToastUtils.js";
import {
    classifyGetUserMediaError,
    isBraveBrowser,
    isMeshChatXAndroid as detectMeshChatXAndroid,
    queryMicrophonePermissionState,
    WEB_AUDIO_MIC_TOAST_KEY,
} from "../../../js/webAudioMicPermission.js";
import {
    DEFAULT_AUDIO_FRAME_MS,
    DEFAULT_AUDIO_INPUT_DEVICE_ID,
    DEFAULT_AUDIO_OUTPUT_DEVICE_ID,
    RECONNECT_ATTACH_DELAY_MS,
    TELEPHONE_AUDIO_WS_PATH,
} from "./constants.js";
import {
    createMicAudioChain,
    enumerateAudioDevices,
    pickMicConstraints,
    requestMicPermission,
    setupMicCaptureNodes,
} from "./callWebAudioMic.js";
import {
    computeSignalLevel,
    extractInt16Samples,
    getOrCreateAudioContext,
    playRemotePcmBuffer,
    resumeAudioContext,
} from "./callWebAudioPlayback.js";
import type { AudioDeviceItem } from "./types.js";

export { computeSignalLevel, extractInt16Samples } from "./callWebAudioPlayback.js";

declare const window: {
    electron?: boolean;
    isSecureContext?: boolean;
    location: {
        protocol: string;
        host: string;
    };
    setTimeout: typeof setTimeout;
    addEventListener: typeof addEventListener;
    removeEventListener: typeof removeEventListener;
    MeshChatXAndroid?: {
        isTelephoneNativeAudioAvailable?: () => boolean;
        isNativePcmAudioAvailable?: () => boolean;
        startTelephoneNativeAudio?: () => string;
        stopTelephoneNativeAudio?: () => void;
    };
};

export interface WebAudioBridgeCallbacks {
    onLocalLevel?: (level: number) => void;
    onRemoteLevel?: (level: number) => void;
    onFailure?: (stage: string, error: unknown) => void;
    onConfigDisable?: () => void | Promise<void>;
}

export interface WebAudioBridgeOptions {
    callbacks?: WebAudioBridgeCallbacks;
    selectedAudioInputId?: string;
    selectedAudioOutputId?: string;
}

/**
 * Main Web Audio bridge controller for LXST telephone calls
 */
export class CallWebAudioBridge {
    private callbacks: WebAudioBridgeCallbacks;
    public selectedAudioInputId: string;
    public selectedAudioOutputId: string;
    public audioInputDevices: AudioDeviceItem[] = [];
    public audioOutputDevices: AudioDeviceItem[] = [];
    public audioWs: WebSocket | null = null;
    public audioCtx: AudioContext | null = null;
    public audioStream: MediaStream | null = null;
    public audioSourceNode: MediaStreamAudioSourceNode | null = null;
    public audioNoiseHighpass: BiquadFilterNode | null = null;
    public audioNoiseCompressor: DynamicsCompressorNode | null = null;
    public audioProcessor: ScriptProcessorNode | null = null;
    public audioWorkletNode: AudioWorkletNode | null = null;
    public audioSilentGain: GainNode | null = null;
    public remoteAudioEl: HTMLAudioElement | null = null;
    public audioFrameMs: number = DEFAULT_AUDIO_FRAME_MS;
    public webAudioStartBlocked: boolean = false;
    public webAudioMicReady: boolean = false;
    public webAudioStartInFlight: boolean = false;
    public useAndroidNativeTelephone: boolean = false;
    private androidListener: ((ev: Event) => void) | null = null;

    constructor(options: WebAudioBridgeOptions = {}) {
        this.callbacks = options.callbacks || {};
        this.selectedAudioInputId = options.selectedAudioInputId || DEFAULT_AUDIO_INPUT_DEVICE_ID;
        this.selectedAudioOutputId = options.selectedAudioOutputId || DEFAULT_AUDIO_OUTPUT_DEVICE_ID;
    }

    public isAndroid(): boolean {
        return detectMeshChatXAndroid();
    }

    private logFailure(stage: string, error: unknown): void {
        const appImage = Boolean(
            window.electron &&
                typeof navigator?.userAgent === "string" &&
                navigator.userAgent.includes("AppImage")
        );
        console.error(`[CallWebAudio] ${stage}`, { isElectron: Boolean(window.electron), isAppImage: appImage }, error);
        this.callbacks.onFailure?.(stage, error);
    }

    public async disableWithError(errorKey: string, error: unknown, stage: string = "unknown"): Promise<void> {
        this.logFailure(stage, error);
        ToastUtils.error(t(errorKey), 5000, WEB_AUDIO_MIC_TOAST_KEY);
        if (!this.isAndroid()) {
            try {
                await this.callbacks.onConfigDisable?.();
            } catch (updateError) {
                this.logFailure("disable-config-update", updateError);
            }
        }
        this.stop();
    }

    public async refreshAudioDevices(): Promise<void> {
        try {
            const res = await enumerateAudioDevices(this.selectedAudioInputId, this.selectedAudioOutputId);
            this.audioInputDevices = res.inputs;
            this.audioOutputDevices = res.outputs;
            this.selectedAudioInputId = res.resolvedInputId;
            this.selectedAudioOutputId = res.resolvedOutputId;
        } catch (e) {
            this.logFailure("refresh-devices", e);
        }
    }

    public async requestAudioPermission(): Promise<boolean> {
        const ok = await requestMicPermission();
        if (ok) {
            this.webAudioMicReady = true;
            this.webAudioStartBlocked = false;
            await this.refreshAudioDevices();
            return true;
        }
        this.webAudioStartBlocked = true;
        return false;
    }

    public async start(): Promise<void> {
        if (this.isAndroid()) {
            this.stop();
            if (!window.MeshChatXAndroid || typeof window.MeshChatXAndroid.startTelephoneNativeAudio !== "function") {
                await this.disableWithError(
                    "call.web_audio_not_available",
                    new Error("Native audio bridge not linked"),
                    "start-android-missing"
                );
                return;
            }
            const telMic = window.MeshChatXAndroid.isTelephoneNativeAudioAvailable;
            const micOk =
                typeof telMic === "function" ? telMic() : window.MeshChatXAndroid.isNativePcmAudioAvailable?.() === true;
            if (!micOk) {
                await this.disableWithError(
                    "call.microphone_permission_denied",
                    new Error("RECORD_AUDIO not granted"),
                    "start-android-perm"
                );
                return;
            }
            const ret = window.MeshChatXAndroid.startTelephoneNativeAudio();
            if (ret !== "ok") {
                await this.disableWithError(
                    "call.web_audio_not_available",
                    new Error(String(ret || "native start")),
                    "start-android"
                );
                return;
            }
            this.bindAndroidListener();
            this.useAndroidNativeTelephone = true;
            return;
        }

        if (this.audioWs && this.audioWs.readyState === WebSocket.OPEN) {
            try {
                this.audioWs.send(JSON.stringify({ type: "attach" }));
            } catch {
                // ignore
            }
            await resumeAudioContext(this.audioCtx);
            return;
        }

        if (this.audioWs) {
            this.stop();
        }

        if (this.webAudioStartInFlight || this.webAudioStartBlocked) {
            return;
        }

        this.webAudioStartInFlight = true;
        try {
            if (typeof window !== "undefined" && window.isSecureContext === false) {
                this.webAudioStartBlocked = true;
                await this.disableWithError(
                    "call.microphone_insecure_context",
                    new Error("insecure context"),
                    "start-preflight-insecure"
                );
                return;
            }
            const mediaDevices = navigator?.mediaDevices;
            if (!mediaDevices) {
                this.webAudioStartBlocked = true;
                await this.disableWithError(
                    "call.web_audio_not_available",
                    new Error("navigator.mediaDevices is unavailable"),
                    "start-preflight-media-devices"
                );
                return;
            }

            this.selectedAudioInputId = DEFAULT_AUDIO_INPUT_DEVICE_ID;
            const constraints = pickMicConstraints(this.selectedAudioInputId, this.audioInputDevices);
            let stream: MediaStream;
            try {
                stream = await mediaDevices.getUserMedia(constraints);
            } catch (e: any) {
                this.selectedAudioInputId = DEFAULT_AUDIO_INPUT_DEVICE_ID;
                this.logFailure("getUserMedia-fallback-wide", e);
                stream = await mediaDevices.getUserMedia({ audio: true });
            }

            this.audioStream = stream;
            this.webAudioMicReady = true;
            this.webAudioStartBlocked = false;
            await this.refreshAudioDevices();

            this.audioCtx = getOrCreateAudioContext(this.audioCtx);
            await resumeAudioContext(this.audioCtx);

            const micChain = createMicAudioChain(this.audioCtx, stream);
            this.audioSourceNode = micChain.audioSourceNode;
            this.audioNoiseHighpass = micChain.audioNoiseHighpass;
            this.audioNoiseCompressor = micChain.audioNoiseCompressor;

            const wsProtocol = window.location.protocol === "https:" ? "wss:" : "ws:";
            const url = `${wsProtocol}//${window.location.host}${TELEPHONE_AUDIO_WS_PATH}`;

            const sendMicPcmToWs = (arrayBuffer: ArrayBuffer) => {
                if (!this.audioWs || this.audioWs.readyState !== WebSocket.OPEN) return;
                if (arrayBuffer && arrayBuffer.byteLength > 0) {
                    this.audioWs.send(arrayBuffer);
                }
            };

            const captureNodes = await setupMicCaptureNodes({
                audioCtx: this.audioCtx,
                captureInput: micChain.captureInput,
                onPcmData: sendMicPcmToWs,
                onLocalLevel: (level) => this.callbacks.onLocalLevel?.(level),
            });
            this.audioWorkletNode = captureNodes.workletNode;
            this.audioProcessor = captureNodes.scriptNode;
            this.audioSilentGain = captureNodes.silentGain;

            const ws = new WebSocket(url);
            ws.binaryType = "arraybuffer";
            ws.onopen = () => {
                ws.send(JSON.stringify({ type: "attach" }));
            };
            ws.onmessage = (event) => {
                if (typeof event.data === "string") {
                    try {
                        const msg = JSON.parse(event.data);
                        if (msg.type === "error") {
                            const errMsg = typeof msg.message === "string" ? msg.message : "";
                            if (errMsg.includes("Web audio is disabled in config")) {
                                this.stop();
                                return;
                            }
                            this.logFailure("ws-server-error", new Error(msg.message || "unknown"));
                            if (typeof msg.message === "string" && msg.message.includes("No active call")) {
                                setTimeout(() => {
                                    try {
                                        if (this.audioWs && this.audioWs.readyState === WebSocket.OPEN) {
                                            this.audioWs.send(JSON.stringify({ type: "attach" }));
                                        }
                                    } catch {
                                        // ignore
                                    }
                                }, RECONNECT_ATTACH_DELAY_MS);
                            }
                        }
                    } catch {
                        // ignore non-json
                    }
                    return;
                }
                this.playRemotePcm(event.data);
            };
            ws.onerror = () => this.stop();
            ws.onclose = () => this.stop();
            this.audioWs = ws;
            this.refreshAudioDevices();
        } catch (err: any) {
            this.webAudioStartBlocked = true;
            const permissionState = await queryMicrophonePermissionState();
            const errorKey = classifyGetUserMediaError(err, {
                permissionState,
                isBrave: isBraveBrowser(),
            });
            await this.disableWithError(errorKey, err, "start-catch");
        } finally {
            this.webAudioStartInFlight = false;
        }
    }

    public playRemotePcm(arrayBuffer: ArrayBuffer): void {
        playRemotePcmBuffer(
            arrayBuffer,
            {
                audioCtx: this.audioCtx,
                remoteAudioEl: this.remoteAudioEl,
                selectedAudioOutputId: this.selectedAudioOutputId,
            },
            (level) => this.callbacks.onRemoteLevel?.(level)
        );
    }

    private bindAndroidListener(): void {
        this.unbindAndroidListener();
        this.androidListener = (ev: any) => {
            const d = ev && ev.detail;
            if (d && d.kind === "levels") {
                this.callbacks.onLocalLevel?.(Number(d.tx_level) || 0);
                this.callbacks.onRemoteLevel?.(Number(d.rx_level) || 0);
                return;
            }
            if (d && d.kind === "error" && d.detail) {
                this.logFailure("android-native", new Error(String(d.sub || d.detail || "error")));
            }
        };
        window.addEventListener("meshchatx-native-telephone-audio", this.androidListener);
    }

    private unbindAndroidListener(): void {
        if (this.androidListener) {
            window.removeEventListener("meshchatx-native-telephone-audio", this.androidListener);
            this.androidListener = null;
        }
    }

    public stop(): void {
        if (this.useAndroidNativeTelephone) {
            this.unbindAndroidListener();
            this.useAndroidNativeTelephone = false;
            try {
                window.MeshChatXAndroid?.stopTelephoneNativeAudio?.();
            } catch (e) {
                this.logFailure("android-native-stop", e);
            }
        }
        if (this.audioWs) {
            try {
                this.audioWs.onopen = null;
                this.audioWs.onmessage = null;
                this.audioWs.onerror = null;
                this.audioWs.onclose = null;
                this.audioWs.close();
            } catch {
                // ignore
            }
            this.audioWs = null;
        }
        if (this.audioSourceNode) {
            try {
                this.audioSourceNode.disconnect();
            } catch {
                // ignore
            }
            this.audioSourceNode = null;
        }
        if (this.audioNoiseHighpass) {
            try {
                this.audioNoiseHighpass.disconnect();
            } catch {
                // ignore
            }
            this.audioNoiseHighpass = null;
        }
        if (this.audioNoiseCompressor) {
            try {
                this.audioNoiseCompressor.disconnect();
            } catch {
                // ignore
            }
            this.audioNoiseCompressor = null;
        }
        if (this.audioProcessor) {
            try {
                this.audioProcessor.disconnect();
            } catch {
                // ignore
            }
            this.audioProcessor = null;
        }
        if (this.audioWorkletNode) {
            try {
                this.audioWorkletNode.port.onmessage = null;
                this.audioWorkletNode.disconnect();
            } catch {
                // ignore
            }
            this.audioWorkletNode = null;
        }
        if (this.audioStream) {
            this.audioStream.getTracks().forEach((t) => {
                try {
                    t.stop();
                } catch {
                    // ignore
                }
            });
            this.audioStream = null;
        }
        if (this.remoteAudioEl) {
            this.remoteAudioEl.srcObject = null;
            this.remoteAudioEl = null;
        }
        if (this.audioSilentGain) {
            try {
                this.audioSilentGain.disconnect();
            } catch {
                // ignore
            }
            this.audioSilentGain = null;
        }
        if (this.audioCtx && this.audioCtx.state !== "closed" && typeof this.audioCtx.close === "function") {
            this.audioCtx.close().catch(() => {
                // ignore
            });
        }
        this.audioCtx = null;
    }
}
