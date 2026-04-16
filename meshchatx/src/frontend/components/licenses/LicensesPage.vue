<!-- SPDX-License-Identifier: 0BSD -->

<template>
    <div class="flex flex-col flex-1 overflow-hidden min-w-0 bg-white dark:bg-zinc-950">
        <div class="flex-1 flex flex-col min-h-0 overflow-y-auto overscroll-y-contain w-full">
            <div class="shrink-0 border-b border-gray-200 dark:border-zinc-800 px-3 sm:px-4 md:px-6 py-4 md:py-5">
                <div class="flex flex-col gap-4 lg:flex-row lg:items-end lg:justify-between lg:gap-6">
                    <div class="space-y-2 min-w-0 flex-1">
                        <div class="text-xs uppercase tracking-wide text-gray-500 dark:text-gray-400">
                            {{ $t("licenses.section_label") }}
                        </div>
                        <div
                            class="text-xl sm:text-2xl md:text-3xl font-black text-gray-900 dark:text-white tracking-tight"
                        >
                            {{ $t("licenses.title") }}
                        </div>
                        <div class="text-sm text-gray-600 dark:text-gray-300 leading-relaxed max-w-2xl">
                            {{ $t("licenses.description") }}
                        </div>
                        <p v-if="meta?.generated_at" class="text-xs text-gray-500 dark:text-zinc-500 break-words">
                            {{ $t("licenses.generated_at", { time: meta.generated_at }) }}
                            <span v-if="meta.frontend_source" class="ml-2 inline-block sm:inline">
                                ({{ $t("licenses.frontend_source", { source: meta.frontend_source }) }})
                            </span>
                        </p>
                    </div>

                    <div class="w-full lg:max-w-md xl:max-w-sm shrink-0">
                        <div class="relative group">
                            <div class="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
                                <MaterialDesignIcon
                                    icon-name="magnify"
                                    class="size-5 text-gray-400 group-focus-within:text-blue-500 transition-colors"
                                />
                            </div>
                            <input
                                v-model="searchQuery"
                                type="search"
                                enterkeyhint="search"
                                autocomplete="off"
                                :placeholder="$t('licenses.search_placeholder')"
                                class="w-full min-h-[44px] sm:min-h-0 pl-10 pr-10 py-3 bg-gray-50 dark:bg-zinc-900 border border-gray-200 dark:border-zinc-800 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500/40 focus:border-blue-500 text-gray-900 dark:text-white placeholder-gray-400 dark:placeholder-gray-500 text-base sm:text-sm"
                            />
                            <button
                                v-if="searchQuery"
                                class="absolute inset-y-0 right-0 pr-3 flex items-center min-w-[44px] justify-end text-gray-400 hover:text-gray-600 dark:hover:text-gray-200"
                                type="button"
                                aria-label="Clear search"
                                @click="searchQuery = ''"
                            >
                                <MaterialDesignIcon icon-name="close-circle" class="size-5" />
                            </button>
                        </div>
                    </div>
                </div>
            </div>

            <div
                class="flex-1 min-h-0 p-3 sm:p-4 md:p-6 xl:p-8 w-full max-w-6xl xl:max-w-[min(100%,96rem)] mx-auto flex flex-col gap-4"
            >
                <div
                    v-if="loadError"
                    class="rounded-lg border border-red-200 dark:border-red-900/50 bg-red-50 dark:bg-red-950/30 px-4 py-3 text-sm text-red-800 dark:text-red-200"
                >
                    {{ loadError }}
                </div>

                <div
                    v-if="loading"
                    class="flex flex-col items-center justify-center py-16 gap-3 text-gray-500 dark:text-zinc-400"
                >
                    <MaterialDesignIcon icon-name="loading" class="size-10 animate-spin" />
                    <span>{{ $t("common.loading") }}</span>
                </div>

                <template v-else>
                    <div class="license-grid grid grid-cols-1 gap-4 xl:grid-cols-2 xl:gap-6 xl:items-start">
                        <details
                            class="license-details rounded-lg border border-gray-200 dark:border-zinc-800 bg-gray-50/50 dark:bg-zinc-900/40 open:bg-white dark:open:bg-zinc-950 overflow-hidden"
                            open
                        >
                            <summary
                                class="cursor-pointer select-none px-3 sm:px-4 py-3.5 sm:py-3 min-h-[48px] sm:min-h-0 font-semibold text-sm sm:text-base text-gray-900 dark:text-white flex items-center justify-between gap-2 list-none touch-manipulation"
                            >
                                <span class="min-w-0 break-words pr-2"
                                    >{{ $t("licenses.backend_section") }} ({{ filteredBackend.length }})</span
                                >
                                <MaterialDesignIcon
                                    icon-name="chevron-down"
                                    class="license-details-chevron size-5 shrink-0 opacity-60"
                                />
                            </summary>
                            <div
                                class="license-details-body border-t border-gray-100/80 dark:border-zinc-800/50 max-h-[min(65vh,32rem)] xl:max-h-[min(calc(100dvh-14rem),44rem)] overflow-x-auto overflow-y-auto overscroll-contain px-1 sm:px-2 pb-3 sm:pb-4"
                            >
                                <table class="min-w-full text-left border-collapse text-xs sm:text-sm">
                                    <thead>
                                        <tr
                                            class="sticky top-0 z-[1] border-b border-gray-200 dark:border-zinc-800 bg-gray-50/95 dark:bg-zinc-900/95 backdrop-blur-sm text-gray-600 dark:text-zinc-400"
                                        >
                                            <th class="py-2 px-2 sm:px-3 font-medium">
                                                {{ $t("licenses.col_package") }}
                                            </th>
                                            <th class="py-2 px-2 sm:px-3 font-medium whitespace-nowrap">
                                                {{ $t("licenses.col_version") }}
                                            </th>
                                            <th class="py-2 px-2 sm:px-3 font-medium">
                                                {{ $t("licenses.col_author") }}
                                            </th>
                                            <th class="py-2 px-2 sm:px-3 font-medium">
                                                {{ $t("licenses.col_license") }}
                                            </th>
                                        </tr>
                                    </thead>
                                    <tbody>
                                        <tr
                                            v-for="row in filteredBackend"
                                            :key="'b-' + row.name + row.version"
                                            class="border-b border-gray-100 dark:border-zinc-800/80 hover:bg-gray-50/80 dark:hover:bg-zinc-900/60"
                                        >
                                            <td
                                                class="py-2 px-2 sm:px-3 font-mono text-[11px] sm:text-xs text-gray-900 dark:text-zinc-100 align-top"
                                            >
                                                {{ row.name }}
                                            </td>
                                            <td
                                                class="py-2 px-2 sm:px-3 text-gray-700 dark:text-zinc-300 align-top whitespace-nowrap"
                                            >
                                                {{ row.version }}
                                            </td>
                                            <td
                                                class="py-2 px-2 sm:px-3 text-gray-700 dark:text-zinc-300 max-w-[10rem] sm:max-w-[14rem] truncate align-top"
                                                :title="row.author"
                                            >
                                                {{ row.author }}
                                            </td>
                                            <td
                                                class="py-2 px-2 sm:px-3 text-gray-700 dark:text-zinc-300 max-w-[8rem] sm:max-w-xs align-top break-words"
                                            >
                                                {{ row.license }}
                                            </td>
                                        </tr>
                                    </tbody>
                                </table>
                                <p
                                    v-if="filteredBackend.length === 0"
                                    class="text-center py-8 text-gray-500 dark:text-zinc-500 text-sm"
                                >
                                    {{ $t("common.no_results") }}
                                </p>
                            </div>
                        </details>

                        <details
                            class="license-details rounded-lg border border-gray-200 dark:border-zinc-800 bg-gray-50/50 dark:bg-zinc-900/40 open:bg-white dark:open:bg-zinc-950 overflow-hidden"
                            open
                        >
                            <summary
                                class="cursor-pointer select-none px-3 sm:px-4 py-3.5 sm:py-3 min-h-[48px] sm:min-h-0 font-semibold text-sm sm:text-base text-gray-900 dark:text-white flex items-center justify-between gap-2 list-none touch-manipulation"
                            >
                                <span class="min-w-0 break-words pr-2"
                                    >{{ $t("licenses.frontend_section") }} ({{ filteredFrontend.length }})</span
                                >
                                <MaterialDesignIcon
                                    icon-name="chevron-down"
                                    class="license-details-chevron size-5 shrink-0 opacity-60"
                                />
                            </summary>
                            <div
                                class="license-details-body border-t border-gray-100/80 dark:border-zinc-800/50 max-h-[min(65vh,32rem)] xl:max-h-[min(calc(100dvh-14rem),44rem)] overflow-x-auto overflow-y-auto overscroll-contain px-1 sm:px-2 pb-3 sm:pb-4"
                            >
                                <table class="min-w-full text-left border-collapse text-xs sm:text-sm">
                                    <thead>
                                        <tr
                                            class="sticky top-0 z-[1] border-b border-gray-200 dark:border-zinc-800 bg-gray-50/95 dark:bg-zinc-900/95 backdrop-blur-sm text-gray-600 dark:text-zinc-400"
                                        >
                                            <th class="py-2 px-2 sm:px-3 font-medium">
                                                {{ $t("licenses.col_package") }}
                                            </th>
                                            <th class="py-2 px-2 sm:px-3 font-medium whitespace-nowrap">
                                                {{ $t("licenses.col_version") }}
                                            </th>
                                            <th class="py-2 px-2 sm:px-3 font-medium">
                                                {{ $t("licenses.col_author") }}
                                            </th>
                                            <th class="py-2 px-2 sm:px-3 font-medium">
                                                {{ $t("licenses.col_license") }}
                                            </th>
                                        </tr>
                                    </thead>
                                    <tbody>
                                        <tr
                                            v-for="row in filteredFrontend"
                                            :key="'f-' + row.name + row.version"
                                            class="border-b border-gray-100 dark:border-zinc-800/80 hover:bg-gray-50/80 dark:hover:bg-zinc-900/60"
                                        >
                                            <td
                                                class="py-2 px-2 sm:px-3 font-mono text-[11px] sm:text-xs text-gray-900 dark:text-zinc-100 align-top"
                                            >
                                                {{ row.name }}
                                            </td>
                                            <td
                                                class="py-2 px-2 sm:px-3 text-gray-700 dark:text-zinc-300 align-top whitespace-nowrap"
                                            >
                                                {{ row.version }}
                                            </td>
                                            <td
                                                class="py-2 px-2 sm:px-3 text-gray-700 dark:text-zinc-300 max-w-[10rem] sm:max-w-[14rem] truncate align-top"
                                                :title="row.author"
                                            >
                                                {{ row.author }}
                                            </td>
                                            <td
                                                class="py-2 px-2 sm:px-3 text-gray-700 dark:text-zinc-300 max-w-[8rem] sm:max-w-xs align-top break-words"
                                            >
                                                {{ row.license }}
                                            </td>
                                        </tr>
                                    </tbody>
                                </table>
                                <p
                                    v-if="filteredFrontend.length === 0"
                                    class="text-center py-8 text-gray-500 dark:text-zinc-500 text-sm"
                                >
                                    {{ $t("common.no_results") }}
                                </p>
                            </div>
                        </details>
                    </div>
                </template>
            </div>
        </div>
    </div>
</template>

<script>
import MaterialDesignIcon from "../MaterialDesignIcon.vue";

export default {
    name: "LicensesPage",
    components: { MaterialDesignIcon },
    data() {
        return {
            loading: true,
            loadError: null,
            searchQuery: "",
            backend: [],
            frontend: [],
            meta: null,
        };
    },
    computed: {
        q() {
            return this.searchQuery.trim().toLowerCase();
        },
        filteredBackend() {
            return this.filterRows(this.backend);
        },
        filteredFrontend() {
            return this.filterRows(this.frontend);
        },
    },
    async mounted() {
        await this.load();
    },
    methods: {
        filterRows(rows) {
            if (!this.q) {
                return rows;
            }
            return rows.filter((r) => {
                const blob = `${r.name} ${r.version} ${r.author} ${r.license}`.toLowerCase();
                return blob.includes(this.q);
            });
        },
        async load() {
            this.loading = true;
            this.loadError = null;
            try {
                const res = await window.api.get("/api/v1/licenses");
                this.backend = res.data.backend || [];
                this.frontend = res.data.frontend || [];
                this.meta = res.data.meta || null;
            } catch (e) {
                this.loadError = e.response?.data?.error || e.message || "Failed to load licenses";
            } finally {
                this.loading = false;
            }
        },
    },
};
</script>

<style scoped>
.license-details summary::-webkit-details-marker {
    display: none;
}
.license-details summary::marker {
    display: none;
}
.license-details[open] .license-details-chevron {
    transform: rotate(180deg);
}
.license-details-chevron {
    transition: transform 0.15s ease;
}
.license-details-body {
    -webkit-overflow-scrolling: touch;
}
</style>
