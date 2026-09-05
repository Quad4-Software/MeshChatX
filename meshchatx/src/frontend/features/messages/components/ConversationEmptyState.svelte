<!-- SPDX-License-Identifier: 0BSD -->

<script lang="ts">
    import MaterialDesignIcon from "../../../ui/svelte/MaterialDesignIcon.svelte";
    import LxmfUserIcon from "../../../ui/svelte/LxmfUserIcon.svelte";
    import EmptyState from "../../../ui/svelte/EmptyState.svelte";
    import Utils from "../../../js/Utils.js";
    import { t } from "../../../js/i18n.js";

    type ConversationPreview = {
        destination_hash?: string | null;
        display_name?: string | null;
        custom_display_name?: string | null;
        contact_image?: string | null;
        lxmf_user_icon?: {
            icon_name?: string;
            foreground_colour?: string;
            background_colour?: string;
        } | null;
        updated_at?: unknown;
        latest_message_preview?: string | null;
        latest_message_title?: string | null;
        [key: string]: unknown;
    };

    type ComposeSuggestion = {
        hash: string;
        name: string;
        icon: string;
        type?: string;
    };

    let {
        latestConversations = [] as ConversationPreview[],
        composeAddress = $bindable(""),
        isSyncingPropagationNode = false,
        isTranslatingMessage = false,
        isComposeInputFocused = $bindable(false),
        composeSuggestions = [] as ComposeSuggestion[],
        selectedComposeSuggestionIndex = 0,
        formatTimeAgo,
        oncompose,
        onsync,
        oncopyaddress,
        onidentities,
        onselectpeer,
        oncomposeenter,
        oncomposeup,
        oncomposedown,
        oncomposebblur,
        onselectsuggestion,
    }: {
        latestConversations?: ConversationPreview[];
        composeAddress?: string;
        isSyncingPropagationNode?: boolean;
        isTranslatingMessage?: boolean;
        isComposeInputFocused?: boolean;
        composeSuggestions?: ComposeSuggestion[];
        selectedComposeSuggestionIndex?: number;
        formatTimeAgo?: (ts: unknown) => string;
        oncompose?: () => void;
        onsync?: () => void;
        oncopyaddress?: () => void;
        onidentities?: () => void;
        onselectpeer?: (chat: ConversationPreview) => void;
        oncomposeenter?: () => void;
        oncomposeup?: () => void;
        oncomposedown?: () => void;
        oncomposebblur?: () => void;
        onselectsuggestion?: (suggestion: ComposeSuggestion) => void;
    } = $props();

    function onAddressKeydown(event: KeyboardEvent) {
        if (event.key === "Enter") {
            event.preventDefault();
            oncomposeenter?.();
        } else if (event.key === "ArrowUp") {
            event.preventDefault();
            oncomposeup?.();
        } else if (event.key === "ArrowDown") {
            event.preventDefault();
            oncomposedown?.();
        }
    }
</script>

<div class="flex flex-col h-full overflow-y-auto bg-gray-50/50 dark:bg-zinc-950/50">
    <div class="max-w-2xl mx-auto w-full px-4 py-8 sm:py-10 flex flex-col items-center">
        <EmptyState
            icon="message-text-outline"
            title={t("messages.no_active_chat")}
            description={t("messages.select_peer_or_enter_address")}
            plain
            class="mb-8"
        />

        <div class="grid grid-cols-2 sm:grid-cols-4 gap-2 w-full mb-8">
            <button
                type="button"
                class="flex flex-col items-center gap-2 p-3 rounded-xl bg-sem-surface border border-sem-border hover:border-blue-400/60 hover:bg-sem-surface-muted transition-colors"
                onclick={() => oncompose?.()}
            >
                <MaterialDesignIcon iconName="plus" class="size-5 text-sem-accent" />
                <span class="text-xs font-medium text-sem-fg">{t("app.compose")}</span>
            </button>
            <button
                type="button"
                class="flex flex-col items-center gap-2 p-3 rounded-xl bg-sem-surface border border-sem-border hover:border-blue-400/60 hover:bg-sem-surface-muted transition-colors"
                onclick={() => onsync?.()}
            >
                <span
                    class={isSyncingPropagationNode ? "animate-spin" : ""}
                    style={isSyncingPropagationNode ? "animation-direction: reverse" : undefined}
                >
                    <MaterialDesignIcon iconName="sync" class="size-5 text-sem-accent" />
                </span>
                <span class="text-xs font-medium text-sem-fg">
                    {isSyncingPropagationNode ? t("app.syncing") : t("app.sync_now")}
                </span>
            </button>
            <button
                type="button"
                class="flex flex-col items-center gap-2 p-3 rounded-xl bg-sem-surface border border-sem-border hover:border-blue-400/60 hover:bg-sem-surface-muted transition-colors"
                onclick={() => oncopyaddress?.()}
            >
                <MaterialDesignIcon iconName="content-copy" class="size-5 text-sem-accent" />
                <span class="text-xs font-medium text-sem-fg">{t("messages.my_address")}</span>
            </button>
            <button
                type="button"
                class="flex flex-col items-center gap-2 p-3 rounded-xl bg-sem-surface border border-sem-border hover:border-blue-400/60 hover:bg-sem-surface-muted transition-colors"
                onclick={() => onidentities?.()}
            >
                <MaterialDesignIcon iconName="account-multiple" class="size-5 text-sem-accent" />
                <span class="text-xs font-medium text-sem-fg">{t("app.identities")}</span>
            </button>
        </div>

        {#if latestConversations.length > 0}
            <div class="w-full mb-8">
                <h2 class="text-xs font-medium text-sem-fg-muted mb-2">{t("messages.latest_conversations")}</h2>
                <div class="grid grid-cols-1 sm:grid-cols-2 gap-2">
                    {#each latestConversations as chat (chat.destination_hash ?? "")}
                        <button
                            type="button"
                            class="group cursor-pointer p-3 bg-sem-surface border border-sem-border rounded-xl hover:border-blue-400/60 hover:bg-sem-surface-muted transition-colors flex items-center gap-3 text-left w-full"
                            onclick={() => onselectpeer?.(chat)}
                        >
                            <div class="shrink-0">
                                <LxmfUserIcon
                                    customImage={chat.contact_image || ""}
                                    iconName={chat.lxmf_user_icon?.icon_name || ""}
                                    iconForegroundColour={chat.lxmf_user_icon?.foreground_colour || ""}
                                    iconBackgroundColour={chat.lxmf_user_icon?.background_colour || ""}
                                    iconClass="size-10"
                                />
                            </div>
                            <div class="flex-1 min-w-0">
                                <div class="flex items-center justify-between gap-2">
                                    <div class="font-medium text-sm text-sem-fg truncate">
                                        {chat.custom_display_name ?? chat.display_name}
                                    </div>
                                    <div class="text-[11px] text-sem-fg-muted whitespace-nowrap">
                                        {formatTimeAgo?.(chat.updated_at) ?? ""}
                                    </div>
                                </div>
                                <div class="text-xs text-sem-fg-muted truncate mt-0.5">
                                    {chat.latest_message_preview ||
                                        chat.latest_message_title ||
                                        t("messages.no_messages_yet")}
                                </div>
                            </div>
                        </button>
                    {/each}
                </div>
            </div>
        {/if}

        <div class="w-full max-w-xl">
            <div class="relative group">
                <div class="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
                    <MaterialDesignIcon
                        iconName="at"
                        class="size-5 text-gray-400 group-focus-within:text-sem-accent transition-colors"
                    />
                </div>
                <input
                    id="compose-input"
                    bind:value={composeAddress}
                    readonly={isTranslatingMessage}
                    type="text"
                    class="w-full bg-sem-surface border border-sem-border text-sem-fg text-sm rounded-xl focus:ring-2 focus:ring-sem-focus/30 focus:border-sem-focus-border pl-10 pr-4 py-2.5 transition-colors placeholder:text-gray-400 dark:placeholder:text-zinc-500"
                    placeholder={t("messages.compose_address_placeholder")}
                    onkeydown={onAddressKeydown}
                    onfocus={() => {
                        isComposeInputFocused = true;
                    }}
                    onblur={() => oncomposebblur?.()}
                />

                {#if isComposeInputFocused && composeSuggestions.length > 0}
                    <div
                        class="absolute z-50 left-0 right-0 bottom-full mb-2 bg-sem-surface border border-sem-border rounded-xl shadow-lg overflow-hidden"
                    >
                        <div class="p-1 space-y-0.5">
                            {#each composeSuggestions as suggestion, index (suggestion.hash)}
                                <button
                                    type="button"
                                    class="w-full px-3 py-2 flex items-center gap-3 cursor-pointer rounded-lg transition-colors text-left {index ===
                                    selectedComposeSuggestionIndex
                                        ? 'bg-blue-600 text-white'
                                        : 'hover:bg-sem-surface-muted/50 text-sem-fg-muted'}"
                                    onmousedown={(e) => {
                                        e.preventDefault();
                                        onselectsuggestion?.(suggestion);
                                    }}
                                >
                                    <div
                                        class="shrink-0 size-8 rounded-lg flex items-center justify-center {index ===
                                        selectedComposeSuggestionIndex
                                            ? 'bg-white/20'
                                            : suggestion.type === 'contact'
                                              ? 'bg-blue-100 dark:bg-blue-900/40 text-blue-600'
                                              : 'bg-sem-surface-muted text-gray-500'}"
                                    >
                                        <MaterialDesignIcon iconName={suggestion.icon} class="size-4" />
                                    </div>
                                    <div class="flex-1 min-w-0">
                                        <div class="text-sm font-medium truncate">{suggestion.name}</div>
                                        <div class="text-[10px] font-mono opacity-60 truncate">
                                            {Utils.formatDestinationHash(suggestion.hash)}
                                        </div>
                                    </div>
                                    {#if suggestion.type === "contact"}
                                        <div class="text-[10px] font-medium text-sem-fg-muted">
                                            {t("messages.contact_badge")}
                                        </div>
                                    {/if}
                                </button>
                            {/each}
                        </div>
                    </div>
                {/if}
            </div>
        </div>
    </div>
</div>
