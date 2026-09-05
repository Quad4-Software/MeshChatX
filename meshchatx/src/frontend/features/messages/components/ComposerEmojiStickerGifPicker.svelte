<!-- SPDX-License-Identifier: 0BSD -->

<script lang="ts">
    import MaterialDesignIcon from "../../../ui/svelte/MaterialDesignIcon.svelte";
    import { t } from "../../../js/i18n.js";
    import InViewAnimatedImg from "./InViewAnimatedImg.svelte";

    export type ComposerPickerTab = "emoji" | "stickers" | "gifs";

    export type ComposerSticker = {
        id: string | number;
        name?: string | null;
        emoji?: string | null;
        image_type?: string | null;
        pack_id?: string | number | null;
        [key: string]: unknown;
    };

    export type ComposerStickerPack = {
        id: string | number;
        title?: string | null;
        [key: string]: unknown;
    };

    export type ComposerGif = {
        id: string | number;
        name?: string | null;
        usage_count?: number | null;
        [key: string]: unknown;
    };

    let {
        open = false,
        activeTab = "emoji",
        emojiPickerDataUrl = "",
        emojiPickerThemeClass = "",
        stickers = [],
        stickerPacks = [],
        activeStickerPackId = null,
        gifs = [],
        stickerDropActive = false,
        gifDropActive = false,
        isStickerUploading = false,
        isGifUploading = false,
        stickerImageUrl = (id) => `/api/v1/stickers/${id}/image`,
        gifImageUrl = (id) => `/api/v1/gifs/${id}/image`,
        ontabchange,
        onpackchange,
        onemojiclick,
        onstickerselect,
        ongifselect,
        onstickerfiles,
        ongiffiles,
        onstickerdragactivechange,
        ongifdragactivechange,
    }: {
        open?: boolean;
        activeTab?: ComposerPickerTab;
        emojiPickerDataUrl?: string;
        emojiPickerThemeClass?: string;
        stickers?: ComposerSticker[];
        stickerPacks?: ComposerStickerPack[];
        activeStickerPackId?: string | number | null;
        gifs?: ComposerGif[];
        stickerDropActive?: boolean;
        gifDropActive?: boolean;
        isStickerUploading?: boolean;
        isGifUploading?: boolean;
        stickerImageUrl?: (id: string | number) => string;
        gifImageUrl?: (id: string | number) => string;
        ontabchange?: (tab: ComposerPickerTab) => void;
        onpackchange?: (packId: string | number | null) => void;
        onemojiclick?: (event: CustomEvent) => void;
        onstickerselect?: (sticker: ComposerSticker) => void;
        ongifselect?: (gif: ComposerGif) => void;
        onstickerfiles?: (files: FileList) => void;
        ongiffiles?: (files: FileList) => void;
        onstickerdragactivechange?: (active: boolean) => void;
        ongifdragactivechange?: (active: boolean) => void;
    } = $props();

    let stickerUploadInput: HTMLInputElement | undefined = $state();
    let gifUploadInput: HTMLInputElement | undefined = $state();

    const visibleStickers = $derived(
        activeStickerPackId === null ? stickers : stickers.filter((sticker) => sticker.pack_id === activeStickerPackId)
    );
    const showDropRing = $derived(
        (stickerDropActive && activeTab === "stickers") || (gifDropActive && activeTab === "gifs")
    );

    function onDragOver(event: DragEvent, setActive?: (active: boolean) => void) {
        event.preventDefault();
        event.stopPropagation();
        if (event.dataTransfer) event.dataTransfer.dropEffect = "copy";
        setActive?.(true);
    }

    function onDragLeave(event: DragEvent, setActive?: (active: boolean) => void) {
        event.preventDefault();
        event.stopPropagation();
        const currentTarget = event.currentTarget;
        if (
            currentTarget instanceof HTMLElement &&
            event.relatedTarget instanceof Node &&
            currentTarget.contains(event.relatedTarget)
        ) {
            return;
        }
        setActive?.(false);
    }

    function onDrop(event: DragEvent, onfiles?: (files: FileList) => void, setActive?: (active: boolean) => void) {
        event.preventDefault();
        event.stopPropagation();
        setActive?.(false);
        if (event.dataTransfer?.files.length) onfiles?.(event.dataTransfer.files);
    }

    function onFileInput(event: Event, onfiles?: (files: FileList) => void) {
        const input = event.currentTarget as HTMLInputElement;
        if (input.files?.length) onfiles?.(input.files);
        input.value = "";
    }
</script>

{#if open}
    <div
        class="absolute bottom-full right-0 mb-2 z-50 w-[min(320px,85vw)] max-h-[min(420px,70vh)] flex flex-col rounded-2xl border border-sem-border bg-sem-surface shadow-xl overflow-hidden {showDropRing
            ? 'ring-2 ring-blue-500/50 ring-offset-2 ring-offset-white dark:ring-offset-zinc-900'
            : ''}"
        onclick={(event) => event.stopPropagation()}
        role="presentation"
    >
        <div class="flex shrink-0 border-b border-sem-border p-1 gap-0.5" role="tablist">
            <button
                type="button"
                role="tab"
                aria-selected={activeTab === "emoji"}
                aria-controls="composer-picker-emojis"
                class="flex-1 rounded-lg px-2 py-1.5 text-xs font-medium transition-colors {activeTab === 'emoji'
                    ? 'bg-blue-100 dark:bg-blue-950/60 text-blue-800 dark:text-blue-200'
                    : 'text-sem-fg-muted hover:bg-sem-surface-muted'}"
                onclick={() => ontabchange?.("emoji")}
            >
                {t("stickers.tab_emojis")}
            </button>
            <button
                type="button"
                role="tab"
                aria-selected={activeTab === "stickers"}
                aria-controls="composer-picker-stickers"
                class="flex-1 rounded-lg px-2 py-1.5 text-xs font-medium transition-colors {activeTab === 'stickers'
                    ? 'bg-blue-100 dark:bg-blue-950/60 text-blue-800 dark:text-blue-200'
                    : 'text-sem-fg-muted hover:bg-sem-surface-muted'}"
                onclick={() => ontabchange?.("stickers")}
            >
                {t("stickers.tab_stickers")}
            </button>
            <button
                type="button"
                role="tab"
                aria-selected={activeTab === "gifs"}
                aria-controls="composer-picker-gifs"
                class="flex-1 rounded-lg px-2 py-1.5 text-xs font-medium transition-colors {activeTab === 'gifs'
                    ? 'bg-blue-100 dark:bg-blue-950/60 text-blue-800 dark:text-blue-200'
                    : 'text-sem-fg-muted hover:bg-sem-surface-muted'}"
                onclick={() => ontabchange?.("gifs")}
            >
                {t("gifs.tab_gifs")}
            </button>
        </div>

        <div
            id="composer-picker-emojis"
            hidden={activeTab !== "emoji"}
            class="min-h-0 flex-1 flex flex-col overflow-hidden p-0"
            role="tabpanel"
            tabindex="0"
        >
            <emoji-picker
                data-source={emojiPickerDataUrl}
                class="compose-emoji-picker {emojiPickerThemeClass}"
                onemoji-click={(event: CustomEvent) => onemojiclick?.(event)}
            ></emoji-picker>
        </div>

        <div
            id="composer-picker-stickers"
            hidden={activeTab !== "stickers"}
            class="min-h-0 flex-1 overflow-y-auto p-2"
            role="tabpanel"
            tabindex="0"
            ondragover={(event) => onDragOver(event, onstickerdragactivechange)}
            ondragleave={(event) => onDragLeave(event, onstickerdragactivechange)}
            ondrop={(event) => onDrop(event, onstickerfiles, onstickerdragactivechange)}
        >
            <input
                bind:this={stickerUploadInput}
                type="file"
                accept="image/png,image/jpeg,image/gif,image/webp,image/bmp,video/webm,application/x-tgsticker,.png,.jpg,.jpeg,.gif,.webp,.bmp,.webm,.tgs"
                multiple
                class="hidden"
                onchange={(event) => onFileInput(event, onstickerfiles)}
            />
            {#if stickerPacks.length > 0}
                <div class="flex shrink-0 gap-1 overflow-x-auto pb-2 mb-2 border-b border-sem-border">
                    <button
                        type="button"
                        class="shrink-0 rounded-lg px-2 py-1 text-[11px] font-medium border {activeStickerPackId ===
                        null
                            ? 'bg-blue-100 dark:bg-blue-950/60 border-blue-300 dark:border-blue-700 text-blue-800 dark:text-blue-200'
                            : 'border-transparent text-sem-fg-muted hover:bg-sem-surface-muted'}"
                        onclick={() => onpackchange?.(null)}
                    >
                        {t("sticker_packs.all")}
                    </button>
                    {#each stickerPacks as pack (pack.id)}
                        <button
                            type="button"
                            class="shrink-0 rounded-lg px-2 py-1 text-[11px] font-medium border max-w-[120px] truncate {activeStickerPackId ===
                            pack.id
                                ? 'bg-blue-100 dark:bg-blue-950/60 border-blue-300 dark:border-blue-700 text-blue-800 dark:text-blue-200'
                                : 'border-transparent text-sem-fg-muted hover:bg-sem-surface-muted'}"
                            title={pack.title ?? ""}
                            onclick={() => onpackchange?.(pack.id)}
                        >
                            {pack.title ?? ""}
                        </button>
                    {/each}
                </div>
            {/if}
            {#if visibleStickers.length > 0}
                <div class="grid grid-cols-4 gap-2 mb-2">
                    {#each visibleStickers as sticker (sticker.id)}
                        <button
                            type="button"
                            class="aspect-square rounded-lg overflow-hidden border border-sem-border hover:ring-2 hover:ring-blue-500/50 bg-gray-50 dark:bg-zinc-800"
                            title={sticker.name ?? sticker.emoji ?? t("stickers.tab_stickers")}
                            onclick={() => onstickerselect?.(sticker)}
                        >
                            {#if sticker.image_type?.toLowerCase() === "webm"}
                                <video
                                    src={stickerImageUrl(sticker.id)}
                                    class="block w-full h-full object-contain"
                                    autoplay
                                    loop
                                    muted
                                    playsinline
                                ></video>
                            {:else if sticker.image_type?.toLowerCase() === "tgs"}
                                <span
                                    class="flex w-full h-full items-center justify-center bg-gray-200/80 dark:bg-zinc-700/50 text-sem-fg-muted"
                                >
                                    <MaterialDesignIcon
                                        iconName="animation-outline"
                                        class="w-[42%] h-[42%] opacity-70"
                                    />
                                </span>
                            {:else}
                                <img
                                    src={stickerImageUrl(sticker.id)}
                                    class="block w-full h-full object-contain"
                                    decoding="async"
                                    loading="lazy"
                                    alt=""
                                />
                            {/if}
                        </button>
                    {/each}
                </div>
            {:else}
                <div class="text-center text-sm text-sem-fg-muted mb-2 px-1">
                    {t("stickers.empty_library")}
                </div>
            {/if}
            <button
                type="button"
                class="w-full rounded-xl border-2 border-dashed border-gray-300 dark:border-zinc-600 px-2 py-2 text-xs hover:border-blue-400 {stickerDropActive
                    ? 'border-blue-500 bg-blue-50/70 dark:bg-blue-950/40'
                    : ''}"
                disabled={isStickerUploading}
                onclick={() => stickerUploadInput?.click()}
            >
                <span class="flex items-center justify-center gap-1">
                    <MaterialDesignIcon iconName="upload" class="size-4 text-blue-500" />
                    {t("stickers.upload_short")}
                </span>
            </button>
        </div>

        <div
            id="composer-picker-gifs"
            hidden={activeTab !== "gifs"}
            class="min-h-0 flex-1 overflow-y-auto p-2"
            role="tabpanel"
            tabindex="0"
            ondragover={(event) => onDragOver(event, ongifdragactivechange)}
            ondragleave={(event) => onDragLeave(event, ongifdragactivechange)}
            ondrop={(event) => onDrop(event, ongiffiles, ongifdragactivechange)}
        >
            <input
                bind:this={gifUploadInput}
                type="file"
                accept="image/gif,image/webp,.gif,.webp"
                multiple
                class="hidden"
                onchange={(event) => onFileInput(event, ongiffiles)}
            />
            {#if gifs.length > 0}
                <div class="grid grid-cols-2 gap-2 mb-2">
                    {#each gifs as gif (gif.id)}
                        <button
                            type="button"
                            class="relative aspect-video rounded-lg overflow-hidden border border-sem-border hover:ring-2 hover:ring-blue-500/50 group"
                            title={gif.name ?? t("gifs.tab_gifs")}
                            onclick={() => ongifselect?.(gif)}
                        >
                            <InViewAnimatedImg
                                src={gifImageUrl(gif.id)}
                                fitParent
                                imgClass="w-full h-full object-contain bg-gray-50 dark:bg-zinc-800"
                            />
                            {#if (gif.usage_count ?? 0) > 0}
                                <span
                                    class="pointer-events-none absolute bottom-1 right-1 rounded-full bg-black/60 text-white text-[10px] px-1.5 py-0.5"
                                >
                                    {gif.usage_count}
                                </span>
                            {/if}
                        </button>
                    {/each}
                </div>
            {:else}
                <div class="text-center text-sm text-sem-fg-muted mb-2 px-1">
                    {t("gifs.empty_library")}
                </div>
            {/if}
            <button
                type="button"
                class="w-full rounded-xl border-2 border-dashed border-gray-300 dark:border-zinc-600 px-3 py-3 text-left transition-colors hover:border-blue-400 hover:bg-blue-50/60 dark:hover:bg-blue-950/30 {gifDropActive
                    ? 'border-blue-500 bg-blue-50/70 dark:bg-blue-950/40'
                    : ''}"
                disabled={isGifUploading}
                onclick={() => gifUploadInput?.click()}
            >
                <span class="flex items-start gap-2">
                    <MaterialDesignIcon iconName="upload" class="size-5 shrink-0 text-blue-500 mt-0.5" />
                    <span class="min-w-0">
                        <span class="block text-xs font-medium text-sem-fg">
                            {gifs.length > 0 ? t("gifs.add_more_hint") : t("gifs.drop_or_click_hint")}
                        </span>
                        {#if isGifUploading}
                            <span class="block text-[11px] text-sem-accent mt-1">{t("common.loading")}</span>
                        {/if}
                    </span>
                </span>
            </button>
        </div>
    </div>
{/if}
