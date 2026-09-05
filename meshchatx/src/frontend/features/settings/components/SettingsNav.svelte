<!-- SPDX-License-Identifier: 0BSD -->

<script lang="ts">
    import { SETTINGS_TABS } from "../../../js/settings/settingsTabs.js";
    import { t } from "../../../js/i18n.js";

    interface Props {
        activeTab: string;
        matchCounts?: Record<string, number> | null;
        isSearching?: boolean;
        onselect?: (tabId: string) => void;
        onselecttab?: (tabId: string) => void;
    }

    let { activeTab, matchCounts = null, isSearching = false, onselect, onselecttab }: Props = $props();

    const tabs = SETTINGS_TABS;
    const searchActive = $derived(matchCounts != null || isSearching);

    function matchCount(tabId: string): number {
        if (matchCounts) {
            const n = matchCounts[tabId];
            return typeof n === "number" && n > 0 ? n : 0;
        }
        return 0;
    }

    function isSearchEmpty(tabId: string): boolean {
        return searchActive && matchCount(tabId) === 0 && matchCounts != null;
    }

    function onTabClick(tabId: string) {
        if (isSearchEmpty(tabId)) return;
        onselect?.(tabId);
        onselecttab?.(tabId);
    }
</script>

<nav
    class="settings-nav flex gap-1 overflow-x-auto pb-1 lg:flex-col lg:overflow-x-visible lg:pb-0 lg:gap-0.5 lg:w-52 lg:shrink-0 lg:sticky lg:top-20 lg:self-start"
    aria-label={t("settings.nav_label")}
>
    {#each tabs as tab (tab.id)}
        <button
            type="button"
            class="settings-nav__tab flex flex-col items-start gap-0.5 rounded-xl border border-transparent px-3 py-2.5 text-left transition-colors shrink-0 lg:w-full text-sem-fg-muted hover:bg-sem-surface-muted {tab.id ===
            activeTab
                ? 'border-sem-border bg-sem-surface text-sem-fg shadow-xs'
                : ''} {isSearchEmpty(tab.id) ? 'opacity-40 pointer-events-none' : ''}"
            aria-current={tab.id === activeTab ? "page" : undefined}
            disabled={isSearchEmpty(tab.id)}
            onclick={() => onTabClick(tab.id)}
        >
            <span class="flex items-center gap-2 w-full min-w-0">
                <span class="text-sm font-semibold leading-tight min-w-0 truncate">{t(tab.labelKey)}</span>
                {#if searchActive}
                    <span
                        class="ml-auto text-[10px] font-semibold tabular-nums rounded-md px-1.5 py-0.5 bg-sem-surface-muted text-sem-fg-muted"
                    >
                        {matchCount(tab.id)}
                    </span>
                {/if}
            </span>
            <span class="hidden text-xs text-sem-fg-muted lg:block">{t(tab.descriptionKey)}</span>
        </button>
    {/each}
</nav>
