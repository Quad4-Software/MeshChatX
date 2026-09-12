// @ts-check
// SPDX-License-Identifier: 0BSD

import { ref } from "vue";

/**
 * Audio device enumeration and selection state for CallPage: browser
 * mediaDevices discovery, default-device placeholders, selected mic and
 * speaker ids, mic getUserMedia constraint picking, and the shared
 * web-audio failure logger the host also uses from its lifecycle code.
 *
 * The host keeps permission prompts, the WebSocket audio lifecycle, and
 * remote playback; it reads selectedAudioInputId when building the
 * capture graph and applies selectedAudioOutputId via setSinkId.
 */
export function useCallAudioDevices() {
    const audioInputDevices = ref([]);
    const audioOutputDevices = ref([]);
    const selectedAudioInputId = ref(null);
    const selectedAudioOutputId = ref(null);

    function getMediaDevicesApi() {
        const mediaDevices = navigator?.mediaDevices;
        if (!mediaDevices || typeof mediaDevices.getUserMedia !== "function") {
            return null;
        }
        return mediaDevices;
    }

    function hasEnumerateDevicesApi(mediaDevices) {
        return Boolean(mediaDevices && typeof mediaDevices.enumerateDevices === "function");
    }

    function logWebAudioFailure(stage, error) {
        const appImage = Boolean(
            window.electron && typeof navigator?.userAgent === "string" && navigator.userAgent.includes("AppImage")
        );
        console.error(
            `[CallPage:web-audio] ${stage}`,
            {
                isElectron: Boolean(window.electron),
                isAppImage: appImage,
                userAgent: navigator?.userAgent || "unknown",
            },
            error
        );
    }

    function pickWebAudioMicConstraints(mediaDevices) {
        const processingHints = {
            echoCancellation: true,
            noiseSuppression: true,
            autoGainControl: true,
        };
        const canEnumerate = hasEnumerateDevicesApi(mediaDevices);
        const validIds = canEnumerate
            ? new Set(
                  (audioInputDevices.value || [])
                      .filter((d) => d.kind === "audioinput" && d.deviceId)
                      .map((d) => d.deviceId)
              )
            : new Set();
        const sid = selectedAudioInputId.value;
        // Bare audio unless a post-permission device id is selected.
        // Processing flags or deviceId.exact before the prompt yield
        // NotFoundError on Brave and Chromium with no permission dialog.
        if (!sid || sid === "__meshchat_default_in__") {
            return { audio: true };
        }
        const id = validIds.has(sid) ? sid : null;
        return id ? { audio: { ...processingHints, deviceId: { exact: id } } } : { audio: true };
    }

    async function getUserMediaWithMicFallback(mediaDevices) {
        const constraints = pickWebAudioMicConstraints(mediaDevices);
        try {
            return await mediaDevices.getUserMedia(constraints);
        } catch (e) {
            const retryable =
                e?.name === "NotFoundError" || e?.name === "OverconstrainedError" || e?.name === "NotReadableError";
            if (!retryable) {
                throw e;
            }
            // Stale exact deviceId, Brave pre-permission device lists, or busy device.
            // Wide-open audio is what actually triggers the browser permission prompt.
            selectedAudioInputId.value = "__meshchat_default_in__";
            logWebAudioFailure("getUserMedia-fallback-wide", e);
            return await mediaDevices.getUserMedia({ audio: true });
        }
    }

    async function refreshAudioDevices() {
        const defaultIn = {
            deviceId: "__meshchat_default_in__",
            kind: "audioinput",
            label: "Default",
            groupId: "",
        };
        const defaultOut = {
            deviceId: "__meshchat_default_out__",
            kind: "audiooutput",
            label: "Default",
            groupId: "",
        };
        try {
            const mediaDevices = getMediaDevicesApi();
            if (!mediaDevices) {
                audioInputDevices.value = [defaultIn];
                audioOutputDevices.value = [defaultOut];
                return;
            }
            if (!hasEnumerateDevicesApi(mediaDevices)) {
                audioInputDevices.value = [defaultIn];
                audioOutputDevices.value = [defaultOut];
                return;
            }
            const devices = await mediaDevices.enumerateDevices();
            let inputs = devices.filter((d) => d.kind === "audioinput");
            let outputs = devices.filter((d) => d.kind === "audiooutput");
            // Pre-permission lists often have blank deviceId and blank labels.
            // Keep the Default placeholder so we do not lock onto phantom IDs.
            const inputsUsable = inputs.some((d) => d.deviceId && String(d.deviceId).trim() !== "" && d.label);
            if (!inputsUsable) {
                inputs = [defaultIn];
            }
            const outputsUsable = outputs.some((d) => d.deviceId && String(d.deviceId).trim() !== "" && d.label);
            if (!outputsUsable) {
                outputs = [defaultOut];
            }
            audioInputDevices.value = inputs;
            audioOutputDevices.value = outputs;
            const selectedInStillValid = audioInputDevices.value.some((d) => d.deviceId === selectedAudioInputId.value);
            if (!selectedInStillValid) {
                selectedAudioInputId.value = audioInputDevices.value[0]?.deviceId || defaultIn.deviceId;
            }
            const selectedOutStillValid = audioOutputDevices.value.some(
                (d) => d.deviceId === selectedAudioOutputId.value
            );
            if (!selectedOutStillValid) {
                selectedAudioOutputId.value = audioOutputDevices.value[0]?.deviceId || defaultOut.deviceId;
            }
        } catch (e) {
            logWebAudioFailure("refresh-devices", e);
            audioInputDevices.value = [defaultIn];
            audioOutputDevices.value = [defaultOut];
        }
    }

    return {
        audioInputDevices,
        audioOutputDevices,
        selectedAudioInputId,
        selectedAudioOutputId,
        getMediaDevicesApi,
        hasEnumerateDevicesApi,
        logWebAudioFailure,
        pickWebAudioMicConstraints,
        getUserMediaWithMicFallback,
        refreshAudioDevices,
    };
}
