<template>
    <!-- eslint-disable vue/no-v-html -->
    <div class="flex flex-col h-full bg-slate-50 dark:bg-zinc-950 overflow-hidden">
        <!-- Header -->
        <div
            class="p-3 border-b border-gray-200 dark:border-zinc-800 bg-white dark:bg-zinc-900 flex items-center justify-between z-30"
        >
            <div class="flex items-center space-x-3">
                <div class="p-2 bg-blue-100 dark:bg-blue-900/30 rounded-lg">
                    <MaterialDesignIcon
                        icon-name="book-open-variant"
                        class="w-5 h-5 text-blue-600 dark:text-blue-400"
                    />
                </div>
                <div>
                    <h1 class="text-sm font-bold text-gray-900 dark:text-zinc-100">{{ $t("docs.title") }}</h1>
                    <div
                        v-if="status.has_docs || status.has_meshchatx_docs"
                        class="flex items-center text-[10px] text-gray-500"
                    >
                        <span class="w-2 h-2 rounded-full bg-green-500 mr-1.5"></span>
                        Offline Ready
                    </div>
                </div>
            </div>

            <div class="flex items-center space-x-2">
                <!-- Export Docs Button -->
                <button
                    v-if="status.has_docs || status.has_meshchatx_docs"
                    class="p-2 text-gray-500 hover:bg-gray-100 dark:hover:bg-zinc-800 rounded-lg transition-colors"
                    title="Export all documentation as ZIP"
                    @click="exportDocs"
                >
                    <MaterialDesignIcon icon-name="download" class="w-5 h-5" />
                </button>

                <div v-if="activeTab === 'reticulum' && otherLanguages.length > 0 && status.has_docs" class="relative">
                    <button
                        v-click-outside="() => (showLanguages = false)"
                        class="p-2 text-gray-500 hover:bg-gray-100 dark:hover:bg-zinc-800 rounded-lg transition-colors"
                        :class="{ 'bg-gray-100 dark:bg-zinc-800': showLanguages }"
                        @click="showLanguages = !showLanguages"
                    >
                        <MaterialDesignIcon icon-name="translate" class="w-5 h-5" />
                    </button>
                    <div
                        v-if="showLanguages"
                        class="absolute right-0 top-full mt-1 bg-white dark:bg-zinc-900 border border-gray-200 dark:border-zinc-800 rounded-lg shadow-xl p-1 min-w-[120px] z-20"
                    >
                        <button
                            v-for="lang in allLanguages"
                            :key="lang.code"
                            class="flex items-center w-full px-3 py-2 text-[10px] font-bold uppercase hover:bg-gray-50 dark:hover:bg-zinc-800 rounded-md transition-colors"
                            :class="lang.code === currentLang ? 'text-blue-500' : 'text-gray-600 dark:text-zinc-400'"
                            @click="setLanguage(lang.code)"
                        >
                            {{ lang.name }} ({{ lang.code }})
                        </button>
                    </div>
                </div>

                <button
                    :disabled="status.status === 'downloading' || status.status === 'extracting'"
                    class="p-2 text-gray-500 hover:bg-gray-100 dark:hover:bg-zinc-800 rounded-lg transition-colors disabled:opacity-50"
                    :title="status.has_docs ? $t('docs.btn_update') : $t('docs.btn_download')"
                    @click="updateDocs"
                >
                    <MaterialDesignIcon
                        :icon-name="
                            status.status === 'downloading' || status.status === 'extracting' ? 'loading' : 'refresh'
                        "
                        :class="{ 'animate-spin': status.status === 'downloading' || status.status === 'extracting' }"
                        class="w-5 h-5"
                    />
                </button>

                <a
                    v-if="status.has_docs"
                    :href="localDocsUrl"
                    target="_blank"
                    class="flex items-center px-3 py-1.5 bg-zinc-900 dark:bg-white text-white dark:text-zinc-900 rounded-lg hover:opacity-90 transition-opacity font-bold text-xs shadow-sm"
                >
                    <MaterialDesignIcon icon-name="open-in-new" class="w-3.5 h-3.5 mr-1.5" />
                    Open
                </a>
            </div>
        </div>

        <!-- Search Bar -->
        <div
            v-if="status.has_docs || status.has_meshchatx_docs"
            class="px-4 py-2 bg-white dark:bg-zinc-900 border-b border-gray-200 dark:border-zinc-800 z-10"
        >
            <div class="flex flex-col md:flex-row items-center gap-4 max-w-4xl mx-auto w-full">
                <!-- Tabs -->
                <div class="flex bg-gray-100 dark:bg-zinc-800 p-1 rounded-xl shrink-0 w-full md:w-auto">
                    <button
                        class="px-4 py-1.5 text-[10px] font-bold uppercase tracking-wider rounded-lg transition-all"
                        :class="
                            activeTab === 'meshchatx'
                                ? 'bg-white dark:bg-zinc-700 text-blue-600 dark:text-blue-400 shadow-sm'
                                : 'text-gray-500 hover:text-gray-700 dark:hover:text-zinc-300'
                        "
                        @click="activeTab = 'meshchatx'"
                    >
                        MeshChatX
                    </button>
                    <button
                        class="px-4 py-1.5 text-[10px] font-bold uppercase tracking-wider rounded-lg transition-all"
                        :class="
                            activeTab === 'reticulum'
                                ? 'bg-white dark:bg-zinc-700 text-blue-600 dark:text-blue-400 shadow-sm'
                                : 'text-gray-500 hover:text-gray-700 dark:hover:text-zinc-300'
                        "
                        @click="activeTab = 'reticulum'"
                    >
                        Reticulum
                    </button>
                </div>

                <!-- Search Input -->
                <div class="relative flex-1 w-full">
                    <div class="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
                        <MaterialDesignIcon icon-name="magnify" class="h-4 w-4 text-gray-400" />
                    </div>
                    <input
                        v-model="searchQuery"
                        type="text"
                        class="block w-full pl-10 pr-10 py-1.5 border border-gray-200 dark:border-zinc-700 rounded-xl bg-gray-50 dark:bg-zinc-800 text-gray-900 dark:text-zinc-100 text-xs focus:outline-none focus:ring-2 focus:ring-blue-500/20 focus:border-blue-500 transition-all"
                        placeholder="Search all documentation..."
                        @input="debounceSearch"
                    />
                    <div v-if="isSearching" class="absolute inset-y-0 right-0 pr-3 flex items-center">
                        <MaterialDesignIcon icon-name="loading" class="h-3 w-3 text-gray-400 animate-spin" />
                    </div>
                    <button
                        v-else-if="searchQuery"
                        class="absolute inset-y-0 right-0 pr-3 flex items-center"
                        @click="clearSearch"
                    >
                        <MaterialDesignIcon
                            icon-name="close"
                            class="h-3 w-3 text-gray-400 hover:text-gray-600 dark:hover:text-zinc-200 cursor-pointer"
                        />
                    </button>
                </div>
            </div>
        </div>

        <!-- Progress Bar -->
        <div
            v-if="status.status === 'downloading' || status.status === 'extracting'"
            class="w-full h-1 bg-gray-200 dark:bg-zinc-800 overflow-hidden relative"
        >
            <div class="bg-blue-500 h-full transition-all duration-300" :style="{ width: status.progress + '%' }"></div>
            <div
                v-if="status.progress === 0 || status.status === 'extracting'"
                class="absolute inset-0 bg-blue-500/30 animate-pulse"
            ></div>
        </div>

        <!-- Main Content (Iframe or Search Results) -->
        <div class="flex-1 relative bg-white dark:bg-zinc-900 overflow-hidden">
            <!-- Search Results Overlay -->
            <div
                v-if="searchResults.length > 0 && searchQuery"
                class="absolute inset-0 z-20 bg-white dark:bg-zinc-900 overflow-y-auto"
            >
                <div class="max-w-2xl mx-auto p-6 space-y-6">
                    <div class="flex items-center justify-between px-2">
                        <h2 class="text-[10px] font-bold text-gray-400 uppercase tracking-widest">Search Results</h2>
                        <span
                            class="text-[10px] font-bold text-blue-500 px-2 py-0.5 bg-blue-50 dark:bg-blue-900/20 rounded-full"
                            >{{ searchResults.length }} matches</span
                        >
                    </div>
                    <div class="space-y-2">
                        <div
                            v-for="result in searchResults"
                            :key="result.path"
                            class="group p-4 hover:bg-gray-50 dark:hover:bg-zinc-800/50 rounded-2xl cursor-pointer transition-colors border border-gray-100 dark:border-zinc-800/50 hover:border-blue-200 dark:hover:border-blue-900/30"
                            @click="navigateTo(result.path)"
                        >
                            <div class="flex items-start justify-between gap-4">
                                <div
                                    class="font-bold text-sm text-gray-900 dark:text-zinc-100 group-hover:text-blue-600 dark:group-hover:text-blue-400 transition-colors"
                                >
                                    {{ result.title }}
                                </div>
                                <div class="flex items-center space-x-2">
                                    <span
                                        class="px-1.5 py-0.5 rounded bg-gray-100 dark:bg-zinc-800 text-[8px] font-bold text-gray-500 uppercase tracking-tighter"
                                    >
                                        {{ result.source }}
                                    </span>
                                    <div class="text-[9px] text-gray-400 uppercase font-mono mt-0.5 shrink-0">
                                        {{ result.path.split("/").pop() }}
                                    </div>
                                </div>
                            </div>
                            <p
                                class="mt-1.5 text-xs text-gray-600 dark:text-zinc-400 line-clamp-3 leading-relaxed"
                                v-html="highlightMatch(result.snippet)"
                            ></p>
                        </div>
                    </div>
                </div>
            </div>

            <!-- No Results State -->
            <div
                v-if="searchQuery && !isSearching && searchResults.length === 0"
                class="absolute inset-0 z-20 bg-white dark:bg-zinc-900 flex flex-col items-center justify-center p-8 text-center"
            >
                <div
                    class="w-16 h-16 bg-gray-50 dark:bg-zinc-800/50 rounded-full flex items-center justify-center mb-4"
                >
                    <MaterialDesignIcon icon-name="text-search" class="w-8 h-8 text-gray-300 dark:text-zinc-600" />
                </div>
                <h3 class="text-sm font-medium text-gray-900 dark:text-zinc-100">No results found</h3>
                <p class="text-xs text-gray-500 dark:text-zinc-400 mt-1">Try different keywords or check spelling.</p>
                <button
                    class="mt-4 text-xs font-bold text-blue-500 hover:text-blue-600 transition-colors"
                    @click="clearSearch"
                >
                    Clear Search
                </button>
            </div>

            <div
                v-if="status.last_error"
                class="absolute inset-0 z-10 flex items-center justify-center p-6 bg-white/90 dark:bg-zinc-900/90 backdrop-blur-sm"
            >
                <div
                    class="max-w-md w-full p-6 bg-red-50 dark:bg-red-900/20 border border-red-100 dark:border-red-900/30 rounded-2xl text-red-600 dark:text-red-400 text-center shadow-xl"
                >
                    <MaterialDesignIcon icon-name="alert-circle-outline" class="w-12 h-12 mx-auto mb-3" />
                    <div class="text-lg font-bold mb-2">{{ $t("docs.error") }}</div>
                    <div class="text-sm opacity-80">{{ status.last_error }}</div>
                    <button
                        class="mt-6 px-6 py-2 bg-red-600 text-white rounded-xl text-xs font-bold hover:bg-red-700 transition-colors"
                        @click="updateDocs"
                    >
                        Retry Download
                    </button>
                </div>
            </div>

            <div
                v-if="status.status === 'downloading' || status.status === 'extracting'"
                class="absolute inset-0 z-10 flex flex-col items-center justify-center bg-white/80 dark:bg-zinc-900/80 backdrop-blur-md"
            >
                <div class="relative w-24 h-24 mb-6">
                    <div class="absolute inset-0 border-4 border-blue-100 dark:border-blue-900/30 rounded-full"></div>
                    <div
                        class="absolute inset-0 border-4 border-blue-600 rounded-full transition-all duration-300"
                        :style="{ clipPath: `inset(0 0 0 0)`, transform: `rotate(${status.progress * 3.6}deg)` }"
                        style="border-color: transparent; border-top-color: currentColor"
                    ></div>
                    <div class="absolute inset-0 flex items-center justify-center">
                        <MaterialDesignIcon
                            :icon-name="
                                status.status === 'downloading' ? 'cloud-download-outline' : 'folder-zip-outline'
                            "
                            class="w-10 h-10 text-blue-600 animate-bounce"
                        />
                    </div>
                </div>
                <h3 class="text-lg font-bold text-gray-900 dark:text-zinc-100 mb-1">
                    {{
                        status.status === "downloading" ? $t("docs.status_downloading") : "Extracting Documentation..."
                    }}
                </h3>
                <p class="text-sm text-gray-500 dark:text-zinc-400">{{ status.progress }}% Complete</p>
                <p class="text-[10px] text-gray-400 mt-8 uppercase tracking-widest animate-pulse">
                    Please wait, setting up offline manual
                </p>
            </div>

            <!-- MeshChatX Docs View -->
            <div v-if="activeTab === 'meshchatx' && !searchQuery" class="flex h-full overflow-hidden">
                <!-- Doc Sidebar (mobile hidden) -->
                <div
                    class="hidden md:flex flex-col w-64 border-r border-gray-200 dark:border-zinc-800 bg-gray-50/50 dark:bg-zinc-900/50"
                >
                    <div class="p-4 border-b border-gray-200 dark:border-zinc-800">
                        <h3 class="text-[10px] font-bold text-gray-400 uppercase tracking-widest">MeshChatX Docs</h3>
                    </div>
                    <div class="flex-1 overflow-y-auto p-2 space-y-1">
                        <button
                            v-for="doc in meshchatxDocs"
                            :key="doc.path"
                            class="w-full text-left px-3 py-2 rounded-xl text-xs transition-all flex items-center space-x-3"
                            :class="
                                selectedDocPath === doc.path
                                    ? 'bg-blue-50 dark:bg-blue-900/20 text-blue-600 dark:text-blue-400 font-bold shadow-sm'
                                    : 'text-gray-600 dark:text-zinc-400 hover:bg-white dark:hover:bg-zinc-800'
                            "
                            @click="selectDoc(doc.path)"
                        >
                            <MaterialDesignIcon
                                :icon-name="doc.type === 'markdown' ? 'language-markdown' : 'file-document-outline'"
                                class="w-4 h-4"
                            />
                            <span class="truncate">{{ (doc.name || "").replace(/\.(md|txt)$/, "") }}</span>
                        </button>
                    </div>
                </div>

                <!-- Doc Content -->
                <div class="flex-1 flex flex-col bg-white dark:bg-zinc-900 overflow-hidden relative">
                    <!-- Mobile Selector -->
                    <div class="md:hidden p-3 border-b border-gray-200 dark:border-zinc-800">
                        <select
                            v-model="selectedDocPath"
                            class="w-full bg-gray-50 dark:bg-zinc-800 border-none rounded-lg text-xs font-bold p-2"
                            @change="selectDoc(selectedDocPath)"
                        >
                            <option v-for="doc in meshchatxDocs" :key="doc.path" :value="doc.path">
                                {{ (doc.name || "").replace(/\.(md|txt)$/, "") }}
                            </option>
                        </select>
                    </div>

                    <div v-if="selectedDocContent" class="flex-1 overflow-y-auto p-6 md:p-10 scroll-smooth">
                        <div class="max-w-3xl mx-auto">
                            <!-- Share Actions -->
                            <div
                                class="flex items-center justify-between mb-8 pb-4 border-b border-gray-100 dark:border-zinc-800"
                            >
                                <div class="flex items-center space-x-2 text-gray-400">
                                    <MaterialDesignIcon icon-name="clock-outline" class="w-3 h-3" />
                                    <span class="text-[10px] font-mono uppercase tracking-tighter"
                                        >Ready for sharing</span
                                    >
                                </div>
                                <div class="flex items-center space-x-2">
                                    <button
                                        class="flex items-center space-x-2 px-3 py-1.5 bg-gray-100 dark:bg-zinc-800 hover:bg-gray-200 dark:hover:bg-zinc-700 rounded-lg text-[10px] font-bold text-gray-600 dark:text-zinc-300 transition-colors"
                                        @click="copyDocLink"
                                    >
                                        <MaterialDesignIcon icon-name="share-variant" class="w-3.5 h-3.5" />
                                        <span>Share Link</span>
                                    </button>
                                </div>
                            </div>

                            <div class="max-w-none break-words" v-html="selectedDocContent.html"></div>
                        </div>
                    </div>
                    <div
                        v-else-if="meshchatxDocs.length > 0"
                        class="flex-1 flex flex-col items-center justify-center p-8 text-center opacity-50"
                    >
                        <MaterialDesignIcon icon-name="book-open-outline" class="w-12 h-12 mb-4 text-gray-300" />
                        <h3 class="text-sm font-bold">Select a document to read</h3>
                    </div>
                    <div v-else class="flex-1 flex flex-col items-center justify-center p-8 text-center opacity-50">
                        <MaterialDesignIcon icon-name="alert-circle-outline" class="w-12 h-12 mb-4 text-gray-300" />
                        <h3 class="text-sm font-bold">No MeshChatX docs found</h3>
                        <p class="text-xs mt-1">Place .md or .txt files in your docs folder.</p>
                    </div>
                </div>
            </div>

            <!-- Reticulum Docs View -->
            <iframe
                v-if="activeTab === 'reticulum' && status.has_docs && !searchQuery"
                ref="docsFrame"
                :src="localDocsUrl"
                class="w-full h-full border-none opacity-0 transition-opacity duration-1000"
                @load="$el.querySelector('iframe').style.opacity = '1'"
            ></iframe>

            <div
                v-else-if="status.status !== 'downloading' && status.status !== 'extracting'"
                class="h-full flex flex-col items-center justify-center p-8 text-center space-y-4"
            >
                <div class="w-16 h-16 bg-gray-50 dark:bg-zinc-800/50 rounded-full flex items-center justify-center">
                    <MaterialDesignIcon icon-name="book-outline" class="w-8 h-8 text-gray-300 dark:text-zinc-600" />
                </div>
                <div>
                    <h3 class="text-sm font-medium text-gray-900 dark:text-zinc-100">Reticulum Manual</h3>
                    <p class="text-xs text-gray-500 dark:text-zinc-400 mt-1 max-w-[200px]">
                        Download the official documentation for offline access.
                    </p>
                </div>
                <button
                    class="px-6 py-2 bg-blue-600 text-white rounded-full text-xs font-bold hover:bg-blue-700 transition-colors shadow-lg shadow-blue-500/20"
                    @click="updateDocs"
                >
                    {{ $t("docs.btn_download") }}
                </button>
            </div>
        </div>
    </div>
</template>

<script>
import MaterialDesignIcon from "../MaterialDesignIcon.vue";
import ToastUtils from "../../js/ToastUtils";

export default {
    components: {
        MaterialDesignIcon,
    },
    data() {
        return {
            status: {
                status: "idle",
                progress: 0,
                last_error: null,
                has_docs: false,
                has_meshchatx_docs: false,
            },
            statusInterval: null,
            showLanguages: false,
            searchQuery: "",
            searchResults: [],
            isSearching: false,
            searchTimeout: null,
            activeTab: "meshchatx",
            meshchatxDocs: [],
            selectedDocPath: null,
            selectedDocContent: null,
            languages: {
                en: "English",
                de: "Deutsch",
                es: "Español",
                jp: "日本語",
                nl: "Nederlands",
                pl: "Polski",
                "pt-br": "Português",
                tr: "Türkçe",
                uk: "Українська",
                "zh-cn": "简体中文",
            },
        };
    },
    computed: {
        currentLang() {
            return this.$i18n.locale;
        },
        localDocsUrl() {
            const lang = this.currentLang;
            if (lang === "en") return "/reticulum-docs/index.html";
            if (Object.keys(this.languages).includes(lang)) {
                return `/reticulum-docs/index_${lang}.html`;
            }
            return "/reticulum-docs/index.html";
        },
        allLanguages() {
            return Object.entries(this.languages).map(([code, name]) => ({
                code,
                name,
            }));
        },
        otherLanguages() {
            if (!this.status.has_docs) return [];
            return this.allLanguages.filter((l) => l.code !== this.currentLang);
        },
    },
    mounted() {
        this.fetchStatus();
        this.fetchMeshChatXDocs();
        this.statusInterval = setInterval(this.fetchStatus, 2000);
    },
    beforeUnmount() {
        if (this.statusInterval) {
            clearInterval(this.statusInterval);
        }
    },
    methods: {
        async fetchStatus() {
            try {
                const response = await window.axios.get("/api/v1/docs/status");
                this.status = response.data;
                // If we don't have Reticulum docs but have MeshChatX docs, default to MeshChatX tab
                if (!this.status.has_docs && this.status.has_meshchatx_docs) {
                    this.activeTab = "meshchatx";
                } else if (this.status.has_docs && !this.status.has_meshchatx_docs) {
                    this.activeTab = "reticulum";
                }
            } catch (error) {
                console.error("Failed to fetch docs status:", error);
            }
        },
        async fetchMeshChatXDocs() {
            try {
                const response = await window.axios.get("/api/v1/meshchatx-docs/list");
                this.meshchatxDocs = response.data;
                if (this.meshchatxDocs.length > 0 && !this.selectedDocPath) {
                    this.selectDoc(this.meshchatxDocs[0].path);
                }
            } catch (error) {
                console.error("Failed to fetch MeshChatX docs list:", error);
            }
        },
        async selectDoc(path) {
            this.selectedDocPath = path;
            try {
                const response = await window.axios.get("/api/v1/meshchatx-docs/content", {
                    params: { path },
                });
                this.selectedDocContent = response.data;
            } catch (error) {
                console.error("Failed to fetch doc content:", error);
                this.selectedDocContent = {
                    html: '<div class="text-red-500 font-bold">Failed to load document.</div>',
                };
            }
        },
        async updateDocs() {
            try {
                await window.axios.post("/api/v1/docs/update");
                this.fetchStatus();
            } catch (error) {
                console.error("Failed to trigger docs update:", error);
            }
        },
        async exportDocs() {
            window.location.href = "/api/v1/docs/export";
        },
        copyDocLink() {
            if (!this.selectedDocPath) return;
            const htmlPath = this.selectedDocPath.replace(/\.(md|txt)$/, ".html");
            const url = `${window.location.origin}/meshchatx-docs/${htmlPath}`;

            navigator.clipboard
                .writeText(url)
                .then(() => {
                    ToastUtils.success("Documentation link copied to clipboard");
                })
                .catch(() => {
                    ToastUtils.error("Failed to copy link");
                });
        },
        async setLanguage(langCode) {
            try {
                this.showLanguages = false;
                await window.axios.patch("/api/v1/config", {
                    language: langCode,
                });
                // The app will update automatically via websocket config sync
            } catch (error) {
                console.error("Failed to update language:", error);
            }
        },
        debounceSearch() {
            if (this.searchTimeout) clearTimeout(this.searchTimeout);
            if (!this.searchQuery) {
                this.searchResults = [];
                return;
            }
            this.searchTimeout = setTimeout(() => {
                this.performSearch();
            }, 400);
        },
        async performSearch() {
            if (!this.searchQuery) return;
            this.isSearching = true;
            try {
                const response = await window.axios.get("/api/v1/docs/search", {
                    params: {
                        q: this.searchQuery,
                        lang: this.currentLang,
                    },
                });
                this.searchResults = response.data.results;
            } catch (error) {
                console.error("Search failed:", error);
            } finally {
                this.isSearching = false;
            }
        },
        clearSearch() {
            this.searchQuery = "";
            this.searchResults = [];
        },
        navigateTo(path) {
            if (path.startsWith("/meshchatx-docs/")) {
                this.activeTab = "meshchatx";
                const docPath = path.replace("/meshchatx-docs/", "");
                this.selectDoc(docPath);
            } else {
                this.activeTab = "reticulum";
                const cleanPath = path.replace("/reticulum-docs/", "");
                const iframe = this.$refs.docsFrame;
                if (iframe) {
                    iframe.src = `/reticulum-docs/${cleanPath}`;
                }
            }
            this.clearSearch();
        },
        highlightMatch(text) {
            if (!this.searchQuery) return text;

            // Escape HTML entities in text to prevent XSS
            const escapedText = text
                .replace(/&/g, "&amp;")
                .replace(/</g, "&lt;")
                .replace(/>/g, "&gt;")
                .replace(/"/g, "&quot;")
                .replace(/'/g, "&#039;");

            const query = this.searchQuery.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
            const regex = new RegExp(`(${query})`, "gi");
            return escapedText.replace(
                regex,
                '<span class="bg-blue-100 dark:bg-blue-900/40 text-blue-700 dark:text-blue-300 px-0.5 rounded">$1</span>'
            );
        },
    },
};
</script>

<style scoped>
/* Ensure the iframe fills the container and respects dark mode if possible */
iframe {
    color-scheme: light dark;
}
</style>
