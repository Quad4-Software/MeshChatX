<!-- SPDX-License-Identifier: 0BSD -->

<script lang="ts">
    import MaterialDesignIcon from "../../../ui/svelte/MaterialDesignIcon.svelte";
    import ToastUtils from "../../../js/ToastUtils.js";
    import { t } from "../../../js/i18n.js";
    import type { ContextMenuCaret } from "../../../js/contextMenuCaret.js";
    import { blockNodeDestination, unblockNodeDestination } from "../lib/nomadSidebarActions.js";
    import type { NomadNode } from "../lib/types.js";

    interface Props {
        node: NomadNode;
        left: number;
        top: number;
        caret: ContextMenuCaret | null;
        isFav: boolean;
        isBlockedNode: boolean;
        panel?: HTMLDivElement | null;
        onaddfavourite?: (node: NomadNode) => void;
        onclose: () => void;
    }

    let {
        node,
        left,
        top,
        caret,
        isFav,
        isBlockedNode,
        panel = $bindable(null),
        onaddfavourite,
        onclose,
    }: Props = $props();

    async function copyText(text: string, message: string) {
        await navigator.clipboard.writeText(text);
        ToastUtils.success(message);
    }
</script>

<div
    bind:this={panel}
    class="fixed z-50 min-w-44 bg-sem-surface border border-sem-border rounded-xl shadow-xl py-1 text-sem-fg"
    style="left: {left}px; top: {top}px;"
>
    {#if !isFav}
        <button
            type="button"
            class="w-full text-left px-3 py-1.5 text-xs hover:bg-sem-surface-muted flex items-center gap-2"
            onclick={() => {
                onaddfavourite?.(node);
                onclose();
            }}
        >
            <MaterialDesignIcon iconName="star-outline" class="size-4 text-yellow-500" />
            {t("nomadnet.add_to_favourites")}
        </button>
    {/if}
    <button
        type="button"
        class="w-full text-left px-3 py-1.5 text-xs hover:bg-sem-surface-muted flex items-center gap-2"
        onclick={() => {
            void copyText(node.destination_hash, "Address copied to clipboard");
            onclose();
        }}
    >
        <MaterialDesignIcon iconName="content-copy" class="size-4" />
        {t("nomadnet.copy_address")}
    </button>
    <button
        type="button"
        class="w-full text-left px-3 py-1.5 text-xs hover:bg-sem-surface-muted flex items-center gap-2"
        onclick={() => {
            void copyText(`nomadnet://${node.destination_hash}`, "Link copied to clipboard");
            onclose();
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
            onclick={() => {
                unblockNodeDestination(node.identity_hash || node.destination_hash);
                onclose();
            }}
        >
            <MaterialDesignIcon iconName="lock-open-outline" class="size-4" />
            {t("nomadnet.lift_banishment")}
        </button>
    {:else}
        <button
            type="button"
            class="w-full text-left px-3 py-1.5 text-xs text-red-600 dark:text-red-400 hover:bg-sem-surface-muted flex items-center gap-2"
            onclick={() => {
                blockNodeDestination(node);
                onclose();
            }}
        >
            <MaterialDesignIcon iconName="cancel" class="size-4" />
            {t("nomadnet.block_node")}
        </button>
    {/if}
</div>
{#if caret}
    <div
        class="dropdown-caret fixed z-50 border-sem-border {caret.borderClass}"
        style="left: {caret.style.left}; top: {caret.style.top};"
        aria-hidden="true"
    ></div>
{/if}
