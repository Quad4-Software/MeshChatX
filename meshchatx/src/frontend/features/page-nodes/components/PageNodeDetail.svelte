<!-- SPDX-License-Identifier: 0BSD -->

<script lang="ts">
    import { t } from "../../../js/i18n.js";
    import MaterialDesignIcon from "../../../ui/svelte/MaterialDesignIcon.svelte";
    import { PAGE_NODE_TABS, type PageNodeDetailTab } from "../lib/constants.js";
    import type { PageNode } from "../lib/types.js";
    import PageNodeAnnounceSettings from "./PageNodeAnnounceSettings.svelte";
    import PageNodeFilesTab from "./PageNodeFilesTab.svelte";
    import PageNodePagesTab from "./PageNodePagesTab.svelte";

    interface Props {
        selectedNode: PageNode;
        detailTab: PageNodeDetailTab;
        announceEnabled: boolean;
        announceIntervalMinutes: number;
        executablePagesEnabled: boolean;
        lastAnnouncedText: string;
        editingPage: string | null;
        editingPageContent: string;
        editingPageExecutable: boolean;
        onRenameClick: () => void;
        onClose: () => void;
        onViewNode: (node: PageNode) => void;
        onSaveAnnounceSettings: () => void;
        onTabChange: (tab: PageNodeDetailTab) => void;
        onAddPage: (name: string) => void;
        onEditPage: (name: string) => void;
        onDeletePage: (name: string) => void;
        onSavePage: () => void;
        onCancelEditPage: () => void;
        onUploadFile: (file: File) => void;
        onDeleteFile: (fileName: string) => void;
    }

    let {
        selectedNode,
        detailTab = $bindable(PAGE_NODE_TABS.PAGES),
        announceEnabled = $bindable(true),
        announceIntervalMinutes = $bindable(15),
        executablePagesEnabled = $bindable(false),
        lastAnnouncedText,
        editingPage,
        editingPageContent = $bindable(""),
        editingPageExecutable = $bindable(false),
        onRenameClick,
        onClose,
        onViewNode,
        onSaveAnnounceSettings,
        onTabChange,
        onAddPage,
        onEditPage,
        onDeletePage,
        onSavePage,
        onCancelEditPage,
        onUploadFile,
        onDeleteFile,
    }: Props = $props();
</script>

<div class="w-full py-4 sm:py-6 space-y-4 border-t border-gray-200/60 dark:border-zinc-800/60">
    <div class="flex items-center justify-between">
        <div class="text-lg font-semibold text-sem-fg">
            {selectedNode.name}
        </div>
        <div class="flex items-center gap-2">
            <button type="button" class="secondary-chip py-1! px-3! text-xs!" onclick={onRenameClick}>
                {t("tools.mesh_server.rename")}
            </button>
            <button type="button" class="secondary-chip py-1! px-3! text-xs!" onclick={onClose}>
                <MaterialDesignIcon iconName="close" class="w-3.5 h-3.5" />
            </button>
        </div>
    </div>

    {#if selectedNode.destination_hash}
        <div class="p-3 rounded-lg bg-sem-surface-muted text-blue-700 dark:text-blue-300">
            <div class="flex items-center justify-between mb-1">
                <div class="text-xs font-bold uppercase tracking-wider">
                    {t("tools.mesh_server.destination_hash")}
                </div>
                {#if selectedNode.running}
                    <button
                        type="button"
                        class="primary-chip py-0.5! px-2! text-xs!"
                        onclick={() => onViewNode(selectedNode)}
                    >
                        <MaterialDesignIcon iconName="eye" class="w-3 h-3" />
                        {t("tools.mesh_server.view_in_browser")}
                    </button>
                {/if}
            </div>
            <div class="font-mono text-sm select-all">{selectedNode.destination_hash}</div>
        </div>
    {/if}

    <PageNodeAnnounceSettings
        bind:announceEnabled
        bind:announceIntervalMinutes
        bind:executablePagesEnabled
        {lastAnnouncedText}
        onSave={onSaveAnnounceSettings}
    />

    <div class="flex gap-2 border-b border-gray-200/60 dark:border-zinc-800/60">
        <button
            type="button"
            class="px-4 py-2 font-semibold transition text-sm -mb-px {detailTab === PAGE_NODE_TABS.PAGES
                ? 'border-b-2 border-blue-500 text-sem-accent'
                : 'text-gray-600 dark:text-gray-400'}"
            onclick={() => onTabChange(PAGE_NODE_TABS.PAGES)}
        >
            {t("tools.mesh_server.tabs_pages", {
                count: selectedNode.pages.length,
            })}
        </button>
        <button
            type="button"
            class="px-4 py-2 font-semibold transition text-sm -mb-px {detailTab === PAGE_NODE_TABS.FILES
                ? 'border-b-2 border-blue-500 text-sem-accent'
                : 'text-gray-600 dark:text-gray-400'}"
            onclick={() => onTabChange(PAGE_NODE_TABS.FILES)}
        >
            {t("tools.mesh_server.tabs_files", {
                count: selectedNode.files.length,
            })}
        </button>
    </div>

    {#if detailTab === PAGE_NODE_TABS.PAGES}
        <PageNodePagesTab
            pages={selectedNode.pages}
            {editingPage}
            bind:editingPageContent
            bind:editingPageExecutable
            {onAddPage}
            {onEditPage}
            {onDeletePage}
            {onSavePage}
            onCancelEdit={onCancelEditPage}
        />
    {:else if detailTab === PAGE_NODE_TABS.FILES}
        <PageNodeFilesTab files={selectedNode.files} {onUploadFile} {onDeleteFile} />
    {/if}
</div>
