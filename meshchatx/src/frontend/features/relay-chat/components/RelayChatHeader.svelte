<!-- SPDX-License-Identifier: 0BSD -->

<script lang="ts">
    import MaterialDesignIcon from "../../../ui/svelte/MaterialDesignIcon.svelte";
    import IconButton from "../../../ui/svelte/IconButton.svelte";
    import { t } from "../../../js/i18n.js";
    import { hubDisplayName } from "../lib/relayFormatters.js";
    import type { RrcHub, RrcRoom } from "../lib/types.js";

    interface Props {
        selectedHub?: RrcHub | null;
        selectedRoom?: RrcRoom | null;
        isPopoutMode?: boolean;
        showMembersPanel?: boolean;
        showSearchPanel?: boolean;
        memberCount?: number;
        onback?: () => void;
        ontogglemembers?: () => void;
        ontogglesearch?: () => void;
        onshare?: () => void;
        onpopout?: () => void;
        onleaveroom?: () => void;
        onclearmessages?: () => void;
        ondisconnecthub?: () => void;
    }

    let {
        selectedHub = null,
        selectedRoom = null,
        isPopoutMode = false,
        showMembersPanel = false,
        showSearchPanel = false,
        memberCount = 0,
        onback,
        ontogglemembers,
        ontogglesearch,
        onshare,
        onpopout,
        onleaveroom,
        onclearmessages,
        ondisconnecthub,
    }: Props = $props();
</script>

<div
    class="flex h-12 shrink-0 items-center justify-between border-b border-sem-border bg-sem-surface px-3 py-1.5 text-sem-fg"
>
    <div class="flex items-center gap-2 min-w-0 flex-1">
        <button
            type="button"
            class="md:hidden p-1.5 rounded-lg text-sem-fg-muted hover:bg-sem-surface-muted transition-colors"
            title={t("relay_chat.back_to_hubs")}
            onclick={() => onback?.()}
        >
            <MaterialDesignIcon iconName="arrow-left" class="size-5" />
        </button>

        <div class="flex flex-col min-w-0 flex-1">
            <div class="flex items-center gap-1.5 min-w-0">
                {#if selectedRoom}
                    <span class="font-bold text-base truncate">#{selectedRoom.name}</span>
                    {#if selectedRoom.has_key}
                        <span title={t("relay_chat.room_keyed")}>
                            <MaterialDesignIcon iconName="lock" class="size-3.5 shrink-0 text-amber-500" />
                        </span>
                    {/if}
                {:else if selectedHub}
                    <span class="font-bold text-base truncate">{hubDisplayName(selectedHub)}</span>
                {/if}
            </div>

            {#if selectedRoom?.topic}
                <div class="text-xs text-sem-fg-muted truncate" title={selectedRoom.topic}>
                    {selectedRoom.topic}
                </div>
            {/if}
        </div>
    </div>

    <div class="flex items-center gap-1 shrink-0">
        {#if selectedRoom}
            <IconButton
                class="size-8 {showSearchPanel
                    ? 'bg-sem-surface-muted text-sem-accent'
                    : 'text-sem-fg-muted hover:text-sem-fg'}"
                title={t("relay_chat.search_messages")}
                onclick={() => ontogglesearch?.()}
            >
                <MaterialDesignIcon iconName="magnify" class="size-4" />
            </IconButton>

            <button
                type="button"
                class="flex items-center gap-1 px-2 py-1 rounded-lg text-xs font-medium transition-colors {showMembersPanel
                    ? 'bg-sem-surface-muted text-sem-accent'
                    : 'text-sem-fg-muted hover:text-sem-fg hover:bg-sem-surface-muted'}"
                title={t("relay_chat.members_list")}
                onclick={() => ontogglemembers?.()}
            >
                <MaterialDesignIcon iconName="account-group" class="size-4" />
                <span>{memberCount}</span>
            </button>

            <IconButton
                class="size-8 text-sem-fg-muted hover:text-sem-fg"
                title={t("relay_chat.share_relay_link")}
                onclick={() => onshare?.()}
            >
                <MaterialDesignIcon iconName="share-variant" class="size-4" />
            </IconButton>

            {#if !isPopoutMode}
                <IconButton
                    class="size-8 text-sem-fg-muted hover:text-sem-fg hidden sm:inline-flex"
                    data-testid="relay-popout"
                    title={t("relay_chat.popout_window")}
                    onclick={() => onpopout?.()}
                >
                    <MaterialDesignIcon iconName="open-in-new" class="size-4" />
                </IconButton>
            {/if}

            <IconButton
                class="size-8 text-sem-fg-muted hover:text-sem-fg"
                title={t("relay_chat.clear_messages")}
                onclick={() => onclearmessages?.()}
            >
                <MaterialDesignIcon iconName="broom" class="size-4" />
            </IconButton>

            <IconButton
                class="size-8 text-sem-fg-muted hover:text-sem-danger"
                title={t("relay_chat.leave_room")}
                onclick={() => onleaveroom?.()}
            >
                <MaterialDesignIcon iconName="logout" class="size-4" />
            </IconButton>
        {:else if selectedHub}
            <IconButton
                class="size-8 text-sem-fg-muted hover:text-sem-danger"
                title={t("relay_chat.disconnect_hub")}
                onclick={() => ondisconnecthub?.()}
            >
                <MaterialDesignIcon iconName="lan-disconnect" class="size-4" />
            </IconButton>
        {/if}
    </div>
</div>
