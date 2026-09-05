<!-- SPDX-License-Identifier: 0BSD AND MIT -->

<script lang="ts">
    import { t } from "../../../js/i18n.js";
    import DialogUtils from "../../../js/DialogUtils.js";
    import ToastUtils from "../../../js/ToastUtils.js";
    import { buildMeshchatMapUri } from "../../../js/mapLinkUtils.js";
    import ComposerEmojiStickerGifPicker, {
        type ComposerGif,
        type ComposerPickerTab,
        type ComposerSticker,
        type ComposerStickerPack,
    } from "./ComposerEmojiStickerGifPicker.svelte";
    import ConversationComposer from "./ConversationComposer.svelte";
    import ConversationTranslateBars from "./ConversationTranslateBars.svelte";
    import {
        startAudioRecordingSession,
        stopAudioRecordingSession,
        formatRecordingDuration,
        type ActiveAudioRecording,
    } from "../lib/conversationAudioRecorder.js";
    import {
        loadGifs,
        loadStickerPacks,
        loadStickers,
        uploadGifFile,
        uploadStickerFile,
    } from "../lib/conversationStickersGifs.js";
    import { translateText, type LangOption } from "../lib/conversationTranslate.js";
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
        translateOptions?: LangOption[];
        hasTranslator?: boolean;
        text?: string;
        replyingTo?: ViewerChatItem | null;
        onjobCreated?: (job: OutboundJob, optimistic: ReturnType<typeof optimisticMessage>) => void;
        onsendpapercompose?: () => void;
        onscrolltobottom?: () => void;
    } = $props();

    let fileInput: HTMLInputElement | undefined = $state();
    let deliveryMethod = $state<string | null>(null);
    let images = $state.raw<File[]>([]);
    let imageUrls = $state.raw<string[]>([]);
    let files = $state.raw<File[]>([]);
    let audio = $state<ComposeAudio | null>(null);

    let isEmojiPickerOpen = $state(false);
    let activePickerTab = $state<ComposerPickerTab>("emoji");
    let stickers = $state.raw<ComposerSticker[]>([]);
    let stickerPacks = $state.raw<ComposerStickerPack[]>([]);
    let activeStickerPackId = $state<string | number | null>(null);
    let gifs = $state.raw<ComposerGif[]>([]);
    let isStickerUploading = $state(false);
    let isGifUploading = $state(false);
    let stickerDropActive = $state(false);
    let gifDropActive = $state(false);

    let isComposeTranslateOpen = $state(false);
    let composeTranslateTargetLang = $state("en");
    let isTranslatingMessage = $state(false);

    let activeRecording = $state<ActiveAudioRecording | null>(null);
    let isRecordingAudioAttachment = $state(false);
    let audioAttachmentRecordingDuration = $state("0:00");
    let audioRecordingTimer: ReturnType<typeof setInterval> | null = null;

    const canSendMessage = $derived(
        Boolean(selectedPeer && (text.trim() || images.length || files.length || audio))
    );

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
        if (!file.type.startsWith("image/")) return;
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
        const pastedFiles = Array.from(event.clipboardData?.files || []).filter((f) =>
            f.type.startsWith("image/")
        );
        if (pastedFiles.length > 0) {
            event.preventDefault();
            for (const f of pastedFiles) addImage(f);
        }
    }

    async function ensureStickersLoaded() {
        if (stickers.length === 0) {
            stickers = await loadStickers(window.api);
            stickerPacks = await loadStickerPacks(window.api);
        }
    }

    async function ensureGifsLoaded() {
        if (gifs.length === 0) {
            gifs = await loadGifs(window.api);
        }
    }

    async function toggleEmojiPicker() {
        isEmojiPickerOpen = !isEmojiPickerOpen;
        if (isEmojiPickerOpen) {
            void ensureStickersLoaded();
            void ensureGifsLoaded();
        }
    }

    function onTabChange(tab: ComposerPickerTab) {
        activePickerTab = tab;
        if (tab === "stickers") void ensureStickersLoaded();
        if (tab === "gifs") void ensureGifsLoaded();
    }

    function onEmojiClick(event: CustomEvent) {
        const char =
            (event.detail as { unicode?: string })?.unicode ||
            (event.detail as { emoji?: { unicode?: string } })?.emoji?.unicode ||
            String(event.detail || "");
        if (char) {
            text += char;
        }
    }

    async function selectSticker(sticker: ComposerSticker) {
        try {
            const response = await window.api.get(`/api/v1/stickers/${sticker.id}/image`, {
                responseType: "blob",
            });
            const type = String(sticker.image_type || "png").toLowerCase();
            const mime = type === "webm" ? "video/webm" : `image/${type}`;
            const file = new File([response.data as BlobPart], `${sticker.name || "sticker"}.${type}`, { type: mime });
            addImage(file);
            isEmojiPickerOpen = false;
        } catch {
            ToastUtils.error(t("stickers.save_failed"));
        }
    }

    async function selectGif(gif: ComposerGif) {
        try {
            const response = await window.api.get(`/api/v1/gifs/${gif.id}/image`, {
                responseType: "blob",
            });
            const file = new File([response.data as BlobPart], `${gif.name || "gif"}.gif`, { type: "image/gif" });
            addImage(file);
            void window.api.post(`/api/v1/gifs/${gif.id}/use`);
            isEmojiPickerOpen = false;
        } catch {
            ToastUtils.error(t("gifs.save_failed"));
        }
    }

    async function handleStickerFiles(uploadedFiles: FileList) {
        isStickerUploading = true;
        try {
            for (const f of Array.from(uploadedFiles)) {
                await uploadStickerFile(window.api, f, activeStickerPackId);
            }
            stickers = await loadStickers(window.api);
            ToastUtils.success(t("stickers.uploaded_count", { count: uploadedFiles.length }));
        } catch {
            ToastUtils.error(t("stickers.save_failed"));
        } finally {
            isStickerUploading = false;
        }
    }

    async function handleGifFiles(uploadedFiles: FileList) {
        isGifUploading = true;
        try {
            for (const f of Array.from(uploadedFiles)) {
                await uploadGifFile(window.api, f);
            }
            gifs = await loadGifs(window.api);
            ToastUtils.success(t("gifs.uploaded_count", { count: uploadedFiles.length }));
        } catch {
            ToastUtils.error(t("gifs.save_failed"));
        } finally {
            isGifUploading = false;
        }
    }

    function toggleLocation() {
        if (!navigator.geolocation) {
            ToastUtils.warning(t("map.geolocation_not_supported"));
            return;
        }
        ToastUtils.loading(t("messages.fetching_location"), 2000);
        navigator.geolocation.getCurrentPosition(
            (pos) => {
                const lat = Number(pos.coords.latitude.toFixed(6));
                const lon = Number(pos.coords.longitude.toFixed(6));
                const mapUri = buildMeshchatMapUri({ lat, lon, zoom: 15 });
                appendText(mapUri || "");
                ToastUtils.success(t("messages.location_sent"));
            },
            () => {
                ToastUtils.error(t("map.location_not_determined"));
            },
            { enableHighAccuracy: true, timeout: 10000 }
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
        activeRecording = session;
        isRecordingAudioAttachment = true;
        audioAttachmentRecordingDuration = "0:00";
        audioRecordingTimer = setInterval(() => {
            if (activeRecording) {
                audioAttachmentRecordingDuration = formatRecordingDuration(
                    Date.now() - activeRecording.startedAt
                );
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
            audio = result;
        }
        activeRecording = null;
    }

    async function translateCompose() {
        if (!text.trim() || isTranslatingMessage) return;
        isTranslatingMessage = true;
        try {
            const result = await translateText(window.api, {
                text,
                targetLang: composeTranslateTargetLang,
            });
            if (result.translatedText) {
                text = result.translatedText;
                isComposeTranslateOpen = false;
                ToastUtils.success(t("translator.translate"));
            }
        } catch {
            ToastUtils.error(t("translator.failed_translate"));
        } finally {
            isTranslatingMessage = false;
        }
    }

    async function sendMessage() {
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
    <ComposerEmojiStickerGifPicker
        open={isEmojiPickerOpen}
        activeTab={activePickerTab}
        {stickers}
        {stickerPacks}
        {activeStickerPackId}
        {gifs}
        {isStickerUploading}
        {isGifUploading}
        {stickerDropActive}
        {gifDropActive}
        ontabchange={onTabChange}
        onpackchange={(packId) => {
            activeStickerPackId = packId;
        }}
        onemojiclick={onEmojiClick}
        onstickerselect={selectSticker}
        ongifselect={selectGif}
        onstickerfiles={handleStickerFiles}
        ongiffiles={handleGifFiles}
        onstickerdragactivechange={(act) => {
            stickerDropActive = act;
        }}
        ongifdragactivechange={(act) => {
            gifDropActive = act;
        }}
    />

    <ConversationTranslateBars
        mode="compose"
        open={isComposeTranslateOpen}
        options={translateOptions}
        bind:value={composeTranslateTargetLang}
        working={isTranslatingMessage}
        onconfirm={translateCompose}
        onclose={() => {
            isComposeTranslateOpen = false;
        }}
    />

    <ConversationComposer
        bind:text
        bind:deliveryMethod
        {imageUrls}
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
        ontoggleemojipicker={toggleEmojiPicker}
        ontogglelocation={toggleLocation}
        ontoggletranslate={() => {
            isComposeTranslateOpen = !isComposeTranslateOpen;
        }}
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
        }}
    />
</div>
