<!-- SPDX-License-Identifier: 0BSD -->

<script lang="ts">
    import { t } from "../../../js/i18n.js";
    import ToastUtils from "../../../js/ToastUtils.js";
    import ComposerEmojiStickerGifPicker, {
        type ComposerGif,
        type ComposerPickerTab,
        type ComposerSticker,
        type ComposerStickerPack,
    } from "./ComposerEmojiStickerGifPicker.svelte";
    import ConversationTranslateBars from "./ConversationTranslateBars.svelte";
    import {
        loadGifs,
        loadStickerPacks,
        loadStickers,
        uploadGifFile,
        uploadStickerFile,
    } from "../lib/conversationStickersGifs.js";
    import { translateText, type LangOption } from "../lib/conversationTranslate.js";
    import { EMOJI_PICKER_DATA_URL, emojiPickerThemeClass, unicodeFromEmojiClickEvent } from "../lib/emojiPicker.js";

    let {
        text = $bindable(""),
        translateOptions = [] as LangOption[],
        isComposeTranslateOpen = $bindable(false),
        isTranslatingMessage = $bindable(false),
        onaddimage,
    }: {
        text?: string;
        translateOptions?: LangOption[];
        isComposeTranslateOpen?: boolean;
        isTranslatingMessage?: boolean;
        onaddimage?: (file: File) => void;
    } = $props();

    const emojiPickerDataUrl = EMOJI_PICKER_DATA_URL;
    const emojiTheme = $derived(emojiPickerThemeClass());

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
    let composeTranslateTargetLang = $state("en");

    export function toggleEmojiPicker() {
        isEmojiPickerOpen = !isEmojiPickerOpen;
        if (isEmojiPickerOpen) {
            void ensureStickersLoaded();
            void ensureGifsLoaded();
        }
    }

    export function toggleTranslate() {
        isComposeTranslateOpen = !isComposeTranslateOpen;
    }

    export function closeEmojiPicker() {
        isEmojiPickerOpen = false;
    }

    export function closeTranslate() {
        isComposeTranslateOpen = false;
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

    function onTabChange(tab: ComposerPickerTab) {
        activePickerTab = tab;
        if (tab === "stickers") void ensureStickersLoaded();
        if (tab === "gifs") void ensureGifsLoaded();
    }

    function onEmojiClick(event: CustomEvent) {
        const char = unicodeFromEmojiClickEvent(event);
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
            const file = new File([response.data as Blob], `${sticker.name || "sticker"}.${type}`, { type: mime });
            onaddimage?.(file);
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
            const file = new File([response.data as Blob], `${gif.name || "gif"}.gif`, { type: "image/gif" });
            onaddimage?.(file);
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
</script>

<ComposerEmojiStickerGifPicker
    open={isEmojiPickerOpen}
    activeTab={activePickerTab}
    {emojiPickerDataUrl}
    emojiPickerThemeClass={emojiTheme}
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
