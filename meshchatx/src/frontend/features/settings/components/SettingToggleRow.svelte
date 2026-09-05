<!-- SPDX-License-Identifier: 0BSD -->

<script lang="ts">
    import type { Snippet } from "svelte";
    import Toggle from "./Toggle.svelte";

    interface Props {
        id: string;
        checked?: boolean;
        title: string;
        description?: string;
        hint?: string;
        disabled?: boolean;
        onchange?: (checked: boolean) => void;
        children?: Snippet;
    }

    let {
        id,
        checked = $bindable(false),
        title,
        description = "",
        hint = "",
        disabled = false,
        onchange,
        children,
    }: Props = $props();

    function handleToggleChange(val: boolean) {
        checked = val;
        onchange?.(val);
    }
</script>

<label
    class="setting-toggle relative flex flex-row-reverse items-start gap-3 rounded-2xl border border-sem-border bg-sem-surface px-3 py-3 {disabled
        ? 'opacity-50 cursor-not-allowed'
        : ''}"
>
    <Toggle {id} {checked} {disabled} onchange={handleToggleChange} />
    <span class="setting-toggle__label flex-1 min-w-0 flex flex-col gap-0.5">
        <span class="setting-toggle__title text-sm font-semibold text-sem-fg wrap-break-word leading-snug">{title}</span
        >
        {#if children}
            <span class="text-xs sm:text-sm text-sem-fg-muted wrap-break-word leading-snug">
                {@render children()}
            </span>
        {:else if description}
            <span class="text-xs sm:text-sm text-sem-fg-muted wrap-break-word leading-snug">{description}</span>
        {/if}
        {#if hint}
            <span class="text-xs text-sem-fg-muted wrap-break-word">{hint}</span>
        {/if}
    </span>
</label>
