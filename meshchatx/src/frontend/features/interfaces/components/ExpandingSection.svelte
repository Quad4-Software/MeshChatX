<!-- SPDX-License-Identifier: 0BSD -->

<script lang="ts">
    import type { Snippet } from "svelte";

    interface Props {
        class?: string;
        isExpanded?: boolean;
        title?: Snippet;
        subtitle?: Snippet;
        content?: Snippet;
        children?: Snippet;
    }

    let { class: className = "", isExpanded = $bindable(false), title, subtitle, content, children }: Props = $props();

    function toggle() {
        isExpanded = !isExpanded;
    }
</script>

<div
    class="bg-white rounded-sm shadow-sm divide-y divide-gray-300 dark:divide-zinc-700 dark:bg-zinc-900 overflow-hidden {className}"
>
    <!-- svelte-ignore a11y_click_events_have_key_events -->
    <!-- svelte-ignore a11y_no_static_element_interactions -->
    <div class="flex p-2 justify-between cursor-pointer hover:bg-sem-surface-muted" onclick={toggle}>
        <div class="my-auto mr-auto">
            <div class="font-bold dark:text-white">
                {#if title}
                    {@render title()}
                {/if}
            </div>
            {#if subtitle}
                <div class="text-sm text-sem-fg-muted">
                    {@render subtitle()}
                </div>
            {/if}
        </div>
        <div class="my-auto ml-2">
            <div
                class="w-5 h-5 text-sem-fg-muted transform transition-transform duration-200 {isExpanded
                    ? 'rotate-90'
                    : ''}"
            >
                <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 256 256" class="size-5">
                    <rect width="256" height="256" fill="none" />
                    <path
                        d="M181.66,122.34l-80-80A8,8,0,0,0,88,48V208a8,8,0,0,0,13.66,5.66l80-80A8,8,0,0,0,181.66,122.34Z"
                        fill="currentColor"
                    />
                </svg>
            </div>
        </div>
    </div>
    {#if isExpanded}
        <div class="divide-y divide-gray-200 dark:text-white">
            {#if content}
                {@render content()}
            {:else if children}
                {@render children()}
            {/if}
        </div>
    {/if}
</div>
