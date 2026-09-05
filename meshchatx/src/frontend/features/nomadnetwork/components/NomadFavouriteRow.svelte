<!-- SPDX-License-Identifier: 0BSD -->

<script lang="ts">
    import MaterialDesignIcon from "../../../ui/svelte/MaterialDesignIcon.svelte";
    import Utils from "../../../js/Utils.js";
    import ToastUtils from "../../../js/ToastUtils.js";
    import GlobalState from "../../../js/GlobalState.js";
    import { t } from "../../../js/i18n.js";
    import { favouriteDisplayName } from "../lib/nomadSidebarFavourites.js";
    import type { NomadFavourite, NomadNode } from "../lib/types.js";

    interface Props {
        fav: NomadFavourite;
        node?: NomadNode;
        selected?: boolean;
        selectionMode?: boolean;
        isSelectedInBulk?: boolean;
        isBlocked?: boolean;
        onclick?: () => void;
        oncontextmenu?: (e: MouseEvent) => void;
        ontoggleselect?: () => void;
        ondragstart?: (e: DragEvent) => void;
        ondragend?: () => void;
    }

    let {
        fav,
        node,
        selected = false,
        selectionMode = false,
        isSelectedInBulk = false,
        isBlocked = false,
        onclick,
        oncontextmenu,
        ontoggleselect,
        ondragstart,
        ondragend,
    }: Props = $props();

    const displayName = $derived(favouriteDisplayName(fav, node, t("nomadnet.unknown_node")));
</script>

<div
    class="favourite-card relative flex items-center gap-3 rounded-lg px-2 py-1.5 cursor-pointer hover:bg-sem-surface-muted/80 {selected
        ? 'bg-blue-50/80 dark:bg-blue-900/25'
        : ''} {selectionMode && isSelectedInBulk ? 'ring-1 ring-blue-400/60 dark:ring-blue-500/50' : ''}"
    draggable="true"
    {ondragstart}
    {ondragend}
    onclick={() => {
        if (isBlocked) return;
        if (selectionMode) {
            ontoggleselect?.();
            return;
        }
        onclick?.();
    }}
    {oncontextmenu}
    role="button"
    tabindex="0"
    onkeydown={(e) => {
        if (e.key === "Enter") onclick?.();
    }}
>
    {#if selectionMode}
        <div
            class="my-auto mr-1 px-0.5 shrink-0"
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

    {#if GlobalState.config?.banished_effect_enabled && isBlocked}
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
        class="favourite-card__icon size-9 rounded-lg bg-sem-surface-muted flex items-center justify-center text-gray-500 dark:text-gray-300 shrink-0"
    >
        <MaterialDesignIcon iconName="star" class="size-5 text-yellow-500" />
    </div>

    <div class="min-w-0 flex-1">
        <div class="flex items-center gap-1.5 min-w-0">
            <span class="text-sm font-semibold text-sem-fg truncate" title={displayName}>
                {displayName}
            </span>
            {#if fav.identify_on_connect}
                <span title={t("nomadnet.identify_enabled_tooltip")} class="shrink-0">
                    <MaterialDesignIcon iconName="account-check" class="size-3.5 text-emerald-500" />
                </span>
            {/if}
        </div>
        <div class="text-xs text-sem-fg-muted flex items-center gap-1">
            <span
                class="cursor-pointer hover:text-blue-500 dark:hover:text-blue-400"
                title={t("common.copy_to_clipboard")}
                onclick={(e) => {
                    e.stopPropagation();
                    navigator.clipboard.writeText(fav.destination_hash);
                    ToastUtils.success("Address copied to clipboard");
                }}
                role="button"
                tabindex="0"
                onkeydown={(e) => {
                    if (e.key === "Enter") navigator.clipboard.writeText(fav.destination_hash);
                }}
            >
                {Utils.formatDestinationHash(fav.destination_hash)}
            </span>
        </div>
    </div>
</div>
