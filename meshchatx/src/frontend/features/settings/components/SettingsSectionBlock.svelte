<!-- SPDX-License-Identifier: 0BSD -->

<script lang="ts">
    import type { Snippet } from "svelte";

    interface Props {
        eyebrow?: string;
        title: string;
        description?: string;
        show?: boolean;
        bodyClass?: string;
        headerText?: Snippet;
        actions?: Snippet;
        children?: Snippet;
    }

    let {
        eyebrow = "",
        title,
        description = "",
        show = true,
        bodyClass = "space-y-3",
        headerText,
        actions,
        children,
    }: Props = $props();
</script>

{#if show}
    <section class="settings-section break-inside-avoid">
        <header class="settings-section__header">
            <div>
                {#if eyebrow}
                    <div class="settings-section__eyebrow">{eyebrow}</div>
                {/if}
                <h2>{title}</h2>
                {#if description}
                    <p>{description}</p>
                {/if}
                {#if headerText}
                    {@render headerText()}
                {/if}
            </div>
            {#if actions}
                {@render actions()}
            {/if}
        </header>
        <div class="settings-section__body {bodyClass}">
            {#if children}
                {@render children()}
            {/if}
        </div>
    </section>
{/if}
