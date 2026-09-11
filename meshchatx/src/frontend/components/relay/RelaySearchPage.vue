<!-- SPDX-License-Identifier: 0BSD -->

<template>
    <div class="flex min-h-0 flex-1 flex-col overflow-hidden">
        <div class="shrink-0 border-b border-sem-border bg-sem-surface-muted px-3 py-2 sm:px-4">
            <SearchInput
                v-model="query"
                :loading="searching"
                :placeholder="$t('relay_chat.search_global_placeholder')"
                @input="scheduleSearch"
                @clear="clearSearch"
            />
            <p class="mt-1.5 text-xs text-sem-fg-muted">{{ $t("relay_chat.search_global_hint") }}</p>
        </div>

        <div class="flex-1 overflow-y-auto custom-scrollbar">
            <div
                v-if="!query.trim()"
                class="flex flex-col items-center gap-2 p-10 text-center text-sm text-sem-fg-muted"
            >
                <MaterialDesignIcon icon-name="text-search" class="size-10 opacity-40" />
                {{ $t("relay_chat.search_global_empty") }}
            </div>
            <div
                v-else-if="!searching && results.length === 0"
                class="flex flex-col items-center gap-2 p-10 text-center text-sm text-sem-fg-muted"
            >
                <MaterialDesignIcon icon-name="magnify-close" class="size-10 opacity-40" />
                {{ $t("relay_chat.search_global_none") }}
            </div>
            <template v-else>
                <div class="px-3 py-1.5 text-xs text-sem-fg-muted sm:px-4">
                    {{ $t("relay_chat.search_global_count", { count: results.length }) }}
                </div>
                <button
                    v-for="(hit, i) in results"
                    :key="i"
                    type="button"
                    class="flex w-full flex-col gap-0.5 border-b border-sem-border px-3 py-2.5 text-left transition-colors hover:bg-sem-surface-muted sm:px-4"
                    @click="$emit('open-room', { hubHash: hit.hub_hash, room: hit.room })"
                >
                    <span class="flex flex-wrap items-center gap-x-2 gap-y-0.5 text-xs text-sem-fg-muted">
                        <span class="font-medium text-sem-fg">{{ hit.hub_name || formatHash(hit.hub_hash) }}</span>
                        <span>#{{ hit.room }}</span>
                        <span v-if="hit.nick" class="text-sem-fg">{{ hit.nick }}</span>
                        <span>{{ timeAgo(hit.ts) }}</span>
                        <MaterialDesignIcon icon-name="arrow-right" class="ml-auto size-3.5 shrink-0 opacity-60" />
                    </span>
                    <!-- eslint-disable vue/no-v-html -- sanitized via renderMessageHtml -->
                    <span class="break-words text-sm text-sem-fg line-clamp-2" v-html="renderHit(hit.text)"></span>
                    <!-- eslint-enable vue/no-v-html -->
                </button>
            </template>
        </div>
    </div>
</template>

<script>
import MaterialDesignIcon from "../MaterialDesignIcon.vue";
import SearchInput from "../SearchInput.vue";
import MarkdownRenderer from "../../js/MarkdownRenderer.js";
import Utils from "../../js/Utils.js";

const SEARCH_DEBOUNCE_MS = 250;

export default {
    name: "RelaySearchPage",
    components: { MaterialDesignIcon, SearchInput },
    emits: ["open-room"],
    data() {
        return {
            query: "",
            results: [],
            searching: false,
            searchTimer: null,
            searchGen: 0,
        };
    },
    beforeUnmount() {
        if (this.searchTimer) clearTimeout(this.searchTimer);
    },
    methods: {
        formatHash(h) {
            const s = String(h || "");
            return s.length > 16 ? `${s.slice(0, 8)}…${s.slice(-6)}` : s;
        },
        timeAgo(ts) {
            return Utils.formatTimeAgoForI18n(ts);
        },
        renderHit(text) {
            return MarkdownRenderer.renderBasic(text);
        },
        scheduleSearch() {
            if (this.searchTimer) clearTimeout(this.searchTimer);
            this.searchTimer = setTimeout(() => this.runSearch(), SEARCH_DEBOUNCE_MS);
        },
        clearSearch() {
            this.query = "";
            this.results = [];
        },
        async runSearch() {
            const q = this.query.trim();
            if (!q) {
                this.results = [];
                this.searching = false;
                return;
            }
            const gen = ++this.searchGen;
            this.searching = true;
            try {
                const res = await window.api.get("/api/v1/rrc/search", {
                    params: { q, limit: 100 },
                });
                if (gen !== this.searchGen) return;
                this.results = res?.data?.results || [];
            } catch {
                if (gen === this.searchGen) this.results = [];
            } finally {
                if (gen === this.searchGen) this.searching = false;
            }
        },
    },
};
</script>
