<!-- SPDX-License-Identifier: 0BSD -->

<script lang="ts">
    import { tick } from "svelte";
    import MaterialDesignIcon from "../../../ui/svelte/MaterialDesignIcon.svelte";
    import type { MicronTab } from "../lib/types.js";

    interface Props {
        tabs: MicronTab[];
        activeTabIndex: number;
        onSelectTab: (index: number) => void;
        onAddTab: () => void;
        onRemoveTab: (index: number) => void;
        onRenameTab: (index: number, newName: string) => void;
    }

    let { tabs, activeTabIndex, onSelectTab, onAddTab, onRemoveTab, onRenameTab }: Props = $props();

    let editingTabIndex = $state(-1);
    let editingTabName = $state("");
    let tabInputEl = $state<HTMLInputElement | null>(null);

    async function startEditingTab(index: number): Promise<void> {
        editingTabIndex = index;
        editingTabName = tabs[index].name;
        await tick();
        if (tabInputEl) {
            tabInputEl.focus();
        }
    }

    function finishEditingTab(): void {
        if (editingTabIndex !== -1) {
            const trimmed = editingTabName.trim();
            if (trimmed) {
                onRenameTab(editingTabIndex, trimmed);
            }
            editingTabIndex = -1;
        }
    }
</script>

<div
    class="flex items-center px-3 sm:px-4 py-1 gap-1 border-b border-sem-border bg-slate-100 dark:bg-zinc-900 overflow-x-auto no-scrollbar shrink-0"
>
    {#each tabs as tab, index (tab.id)}
        <div
            class="group flex items-center h-8 px-3 rounded-lg text-xs font-medium transition-colors cursor-pointer whitespace-nowrap {activeTabIndex ===
            index
                ? 'bg-white dark:bg-zinc-800 text-teal-600 dark:text-teal-400 shadow-xs'
                : 'text-gray-500 hover:bg-white/50 dark:hover:bg-zinc-800/50 hover:text-gray-700 dark:hover:text-zinc-300'}"
            role="button"
            tabindex="0"
            onkeydown={(e) => {
                if (e.key === "Enter" && editingTabIndex !== index) {
                    onSelectTab(index);
                }
            }}
            onclick={() => {
                if (editingTabIndex !== index) {
                    onSelectTab(index);
                }
            }}
        >
            {#if editingTabIndex !== index}
                <span
                    role="button"
                    tabindex="0"
                    onkeydown={(e) => {
                        if (e.key === "Enter") {
                            e.stopPropagation();
                            void startEditingTab(index);
                        }
                    }}
                    ondblclick={(e) => {
                        e.stopPropagation();
                        void startEditingTab(index);
                    }}
                >
                    {tab.name}
                </span>
            {:else}
                <input
                    bind:this={tabInputEl}
                    bind:value={editingTabName}
                    class="bg-transparent border-none focus:ring-0 w-20 p-0 text-inherit"
                    onblur={finishEditingTab}
                    onkeyup={(e) => {
                        if (e.key === "Enter") finishEditingTab();
                    }}
                    onclick={(e) => e.stopPropagation()}
                />
            {/if}
            {#if tabs.length > 1}
                <button
                    type="button"
                    class="ml-1 inline-flex min-h-[28px] min-w-[28px] items-center justify-center opacity-100 lg:opacity-0 lg:group-hover:opacity-100 hover:text-red-500 transition-opacity"
                    onclick={(e) => {
                        e.stopPropagation();
                        onRemoveTab(index);
                    }}
                >
                    <MaterialDesignIcon iconName="close" class="size-3" />
                </button>
            {/if}
        </div>
    {/each}
    <button
        type="button"
        class="flex items-center justify-center size-8 text-gray-400 hover:text-teal-500 transition-colors"
        onclick={onAddTab}
    >
        <MaterialDesignIcon iconName="plus" class="size-4" />
    </button>
</div>
