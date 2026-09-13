<!-- SPDX-License-Identifier: 0BSD -->

<script lang="ts">
    import { onDestroy } from "svelte";
    import MaterialDesignIcon from "../../../ui/svelte/MaterialDesignIcon.svelte";
    import SearchInput from "../../../ui/svelte/SearchInput.svelte";
    import MarkdownRenderer from "../../../js/MarkdownRenderer.js";
    import Utils from "../../../js/Utils.js";
    import { apiPath } from "../../../js/constants.js";
    import { t } from "../../../js/i18n.js";
    import type { RrcSearchHit } from "../lib/types.js";

    const SEARCH_DEBOUNCE_MS = 250;

    interface Props {
        onopenroom?: (target: { hubHash: string; room: string }) => void;
    }

    let { onopenroom }: Props = $props();

    let query = $state("");
    let results = $state<RrcSearchHit[]>([]);
    let searching = $state(false);
    let searchTimer: ReturnType<typeof setTimeout> | null = null;
    let searchGen = 0;

    function formatHash(h: unknown): string {
        const s = String(h || "");
        return s.length > 16 ? `${s.slice(0, 8)}…${s.slice(-6)}` : s;
    }

    function timeAgo(ts: number | string | undefined): string {
        return Utils.formatTimeAgoForI18n(ts);
    }

    function renderHit(text: string): string {
        return MarkdownRenderer.renderBasic(text);
    }

    function scheduleSearch(): void {
        if (searchTimer) clearTimeout(searchTimer);
        searchTimer = setTimeout(() => void runSearch(), SEARCH_DEBOUNCE_MS);
    }

    function clearSearch(): void {
        query = "";
        results = [];
    }

    async function runSearch(): Promise<void> {
        const q = query.trim();
        if (!q) {
            results = [];
            searching = false;
            return;
        }
        const gen = ++searchGen;
        searching = true;
        try {
            const res = await window.api.get(apiPath("/rrc/search"), {
                params: { q, limit: 100 },
            });
            if (gen !== searchGen) return;
            results = (res?.data as { results?: RrcSearchHit[] })?.results || [];
        } catch {
            if (gen === searchGen) results = [];
        } finally {
            if (gen === searchGen) searching = false;
        }
    }

    onDestroy(() => {
        if (searchTimer) clearTimeout(searchTimer);
    });
</script>

<div class="flex min-h-0 flex-1 flex-col overflow-hidden">
    <div class="shrink-0 border-b border-sem-border bg-sem-surface-muted px-3 py-2 sm:px-4">
        <SearchInput
            bind:value={query}
            loading={searching}
            placeholder={t("relay_chat.search_global_placeholder")}
            oninput={scheduleSearch}
            onclear={clearSearch}
        />
        <p class="mt-1.5 text-xs text-sem-fg-muted">{t("relay_chat.search_global_hint")}</p>
    </div>

    <div class="flex-1 overflow-y-auto custom-scrollbar">
        {#if !query.trim()}
            <div class="flex flex-col items-center gap-2 p-10 text-center text-sm text-sem-fg-muted">
                <MaterialDesignIcon iconName="text-search" class="size-10 opacity-40" />
                {t("relay_chat.search_global_empty")}
            </div>
        {:else if !searching && results.length === 0}
            <div class="flex flex-col items-center gap-2 p-10 text-center text-sm text-sem-fg-muted">
                <MaterialDesignIcon iconName="magnify-close" class="size-10 opacity-40" />
                {t("relay_chat.search_global_none")}
            </div>
        {:else}
            <div class="px-3 py-1.5 text-xs text-sem-fg-muted sm:px-4">
                {t("relay_chat.search_global_count", { count: results.length })}
            </div>
            {#each results as hit, i (i)}
                <button
                    type="button"
                    class="flex w-full flex-col gap-0.5 border-b border-sem-border px-3 py-2.5 text-left transition-colors hover:bg-sem-surface-muted sm:px-4"
                    onclick={() => onopenroom?.({ hubHash: hit.hub_hash, room: hit.room })}
                >
                    <span class="flex flex-wrap items-center gap-x-2 gap-y-0.5 text-xs text-sem-fg-muted">
                        <span class="font-medium text-sem-fg">{hit.hub_name || formatHash(hit.hub_hash)}</span>
                        <span>#{hit.room}</span>
                        {#if hit.nick}
                            <span class="text-sem-fg">{hit.nick}</span>
                        {/if}
                        <span>{timeAgo(hit.ts)}</span>
                        <MaterialDesignIcon iconName="arrow-right" class="ml-auto size-3.5 shrink-0 opacity-60" />
                    </span>
                    <!-- sanitized via MarkdownRenderer.renderBasic -->
                    <span class="break-words text-sm text-sem-fg line-clamp-2">{@html renderHit(hit.text)}</span>
                </button>
            {/each}
        {/if}
    </div>
</div>
