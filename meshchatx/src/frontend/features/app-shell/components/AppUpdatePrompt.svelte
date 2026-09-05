<!-- SPDX-License-Identifier: 0BSD -->

<script lang="ts">
    import type { Snippet } from "svelte";
    import Modal from "../../../ui/svelte/Modal.svelte";

    interface Props {
        open?: boolean;
        title: string;
        description?: string;
        primaryLabel?: string;
        secondaryLabel?: string;
        busy?: boolean;
        busyText?: string;
        primaryDisabled?: boolean;
        maxWidth?: number | string;
        onprimary?: () => void;
        onsecondary?: () => void;
        children?: Snippet;
    }

    let {
        open = $bindable(false),
        title,
        description = "",
        primaryLabel = "",
        secondaryLabel = "",
        busy = false,
        busyText = "",
        primaryDisabled = false,
        maxWidth = 520,
        onprimary,
        onsecondary,
        children: bodySnippet,
    }: Props = $props();
</script>

<Modal bind:open {title} persistent {maxWidth} showClose={false}>
    <div class="space-y-3 px-4 py-4 text-sm text-sem-fg-muted sm:px-5">
        {#if description}
            <p>{description}</p>
        {/if}
        {#if bodySnippet}
            {@render bodySnippet()}
        {/if}
        {#if busy && busyText}
            <p class="text-center text-xs text-sem-fg-muted">
                {busyText}
            </p>
        {/if}
    </div>

    {#snippet footer()}
        <div class="flex w-full flex-col gap-2 sm:flex-row sm:justify-end">
            {#if secondaryLabel}
                <button
                    type="button"
                    class="tutorial-action-btn tutorial-action-btn-secondary w-full sm:w-auto"
                    disabled={busy}
                    onclick={() => onsecondary?.()}
                >
                    {secondaryLabel}
                </button>
            {/if}
            {#if primaryLabel}
                <button
                    type="button"
                    class="tutorial-action-btn tutorial-action-btn-primary w-full sm:w-auto"
                    disabled={busy || primaryDisabled}
                    onclick={() => onprimary?.()}
                >
                    {primaryLabel}
                </button>
            {/if}
        </div>
    {/snippet}
</Modal>
