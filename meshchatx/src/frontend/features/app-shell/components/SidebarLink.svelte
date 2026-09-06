<!-- SPDX-License-Identifier: 0BSD -->

<script lang="ts">
    import type { Snippet } from "svelte";
    import { navRouteIsActive } from "../../../js/navRouteActive.js";
    import { resolveTarget } from "../../../shell/hashRouter.js";
    import type { RouteTarget } from "../../../shell/hashRouter.js";

    interface Props {
        to: RouteTarget;
        isCollapsed?: boolean;
        editMode?: boolean;
        activeRouteName?: string;
        class?: string;
        onclick?: (event: MouseEvent) => void;
        icon?: Snippet;
        text?: Snippet;
    }

    let {
        to,
        isCollapsed = false,
        editMode = false,
        activeRouteName = "",
        class: className = "",
        onclick,
        icon,
        text,
    }: Props = $props();

    const isActive = $derived(navRouteIsActive(to?.name, activeRouteName));

    const href = $derived.by(() => {
        if (!to?.path && !to?.name) {
            return "#";
        }
        try {
            return `#${resolveTarget(to)}`;
        } catch {
            if (to.path) {
                return `#${to.path.startsWith("/") ? to.path : `/${to.path}`}`;
            }
            if (to.name) {
                return `#/${to.name}`;
            }
            return "#";
        }
    });

    const activeClass = $derived.by(() => {
        if (isCollapsed && isActive) {
            return "text-sem-accent bg-sem-surface-muted shadow-[inset_2px_2px_5px_rgba(0,0,0,0.12),inset_-1px_-1px_2px_rgba(255,255,255,0.6)] dark:shadow-[inset_2px_2px_6px_rgba(0,0,0,0.72),inset_-1px_-1px_1px_rgba(255,255,255,0.07)]";
        }
        if (isActive) {
            return "sidebar-nav-link--active";
        }
        return "sidebar-nav-link--hover";
    });

    function handleClick(event: MouseEvent): void {
        onclick?.(event);
        if (editMode) {
            event.preventDefault();
        }
    }
</script>

<a
    {href}
    draggable="false"
    class="sidebar-nav-link group focus-visible:outline-sem-focus {activeClass} {isCollapsed
        ? 'overflow-visible justify-center rounded-none'
        : 'overflow-hidden rounded-r-full mr-2'} {className}"
    onclick={handleClick}
>
    <span class="my-auto shrink-0">
        {#if icon}
            {@render icon()}
        {/if}
    </span>
    {#if !isCollapsed}
        <span class="my-auto flex w-full truncate transition-all duration-300">
            {#if text}
                {@render text()}
            {/if}
        </span>
    {/if}
</a>
