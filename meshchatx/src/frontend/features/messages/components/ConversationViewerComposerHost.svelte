<!-- SPDX-License-Identifier: 0BSD -->

<script lang="ts">
    import { onDestroy } from "svelte";
    import { t } from "../../../js/i18n.js";
    import DialogUtils from "../../../js/DialogUtils.js";
    import ToastUtils from "../../../js/ToastUtils.js";
    import { buildMeshchatMapUri } from "../../../js/mapLinkUtils.js";
    import { getAndroidPosition, isAndroidLocationSupported } from "../../../js/androidLocation.js";
    import { parseCommandOrRequestText } from "../lib/lxmf/normalize.js";
    import ConversationComposer from "./ConversationComposer.svelte";
    import ConversationViewerComposerPickerHost from "./ConversationViewerComposerPickerHost.svelte";
    import {
        startAudioRecordingSession,
        stopAudioRecordingSession,
        formatRecordingDuration,
        type ActiveAudioRecording,
    } from "../lib/conversationAudioRecorder.js";
    import type { LangOption } from "../lib/conversationTranslate.js";
    import {
        buildOutboundJob,
        optimisticMessage,
        type ComposeAudio,
        type OutboundJob,
    } from "../lib/conversationViewerSend.js";
    import { peerPathNeedsRefresh } from "../lib/conversationViewerPath.js";
    import type { ViewerChatItem, ViewerPathSnapshot } from "../lib/conversationViewerCtx.js";
    import type { Peer } from "../lib/types.js";

    let {
        selectedPeer = null as Peer | null,
        selectedHash = "",
        myLxmfAddressHash = "",
        peerPathSnapshot = null as ViewerPathSnapshot | null,
        isSelectedPeerBlocked = false,
        config = null as Record<string, unknown> | null,
        translateOptions = [] as LangOption[],
        hasTranslator = false,
        text = $bindable(""),
        replyingTo = $bindable(null as ViewerChatItem | null),
        onjobCreated,
        onsendpapercompose,
        onscrolltobottom,
    }: {
        selectedPeer?: Peer | null;
        selectedHash?: string;
        myLxmfAddressHash?: string;
        peerPathSnapshot?: ViewerPathSnapshot | null;
        isSelectedPeerBlocked?: boolean;
        config?: Record<string, unknown> | null;
        translateOptions?: LangOption[];
        hasTranslator?: boolean;
        text?: string;
        replyingTo?: ViewerChatItem | null;
        onjobCreated?: (job: OutboundJob, optimistic: ReturnType<typeof optimisticMessage>) => void;
        onsendpapercompose?: () => void;
        onscrolltobottom?: () => void;
    } = $props();

    let pickerHost: ConversationViewerComposerPickerHost | undefined = $state();
    let fileInput: HTMLInputElement | undefined = $state();
    let videoInput: HTMLInputElement | undefined = $state();
    let deliveryMethod = $state<string | null>(null);
    // Armed by the send menu: next send parses the composer text as a
    // command/request payload instead of a chat message.
    let pendingSendAsCommandOrRequest = $state(false);
    let images = $state.raw<File[]>([]);
    let imageUrls = $state.raw<string[]>([]);
    let files = $state.raw<File[]>([]);
    let audio = $state<ComposeAudio | null>(null);

    let isComposeTranslateOpen = $state(false);
    let isTranslatingMessage = $state(false);

    let activeRecording = $state<ActiveAudioRecording | null>(null);
    let isRecordingAudioAttachment = $state(false);
    let audioAttachmentRecordingDuration = $state("0:00");
    let audioRecordingTimer: ReturnType<typeof setInterval> | null = null;
    let destroyed = false;

    onDestroy(() => {
        destroyed = true;
        if (audioRecordingTimer) {
            clearInterval(audioRecordingTimer);
            audioRecordingTimer = null;
        }
        if (activeRecording) {
            void stopAudioRecording();
        }
    });

    const canSendMessage = $derived(Boolean(selectedPeer && (text.trim() || images.length || files.length || audio)));

    const composePlaceholder = $derived(
        deliveryMethod === "direct"
            ? t("messages.compose_hint_direct")
            : deliveryMethod === "propagated"
              ? t("messages.compose_hint_propagated")
              : deliveryMethod === "opportunistic"
                ? t("messages.compose_hint_opportunistic")
                : t("messages.compose_hint_automatic")
    );

    export function clear() {
        text = "";
        releaseImageUrls();
        images = [];
        imageUrls = [];
        files = [];
        if (audio?.audio_preview_url) URL.revokeObjectURL(audio.audio_preview_url);
        audio = null;
        replyingTo = null;
        if (fileInput) fileInput.value = "";
    }

    export function appendText(extra: string) {
        text = text ? `${text}\n${extra}` : extra;
    }

    export async function sendNow() {
        await sendMessage();
    }

    function releaseImageUrls() {
        for (const url of imageUrls) URL.revokeObjectURL(url);
    }

    function addImage(file: File) {
        const allowed = file.type.startsWith("image/") || file.type === "video/webm";
        if (!allowed) return;
        images = images.concat(file);
        imageUrls = imageUrls.concat(URL.createObjectURL(file));
    }

    function removeImage(index: number) {
        const url = imageUrls[index];
        if (url) URL.revokeObjectURL(url);
        images = images.filter((_, idx) => idx !== index);
        imageUrls = imageUrls.filter((_, idx) => idx !== index);
    }

    function onPaste(event: ClipboardEvent) {
        const pastedFiles = Array.from(event.clipboardData?.files || []).filter((f) => f.type.startsWith("image/"));
        if (pastedFiles.length > 0) {
            event.preventDefault();
            for (const f of pastedFiles) addImage(f);
        }
    }

    function locationSettingsToastAction() {
        return {
            label: t("common.configure"),
            handler: () => {
                window.location.hash = "#/settings?section=location";
            },
        };
    }

    function appendLocationMapUri(lat: number, lon: number) {
        const mapUri = buildMeshchatMapUri({ lat, lon, zoom: 15 });
        appendText(mapUri || "");
        ToastUtils.success(t("messages.location_sent"), 3000, "location_share");
    }

    async function toggleLocation() {
        const toastKey = "location_share";
        const source = String(config?.location_source || "browser");
        if (source === "disabled") {
            ToastUtils.show(t("messages.location_disabled"), "error", 8000, toastKey, locationSettingsToastAction());
            return;
        }
        if (source === "manual") {
            const lat = parseFloat(String(config?.location_manual_lat ?? ""));
            const lon = parseFloat(String(config?.location_manual_lon ?? ""));
            if (isNaN(lat) || isNaN(lon)) {
                ToastUtils.error("Invalid manual coordinates in settings", 5000, toastKey);
                return;
            }
            appendLocationMapUri(lat, lon);
            return;
        }
        if (source === "android") {
            if (!isAndroidLocationSupported()) {
                ToastUtils.show(
                    t("messages.location_android_unavailable"),
                    "error",
                    8000,
                    toastKey,
                    locationSettingsToastAction()
                );
                return;
            }
            ToastUtils.loading(t("messages.fetching_location"), 0, toastKey);
            try {
                const pos = await getAndroidPosition();
                appendLocationMapUri(Number(pos.latitude.toFixed(6)), Number(pos.longitude.toFixed(6)));
            } catch (err) {
                const code = (err as { code?: string } | null)?.code;
                const key =
                    code === "permission_denied"
                        ? "messages.location_permission_denied"
                        : code === "location_disabled"
                          ? "messages.location_service_off"
                          : "messages.location_failed";
                ToastUtils.show(t(key), "error", 8000, toastKey, locationSettingsToastAction());
            }
            return;
        }
        if (!navigator.geolocation) {
            ToastUtils.warning(t("map.geolocation_not_supported"));
            return;
        }
        ToastUtils.loading(t("messages.fetching_location"), 0, toastKey);
        navigator.geolocation.getCurrentPosition(
            (pos) => {
                const lat = Number(pos.coords.latitude.toFixed(6));
                const lon = Number(pos.coords.longitude.toFixed(6));
                appendLocationMapUri(lat, lon);
            },
            () => {
                ToastUtils.show(
                    t("messages.location_failed"),
                    "error",
                    8000,
                    toastKey,
                    locationSettingsToastAction()
                );
            },
            { enableHighAccuracy: true, timeout: 30000, maximumAge: 0 }
        );
    }

    async function startAudioRecording(args: { codec: string; mode?: string }) {
        if (isRecordingAudioAttachment) return;
        const session = await startAudioRecordingSession({
            codec: args.codec,
            mode: args.mode,
            hasExistingAudio: Boolean(audio),
        });
        if (!session) return;
        if (destroyed) {
            // Unmounted while getUserMedia was still resolving; release the mic.
            void stopAudioRecordingSession(session);
            return;
        }
        activeRecording = session;
        isRecordingAudioAttachment = true;
        audioAttachmentRecordingDuration = "0:00";
        audioRecordingTimer = setInterval(() => {
            if (activeRecording) {
                audioAttachmentRecordingDuration = formatRecordingDuration(Date.now() - activeRecording.startedAt);
            }
        }, 1000);
    }

    async function stopAudioRecording() {
        if (audioRecordingTimer) clearInterval(audioRecordingTimer);
        audioRecordingTimer = null;
        if (!isRecordingAudioAttachment || !activeRecording) return;
        isRecordingAudioAttachment = false;
        const result = await stopAudioRecordingSession(activeRecording);
        if (result) {
            if (destroyed) {
                URL.revokeObjectURL(result.audio_preview_url);
            } else {
                audio = result;
            }
        }
        activeRecording = null;
    }

    async function requestLocation() {
        if (!selectedHash) return;
        try {
            // Telemetry request command asks the peer to report its position.
            await window.api.post("/api/v1/lxmf-messages/send", {
                lxmf_message: {
                    destination_hash: selectedHash,
                    content: "",
                    fields: {
                        commands: [{ "0x01": Math.floor(Date.now() / 1000) }],
                    },
                },
            });
            ToastUtils.success(t("messages.location_request_sent"));
        } catch (e) {
            console.log(e);
            ToastUtils.error(t("messages.failed_send_location_request"));
        }
    }

    async function sendCommandOrRequest() {
        if (!selectedHash) return;
        try {
            const commands = parseCommandOrRequestText(text);
            await window.api.post("/api/v1/lxmf-messages/send", {
                lxmf_message: {
                    destination_hash: selectedHash,
                    content: "",
                    fields: { commands },
                },
            });
            text = "";
            pendingSendAsCommandOrRequest = false;
            ToastUtils.success("Command or request sent");
        } catch (e) {
            console.log(e);
            ToastUtils.error(`Failed to send command/request: ${(e as Error)?.message || e}`);
        }
    }

    async function sendMessage() {
        if (pendingSendAsCommandOrRequest) {
            await sendCommandOrRequest();
            return;
        }
        if (!canSendMessage || !selectedHash) return;
        try {
            const job = await buildOutboundJob({
                destinationHash: selectedHash,
                deliveryMethod,
                text,
                files,
                images,
                audio,
                replyToHash: replyingTo?.lxmf_message.hash || null,
                replyQuotedContent: replyingTo?.lxmf_message.content || null,
                myLxmfAddressHash,
                confirmOversized: (size) =>
                    DialogUtils.confirm(t("messages.send_oversized_confirm", { size: String(size) })),
            });
            if (!job) return;
            const optimistic = optimisticMessage(job, peerPathNeedsRefresh(peerPathSnapshot));
            clear();
            onjobCreated?.(job, optimistic);
            onscrolltobottom?.();
        } catch (error) {
            const message = (error as Error)?.message || t("messages.failed_to_send");
            await DialogUtils.alert(message);
        }
    }

    function composeEnter() {
        if (navigator.userAgent.match(/Android|iPhone|iPad|iPod/i)) {
            text += "\n";
        } else {
            void sendMessage();
        }
    }
</script>

<div class="relative w-full">
    <ConversationViewerComposerPickerHost
        bind:this={pickerHost}
        bind:text
        bind:isComposeTranslateOpen
        bind:isTranslatingMessage
        {translateOptions}
        onaddimage={addImage}
    />

    <ConversationComposer
        bind:text
        bind:deliveryMethod
        {imageUrls}
        imageFiles={images}
        {files}
        {audio}
        {replyingTo}
        {canSendMessage}
        compactSendLayout={false}
        {isRecordingAudioAttachment}
        {audioAttachmentRecordingDuration}
        {isTranslatingMessage}
        isPeerBlocked={isSelectedPeerBlocked}
        {hasTranslator}
        translateBarOpen={isComposeTranslateOpen}
        {composePlaceholder}
        sendingTooltip={t("messages.send_pathfinding_tooltip")}
        onsend={() => void sendMessage()}
        onaddfiles={() => fileInput?.click()}
        onaddimage={addImage}
        onaddvideo={() => videoInput?.click()}
        onrequestlocation={() => void requestLocation()}
        onsendcommandorrequest={() => {
            pendingSendAsCommandOrRequest = true;
        }}
        onstartrecording={(args) => void startAudioRecording(args)}
        onstoprecording={() => void stopAudioRecording()}
        onremovefile={(f) => {
            files = files.filter((candidate) => candidate !== f);
        }}
        onremoveimage={removeImage}
        onremoveaudio={() => {
            if (audio?.audio_preview_url) URL.revokeObjectURL(audio.audio_preview_url);
            audio = null;
        }}
        oncancelreply={() => {
            replyingTo = null;
        }}
        onpaste={onPaste}
        ontoggleemojipicker={() => pickerHost?.toggleEmojiPicker()}
        ontogglelocation={toggleLocation}
        ontoggletranslate={() => pickerHost?.toggleTranslate()}
        onsendpapercompose={() => onsendpapercompose?.()}
        onenter={composeEnter}
        onshiftenter={() => {
            text += "\n";
        }}
    />

    <input
        bind:this={fileInput}
        type="file"
        multiple
        class="hidden"
        onchange={(event) => {
            files = files.concat(Array.from(event.currentTarget.files || []));
            // Clear so picking the same file again re-fires change.
            event.currentTarget.value = "";
        }}
    />

    <!-- hidden video input for the mobile attachments menu -->
    <input
        bind:this={videoInput}
        type="file"
        accept="video/*"
        class="hidden"
        onchange={(event) => {
            files = files.concat(Array.from(event.currentTarget.files || []));
            event.currentTarget.value = "";
        }}
    />
</div>
