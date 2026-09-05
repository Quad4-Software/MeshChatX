<!-- SPDX-License-Identifier: 0BSD -->

<script lang="ts">
    import MaterialDesignIcon from "../../../ui/svelte/MaterialDesignIcon.svelte";
    import LxmfUserIcon from "../../../ui/svelte/LxmfUserIcon.svelte";
    import type { ResultItem } from "../lib/commandPaletteTypes.js";

    interface Props {
        result: ResultItem;
        isHighlighted: boolean;
        onselect: (result: ResultItem) => void;
        onhighlight: (id: string) => void;
    }

    let { result, isHighlighted, onselect, onhighlight }: Props = $props();
</script>

<button
    type="button"
    class="w-full flex items-center gap-3 p-3 rounded-xl transition-all text-left {isHighlighted
        ? 'bg-sem-surface-muted text-sem-accent'
        : 'hover:bg-sem-surface-muted/50 text-sem-fg-muted'}"
    onclick={() => onselect(result)}
    onmousemove={() => onhighlight(result.id)}
>
    <div
        class="size-10 rounded-xl flex items-center justify-center shrink-0 border transition-colors {isHighlighted
            ? 'bg-blue-100 dark:bg-blue-900/40 border-blue-200 dark:border-blue-800'
            : 'bg-sem-surface-muted border-sem-border'}"
    >
        {#if result.type === "contact" || result.type === "peer"}
            <LxmfUserIcon
                customImage={result.type === "contact" ? result.contact?.custom_image : ""}
                iconName={result.icon}
                iconForegroundColour={result.iconForeground}
                iconBackgroundColour={result.iconBackground}
                iconClass="size-5"
            />
        {:else}
            <MaterialDesignIcon iconName={result.icon} class="size-5" />
        {/if}
    </div>
    <div class="min-w-0 flex-1">
        <div class="font-bold truncate">{result.title}</div>
        <div class="text-xs opacity-60 truncate">{result.description}</div>
    </div>
    {#if isHighlighted}
        <MaterialDesignIcon iconName="arrow-right" class="size-4" />
    {/if}
</button>
