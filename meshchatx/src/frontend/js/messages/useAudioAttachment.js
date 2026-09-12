// @ts-check

import { ref } from "vue";
import DialogUtils from "../DialogUtils";
import Utils from "../Utils";
import MicrophoneRecorder from "../MicrophoneRecorder";
import {
    MAX_CODEC2_DECODED_RAW_BYTES,
    MAX_CODEC2_ENCODED_BYTES,
    MAX_CODEC2_WAV_BYTES,
    assertByteLengthAtMost,
} from "../codec2DecodeLimits.js";

/**
 * Compose-side audio attachment state for ConversationViewer: microphone
 * recording (codec2 and opus, including the Android native wav bridge), the
 * recording duration timer, and the pending newMessageAudio attachment with
 * its object-url preview.
 *
 * options.t translates failure messages. options.isMeshChatXAndroid and
 * options.androidNativeWavAttachmentAllowed are host callbacks that gate the
 * Android native wav recording path.
 */
export function useAudioAttachment(options = {}) {
    const {
        t = (key) => key,
        isMeshChatXAndroid = () => false,
        androidNativeWavAttachmentAllowed = () => false,
    } = options;

    const newMessageAudio = ref(null);
    const isRecordingAudioAttachment = ref(false);
    const audioAttachmentMicrophoneRecorder = ref(null);
    const audioAttachmentMicrophoneRecorderCodec = ref(null);
    const audioAttachmentRecordingStartedAt = ref(null);
    const audioAttachmentRecordingDuration = ref(null);
    const audioAttachmentRecordingTimer = ref(null);
    const androidNativeOpusAttachment = ref(false);

    async function startRecordingAudioAttachment(args) {
        // do nothing if already recording
        if (isRecordingAudioAttachment.value) {
            return;
        }

        // ask user to confirm recording new audio attachment, if an existing audio attachment exists
        if (
            newMessageAudio.value &&
            !(await DialogUtils.confirm(
                "An audio recording is already attached. A new recording will replace it. Do you want to continue?"
            ))
        ) {
            return;
        }

        // handle selected codec
        switch (args.codec) {
            case "codec2": {
                // start recording microphone
                audioAttachmentMicrophoneRecorderCodec.value = "codec2";
                audioAttachmentMicrophoneRecorder.value = new Codec2MicrophoneRecorder();
                audioAttachmentMicrophoneRecorder.value.codec2Mode = args.mode;
                audioAttachmentRecordingStartedAt.value = Date.now();
                isRecordingAudioAttachment.value = await audioAttachmentMicrophoneRecorder.value.start();

                // update recording time in ui every second
                audioAttachmentRecordingDuration.value = Utils.formatMinutesSeconds(0);
                audioAttachmentRecordingTimer.value = setInterval(() => {
                    const recordingDurationMillis = Date.now() - audioAttachmentRecordingStartedAt.value;
                    const recordingDurationSeconds = recordingDurationMillis / 1000;
                    audioAttachmentRecordingDuration.value = Utils.formatMinutesSeconds(recordingDurationSeconds);
                }, 1000);

                // alert if failed to start recording
                if (!isRecordingAudioAttachment.value) {
                    DialogUtils.alert(buildAudioRecordingFailureMessage());
                }

                break;
            }
            case "opus": {
                if (isMeshChatXAndroid() && androidNativeWavAttachmentAllowed()) {
                    const res = window.MeshChatXAndroid.startNativeWavAttachment();
                    if (res === "ok") {
                        androidNativeOpusAttachment.value = true;
                        audioAttachmentMicrophoneRecorderCodec.value = "opus";
                        audioAttachmentMicrophoneRecorder.value = { _androidNative: true };
                        audioAttachmentRecordingStartedAt.value = Date.now();
                        isRecordingAudioAttachment.value = true;
                        audioAttachmentRecordingDuration.value = Utils.formatMinutesSeconds(0);
                        audioAttachmentRecordingTimer.value = setInterval(() => {
                            const recordingDurationMillis = Date.now() - audioAttachmentRecordingStartedAt.value;
                            const recordingDurationSeconds = recordingDurationMillis / 1000;
                            audioAttachmentRecordingDuration.value =
                                Utils.formatMinutesSeconds(recordingDurationSeconds);
                        }, 1000);
                        break;
                    }
                }
                audioAttachmentMicrophoneRecorderCodec.value = "opus";
                audioAttachmentMicrophoneRecorder.value = new MicrophoneRecorder();
                audioAttachmentRecordingStartedAt.value = Date.now();
                isRecordingAudioAttachment.value = await audioAttachmentMicrophoneRecorder.value.start();

                audioAttachmentRecordingDuration.value = Utils.formatMinutesSeconds(0);
                audioAttachmentRecordingTimer.value = setInterval(() => {
                    const recordingDurationMillis = Date.now() - audioAttachmentRecordingStartedAt.value;
                    const recordingDurationSeconds = recordingDurationMillis / 1000;
                    audioAttachmentRecordingDuration.value = Utils.formatMinutesSeconds(recordingDurationSeconds);
                }, 1000);

                if (!isRecordingAudioAttachment.value) {
                    DialogUtils.alert(buildAudioRecordingFailureMessage());
                }

                break;
            }
            default: {
                DialogUtils.alert(`Unhandled microphone recorder codec: ${args.codec}`);
                break;
            }
        }
    }

    async function stopRecordingAudioAttachment() {
        // clear audio recording timer
        clearInterval(audioAttachmentRecordingTimer.value);

        if (!isRecordingAudioAttachment.value) {
            return;
        }

        isRecordingAudioAttachment.value = false;
        if (androidNativeOpusAttachment.value) {
            androidNativeOpusAttachment.value = false;
            const p = new Promise((resolve) => {
                const done = () => {
                    try {
                        if (window.__meshchatXNative) {
                            window.__meshchatXNative = undefined;
                        }
                    } catch {
                        // ignore
                    }
                    resolve();
                };
                window.__meshchatXNative = {
                    onWav: (payload) => {
                        if (!payload || !payload.ok) {
                            const err = payload && payload.error ? String(payload.error) : "unknown";
                            if (err !== "empty") {
                                DialogUtils.alert(`${t("messages.failed")}${err ? ` (${err})` : ""}`);
                            }
                            done();
                            return;
                        }
                        try {
                            const binary = atob(payload.data);
                            const bytes = new Uint8Array(binary.length);
                            for (let i = 0; i < binary.length; i += 1) {
                                bytes[i] = binary.charCodeAt(i);
                            }
                            const audio = new Blob([bytes], { type: "audio/wav" });
                            revokeNewMessageAudioPreview();
                            newMessageAudio.value = {
                                audio_mode: 0x10,
                                audio_blob: audio,
                                audio_preview_url: URL.createObjectURL(audio),
                            };
                        } catch {
                            DialogUtils.alert(buildAudioRecordingFailureMessage());
                        }
                        done();
                    },
                };
                try {
                    window.MeshChatXAndroid.stopNativeWavAttachment();
                } catch {
                    DialogUtils.alert(buildAudioRecordingFailureMessage());
                    done();
                }
            });
            await p;
            audioAttachmentMicrophoneRecorder.value = null;
            audioAttachmentMicrophoneRecorderCodec.value = null;
            return;
        }

        const audio = await audioAttachmentMicrophoneRecorder.value.stop();

        // handle audio based on codec
        switch (audioAttachmentMicrophoneRecorderCodec.value) {
            case "codec2": {
                // do nothing if no audio was provided
                if (audio.length === 0) {
                    return;
                }

                // decode codec2 audio back to wav so we can show a preview audio player before user sends it
                const codec2Mode = audioAttachmentMicrophoneRecorder.value.codec2Mode;
                const encoded = assertByteLengthAtMost(new Uint8Array(audio), MAX_CODEC2_ENCODED_BYTES);
                const decoded = assertByteLengthAtMost(
                    await Codec2Lib.runDecode(codec2Mode, encoded),
                    MAX_CODEC2_DECODED_RAW_BYTES
                );

                // convert decoded codec2 to wav audio and create a blob
                const wavAudio = assertByteLengthAtMost(await Codec2Lib.rawToWav(decoded), MAX_CODEC2_WAV_BYTES);
                const wavBlob = new Blob([/** @type {BlobPart} */ (wavAudio)], {
                    type: "audio/wav",
                });

                // determine audio mode
                var audioMode = null;
                switch (codec2Mode) {
                    case "1200": {
                        audioMode = 0x04; // LXMF.AM_CODEC2_1200
                        break;
                    }
                    case "3200": {
                        audioMode = 0x09; // LXMF.AM_CODEC2_3200
                        break;
                    }
                    default: {
                        DialogUtils.alert(`Unhandled microphone recorder codec2Mode: ${codec2Mode}`);
                        return;
                    }
                }

                // update message audio attachment
                revokeNewMessageAudioPreview();
                newMessageAudio.value = {
                    audio_mode: audioMode,
                    audio_blob: new Blob([audio]),
                    audio_preview_url: URL.createObjectURL(wavBlob),
                };

                break;
            }
            case "opus": {
                // do nothing if no audio was provided
                if (audio.size === 0) {
                    return;
                }

                // update message audio attachment
                revokeNewMessageAudioPreview();
                newMessageAudio.value = {
                    audio_mode: 0x10, // LXMF.AM_OPUS_OGG
                    audio_blob: audio, // opus microphone recorder returns a blob
                    audio_preview_url: URL.createObjectURL(audio),
                };

                break;
            }
        }
    }

    function revokeNewMessageAudioPreview() {
        const url = newMessageAudio.value?.audio_preview_url;
        if (url) {
            try {
                URL.revokeObjectURL(url);
            } catch {
                // ignore
            }
        }
    }

    async function removeAudioAttachment() {
        // remove audio
        revokeNewMessageAudioPreview();
        newMessageAudio.value = null;
    }

    function buildAudioRecordingFailureMessage() {
        if (!navigator?.mediaDevices || typeof navigator.mediaDevices.getUserMedia !== "function") {
            return `${t("messages.failed_start_recording")}. ${t("messages.failed_start_recording_help_mediadevices")}`;
        }
        const AudioContextCtor = globalThis.AudioContext || globalThis.webkitAudioContext;
        if (typeof AudioContextCtor !== "function") {
            return `${t("messages.failed_start_recording")}. ${t("messages.failed_start_recording_help_web_audio")}`;
        }
        let probe = null;
        try {
            probe = new AudioContextCtor();
            const canWorklet =
                globalThis.isSecureContext !== false &&
                probe.audioWorklet &&
                typeof probe.audioWorklet.addModule === "function";
            const canScriptProcessor = typeof probe.createScriptProcessor === "function";
            if (!canWorklet && !canScriptProcessor) {
                return `${t("messages.failed_start_recording")}. ${t("messages.failed_start_recording_help_audio_worklet")}`;
            }
        } catch {
            return `${t("messages.failed_start_recording")}. ${t("messages.failed_start_recording_help_web_audio")}`;
        } finally {
            try {
                if (probe && typeof probe.close === "function") {
                    const closed = probe.close();
                    if (closed && typeof closed.catch === "function") {
                        void closed.catch(() => {});
                    }
                }
            } catch {
                // ignore
            }
        }
        return `${t("messages.failed_start_recording")}. ${t("messages.failed_start_recording_help_permission")}`;
    }

    return {
        newMessageAudio,
        isRecordingAudioAttachment,
        audioAttachmentMicrophoneRecorder,
        audioAttachmentMicrophoneRecorderCodec,
        audioAttachmentRecordingStartedAt,
        audioAttachmentRecordingDuration,
        audioAttachmentRecordingTimer,
        androidNativeOpusAttachment,
        startRecordingAudioAttachment,
        stopRecordingAudioAttachment,
        revokeNewMessageAudioPreview,
        removeAudioAttachment,
        buildAudioRecordingFailureMessage,
    };
}
