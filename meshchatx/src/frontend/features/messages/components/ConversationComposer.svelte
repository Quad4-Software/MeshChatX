<!-- SPDX-License-Identifier: 0BSD AND MIT -->

<script lang="ts">
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
            {files}
            {audio}
            {onremoveimage}
            {onremovefile}
            {onremoveaudio}
            {onopenimage}
        />

        <div class="flex items-center gap-2 min-w-0">
            <div class="relative flex-1 min-w-0">
                <textarea
                    bind:this={messageInput}
                    bind:value={text}
                    readonly={isTranslatingMessage}
                    class="bg-sem-surface border border-sem-border text-sem-fg text-sm rounded-xl focus:ring-2 focus:ring-sem-focus focus:border-sem-focus-border block w-full min-w-0 pl-3 sm:pl-4 pr-16 py-2.5 resize-none shadow-xs transition-all placeholder:text-sem-fg-muted min-h-[44px] max-h-[200px] overflow-y-auto leading-snug"
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

        <div class="flex flex-wrap gap-2 items-center mt-2">
            <button
                type="button"
                class="my-auto inline-flex items-center gap-x-1 rounded-lg px-2 py-1.5 text-xs font-medium text-sem-fg-muted hover:bg-sem-surface-muted hover:text-gray-900 dark:hover:text-white transition-colors"
                onclick={() => onaddfiles?.()}
            >
                <MaterialDesignIcon iconName="paperclip-plus" class="w-4 h-4" />
                <span class="hidden sm:inline whitespace-nowrap">{t("messages.add_files")}</span>
            </button>
            <AddImageButton onaddimage={(file) => onaddimage?.(file)} />
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
