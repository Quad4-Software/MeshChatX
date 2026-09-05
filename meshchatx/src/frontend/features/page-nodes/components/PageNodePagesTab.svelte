<!-- SPDX-License-Identifier: 0BSD -->

<script lang="ts">
    import { t } from "../../../js/i18n.js";
    import MaterialDesignIcon from "../../../ui/svelte/MaterialDesignIcon.svelte";
    import type { PageNodePageItem } from "../lib/types.js";
    import PageNodeToggle from "./PageNodeToggle.svelte";

    interface Props {
        pages: PageNodePageItem[];
        editingPage: string | null;
        editingPageContent: string;
        editingPageExecutable: boolean;
        onAddPage: (pageName: string) => void;
        onEditPage: (pageName: string) => void;
        onDeletePage: (pageName: string) => void;
        onSavePage: () => void;
        onCancelEdit: () => void;
    }

    let {
        pages,
        editingPage,
        editingPageContent = $bindable(""),
        editingPageExecutable = $bindable(false),
        onAddPage,
        onEditPage,
        onDeletePage,
        onSavePage,
        onCancelEdit,
    }: Props = $props();

    let newPageName = $state("");

    function handleAdd() {
        if (!newPageName.trim()) return;
        onAddPage(newPageName.trim());
        newPageName = "";
    }

    function handleKeydown(event: KeyboardEvent) {
        if (event.key === "Enter") {
            handleAdd();
        }
    }
</script>

<div class="space-y-3">
    <div class="flex gap-2">
        <input
            type="text"
            placeholder={t("tools.mesh_server.page_name_placeholder")}
            class="input-field flex-1"
            bind:value={newPageName}
            onkeydown={handleKeydown}
        />
        <button type="button" class="primary-chip py-1! px-3! text-xs!" onclick={handleAdd}>
            <MaterialDesignIcon iconName="plus" class="w-3.5 h-3.5" />
            {t("tools.mesh_server.add_page")}
        </button>
    </div>

    {#if pages.length === 0}
        <div class="text-sm text-sem-fg-muted py-4 text-center">
            {t("tools.mesh_server.no_pages")}
        </div>
    {/if}

    {#each pages as page (page.name)}
        <div
            class="flex items-center justify-between p-3 rounded-lg bg-slate-50 dark:bg-zinc-800/50 border border-sem-border"
        >
            <div class="flex items-center gap-2">
                <MaterialDesignIcon iconName="file-document-outline" class="w-4 h-4 text-teal-500" />
                <span class="text-sm font-mono text-sem-fg">{page.name}</span>
                {#if page.executable}
                    <span
                        class="text-[10px] uppercase tracking-wide px-1.5 py-0.5 rounded bg-violet-100 dark:bg-violet-900/40 text-violet-700 dark:text-violet-300"
                    >
                        {t("tools.mesh_server.executable_badge")}
                    </span>
                {/if}
            </div>
            <div class="flex items-center gap-2">
                <button
                    type="button"
                    class="secondary-chip py-0.5! px-2! text-xs!"
                    onclick={() => onEditPage(page.name)}
                >
                    {t("common.edit")}
                </button>
                <button
                    type="button"
                    class="secondary-chip py-0.5! px-2! text-xs! text-red-500!"
                    onclick={() => onDeletePage(page.name)}
                >
                    <MaterialDesignIcon iconName="delete" class="w-3 h-3" />
                </button>
            </div>
        </div>
    {/each}

    {#if editingPage}
        <div class="space-y-2">
            <div class="flex items-center justify-between">
                <div class="text-sm font-semibold text-sem-fg">
                    {t("tools.mesh_server.editing_page", {
                        name: editingPage,
                    })}
                </div>
                <div class="flex gap-2">
                    <button type="button" class="primary-chip py-1! px-3! text-xs!" onclick={onSavePage}>
                        {t("common.save")}
                    </button>
                    <button type="button" class="secondary-chip py-1! px-3! text-xs!" onclick={onCancelEdit}>
                        {t("common.cancel")}
                    </button>
                </div>
            </div>
            <div class="flex items-center gap-2">
                <PageNodeToggle
                    id="mesh-server-page-executable"
                    bind:checked={editingPageExecutable}
                    label={t("tools.mesh_server.page_executable_label")}
                />
            </div>
            <textarea
                class="w-full h-64 bg-sem-surface text-sem-fg p-3 font-mono text-sm rounded-lg border border-sem-border resize-y focus:outline-hidden focus:ring-2 focus:ring-blue-500/50"
                bind:value={editingPageContent}></textarea>
        </div>
    {/if}
</div>
