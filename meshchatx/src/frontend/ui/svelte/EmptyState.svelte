<!-- SPDX-License-Identifier: 0BSD -->

<script>
    import MaterialDesignIcon from "./MaterialDesignIcon.svelte";

    /**
     * @type {{
     *   icon?: string,
     *   title?: string,
     *   description?: string,
     *   plain?: boolean,
     *   class?: string,
     *   children?: import('svelte').Snippet,
     * }}
     */
    let { icon = "", title = "", description = "", plain = false, class: rootClass = "", children } = $props();

    const iconClass = $derived(
        plain ? "w-8 h-8 mx-auto mb-2 text-sem-fg-muted" : "w-12 h-12 mx-auto mb-4 text-sem-fg-muted"
    );
    const shellClass = $derived(
        [
            "text-center",
            plain
                ? "px-2 py-3"
                : "rounded-lg border border-dashed border-sem-border px-4 py-12 bg-sem-surface-muted/40",
            rootClass,
        ]
            .filter(Boolean)
            .join(" ")
    );
</script>

<div class={shellClass}>
    {#if icon}
        <MaterialDesignIcon iconName={icon} class={iconClass} />
    {/if}
    {#if title}
        <div class="text-base font-semibold text-sem-fg">{title}</div>
    {/if}
    {#if description}
        <p class="mt-2 text-sm text-sem-fg-muted max-w-md mx-auto">{description}</p>
    {/if}
    {#if children}
        <div class="flex justify-center {plain ? 'mt-3' : 'mt-4'}">
            {@render children()}
        </div>
    {/if}
</div>
