<!-- SPDX-License-Identifier: 0BSD -->

<script lang="ts">
    import type { Snippet } from "svelte";
    import type { HTMLButtonAttributes } from "svelte/elements";

    interface Props extends HTMLButtonAttributes {
        title?: string;
        disabled?: boolean;
        class?: string;
        onclick?: (e: MouseEvent) => void;
        children?: Snippet;
    }

    let {
        title = "",
        disabled = false,
        class: className = "",
        onclick,
        children,
        type = "button",
        ...restProps
    }: Props = $props();

    const buttonClasses = $derived(
        [
            "icon-btn-sem press-feedback text-sem-fg-muted hover:text-sem-fg hover:bg-sem-surface-muted p-2 rounded-full min-w-11 min-h-11 w-11 h-11 flex items-center justify-center shrink-0 transition-colors duration-200 focus-ring-sem",
            className,
        ]
            .filter(Boolean)
            .join(" ")
    );
</script>

<button {type} {title} {disabled} {onclick} class={buttonClasses} {...restProps}>
    {#if children}
        {@render children()}
    {/if}
</button>
