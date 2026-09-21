<!-- SPDX-License-Identifier: 0BSD -->

<script lang="ts">
    import { onClickOutside } from "runed";
    import MaterialDesignIcon from "../../../ui/svelte/MaterialDesignIcon.svelte";
    import { t } from "../../../js/i18n.js";
    import ComposerAttachmentStrip from "./ComposerAttachmentStrip.svelte";
    import SendMessageButton from "./composer/SendMessageButton.svelte";
    import AddImageButton from "./composer/AddImageButton.svelte";
    import AddAudioButton from "./composer/AddAudioButton.svelte";

    type AudioAttachment = {
        audio_blob: Blob;
        audio_preview_url: string;
    };

    type ReplyPreview = {
        lxmf_message?: { content?: string };
    };

    let {
        text = $bindable(""),
        deliveryMethod = $bindable(null as string | null),
        imageUrls = [] as string[],
        imageFiles = [] as File[],
        files = [] as File[],
        audio = null as AudioAttachment | null,
        replyingTo = null as ReplyPreview | null,
        canSendMessage = false,
        compactSendLayout = false,
        isRecordingAudioAttachment = false,
        audioAttachmentRecordingDuration = "0:00",
        isTranslatingMessage = false,
        isPeerBlocked = false,
        hasTranslator = false,
        translateBarOpen = false,
        composePlaceholder = "",
        sendingTooltip = "",
        onsend,
        onaddfiles,
        onaddimage,
        onaddvideo,
        onrequestlocation,
        onstartrecording,
        onstoprecording,
        onremovefile,
        onremoveimage,
        onremoveaudio,
        onopenimage,
        oncancelreply,
        onpaste,
        ontoggleemojipicker,
        ontogglelocation,
        ontoggletranslate,
        onsendcommandorrequest,
        onsendpapercompose,
        onenter,
        onshiftenter,
    }: {
        text?: string;
        deliveryMethod?: string | null;
        imageUrls?: string[];
        imageFiles?: File[];
        files?: File[];
        audio?: AudioAttachment | null;
        replyingTo?: ReplyPreview | null;
        canSendMessage?: boolean;
        compactSendLayout?: boolean;
        isRecordingAudioAttachment?: boolean;
        audioAttachmentRecordingDuration?: string;
        isTranslatingMessage?: boolean;
        isPeerBlocked?: boolean;
        hasTranslator?: boolean;
        translateBarOpen?: boolean;
        composePlaceholder?: string;
        sendingTooltip?: string;
        onsend?: () => void;
        onaddfiles?: () => void;
        onaddimage?: (file: File) => void;
        onaddvideo?: () => void;
        onrequestlocation?: () => void;
        onstartrecording?: (args: { codec: string; mode?: string }) => void;
        onstoprecording?: () => void;
        onremovefile?: (file: File) => void;
        onremoveimage?: (index: number) => void;
        onremoveaudio?: () => void;
        onopenimage?: (url: string, gallery: string[]) => void;
        oncancelreply?: () => void;
        onpaste?: (event: ClipboardEvent) => void;
        ontoggleemojipicker?: () => void;
        ontogglelocation?: () => void;
        ontoggletranslate?: () => void;
        onsendcommandorrequest?: () => void;
        onsendpapercompose?: () => void;
        onenter?: () => void;
        onshiftenter?: () => void;
    } = $props();

    let messageInput: HTMLTextAreaElement | undefined = $state();
    let addImageButton: AddImageButton | undefined = $state();
    let mobileAttachEl: HTMLDivElement | undefined = $state();
    let mobileAttachMenuOpen = $state(false);
    let mobileImageQualityOpen = $state(false);

    function closeMobileAttachMenu() {
        mobileAttachMenuOpen = false;
        mobileImageQualityOpen = false;
    }

    onClickOutside(() => mobileAttachEl, closeMobileAttachMenu);

    function onKeydown(event: KeyboardEvent) {
        if (event.key === "Enter" && !event.shiftKey) {
            event.preventDefault();
            onenter?.();
        } else if (event.key === "Enter" && event.shiftKey) {
            event.preventDefault();
            onshiftenter?.();
        }
    }
</script>

<div
    class="w-full border-t border-sem-border bg-sem-surface px-3 sm:px-4 pt-2 pb-[max(0.5rem,env(safe-area-inset-bottom))]"
>
    <div class="w-full">
        {#if isPeerBlocked}
            <div
                class="mb-3 p-3 bg-yellow-50 dark:bg-yellow-900/20 border border-yellow-200 dark:border-yellow-800 rounded-lg flex items-center gap-2"
            >
                <MaterialDesignIcon iconName="alert" class="w-5 h-5 text-yellow-600 dark:text-yellow-400 shrink-0" />
                <span class="text-sm text-yellow-800 dark:text-yellow-200">{t("messages.banished_peer_notice")}</span>
            </div>
        {/if}

        <ComposerAttachmentStrip
            {imageUrls}
            {imageFiles}
            {files}
            {audio}
            {onremoveimage}
            {onremovefile}
            {onremoveaudio}
            {onopenimage}
        />

        <div class="flex items-center gap-2 min-w-0">
            <div class="relative flex-1 min-w-0">
                <!-- mobile: attachments button inside the input, left side -->
                <div bind:this={mobileAttachEl} class="absolute left-1 top-1/2 -translate-y-1/2 z-10 sm:hidden">
                    <button
                        type="button"
                        class="inline-flex items-center justify-center rounded-lg size-8 text-sem-fg-muted hover:bg-sem-surface-muted hover:text-sem-fg transition-colors"
                        title={t("messages.attachments")}
                        onclick={(event) => {
                            event.stopPropagation();
                            mobileAttachMenuOpen = !mobileAttachMenuOpen;
                            if (!mobileAttachMenuOpen) mobileImageQualityOpen = false;
                        }}
                    >
                        <MaterialDesignIcon iconName="paperclip" class="w-5 h-5" />
                    </button>
                </div>
                {#if mobileAttachMenuOpen}
                    <div
                        class="absolute left-0 bottom-full mb-2 z-50 min-w-[200px] rounded-xl border border-sem-border bg-sem-surface shadow-lg sm:hidden"
                    >
                        <div
                            class="absolute -bottom-[5px] left-4 w-2.5 h-2.5 rotate-45 bg-sem-surface border-b border-r border-sem-border"
                            aria-hidden="true"
                        ></div>
                        <div class="overflow-hidden rounded-xl">
                            <button
                                type="button"
                                class="w-full flex items-center gap-2 px-3 py-2.5 text-sm text-sem-fg-secondary hover:bg-sem-surface-muted"
                                onclick={() => (mobileImageQualityOpen = !mobileImageQualityOpen)}
                            >
                                <MaterialDesignIcon iconName="image-plus" class="size-4" />
                                <span class="flex-1 text-left">{t("messages.add_image")}</span>
                                <MaterialDesignIcon
                                    iconName={mobileImageQualityOpen ? "chevron-up" : "chevron-down"}
                                    class="size-4 text-sem-fg-muted"
                                />
                            </button>
                            {#if mobileImageQualityOpen}
                                <div class="border-t border-sem-border/50">
                                    {#each ["low", "medium", "high", "original"] as quality (quality)}
                                        <button
                                            type="button"
                                            class="w-full text-left pl-9 pr-3 py-2 text-sm text-sem-fg-secondary hover:bg-sem-surface-muted"
                                            onclick={() => {
                                                closeMobileAttachMenu();
                                                addImageButton?.pickImage(quality);
                                            }}
                                        >
                                            {t(`messages.image_quality_${quality}`)}
                                        </button>
                                    {/each}
                                </div>
                            {/if}
                            <button
                                type="button"
                                class="w-full flex items-center gap-2 px-3 py-2.5 text-sm text-sem-fg-secondary hover:bg-sem-surface-muted"
                                onclick={() => {
                                    closeMobileAttachMenu();
                                    onaddvideo?.();
                                }}
                            >
                                <MaterialDesignIcon iconName="video-plus" class="size-4" />
                                {t("messages.add_video")}
                            </button>
                            <button
                                type="button"
                                class="w-full flex items-center gap-2 px-3 py-2.5 text-sm text-sem-fg-secondary hover:bg-sem-surface-muted"
                                onclick={() => {
                                    closeMobileAttachMenu();
                                    ontogglelocation?.();
                                }}
                            >
                                <MaterialDesignIcon iconName="map-marker" class="size-4" />
                                {t("messages.share_location")}
                            </button>
                            <button
                                type="button"
                                class="w-full flex items-center gap-2 px-3 py-2.5 text-sm text-sem-fg-secondary hover:bg-sem-surface-muted"
                                onclick={() => {
                                    closeMobileAttachMenu();
                                    onrequestlocation?.();
                                }}
                            >
                                <MaterialDesignIcon iconName="map-marker-question" class="size-4" />
                                {t("messages.request_location")}
                            </button>
                            <button
                                type="button"
                                class="w-full flex items-center gap-2 px-3 py-2.5 text-sm text-sem-fg-secondary hover:bg-sem-surface-muted"
                                onclick={() => {
                                    closeMobileAttachMenu();
                                    onaddfiles?.();
                                }}
                            >
                                <MaterialDesignIcon iconName="file-plus" class="size-4" />
                                {t("messages.add_files")}
                            </button>
                            {#if hasTranslator && text}
                                <button
                                    type="button"
                                    class="w-full flex items-center gap-2 px-3 py-2.5 text-sm text-sem-fg-secondary hover:bg-sem-surface-muted"
                                    onclick={() => {
                                        closeMobileAttachMenu();
                                        ontoggletranslate?.();
                                    }}
                                >
                                    <MaterialDesignIcon iconName="translate" class="size-4" />
                                    {t("translator.translate")}
                                </button>
                            {/if}
                        </div>
                    </div>
                {/if}
                <textarea
                    bind:this={messageInput}
                    bind:value={text}
                    readonly={isTranslatingMessage}
                    class="bg-sem-surface border border-sem-border text-sem-fg text-sm rounded-xl focus:ring-2 focus:ring-sem-focus focus:border-sem-focus-border block w-full min-w-0 pl-11 sm:pl-4 pr-16 py-2.5 resize-none shadow-xs transition-all placeholder:text-sem-fg-muted min-h-[44px] max-h-[200px] overflow-y-auto leading-snug"
                    rows="1"
                    spellcheck="true"
                    placeholder={composePlaceholder}
                    onkeydown={onKeydown}
                    onpaste={(e) => onpaste?.(e)}></textarea>
                <div class="absolute right-1 top-1/2 -translate-y-1/2 flex items-center gap-0">
                    <AddAudioButton
                        {isRecordingAudioAttachment}
                        onstartrecording={(args) => onstartrecording?.(args)}
                        onstoprecording={() => onstoprecording?.()}
                    >
                        <span class="text-[10px] whitespace-nowrap">
                            {t("messages.recording", { duration: audioAttachmentRecordingDuration })}
                        </span>
                    </AddAudioButton>
                    <button
                        type="button"
                        class="inline-flex shrink-0 items-center justify-center rounded-lg size-8 text-sem-fg-muted hover:bg-sem-surface-muted hover:text-gray-800 dark:hover:text-zinc-100 transition-colors"
                        title={t("stickers.picker_tooltip")}
                        onclick={() => ontoggleemojipicker?.()}
                    >
                        <MaterialDesignIcon iconName="emoticon-outline" class="w-5 h-5" />
                    </button>
                </div>
            </div>
            <div class="shrink-0 flex items-center">
                <SendMessageButton
                    {deliveryMethod}
                    {canSendMessage}
                    isSendingMessage={false}
                    compact={compactSendLayout}
                    {sendingTooltip}
                    canOpenSendMenu={true}
                    onsend={() => onsend?.()}
                    ondeliverymethodchanged={(m) => {
                        deliveryMethod = m;
                    }}
                    onsendcommandorrequest={() => onsendcommandorrequest?.()}
                    onsendpapercompose={() => onsendpapercompose?.()}
                />
            </div>
        </div>

        {#if replyingTo}
            <div
                class="mt-2 p-2 rounded-xl bg-gray-50 dark:bg-zinc-800/50 border border-sem-border/50 flex items-center gap-3"
            >
                <div class="flex-1 min-w-0 border-l-2 border-sem-accent pl-3">
                    <div class="flex items-center gap-1 text-[11px] font-medium text-sem-accent mb-0.5">
                        <MaterialDesignIcon iconName="reply" class="size-3" />
                        {t("messages.replying_to")}
                    </div>
                    <div class="text-xs text-sem-fg-muted truncate italic">
                        {replyingTo.lxmf_message?.content || t("messages.attachment_placeholder")}
                    </div>
                </div>
                <button
                    type="button"
                    class="p-1.5 hover:bg-sem-surface-muted rounded-lg transition-colors text-gray-400 hover:text-sem-fg"
                    onclick={() => oncancelreply?.()}
                >
                    <MaterialDesignIcon iconName="close" class="w-4 h-4" />
                </button>
            </div>
        {/if}

        <!-- desktop actions; mobile uses the paperclip menu inside the input -->
        <div class="hidden sm:flex flex-wrap gap-2 items-center mt-2">
            <button
                type="button"
                class="my-auto inline-flex items-center gap-x-1 rounded-lg px-2 py-1.5 text-xs font-medium text-sem-fg-muted hover:bg-sem-surface-muted hover:text-gray-900 dark:hover:text-white transition-colors"
                onclick={() => onaddfiles?.()}
            >
                <MaterialDesignIcon iconName="paperclip-plus" class="w-4 h-4" />
                <span class="hidden sm:inline whitespace-nowrap">{t("messages.add_files")}</span>
            </button>
            <AddImageButton bind:this={addImageButton} onaddimage={(file) => onaddimage?.(file)} />
            <button
                type="button"
                class="my-auto inline-flex items-center gap-x-1 rounded-lg px-2 py-1.5 text-xs font-medium text-sem-fg-muted hover:bg-sem-surface-muted hover:text-gray-900 dark:hover:text-white transition-colors"
                title={t("messages.location")}
                onclick={() => ontogglelocation?.()}
            >
                <MaterialDesignIcon iconName="map-marker" class="w-4 h-4" />
                <span class="hidden sm:inline whitespace-nowrap">{t("messages.location")}</span>
            </button>
            {#if hasTranslator && text}
                <button
                    type="button"
                    class="my-auto inline-flex items-center gap-x-1 rounded-lg px-2 py-1.5 text-xs font-medium text-sem-fg-muted hover:bg-sem-surface-muted hover:text-gray-900 dark:hover:text-white transition-colors {translateBarOpen
                        ? 'ring-1 ring-sem-accent/60'
                        : ''}"
                    title={t("translator.translate")}
                    onclick={() => ontoggletranslate?.()}
                >
                    <MaterialDesignIcon iconName="translate" class="w-4 h-4" />
                    <span class="hidden sm:inline whitespace-nowrap">{t("translator.translate")}</span>
                </button>
            {/if}
        </div>
    </div>
</div>
