<!-- SPDX-License-Identifier: 0BSD -->

<script lang="ts">
    import MaterialDesignIcon from "../../../ui/svelte/MaterialDesignIcon.svelte";
    import Utils from "../../../js/Utils.js";
    import ToastUtils from "../../../js/ToastUtils.js";
    import GlobalState from "../../../js/GlobalState.js";
    import { t } from "../../../js/i18n.js";
    import { blockNodeDestination, unblockNodeDestination } from "../lib/nomadSidebarActions.js";
    import type { NomadNode } from "../lib/types.js";

    interface Props {
        node: NomadNode;
        selected?: boolean;
        selectionMode?: boolean;
        isSelectedInBulk?: boolean;
        isDropdownActive?: boolean;
        isBlockedNode?: boolean;
        isFav?: boolean;
        onclick?: () => void;
        oncontextmenu?: (e: MouseEvent) => void;
        ontoggleselect?: () => void;
        ontoggledropdown?: (e: MouseEvent) => void;
        onaddfavourite?: (node: NomadNode) => void;
    }

    let {
        node,
        selected = false,
        selectionMode = false,
        isSelectedInBulk = false,
        isDropdownActive = false,
        isBlockedNode = false,
        isFav = false,
        onclick,
        oncontextmenu,
        ontoggleselect,
        ontoggledropdown,
        onaddfavourite,
    }: Props = $props();
</script>

<div
    class="announce-card relative flex items-center gap-3 rounded-lg px-2 py-1.5 hover:bg-sem-surface-muted/80 {selected
        ? 'bg-blue-50/80 dark:bg-blue-900/25'
        : ''} {selectionMode && isSelectedInBulk ? 'ring-1 ring-blue-400/60 dark:ring-blue-500/50' : ''}"
    role="group"
    {oncontextmenu}
>
    {#if GlobalState.config?.banished_effect_enabled && isBlockedNode}
        <div
            class="banished-overlay absolute inset-0 z-10 flex items-center justify-center rounded-lg"
            style="background: {GlobalState.config.banished_color + '33'}"
        >
            <span
                class="banished-text text-[10px] opacity-100 tracking-widest border px-1 py-0.5 text-white shadow-lg"
                style="background-color: {GlobalState.config.banished_color}"
            >
                {GlobalState.config.banished_text}
            </span>
        </div>
    {/if}

    <div
        class="flex items-center gap-3 flex-1 min-w-0 cursor-pointer"
        onclick={() => {
            if (isBlockedNode) return;
            if (selectionMode) {
                ontoggleselect?.();
                return;
            }
            onclick?.();
        }}
        role="button"
        tabindex="0"
        onkeydown={(e) => {
            if (e.key === "Enter") onclick?.();
        }}
    >
        {#if selectionMode}
            <div
                class="my-auto shrink-0 px-0.5"
                onclick={(e) => e.stopPropagation()}
                role="presentation"
                onkeydown={(e) => e.stopPropagation()}
            >
                <input
                    type="checkbox"
                    checked={isSelectedInBulk}
                    class="rounded-sm border-gray-300 text-blue-600 focus:ring-blue-500"
                    onchange={ontoggleselect}
                />
            </div>
        {/if}

        <div
            class="announce-card__icon size-9 rounded-lg bg-sem-surface-muted flex items-center justify-center text-gray-500 dark:text-gray-300 shrink-0"
        >
            <MaterialDesignIcon iconName="satellite-uplink" class="size-5" />
        </div>

        <div class="min-w-0 flex-1">
            <div
                class="text-sm font-semibold text-sem-fg truncate"
                title={node.custom_display_name || node.display_name}
            >
                {node.custom_display_name || node.display_name}
            </div>
            <div class="text-xs text-sem-fg-muted flex flex-col gap-0.5">
                <span class="truncate">
                    {t("nomadnet.announced_time_ago", {
                        time: Utils.formatTimeAgoForI18n(node.updated_at),
                    })}
                </span>
                <span
                    class="cursor-pointer hover:text-blue-500 dark:hover:text-blue-400 inline-flex items-center"
                    title={t("common.copy_to_clipboard")}
                    onclick={(e) => {
                        e.stopPropagation();
                        navigator.clipboard.writeText(node.destination_hash);
                        ToastUtils.success("Address copied to clipboard");
                    }}
                    role="button"
                    tabindex="0"
                    onkeydown={(e) => {
                        if (e.key === "Enter") navigator.clipboard.writeText(node.destination_hash);
                    }}
                >
                    {Utils.formatDestinationHash(node.destination_hash)}
                </span>
            </div>
        </div>
    </div>

    <div class="relative shrink-0">
        <button
            type="button"
            class="p-1 text-gray-500 dark:text-gray-300 hover:text-sem-fg rounded-lg"
            onclick={ontoggledropdown}
        >
            <MaterialDesignIcon iconName="dots-vertical" class="size-5" />
        </button>

        {#if isDropdownActive}
            <div
                class="absolute right-0 top-full mt-1 z-50 min-w-44 bg-sem-surface border border-sem-border rounded-xl shadow-xl py-1 text-sem-fg"
            >
                {#if !isFav}
                    <button
                        type="button"
                        class="w-full text-left px-3 py-1.5 text-xs hover:bg-sem-surface-muted flex items-center gap-2"
                        onclick={() => onaddfavourite?.(node)}
                    >
                        <MaterialDesignIcon iconName="star-outline" class="size-4 text-yellow-500" />
                        {t("nomadnet.add_to_favourites")}
                    </button>
                {/if}
                <button
                    type="button"
                    class="w-full text-left px-3 py-1.5 text-xs hover:bg-sem-surface-muted flex items-center gap-2"
                    onclick={() => {
                        navigator.clipboard.writeText(node.destination_hash);
                        ToastUtils.success("Address copied to clipboard");
                    }}
                >
                    <MaterialDesignIcon iconName="content-copy" class="size-4" />
                    {t("nomadnet.copy_address")}
                </button>
                <button
                    type="button"
                    class="w-full text-left px-3 py-1.5 text-xs hover:bg-sem-surface-muted flex items-center gap-2"
                    onclick={() => {
                        navigator.clipboard.writeText(`nomadnet://${node.destination_hash}`);
                        ToastUtils.success("Link copied to clipboard");
                    }}
                >
                    <MaterialDesignIcon iconName="link" class="size-4" />
                    {t("nomadnet.copy_nomad_link")}
                </button>
                <hr class="my-1 border-sem-border" />
                {#if isBlockedNode}
                    <button
                        type="button"
                        class="w-full text-left px-3 py-1.5 text-xs text-green-600 dark:text-green-400 hover:bg-sem-surface-muted flex items-center gap-2"
                        onclick={() => unblockNodeDestination(node.identity_hash || node.destination_hash)}
                    >
                        <MaterialDesignIcon iconName="lock-open-outline" class="size-4" />
                        {t("nomadnet.lift_banishment")}
                    </button>
                {:else}
                    <button
                        type="button"
                        class="w-full text-left px-3 py-1.5 text-xs text-red-600 dark:text-red-400 hover:bg-sem-surface-muted flex items-center gap-2"
                        onclick={() => blockNodeDestination(node)}
                    >
                        <MaterialDesignIcon iconName="cancel" class="size-4" />
                        {t("nomadnet.block_node")}
                    </button>
                {/if}
            </div>
        {/if}
    </div>
</div>
