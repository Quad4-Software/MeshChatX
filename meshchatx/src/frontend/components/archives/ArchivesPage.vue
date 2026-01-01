<template>
    <!-- eslint-disable vue/no-v-html -->
    <div class="flex flex-col flex-1 h-full overflow-hidden bg-slate-50 dark:bg-zinc-950">
        <!-- header -->
        <div
            class="flex items-center px-4 py-4 bg-white dark:bg-zinc-900 border-b border-gray-200 dark:border-zinc-800 shadow-sm"
        >
            <div class="flex items-center gap-3">
                <div class="p-2 bg-blue-100 dark:bg-blue-900/30 rounded-lg">
                    <MaterialDesignIcon icon-name="archive" class="size-6 text-blue-600 dark:text-blue-400" />
                </div>
                <div>
                    <h1 class="text-xl font-bold text-gray-900 dark:text-white">{{ $t("app.archives") }}</h1>
                    <p class="text-sm text-gray-500 dark:text-gray-400">{{ $t("archives.description") }}</p>
                </div>
            </div>

            <div class="ml-auto flex items-center gap-2 sm:gap-4">
                <div class="relative w-32 sm:w-64 md:w-80">
                    <div class="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
                        <MaterialDesignIcon icon-name="magnify" class="size-5 text-gray-400" />
                    </div>
                    <input
                        v-model="searchQuery"
                        type="text"
                        class="block w-full pl-10 pr-3 py-2 border border-gray-300 dark:border-zinc-700 rounded-lg bg-gray-50 dark:bg-zinc-800 text-gray-900 dark:text-gray-100 placeholder-gray-500 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent transition-all"
                        :placeholder="$t('archives.search_placeholder')"
                        @input="onSearchInput"
                    />
                </div>
                <button
                    class="p-2 text-gray-500 hover:text-blue-500 dark:text-gray-400 dark:hover:text-blue-400 transition-colors"
                    :title="$t('common.refresh')"
                    @click="getArchives"
                >
                    <MaterialDesignIcon icon-name="refresh" class="size-6" :class="{ 'animate-spin': isLoading }" />
                </button>
            </div>
        </div>

        <!-- content -->
        <div class="flex-1 overflow-y-auto p-4 md:p-6">
            <div v-if="isLoading && archives.length === 0" class="flex flex-col items-center justify-center h-64">
                <div class="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-500 mb-4"></div>
                <p class="text-gray-500 dark:text-gray-400">{{ $t("archives.loading") }}</p>
            </div>

            <div
                v-else-if="groupedArchives.length === 0"
                class="flex flex-col items-center justify-center h-64 text-center"
            >
                <div class="p-4 bg-gray-100 dark:bg-zinc-800 rounded-full mb-4 text-gray-400 dark:text-zinc-600">
                    <MaterialDesignIcon icon-name="archive-off" class="size-12" />
                </div>
                <h3 class="text-lg font-medium text-gray-900 dark:text-white">
                    {{ $t("archives.no_archives_found") }}
                </h3>
                <p class="text-gray-500 dark:text-gray-400 max-w-sm mx-auto">
                    {{ searchQuery ? $t("archives.adjust_filters") : $t("archives.browse_to_archive") }}
                </p>
            </div>

            <div v-else class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6 items-stretch">
                <div v-for="group in groupedArchives" :key="group.destination_hash" class="relative flex">
                    <div class="sticky top-6 w-full flex flex-col">
                        <div
                            class="bg-white dark:bg-zinc-900 border border-gray-200 dark:border-zinc-800 rounded-xl shadow-lg overflow-hidden flex flex-col h-full min-h-[400px]"
                        >
                            <div
                                class="p-5 border-b border-gray-100 dark:border-zinc-800 bg-gradient-to-r from-blue-50 to-indigo-50 dark:from-zinc-800 dark:to-zinc-800/50"
                            >
                                <div class="flex items-center justify-between mb-3">
                                    <span
                                        class="text-xs font-bold px-3 py-1.5 bg-blue-500 dark:bg-blue-600 text-white rounded-full uppercase tracking-wider shadow-sm"
                                    >
                                        {{ group.archives.length }}
                                        {{ group.archives.length === 1 ? $t("archives.page") : $t("archives.pages") }}
                                    </span>
                                </div>
                                <h4
                                    class="text-base font-bold text-gray-900 dark:text-white mb-1 truncate"
                                    :title="group.node_name"
                                >
                                    {{ group.node_name }}
                                </h4>
                                <p class="text-xs text-gray-600 dark:text-gray-400 font-mono truncate">
                                    {{ group.destination_hash.substring(0, 16) }}...
                                </p>
                            </div>
                            <div class="p-5 pb-6 flex-1 flex flex-col min-h-0">
                                <CardStack :items="group.archives" :max-visible="3">
                                    <template #default="{ item: archive }">
                                        <div
                                            class="stacked-card bg-white dark:bg-zinc-800 border border-gray-200 dark:border-zinc-700 rounded-lg p-4 h-full flex flex-col hover:shadow-xl transition-all duration-200 cursor-pointer group"
                                            @click="viewArchive(archive)"
                                        >
                                            <div class="flex items-start justify-between mb-3">
                                                <div class="flex-1 min-w-0">
                                                    <p
                                                        class="text-sm font-semibold text-gray-900 dark:text-gray-100 font-mono truncate mb-1 group-hover:text-blue-600 dark:group-hover:text-blue-400 transition-colors"
                                                        :title="archive.page_path || '/'"
                                                    >
                                                        {{ archive.page_path || "/" }}
                                                    </p>
                                                    <div
                                                        class="flex items-center gap-2 text-xs text-gray-500 dark:text-gray-400"
                                                    >
                                                        <MaterialDesignIcon icon-name="clock-outline" class="size-3" />
                                                        <span>{{ formatDate(archive.created_at) }}</span>
                                                    </div>
                                                </div>
                                                <div class="ml-3 flex-shrink-0">
                                                    <div
                                                        class="w-2 h-2 rounded-full bg-blue-500 dark:bg-blue-400 opacity-0 group-hover:opacity-100 transition-opacity"
                                                    ></div>
                                                </div>
                                            </div>
                                            <!-- eslint-disable-next-line vue/no-v-html -->
                                            <div
                                                class="text-xs text-gray-700 dark:text-gray-300 line-clamp-5 micron-preview leading-relaxed flex-1 min-h-[120px]"
                                                v-html="renderPreview(archive)"
                                            ></div>
                                            <div
                                                class="mt-3 pt-3 border-t border-gray-100 dark:border-zinc-700 flex items-center justify-between flex-shrink-0"
                                            >
                                                <div
                                                    class="flex items-center gap-1 text-xs text-gray-500 dark:text-gray-400"
                                                >
                                                    <MaterialDesignIcon icon-name="tag" class="size-3" />
                                                    <span class="font-mono">{{ archive.hash.substring(0, 8) }}</span>
                                                </div>
                                                <div
                                                    class="text-xs font-medium text-blue-600 dark:text-blue-400 opacity-0 group-hover:opacity-100 transition-opacity flex items-center gap-1"
                                                >
                                                    {{ $t("archives.view") }}
                                                    <MaterialDesignIcon icon-name="arrow-right" class="size-3" />
                                                </div>
                                            </div>
                                        </div>
                                    </template>
                                </CardStack>
                            </div>
                        </div>
                    </div>
                </div>
            </div>

            <div v-if="archives.length > 0" class="mt-8 mb-4 flex items-center justify-between">
                <div class="text-sm text-gray-500 dark:text-gray-400">
                    {{
                        $t("archives.showing_range", {
                            start: pagination.total_count > 0 ? (pagination.page - 1) * pagination.limit + 1 : 0,
                            end: Math.min(pagination.page * pagination.limit, pagination.total_count),
                            total: pagination.total_count,
                        })
                    }}
                </div>
                <div class="flex items-center gap-2">
                    <button
                        :disabled="pagination.page <= 1 || isLoading"
                        class="p-2 rounded-lg border border-gray-200 dark:border-zinc-800 bg-white dark:bg-zinc-900 text-gray-700 dark:text-gray-300 disabled:opacity-50 hover:bg-gray-50 dark:hover:bg-zinc-800 transition-colors"
                        @click="changePage(pagination.page - 1)"
                    >
                        <MaterialDesignIcon icon-name="chevron-left" class="size-5" />
                    </button>
                    <span class="text-sm font-medium text-gray-900 dark:text-white px-4">
                        {{
                            $t("archives.page_of", {
                                page: pagination.page,
                                total_pages: pagination.total_pages,
                            })
                        }}
                    </span>
                    <button
                        :disabled="pagination.page >= pagination.total_pages || isLoading"
                        class="p-2 rounded-lg border border-gray-200 dark:border-zinc-800 bg-white dark:bg-zinc-900 text-gray-700 dark:text-gray-300 disabled:opacity-50 hover:bg-gray-50 dark:hover:bg-zinc-800 transition-colors"
                        @click="changePage(pagination.page + 1)"
                    >
                        <MaterialDesignIcon icon-name="chevron-right" class="size-5" />
                    </button>
                </div>
            </div>
        </div>
    </div>
</template>

<script>
import MaterialDesignIcon from "../MaterialDesignIcon.vue";
import Utils from "../../js/Utils";
import MicronParser from "micron-parser";
import CardStack from "../CardStack.vue";

export default {
    name: "ArchivesPage",
    components: {
        MaterialDesignIcon,
        CardStack,
    },
    data() {
        return {
            archives: [],
            searchQuery: "",
            isLoading: false,
            searchTimeout: null,
            muParser: new MicronParser(),
            pagination: {
                page: 1,
                limit: 15,
                total_count: 0,
                total_pages: 0,
            },
        };
    },
    computed: {
        groupedArchives() {
            const groups = {};

            for (const archive of this.archives) {
                const hash = archive.destination_hash;
                if (!groups[hash]) {
                    groups[hash] = {
                        destination_hash: hash,
                        node_name: archive.node_name,
                        archives: [],
                    };
                }
                groups[hash].archives.push(archive);
            }

            // sort each group by date
            const grouped = Object.values(groups).map((group) => ({
                ...group,
                archives: group.archives.sort((a, b) => {
                    const dateA = new Date(a.created_at);
                    const dateB = new Date(b.created_at);
                    return dateB - dateA;
                }),
            }));

            // sort groups by the date of their most recent archive
            return grouped.sort((a, b) => {
                const dateA = new Date(a.archives[0].created_at);
                const dateB = new Date(b.archives[0].created_at);
                return dateB - dateA;
            });
        },
    },
    mounted() {
        this.getArchives();
    },
    methods: {
        async getArchives() {
            this.isLoading = true;
            try {
                const response = await window.axios.get("/api/v1/nomadnet/archives", {
                    params: {
                        q: this.searchQuery,
                        page: this.pagination.page,
                        limit: this.pagination.limit,
                    },
                });
                this.archives = response.data.archives;
                this.pagination = response.data.pagination;
            } catch (e) {
                console.error("Failed to load archives:", e);
            } finally {
                this.isLoading = false;
            }
        },
        onSearchInput() {
            this.pagination.page = 1; // reset to first page on search
            clearTimeout(this.searchTimeout);
            this.searchTimeout = setTimeout(() => {
                this.getArchives();
            }, 300);
        },
        async changePage(page) {
            this.pagination.page = page;
            await this.getArchives();
            // scroll to top of content
            const contentElement = document.querySelector(".overflow-y-auto");
            if (contentElement) contentElement.scrollTop = 0;
        },
        viewArchive(archive) {
            this.$router.push({
                name: "nomadnetwork",
                params: { destinationHash: archive.destination_hash },
                query: {
                    path: archive.page_path,
                    archive_id: archive.id,
                },
            });
        },
        formatDate(dateStr) {
            return Utils.formatTimeAgo(dateStr);
        },
        renderPreview(archive) {
            if (!archive.content) return "";

            // limit content for preview
            const previewContent = archive.content.substring(0, 500);

            // convert micron to html if it looks like micron or ends with .mu
            if (archive.page_path?.endsWith(".mu") || archive.content.includes("`")) {
                try {
                    return this.muParser.convertMicronToHtml(previewContent);
                } catch {
                    return previewContent;
                }
            }

            return previewContent;
        },
    },
};
</script>

<style scoped>
.line-clamp-2 {
    display: -webkit-box;
    -webkit-line-clamp: 2;
    -webkit-box-orient: vertical;
    overflow: hidden;
}

.line-clamp-3 {
    display: -webkit-box;
    -webkit-line-clamp: 3;
    -webkit-box-orient: vertical;
    overflow: hidden;
}

.line-clamp-5 {
    display: -webkit-box;
    -webkit-line-clamp: 5;
    -webkit-box-orient: vertical;
    overflow: hidden;
}

.stacked-card {
    box-shadow:
        0 1px 3px 0 rgba(0, 0, 0, 0.1),
        0 1px 2px 0 rgba(0, 0, 0, 0.06);
}

.stacked-card:hover {
    box-shadow:
        0 10px 25px -5px rgba(0, 0, 0, 0.1),
        0 8px 10px -6px rgba(0, 0, 0, 0.1);
}

.dark .stacked-card {
    box-shadow:
        0 1px 3px 0 rgba(0, 0, 0, 0.3),
        0 1px 2px 0 rgba(0, 0, 0, 0.2);
}

.dark .stacked-card:hover {
    box-shadow:
        0 10px 25px -5px rgba(0, 0, 0, 0.5),
        0 8px 10px -6px rgba(0, 0, 0, 0.4);
}

.micron-preview {
    font-family:
        Roboto Mono Nerd Font,
        monospace;
    white-space: pre-wrap;
    word-break: break-word;
}

:deep(.micron-preview) a {
    pointer-events: none;
}

:deep(.micron-preview) p {
    margin: 0.25rem 0;
}

:deep(.micron-preview) h1,
:deep(.micron-preview) h2,
:deep(.micron-preview) h3,
:deep(.micron-preview) h4 {
    margin: 0.5rem 0 0.25rem 0;
    font-weight: 600;
}
</style>
