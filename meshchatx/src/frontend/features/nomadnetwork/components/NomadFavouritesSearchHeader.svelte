<!-- SPDX-License-Identifier: 0BSD -->

<script lang="ts">
    import MaterialDesignIcon from "../../../ui/svelte/MaterialDesignIcon.svelte";
    import { t } from "../../../js/i18n.js";

    interface Props {
        searchTerm: string;
        favouritesCount: number;
        selectionMode: boolean;
        onSearchChange: (term: string) => void;
        onAddSection: () => void;
        onToggleSelectionMode: () => void;
    }

    let { searchTerm, favouritesCount, selectionMode, onSearchChange, onAddSection, onToggleSelectionMode }: Props =
        $props();
</script>

<div class="flex gap-1.5 items-center">
    <input
        value={searchTerm}
        type="text"
        placeholder={t("nomadnet.search_placeholder_favourites", { count: favouritesCount })}
        class="input-field flex-1 min-w-0"
        oninput={(e) => onSearchChange((e.target as HTMLInputElement).value)}
    />
    <button
        type="button"
        class="icon-btn-sem press-feedback text-sem-fg-muted hover:text-sem-fg hover:bg-sem-surface-muted p-2 rounded-full min-w-11 min-h-11 w-11 h-11 flex items-center justify-center shrink-0 transition-colors duration-200 focus-ring-sem"
        title={t("nomadnet.add_section")}
        onclick={onAddSection}
    >
        <MaterialDesignIcon iconName="folder-plus-outline" class="size-5" />
    </button>
    <button
        type="button"
        class="shrink-0 self-center inline-flex items-center justify-center p-0.5 rounded-sm text-gray-400 hover:text-blue-500 dark:hover:text-blue-400 transition-colors leading-none"
        title={t("nomadnet.sidebar_selection_mode")}
        class:text-blue-500={selectionMode}
        onclick={onToggleSelectionMode}
    >
        <span class="block size-[14px]">
            <MaterialDesignIcon iconName="checkbox-multiple-marked-outline" />
        </span>
    </button>
</div>
