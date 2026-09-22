<!-- SPDX-License-Identifier: 0BSD -->

<script lang="ts">
    import MaterialDesignIcon from "../../../ui/svelte/MaterialDesignIcon.svelte";
    import { t } from "../../../js/i18n.js";
    import { listNavItems } from "../../../js/registries/navRegistry.js";
    import type { NavEntry } from "../../../js/registries/navRegistry.js";
    import {
        resolveTopNavItemIds,
        resetTopNavItemIds,
        saveTopNavItemIds,
        topNavLayoutState,
    } from "../../../js/appTopNavLayout.svelte.js";

    type TopNavRow = { item: NavEntry; pinned: boolean; pinnedIndex: number };

    const topNavItemIds = $derived(resolveTopNavItemIds(topNavLayoutState.itemIds));

    const topNavEditorRows = $derived.by((): TopNavRow[] => {
        const pinnedIds = topNavItemIds;
        const allItems = listNavItems();
        const byId = new Map(allItems.map((item) => [item.id, item]));
        const rows: TopNavRow[] = [];
        for (const id of pinnedIds) {
            const item = byId.get(id);
            if (item) {
                rows.push({ item, pinned: true, pinnedIndex: rows.length });
            }
        }
        for (const item of allItems) {
            if (!pinnedIds.includes(item.id)) {
                rows.push({ item, pinned: false, pinnedIndex: -1 });
            }
        }
        return rows;
    });

    const topNavPinnedCount = $derived(topNavEditorRows.filter((row) => row.pinned).length);

    function toggleTopNavItem(id: string) {
        const ids = [...topNavItemIds];
        const index = ids.indexOf(id);
        if (index >= 0) {
            ids.splice(index, 1);
        } else {
            ids.push(id);
        }
        saveTopNavItemIds(ids);
    }

    function moveTopNavItem(id: string, delta: number) {
        const ids = [...topNavItemIds];
        const index = ids.indexOf(id);
        const target = index + delta;
        if (index < 0 || target < 0 || target >= ids.length) {
            return;
        }
        ids.splice(index, 1);
        ids.splice(target, 0, id);
        saveTopNavItemIds(ids);
    }

    function resetTopNav() {
        resetTopNavItemIds();
    }
</script>

<div class="space-y-2">
    <div class="flex items-center justify-between gap-2">
        <div class="text-sm font-medium text-sem-fg">
            {t("app.top_nav_buttons")}
        </div>
        <button
            type="button"
            class="text-xs font-semibold text-sem-accent hover:underline cursor-pointer"
            onclick={resetTopNav}
        >
            {t("app.top_nav_reset")}
        </button>
    </div>
    <p class="text-xs text-sem-fg-muted">
        {t("app.top_nav_description")}
    </p>
    <ul class="divide-y divide-sem-border rounded-xl border border-sem-border overflow-hidden">
        {#each topNavEditorRows as row (row.item.id)}
            <li
                class="flex items-center gap-2 px-3 py-2 {row.pinned
                    ? 'bg-sem-surface'
                    : 'bg-sem-surface-muted/40 opacity-60'}"
                data-testid={`topnav-row-${row.item.id}`}
            >
                <input
                    type="checkbox"
                    class="size-4 shrink-0 accent-sem-accent"
                    checked={row.pinned}
                    aria-label={t(row.item.labelKey)}
                    onchange={() => toggleTopNavItem(row.item.id)}
                />
                <MaterialDesignIcon iconName={row.item.icon} class="size-4 shrink-0 text-sem-fg-muted" />
                <span class="flex-1 min-w-0 truncate text-sm text-sem-fg">{t(row.item.labelKey)}</span>
                {#if row.pinned}
                    <button
                        type="button"
                        class="p-1 rounded-md text-sem-fg-muted hover:bg-sem-surface-muted disabled:opacity-30 cursor-pointer"
                        disabled={row.pinnedIndex === 0}
                        title={t("app.nav_move_up")}
                        aria-label={t("app.nav_move_up")}
                        onclick={() => moveTopNavItem(row.item.id, -1)}
                    >
                        <MaterialDesignIcon iconName="chevron-up" class="size-4" />
                    </button>
                    <button
                        type="button"
                        class="p-1 rounded-md text-sem-fg-muted hover:bg-sem-surface-muted disabled:opacity-30 cursor-pointer"
                        disabled={row.pinnedIndex === topNavPinnedCount - 1}
                        title={t("app.nav_move_down")}
                        aria-label={t("app.nav_move_down")}
                        onclick={() => moveTopNavItem(row.item.id, 1)}
                    >
                        <MaterialDesignIcon iconName="chevron-down" class="size-4" />
                    </button>
                {/if}
            </li>
        {/each}
    </ul>
</div>
