<!-- SPDX-License-Identifier: 0BSD -->

<script lang="ts">
    import { t } from "../../../js/i18n.js";
    import type { NomadSection } from "../lib/types.js";

    interface Props {
        selectedCount: number;
        allVisibleSelected: boolean;
        orderedSections: NomadSection[];
        onToggleSelectAll: () => void;
        onMoveToSection: (sectionId: string) => void;
        onBulkRemove: () => void;
        onBulkExport: () => void;
    }

    let {
        selectedCount,
        allVisibleSelected,
        orderedSections,
        onToggleSelectAll,
        onMoveToSection,
        onBulkRemove,
        onBulkExport,
    }: Props = $props();

    let bulkMoveMenuOpen = $state(false);
</script>

<div class="flex flex-col gap-2 px-2 py-2 bg-blue-50 dark:bg-blue-900/10 rounded-lg">
    <div class="flex items-center gap-2 min-w-0 w-full">
        <div class="flex items-center gap-2 min-w-0 flex-1 overflow-hidden">
            <input
                type="checkbox"
                checked={allVisibleSelected}
                class="rounded-sm border-gray-300 text-blue-600 focus:ring-blue-500 shrink-0"
                onchange={onToggleSelectAll}
            />
            <span class="text-xs font-semibold text-blue-700 dark:text-blue-400 truncate leading-none">
                {t("nomadnet.bulk_selected_count", { count: selectedCount })}
            </span>
        </div>
        <div class="flex items-center gap-2 shrink-0">
            <div class="relative">
                <button
                    type="button"
                    class="inline-flex items-center whitespace-nowrap rounded px-0 py-0.5 text-xs font-bold leading-none text-blue-600 dark:text-blue-400 hover:underline disabled:pointer-events-none disabled:opacity-40"
                    disabled={selectedCount === 0}
                    onclick={(e) => {
                        e.stopPropagation();
                        bulkMoveMenuOpen = !bulkMoveMenuOpen;
                    }}
                >
                    {t("nomadnet.bulk_move_to_section")}
                </button>
                {#if bulkMoveMenuOpen}
                    <div
                        class="absolute right-0 top-full mt-1 z-50 min-w-36 bg-sem-surface border border-sem-border rounded-xl shadow-xl py-1 text-sem-fg"
                    >
                        {#each orderedSections as s (s.id)}
                            <button
                                type="button"
                                class="w-full text-left px-3 py-1.5 text-xs hover:bg-sem-surface-muted truncate"
                                onclick={() => {
                                    bulkMoveMenuOpen = false;
                                    onMoveToSection(s.id);
                                }}
                            >
                                {s.name}
                            </button>
                        {/each}
                    </div>
                {/if}
            </div>
            <button
                type="button"
                class="inline-flex items-center whitespace-nowrap rounded px-0 py-0.5 text-xs font-bold leading-none text-red-600 dark:text-red-400 hover:underline disabled:pointer-events-none disabled:opacity-40"
                disabled={selectedCount === 0}
                onclick={onBulkRemove}
            >
                {t("nomadnet.bulk_delete")}
            </button>
            <button
                type="button"
                class="inline-flex items-center whitespace-nowrap rounded px-0 py-0.5 text-xs font-bold leading-none text-gray-600 dark:text-gray-400 hover:underline disabled:pointer-events-none disabled:opacity-40"
                disabled={selectedCount === 0}
                onclick={onBulkExport}
            >
                {t("nomadnet.bulk_export")}
            </button>
        </div>
    </div>
</div>
