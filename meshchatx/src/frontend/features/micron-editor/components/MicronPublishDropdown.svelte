<!-- SPDX-License-Identifier: 0BSD -->

<script lang="ts">
    import { onMount } from "svelte";
    import MaterialDesignIcon from "../../../ui/svelte/MaterialDesignIcon.svelte";
    import { t } from "../../../js/i18n.js";
    import type { LastPublishedInfo, PageNodeItem } from "../lib/types.js";

    interface Props {
        showPublishMenu: boolean;
        pageNodes: PageNodeItem[];
        publishBusy: boolean;
        lastPublished: LastPublishedInfo | null;
        onTogglePublishMenu: () => void;
        onCreateMeshServerAndPublish: () => void;
        onPublishToNode: (node: PageNodeItem) => void;
        onPublishAllToNode: () => void;
        onOpenPublishedInNomadNet: () => void;
        onCloseMenu: () => void;
    }

    let {
        showPublishMenu,
        pageNodes,
        publishBusy,
        lastPublished,
        onTogglePublishMenu,
        onCreateMeshServerAndPublish,
        onPublishToNode,
        onPublishAllToNode,
        onOpenPublishedInNomadNet,
        onCloseMenu,
    }: Props = $props();

    let dropdownEl = $state<HTMLElement | null>(null);

    onMount(() => {
        function handleClickOutside(event: MouseEvent): void {
            if (showPublishMenu && dropdownEl && !dropdownEl.contains(event.target as Node | null)) {
                onCloseMenu();
            }
        }
        document.addEventListener("click", handleClickOutside);
        return () => {
            document.removeEventListener("click", handleClickOutside);
        };
    });
</script>

<div class="relative" bind:this={dropdownEl}>
    <button
        type="button"
        class="primary-chip py-1! px-3!"
        onclick={(e) => {
            e.stopPropagation();
            onTogglePublishMenu();
        }}
    >
        <MaterialDesignIcon iconName="publish" class="w-3.5 h-3.5" />
        <span class="hidden sm:inline">{t("tools.micron_editor.publish")}</span>
    </button>
    {#if showPublishMenu}
        <div
            class="absolute right-0 top-full mt-1 w-72 bg-white dark:bg-zinc-800 rounded-xl shadow-xl border border-sem-border z-50 py-2"
        >
            <div class="px-3 py-1.5 text-xs font-bold uppercase tracking-wider text-sem-fg-muted">
                {t("tools.micron_editor.publish_to_mesh_server")}
            </div>
            {#if pageNodes.length === 0}
                <div class="px-3 py-2 text-xs text-sem-fg-muted space-y-2">
                    <div>{t("tools.micron_editor.publish_no_servers")}</div>
                    <button
                        type="button"
                        class="w-full text-left rounded-lg bg-teal-600 px-3 py-2 text-sm font-semibold text-white hover:bg-teal-500 disabled:opacity-50"
                        disabled={publishBusy}
                        onclick={onCreateMeshServerAndPublish}
                    >
                        {t("tools.micron_editor.publish_create_and_publish")}
                    </button>
                    <a href="#/mesh-server" class="inline-block text-blue-500 hover:underline" onclick={onCloseMenu}>
                        {t("tools.micron_editor.publish_manage_servers")}
                    </a>
                </div>
            {:else}
                {#each pageNodes as pn (pn.node_id)}
                    <button
                        type="button"
                        class="w-full text-left px-3 py-2 text-sm hover:bg-gray-100 dark:hover:bg-sem-surface-muted flex items-center gap-2 transition-colors disabled:opacity-50"
                        disabled={publishBusy}
                        onclick={() => onPublishToNode(pn)}
                    >
                        <div class="w-2 h-2 rounded-full shrink-0 {pn.running ? 'bg-green-500' : 'bg-gray-400'}"></div>
                        <span class="truncate text-sem-fg">{pn.name}</span>
                        {#if !pn.running}
                            <span class="ml-auto text-[10px] text-sem-fg-muted shrink-0">
                                {t("tools.micron_editor.publish_will_start")}
                            </span>
                        {/if}
                    </button>
                {/each}
                <div class="border-t border-sem-border mt-1 pt-1">
                    <button
                        type="button"
                        class="w-full text-left px-3 py-2 text-xs text-sem-fg-muted hover:bg-gray-100 dark:hover:bg-sem-surface-muted transition-colors disabled:opacity-50"
                        disabled={publishBusy}
                        onclick={onCreateMeshServerAndPublish}
                    >
                        {t("tools.micron_editor.publish_create_and_publish")}
                    </button>
                    <button
                        type="button"
                        class="w-full text-left px-3 py-2 text-xs text-sem-fg-muted hover:bg-gray-100 dark:hover:bg-sem-surface-muted transition-colors disabled:opacity-50"
                        disabled={publishBusy}
                        onclick={onPublishAllToNode}
                    >
                        {t("tools.micron_editor.publish_all_tabs")}
                    </button>
                </div>
            {/if}
            {#if lastPublished?.destinationHash}
                <div class="border-t border-sem-border mt-1 pt-1">
                    <button
                        type="button"
                        class="w-full text-left px-3 py-2 text-xs font-medium text-teal-600 dark:text-teal-400 hover:bg-gray-100 dark:hover:bg-sem-surface-muted transition-colors flex items-center gap-2"
                        onclick={onOpenPublishedInNomadNet}
                    >
                        <MaterialDesignIcon iconName="web" class="w-3.5 h-3.5" />
                        <span class="truncate">
                            {t("tools.micron_editor.publish_open_in_nomadnet", {
                                page: lastPublished.pageName,
                            })}
                        </span>
                    </button>
                </div>
            {/if}
        </div>
    {/if}
</div>
