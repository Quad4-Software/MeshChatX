<!-- SPDX-License-Identifier: 0BSD -->

<script lang="ts">
    import MaterialDesignIcon from "../../ui/svelte/MaterialDesignIcon.svelte";
    import { t } from "../../js/i18n.js";
    import ToolListRow from "./ToolListRow.svelte";
    import { toolRouteHref, toolRowClass } from "./lib/toolsList.js";
    import type { ToolRecord } from "./lib/toolsList.js";

    interface Props {
        sectionId: string;
        tools: ToolRecord[];
        collapsed?: boolean;
        onToggle?: (sectionId: string) => void;
    }

    let { sectionId, tools, collapsed = false, onToggle }: Props = $props();

    function toggle(): void {
        onToggle?.(sectionId);
    }
</script>

<div class="mb-6 rounded-lg overflow-hidden border border-sem-border bg-sem-surface">
    <button
        type="button"
        class="w-full px-4 py-3 border-b border-sem-border text-xs font-bold uppercase tracking-widest text-sem-fg-muted flex items-center justify-between gap-2 text-left hover:bg-sem-surface-muted/50 transition-colors"
        aria-expanded={!collapsed}
        aria-controls={`tools-section-${sectionId}`}
        id={`tools-section-toggle-${sectionId}`}
        onclick={toggle}
    >
        <span>{t(`tools.group.${sectionId}`)}</span>
        <span class="opacity-60 inline-flex transition-transform {collapsed ? '' : 'rotate-180'}">
            <MaterialDesignIcon iconName="chevron-down" class="size-4" />
        </span>
    </button>
    {#if !collapsed}
        <div
            id={`tools-section-${sectionId}`}
            role="region"
            aria-labelledby={`tools-section-toggle-${sectionId}`}
            class="grid grid-cols-1 lg:grid-cols-2 divide-y divide-sem-border divide-x-0 lg:divide-x lg:divide-y"
        >
            {#each tools as tool (String(tool.name))}
                {#if tool.comingSoon}
                    <div class={toolRowClass(tool)}>
                        <ToolListRow {tool} />
                    </div>
                {:else}
                    <a href={toolRouteHref(tool.route)} class={toolRowClass(tool)}>
                        <ToolListRow {tool} />
                    </a>
                {/if}
            {/each}
        </div>
    {/if}
</div>
