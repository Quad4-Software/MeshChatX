<!-- SPDX-License-Identifier: 0BSD -->

<script lang="ts">
    import MaterialDesignIcon from "../../../ui/svelte/MaterialDesignIcon.svelte";
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

    const iconBtn = "toolbar-icon-btn focus-ring-sem cursor-pointer";
    const iconBtnActive = "toolbar-icon-btn text-sem-accent focus-ring-sem cursor-pointer";
    const iconBtnDanger = "toolbar-icon-btn hover:text-sem-danger focus-ring-sem cursor-pointer";
</script>

<div
    class="flex h-12 shrink-0 items-center justify-between border-b border-sem-border bg-sem-surface px-3 py-1.5 text-sem-fg"
>
    <div class="flex items-center gap-2 min-w-0 flex-1">
        <button
            type="button"
            class="md:hidden {iconBtn}"
            title={t("relay_chat.back_to_hubs")}
            aria-label={t("relay_chat.back_to_hubs")}
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
            <button
                type="button"
                class={showSearchPanel ? iconBtnActive : iconBtn}
                title={t("relay_chat.search_messages")}
                aria-label={t("relay_chat.search_messages")}
                onclick={() => ontogglesearch?.()}
            >
                <MaterialDesignIcon iconName="magnify" class="size-5" />
            </button>

            <button
                type="button"
                class="toolbar-label-chip min-h-11 sm:min-h-8 border transition-colors focus-ring-sem cursor-pointer {showMembersPanel
                    ? 'border-sem-border bg-sem-surface-muted text-sem-accent'
                    : 'border-transparent text-sem-fg-muted hover:border-sem-border hover:bg-sem-surface-muted hover:text-sem-fg'}"
                title={t("relay_chat.members_list")}
                onclick={() => ontogglemembers?.()}
            >
                <MaterialDesignIcon iconName="account-group" class="size-5 shrink-0" />
                <span class="leading-none">{memberCount}</span>
            </button>

            <button
                type="button"
                class={iconBtn}
                title={t("relay_chat.share_relay_link")}
                aria-label={t("relay_chat.share_relay_link")}
                onclick={() => onshare?.()}
            >
                <MaterialDesignIcon iconName="share-variant" class="size-5" />
            </button>

            {#if !isPopoutMode}
                <button
                    type="button"
                    class="hidden sm:inline-flex {iconBtn}"
                    data-testid="relay-popout"
                    title={t("relay_chat.popout_window")}
                    aria-label={t("relay_chat.popout_window")}
                    onclick={() => onpopout?.()}
                >
                    <MaterialDesignIcon iconName="open-in-new" class="size-5" />
                </button>
            {/if}

            <button
                type="button"
                class={iconBtn}
                title={t("relay_chat.clear_messages")}
                aria-label={t("relay_chat.clear_messages")}
                onclick={() => onclearmessages?.()}
            >
                <MaterialDesignIcon iconName="broom" class="size-5" />
            </button>

            <button
                type="button"
                class={iconBtnDanger}
                title={t("relay_chat.leave_room")}
                aria-label={t("relay_chat.leave_room")}
                onclick={() => onleaveroom?.()}
            >
                <MaterialDesignIcon iconName="logout" class="size-5" />
            </button>
        {:else if selectedHub}
            <button
                type="button"
                class={iconBtnDanger}
                title={t("relay_chat.disconnect_hub")}
                aria-label={t("relay_chat.disconnect_hub")}
                onclick={() => ondisconnecthub?.()}
            >
                <MaterialDesignIcon iconName="lan-disconnect" class="size-5" />
            </button>
        {/if}
    </div>
</div>
