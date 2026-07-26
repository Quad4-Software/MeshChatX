<!-- SPDX-License-Identifier: 0BSD -->

<template>
    <!-- eslint-disable vue/no-v-html -->
    <div class="flex flex-col flex-1 overflow-hidden min-w-0 bg-slate-50 dark:bg-zinc-950">
        <ToolsPageHeader
            icon="book-open-variant"
            :title="$t('docs.title')"
            :description="$t('docs.subtitle')"
            accent="cyan"
        />
        <!-- Toolbar -->
        <div
            class="p-2 md:p-3 border-b border-gray-200 dark:border-zinc-800 bg-white dark:bg-zinc-900 flex items-center gap-4 z-30 shrink-0"
        >
            <!-- Search & Navigation (Desktop) -->
            <div class="hidden lg:flex flex-1 items-center gap-4 max-w-3xl">
                <!-- Tabs -->
                <div class="flex bg-gray-100 dark:bg-zinc-800 p-0.5 rounded-lg shrink-0">
                    <button
                        class="px-3 py-1 text-[10px] font-bold uppercase tracking-wider rounded-md transition-all"
                        :class="
                            activeTab === 'meshchatx'
                                ? 'bg-white dark:bg-zinc-700 text-blue-600 dark:text-blue-400 shadow-xs'
                                : 'text-gray-500 hover:text-gray-700 dark:hover:text-zinc-300'
                        "
                        @click="activeTab = 'meshchatx'"
                    >
                        {{ $t("docs.tab_meshchatx") }}
                    </button>
                    <button
                        class="px-3 py-1 text-[10px] font-bold uppercase tracking-wider rounded-md transition-all"
                        :class="
                            activeTab === 'reticulum'
                                ? 'bg-white dark:bg-zinc-700 text-blue-600 dark:text-blue-400 shadow-xs'
                                : 'text-gray-500 hover:text-gray-700 dark:hover:text-zinc-300'
                        "
                        @click="activeTab = 'reticulum'"
                    >
                        {{ $t("docs.tab_reticulum") }}
                    </button>
                </div>

                <!-- Search Input -->
                <div v-if="status.has_docs || status.has_meshchatx_docs" class="relative flex-1">
                    <div class="absolute inset-y-0 left-0 pl-2.5 flex items-center pointer-events-none">
                        <MaterialDesignIcon icon-name="magnify" class="h-3.5 w-3.5 text-gray-400" />
                    </div>
                    <input
                        v-model="searchQuery"
                        type="text"
                        class="block w-full pl-8 pr-8 py-1.5 border border-gray-200 dark:border-zinc-700 rounded-lg bg-gray-50 dark:bg-zinc-800 text-gray-900 dark:text-zinc-100 text-[11px] focus:outline-hidden focus:ring-2 focus:ring-blue-500/20 focus:border-blue-500 transition-all"
                        :placeholder="$t('docs.search_placeholder')"
                        @input="debounceSearch"
                    />
                    <div v-if="isSearching" class="absolute inset-y-0 right-0 pr-2.5 flex items-center">
                        <MaterialDesignIcon icon-name="loading" class="h-3 w-3 text-gray-400 animate-spin" />
                    </div>
                    <button
                        v-else-if="searchQuery"
                        class="absolute inset-y-0 right-0 pr-2.5 flex items-center"
                        @click="clearSearch"
                    >
                        <MaterialDesignIcon
                            icon-name="close"
                            class="h-3 w-3 text-gray-400 hover:text-gray-600 dark:hover:text-zinc-200 cursor-pointer"
                        />
                    </button>
                </div>
            </div>

            <!-- Actions Section -->
            <div class="flex items-center space-x-1 md:space-x-2 ml-auto shrink-0">
                <!-- Version Selector -->
                <div
                    v-if="activeTab === 'reticulum' && (status.has_docs || status.versions.length > 0)"
                    class="relative"
                >
                    <button
                        v-click-outside="() => (showVersions = false)"
                        class="p-1.5 text-gray-500 hover:bg-gray-100 dark:hover:bg-zinc-800 rounded-lg transition-colors flex items-center gap-1.5"
                        :class="{ 'bg-gray-100 dark:bg-zinc-800': showVersions }"
                        @click="showVersions = !showVersions"
                    >
                        <MaterialDesignIcon icon-name="history" class="w-4 h-4 md:w-5 md:h-5" />
                        <span class="hidden xl:inline text-[10px] font-bold uppercase">{{
                            status.current_version || $t("docs.default_version")
                        }}</span>
                    </button>
                    <div
                        v-if="showVersions"
                        class="absolute right-0 mt-2 w-48 bg-white dark:bg-zinc-800 border border-gray-200 dark:border-zinc-700 rounded-xl shadow-xl z-50 overflow-hidden"
                    >
                        <div
                            class="p-2 border-b border-gray-100 dark:border-zinc-700 bg-gray-50/50 dark:bg-zinc-800/50"
                        >
                            <span class="text-[10px] font-bold text-gray-400 uppercase tracking-wider">{{
                                $t("docs.versions")
                            }}</span>
                        </div>
                        <div class="max-h-64 overflow-y-auto py-1">
                            <button
                                v-for="version in status.versions"
                                :key="version"
                                class="w-full px-4 py-2 text-left text-[11px] hover:bg-blue-50 dark:hover:bg-blue-900/20 transition-colors flex items-center justify-between group"
                                :class="
                                    status.current_version === version
                                        ? 'text-blue-600 dark:text-blue-400 font-bold'
                                        : 'text-gray-700 dark:text-zinc-300'
                                "
                                @click="switchVersion(version)"
                            >
                                <span class="truncate">{{ version }}</span>
                                <div class="flex items-center space-x-1">
                                    <MaterialDesignIcon
                                        v-if="status.current_version === version"
                                        icon-name="check"
                                        class="w-3.5 h-3.5"
                                    />
                                    <button
                                        v-if="status.versions.length > 1"
                                        type="button"
                                        class="p-1 hover:text-red-500 opacity-0 group-hover:opacity-100 transition-opacity"
                                        title="Delete this version"
                                        @click.stop="deleteVersion(version)"
                                    >
                                        <MaterialDesignIcon icon-name="delete" class="w-3.5 h-3.5" />
                                    </button>
                                </div>
                            </button>
                            <div
                                v-if="status.versions.length === 0"
                                class="px-4 py-3 text-center text-gray-500 text-[10px]"
                            >
                                {{ $t("docs.no_versions") }}
                            </div>
                        </div>
                        <div
                            class="p-2 border-t border-gray-100 dark:border-zinc-700 bg-gray-50/50 dark:bg-zinc-800/50"
                        >
                            <label
                                class="flex items-center justify-center gap-2 px-3 py-1.5 bg-blue-600 hover:bg-blue-700 text-white rounded-lg cursor-pointer transition-colors text-[10px] font-bold uppercase"
                            >
                                <MaterialDesignIcon icon-name="upload" class="w-3.5 h-3.5" />
                                <span>{{ $t("docs.upload_zip") }}</span>
                                <input type="file" accept=".zip" class="hidden" @change="handleZipUpload" />
                            </label>
                        </div>
                    </div>
                </div>

                <!-- Language Selector -->
                <div v-if="activeTab === 'reticulum' && status.has_docs" class="relative">
                    <button
                        v-click-outside="() => (showLanguages = false)"
                        class="p-1.5 text-gray-500 hover:bg-gray-100 dark:hover:bg-zinc-800 rounded-lg transition-colors flex items-center gap-1.5"
                        :class="{ 'bg-gray-100 dark:bg-zinc-800': showLanguages }"
                        @click="showLanguages = !showLanguages"
                    >
                        <MaterialDesignIcon icon-name="translate" class="w-4 h-4 md:w-5 md:h-5" />
                        <span class="hidden xl:inline text-[10px] font-bold uppercase">{{ currentLang }}</span>
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

                <!-- Export Button -->
                <button
                    v-if="status.has_docs || status.has_meshchatx_docs"
                    class="p-1.5 text-gray-500 hover:bg-gray-100 dark:hover:bg-zinc-800 rounded-lg transition-colors"
                    title="Export all documentation as ZIP"
                    @click="exportDocs"
                >
                    <MaterialDesignIcon icon-name="download" class="w-4 h-4 md:w-5 md:h-5" />
                </button>

                <!-- Share Reticulum Manual (re-uploadable ZIP) -->
                <button
                    v-if="status.has_docs"
                    class="p-1.5 text-gray-500 hover:bg-gray-100 dark:hover:bg-zinc-800 rounded-lg transition-colors"
                    :title="$t('docs.btn_share')"
                    @click="exportReticulumDocs"
                >
                    <MaterialDesignIcon icon-name="share-variant" class="w-4 h-4 md:w-5 md:h-5" />
                </button>

                <!-- Upload Custom Manual -->
                <label
                    :class="{ 'opacity-50 pointer-events-none': status.status === 'extracting' }"
                    class="p-1.5 text-gray-500 hover:bg-gray-100 dark:hover:bg-zinc-800 rounded-lg transition-colors cursor-pointer"
                    :title="$t('docs.btn_upload')"
                >
                    <MaterialDesignIcon
                        :icon-name="status.status === 'extracting' ? 'loading' : 'upload'"
                        :class="{ 'animate-spin': status.status === 'extracting' }"
                        class="w-4 h-4 md:w-5 md:h-5"
                    />
                    <input
                        type="file"
                        accept=".zip"
                        class="hidden"
                        :disabled="status.status === 'extracting'"
                        @change="handleZipUpload"
                    />
                </label>

                <!-- Open External -->
                <a
                    v-if="status.has_docs"
                    :href="localDocsUrl"
                    target="_blank"
                    class="hidden sm:flex items-center px-2.5 py-1.5 bg-zinc-900 dark:bg-white text-white dark:text-zinc-900 rounded-lg hover:opacity-90 transition-opacity font-bold text-[10px] shadow-xs"
                >
                    <MaterialDesignIcon icon-name="open-in-new" class="w-3 h-3 mr-1.5" />
                    {{ $t("docs.open_external") }}
                </a>
            </div>
        </div>

        <!-- Secondary Navigation (Mobile/Tablet) -->
        <div
            v-if="(status.has_docs || status.has_meshchatx_docs) && !isSearching"
            class="lg:hidden px-3 py-2 bg-white dark:bg-zinc-900 border-b border-gray-200 dark:border-zinc-800 z-10"
        >
            <div class="flex flex-col lg:flex-row items-center gap-2 w-full">
                <!-- Tabs -->
                <div class="flex bg-gray-100 dark:bg-zinc-800 p-0.5 rounded-lg w-full md:w-auto">
                    <button
                        class="flex-1 md:flex-none px-4 py-1.5 text-[10px] font-bold uppercase tracking-wider rounded-md transition-all"
                        :class="
                            activeTab === 'meshchatx'
                                ? 'bg-white dark:bg-zinc-700 text-blue-600 dark:text-blue-400 shadow-xs'
                                : 'text-gray-500 hover:text-gray-700 dark:hover:text-zinc-300'
                        "
                        @click="activeTab = 'meshchatx'"
                    >
                        {{ $t("docs.tab_meshchatx") }}
                    </button>
                    <button
                        class="flex-1 md:flex-none px-4 py-1.5 text-[10px] font-bold uppercase tracking-wider rounded-md transition-all"
                        :class="
                            activeTab === 'reticulum'
                                ? 'bg-white dark:bg-zinc-700 text-blue-600 dark:text-blue-400 shadow-xs'
                                : 'text-gray-500 hover:text-gray-700 dark:hover:text-zinc-300'
                        "
                        @click="activeTab = 'reticulum'"
                    >
                        {{ $t("docs.tab_reticulum") }}
                    </button>
                </div>

                <!-- Search Input -->
                <div class="relative w-full">
                    <div class="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
                        <MaterialDesignIcon icon-name="magnify" class="h-3.5 w-3.5 text-gray-400" />
                    </div>
                    <input
                        v-model="searchQuery"
                        type="text"
                        class="block w-full pl-9 pr-9 py-2 border border-gray-200 dark:border-zinc-700 rounded-lg bg-gray-50 dark:bg-zinc-800 text-gray-900 dark:text-zinc-100 text-xs focus:outline-hidden focus:ring-2 focus:ring-blue-500/20 focus:border-blue-500 transition-all"
                        :placeholder="$t('docs.search_placeholder_mobile')"
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
            v-if="status.status === 'extracting'"
            class="w-full h-1 bg-gray-200 dark:bg-zinc-800 overflow-hidden relative"
        >
            <div class="bg-blue-500 h-full transition-all duration-300" :style="{ width: status.progress + '%' }"></div>
            <div class="absolute inset-0 bg-blue-500/30 animate-pulse"></div>
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
                        <h2 class="text-[10px] font-bold text-gray-400 uppercase tracking-widest">
                            {{ $t("docs.search_results") }}
                        </h2>
                        <span
                            class="text-[10px] font-bold text-blue-500 px-2 py-0.5 bg-blue-50 dark:bg-blue-900/20 rounded-full"
                            >{{ $t("docs.matches_count", { count: searchResults.length }) }}</span
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
                                        class="px-1.5 py-0.5 rounded-sm bg-gray-100 dark:bg-zinc-800 text-[8px] font-bold text-gray-500 uppercase tracking-tighter"
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
                v-if="searchQuery && !isSearching && searchResults.length === 0 && !searchError"
                class="absolute inset-0 z-20 bg-white dark:bg-zinc-900 flex flex-col items-center justify-center p-8 text-center"
            >
                <div
                    class="w-16 h-16 bg-gray-50 dark:bg-zinc-800/50 rounded-full flex items-center justify-center mb-4"
                >
                    <MaterialDesignIcon icon-name="text-search" class="w-8 h-8 text-gray-300 dark:text-zinc-600" />
                </div>
                <h3 class="text-sm font-medium text-gray-900 dark:text-zinc-100">{{ $t("docs.no_results") }}</h3>
                <p class="text-xs text-gray-500 dark:text-zinc-400 mt-1">{{ $t("docs.no_results_hint") }}</p>
                <button
                    class="mt-4 text-xs font-bold text-blue-500 hover:text-blue-600 transition-colors"
                    @click="clearSearch"
                >
                    {{ $t("docs.clear_search") }}
                </button>
            </div>

            <div
                v-if="searchError && searchQuery"
                class="absolute inset-0 z-20 bg-white dark:bg-zinc-900 flex flex-col items-center justify-center p-8 text-center"
            >
                <div class="w-16 h-16 bg-red-50 dark:bg-red-950/30 rounded-full flex items-center justify-center mb-4">
                    <MaterialDesignIcon icon-name="alert-circle-outline" class="w-8 h-8 text-red-400" />
                </div>
                <h3 class="text-sm font-medium text-gray-900 dark:text-zinc-100">{{ $t("docs.search_failed") }}</h3>
                <p class="text-xs text-gray-500 dark:text-zinc-400 mt-1 max-w-sm">{{ searchError }}</p>
                <button
                    class="mt-4 text-xs font-bold text-blue-500 hover:text-blue-600 transition-colors"
                    @click="clearSearch"
                >
                    {{ $t("docs.clear_search") }}
                </button>
            </div>

            <div
                v-if="status.last_error"
                class="absolute inset-0 z-10 flex items-center justify-center p-6 bg-white/90 dark:bg-zinc-900/90 backdrop-blur-xs"
            >
                <div
                    class="max-w-md w-full p-6 bg-red-50 dark:bg-red-900/20 border border-red-100 dark:border-red-900/30 rounded-2xl text-red-600 dark:text-red-400 text-center shadow-xl"
                >
                    <MaterialDesignIcon icon-name="alert-circle-outline" class="w-12 h-12 mx-auto mb-3" />
                    <div class="text-lg font-bold mb-2">{{ $t("docs.error") }}</div>
                    <div class="text-sm opacity-80">{{ status.last_error }}</div>
                    <div class="flex flex-col gap-4 mt-6">
                        <label
                            class="w-full px-6 py-2.5 bg-zinc-900 dark:bg-white text-white dark:text-zinc-900 rounded-xl text-xs font-bold hover:opacity-90 transition-opacity cursor-pointer flex items-center justify-center gap-2"
                        >
                            <MaterialDesignIcon icon-name="upload" class="w-3.5 h-3.5" />
                            <span>{{ $t("docs.btn_upload") }}</span>
                            <input type="file" accept=".zip" class="hidden" @change="handleZipUpload" />
                        </label>
                        <button
                            class="text-[10px] font-bold text-red-500/60 hover:text-red-500 uppercase tracking-widest transition-colors"
                            @click="dismissError"
                        >
                            {{ $t("docs.dismiss") }}
                        </button>
                    </div>
                </div>
            </div>

            <div
                v-if="status.status === 'extracting'"
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
                            icon-name="folder-zip-outline"
                            class="w-10 h-10 text-blue-600 animate-bounce"
                        />
                    </div>
                </div>
                <h3 class="text-lg font-bold text-gray-900 dark:text-zinc-100 mb-1">
                    {{ $t("docs.status_extracting") }}
                </h3>
                <p class="text-sm text-gray-500 dark:text-zinc-400">
                    {{ $t("docs.complete_percent", { percent: status.progress }) }}
                </p>
            </div>

            <!-- MeshChatX Docs View -->
            <div v-if="activeTab === 'meshchatx' && !searchQuery" class="flex h-full overflow-hidden">
                <!-- Section sidebar -->
                <aside
                    class="hidden lg:flex flex-col w-72 shrink-0 border-r border-sem-border bg-sem-canvas/80 dark:bg-zinc-950/80"
                >
                    <div class="p-4 border-b border-sem-border space-y-3">
                        <h3 class="text-[10px] font-bold text-sem-fg-muted uppercase tracking-widest">
                            {{ $t("docs.sections_title") }}
                        </h3>
                        <p
                            v-if="manifestWarning"
                            class="text-[11px] leading-relaxed text-amber-700 dark:text-amber-300 bg-amber-50 dark:bg-amber-950/30 border border-amber-200 dark:border-amber-900/40 rounded-lg px-2.5 py-2"
                        >
                            {{ manifestWarning }}
                        </p>
                        <p
                            v-if="meshchatxListError"
                            class="text-[11px] leading-relaxed text-red-600 dark:text-red-400 bg-red-50 dark:bg-red-950/30 border border-red-200 dark:border-red-900/40 rounded-lg px-2.5 py-2"
                        >
                            {{ meshchatxListError }}
                        </p>
                        <div v-if="docLanguages.length > 1" class="flex flex-wrap gap-1.5">
                            <button
                                v-for="lang in docLanguages"
                                :key="lang.code"
                                type="button"
                                class="px-2 py-1 rounded-md text-[10px] font-bold uppercase tracking-wide transition-colors"
                                :class="
                                    meshchatxDocsLang === lang.code
                                        ? 'bg-cyan-100 dark:bg-cyan-900/30 text-cyan-700 dark:text-cyan-300'
                                        : 'bg-sem-surface-muted text-sem-fg-muted hover:text-sem-fg'
                                "
                                @click="setMeshchatxDocsLang(lang.code)"
                            >
                                {{ lang.code }}
                            </button>
                        </div>
                    </div>
                    <nav class="flex-1 overflow-y-auto p-3 space-y-5 custom-scroll">
                        <div v-for="section in visibleDocSections" :key="section.id">
                            <p class="px-2 mb-2 text-[10px] font-bold uppercase tracking-widest text-sem-fg-muted">
                                {{ section.title }}
                            </p>
                            <div class="space-y-0.5">
                                <button
                                    v-for="item in section.items"
                                    :key="item.path"
                                    type="button"
                                    class="w-full text-left px-3 py-2 rounded-xl text-xs transition-all flex items-center gap-2.5"
                                    :class="
                                        selectedDocPath === item.path
                                            ? 'bg-cyan-50 dark:bg-cyan-950/40 text-cyan-700 dark:text-cyan-300 font-semibold shadow-xs ring-1 ring-cyan-200/80 dark:ring-cyan-800/60'
                                            : 'text-sem-fg-muted hover:bg-sem-surface-muted hover:text-sem-fg'
                                    "
                                    @click="selectDoc(item.path)"
                                >
                                    <MaterialDesignIcon
                                        :icon-name="
                                            item.type === 'markdown' ? 'language-markdown' : 'file-document-outline'
                                        "
                                        class="w-4 h-4 shrink-0 opacity-70"
                                    />
                                    <span class="truncate">{{ item.title }}</span>
                                </button>
                            </div>
                        </div>
                    </nav>
                </aside>

                <!-- Doc content -->
                <div class="flex-1 flex min-w-0 bg-sem-surface dark:bg-zinc-900 overflow-hidden">
                    <div class="flex-1 flex flex-col min-w-0 overflow-hidden">
                        <div class="lg:hidden p-3 border-b border-sem-border bg-sem-surface space-y-2">
                            <label class="text-[10px] font-bold uppercase tracking-widest text-sem-fg-muted">{{
                                $t("docs.sections_title")
                            }}</label>
                            <select
                                v-model="selectedDocPath"
                                class="w-full bg-sem-surface-muted border border-sem-border rounded-xl text-xs font-medium p-2.5 text-sem-fg"
                                @change="selectDoc(selectedDocPath)"
                            >
                                <optgroup
                                    v-for="section in visibleDocSections"
                                    :key="section.id"
                                    :label="section.title"
                                >
                                    <option v-for="item in section.items" :key="item.path" :value="item.path">
                                        {{ item.title }}
                                    </option>
                                </optgroup>
                            </select>
                        </div>

                        <div
                            v-if="selectedDocContent"
                            ref="docContentScroller"
                            class="flex-1 overflow-y-auto scroll-smooth custom-scroll"
                        >
                            <div class="max-w-3xl mx-auto px-5 py-8 md:px-10 md:py-12">
                                <article
                                    ref="docsProse"
                                    class="docs-prose max-w-none wrap-break-word"
                                    @click="handleDocClick"
                                    v-html="selectedDocContent.html"
                                ></article>
                            </div>
                        </div>
                        <div
                            v-else-if="docLoadError"
                            class="flex-1 flex flex-col items-center justify-center p-8 text-center"
                        >
                            <MaterialDesignIcon icon-name="alert-circle-outline" class="w-12 h-12 mb-4 text-red-400" />
                            <h3 class="text-sm font-semibold text-sem-fg">{{ $t("docs.load_doc_failed") }}</h3>
                            <p class="text-xs mt-2 max-w-sm text-sem-fg-muted">{{ docLoadError }}</p>
                        </div>
                        <div
                            v-else-if="meshchatxDocs.length > 0"
                            class="flex-1 flex flex-col items-center justify-center p-8 text-center text-sem-fg-muted"
                        >
                            <MaterialDesignIcon icon-name="book-open-outline" class="w-12 h-12 mb-4 opacity-40" />
                            <h3 class="text-sm font-semibold text-sem-fg">{{ $t("docs.select_doc") }}</h3>
                        </div>
                        <div
                            v-else
                            class="flex-1 flex flex-col items-center justify-center p-8 text-center text-sem-fg-muted"
                        >
                            <MaterialDesignIcon icon-name="alert-circle-outline" class="w-12 h-12 mb-4 opacity-40" />
                            <h3 class="text-sm font-semibold text-sem-fg">{{ $t("docs.no_docs_found") }}</h3>
                            <p class="text-xs mt-1 max-w-xs">{{ $t("docs.no_docs_hint") }}</p>
                        </div>
                    </div>

                    <!-- On-page table of contents -->
                    <aside
                        v-if="docToc.length > 0 && selectedDocContent"
                        class="hidden xl:flex flex-col w-56 shrink-0 border-l border-sem-border bg-sem-canvas/50 dark:bg-zinc-950/50"
                    >
                        <div class="p-4 border-b border-sem-border">
                            <h3 class="text-[10px] font-bold text-sem-fg-muted uppercase tracking-widest">
                                {{ $t("docs.on_this_page") }}
                            </h3>
                        </div>
                        <nav class="flex-1 overflow-y-auto p-3 space-y-1 custom-scroll">
                            <a
                                v-for="entry in docToc"
                                :key="entry.id"
                                :href="`#${entry.id}`"
                                class="block py-1 text-xs text-sem-fg-muted hover:text-cyan-600 dark:hover:text-cyan-400 transition-colors"
                                :class="entry.level === 3 ? 'pl-3' : ''"
                                @click.prevent="scrollToHeading(entry.id)"
                            >
                                {{ entry.text }}
                            </a>
                        </nav>
                    </aside>
                </div>
            </div>

            <!-- Reticulum Docs View -->
            <iframe
                v-if="activeTab === 'reticulum' && status.has_docs && !searchQuery"
                :key="localDocsUrl"
                ref="docsFrame"
                :src="localDocsUrl"
                class="w-full h-full border-none opacity-0 transition-opacity duration-1000"
                @load="onReticulumFrameLoad"
            ></iframe>

            <div
                v-else-if="
                    activeTab === 'reticulum' && !status.has_docs && status.status !== 'extracting' && !searchQuery
                "
                class="h-full flex flex-col items-center justify-center p-8 text-center space-y-4"
            >
                <div class="w-16 h-16 bg-gray-50 dark:bg-zinc-800/50 rounded-full flex items-center justify-center">
                    <MaterialDesignIcon icon-name="book-outline" class="w-8 h-8 text-gray-300 dark:text-zinc-600" />
                </div>
                <div>
                    <h3 class="text-sm font-medium text-gray-900 dark:text-zinc-100">
                        {{ $t("docs.reticulum_manual") }}
                    </h3>
                    <p class="text-xs text-gray-500 dark:text-zinc-400 mt-1 max-w-[260px]">
                        {{ $t("docs.empty_state_hint") }}
                    </p>
                </div>
                <label
                    class="px-6 py-2 bg-blue-600 text-white rounded-full text-xs font-bold hover:bg-blue-700 transition-colors shadow-lg shadow-blue-500/20 cursor-pointer flex items-center gap-2"
                >
                    <MaterialDesignIcon icon-name="upload" class="w-3.5 h-3.5" />
                    <span>{{ $t("docs.btn_upload") }}</span>
                    <input type="file" accept=".zip" class="hidden" @change="handleZipUpload" />
                </label>
            </div>
        </div>
    </div>
</template>

<script>
import MaterialDesignIcon from "../MaterialDesignIcon.vue";
import ToastUtils from "../../js/ToastUtils";
import DialogUtils from "../../js/DialogUtils";
import { bundledReticulumDocsUrl } from "../../js/reticulumDocsEntryUrl.js";
import ToolsPageHeader from "../tools/ToolsPageHeader.vue";

export default {
    components: {
        MaterialDesignIcon,
        ToolsPageHeader,
    },
    data() {
        return {
            status: {
                status: "idle",
                progress: 0,
                last_error: null,
                has_docs: false,
                has_meshchatx_docs: false,
                versions: [],
                current_version: null,
            },
            statusInterval: null,
            showLanguages: false,
            showVersions: false,
            searchQuery: "",
            searchResults: [],
            isSearching: false,
            searchTimeout: null,
            activeTab: "meshchatx",
            meshchatxDocs: [],
            docSections: [],
            docLanguages: [],
            defaultDocsLanguage: "en",
            reticulumDocsLang: "en",
            meshchatxDocsLang: "en",
            docToc: [],
            meshchatxListError: null,
            docLoadError: null,
            manifestWarning: null,
            searchError: null,
            selectedDocPath: null,
            selectedDocContent: null,
            selectedReticulumPath: null,
            reticulumDocsCacheBust: 0,
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
            return this.reticulumDocsLang;
        },
        localDocsUrl() {
            let path;
            if (this.selectedReticulumPath) {
                path = `/reticulum-docs/${this.selectedReticulumPath}`;
            } else {
                path = bundledReticulumDocsUrl(this.currentLang);
            }
            if (this.reticulumDocsCacheBust) {
                const sep = path.includes("?") ? "&" : "?";
                return `${path}${sep}v=${this.reticulumDocsCacheBust}`;
            }
            return path;
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
        reticulumDocsQueryParam() {
            return this.$route?.query?.reticulum;
        },
        visibleDocSections() {
            const lang = this.meshchatxDocsLang;
            const fallback = this.defaultDocsLanguage || "en";
            return this.docSections
                .map((section) => ({
                    ...section,
                    items: (section.items || []).filter(
                        (item) => item.lang === lang || item.lang === fallback || lang === fallback
                    ),
                }))
                .filter((section) => section.items.length > 0);
        },
        firstDocPath() {
            for (const section of this.visibleDocSections) {
                if (section.items?.length) {
                    return section.items[0].path;
                }
            }
            return this.meshchatxDocs[0]?.path || null;
        },
    },
    watch: {
        reticulumDocsQueryParam() {
            this.applyDocumentationRouteQuery();
        },
    },
    mounted() {
        this.fetchStatus();
        this.fetchMeshChatXDocs();
        this.statusInterval = setInterval(this.fetchStatus, 2000);
        this.applyDocumentationRouteQuery();
    },
    beforeUnmount() {
        if (this.statusInterval) {
            clearInterval(this.statusInterval);
        }
    },
    methods: {
        async fetchStatus() {
            try {
                const response = await window.api.get("/api/v1/docs/status");
                this.status = response.data;

                if (!this.status.has_docs && this.status.has_meshchatx_docs && this.activeTab === "reticulum") {
                    this.activeTab = "meshchatx";
                } else if (this.status.has_docs && !this.status.has_meshchatx_docs && this.activeTab === "meshchatx") {
                    this.activeTab = "reticulum";
                }
            } catch (error) {
                console.error("Failed to fetch docs status:", error);
            }
            if (this.reticulumDocsQueryParam) {
                this.applyDocumentationRouteQuery();
            }
        },
        dismissError() {
            this.status = { ...this.status, last_error: null };
        },
        async fetchMeshChatXDocs() {
            this.meshchatxListError = null;
            this.manifestWarning = null;
            try {
                const response = await window.api.get("/api/v1/meshchatx-docs/list", {
                    params: { lang: this.meshchatxDocsLang },
                });
                const data = response.data;
                if (Array.isArray(data)) {
                    this.meshchatxDocs = data;
                    this.docSections = [];
                    this.docLanguages = [{ code: "en", name: "English" }];
                } else {
                    this.meshchatxDocs = data.docs || [];
                    this.docSections = data.sections || [];
                    this.docLanguages = data.languages || [{ code: "en", name: "English" }];
                    this.defaultDocsLanguage = data.default_language || "en";
                    if (data.manifest_error) {
                        this.manifestWarning = this.$t("docs.manifest_warning");
                    }
                }
                if (!this.docLanguages.some((l) => l.code === this.meshchatxDocsLang)) {
                    this.meshchatxDocsLang = this.defaultDocsLanguage || "en";
                }
                if (this.meshchatxDocs.length > 0 && !this.selectedDocPath) {
                    const start = this.firstDocPath;
                    if (start) {
                        this.selectDoc(start);
                    }
                }
            } catch (error) {
                console.error("Failed to fetch MeshChatX docs list:", error);
                this.meshchatxDocs = [];
                this.docSections = [];
                this.meshchatxListError = error.response?.data?.error || this.$t("docs.load_list_failed");
            }
        },
        async setMeshchatxDocsLang(langCode) {
            if (this.meshchatxDocsLang === langCode) {
                return;
            }
            this.meshchatxDocsLang = langCode;
            this.selectedDocPath = null;
            this.selectedDocContent = null;
            this.docToc = [];
            await this.fetchMeshChatXDocs();
        },
        async selectDoc(path) {
            if (!path) {
                return;
            }
            this.selectedDocPath = path;
            this.docLoadError = null;
            try {
                const response = await window.api.get("/api/v1/meshchatx-docs/content", {
                    params: { path },
                });
                if (!response.data?.html && !response.data?.content) {
                    throw new Error("Empty document response");
                }
                this.selectedDocContent = response.data;
                this.docToc = this.extractDocToc(this.selectedDocContent?.html || "");
            } catch (error) {
                console.error("Failed to fetch doc content:", error);
                this.docLoadError = error.response?.data?.error || this.$t("docs.load_doc_failed");
                this.selectedDocContent = null;
                this.docToc = [];
            }
        },
        extractDocToc(htmlContent) {
            if (!htmlContent) {
                return [];
            }
            try {
                const parser = new DOMParser();
                const doc = parser.parseFromString(htmlContent, "text/html");
                return Array.from(doc.querySelectorAll("h2, h3"))
                    .map((heading) => ({
                        id: heading.id,
                        text: heading.textContent?.trim() || "",
                        level: heading.tagName === "H2" ? 2 : 3,
                    }))
                    .filter((entry) => entry.id && entry.text);
            } catch {
                return [];
            }
        },
        scrollToHeading(id) {
            const prose = this.$refs.docsProse;
            if (!prose || typeof prose.querySelector !== "function") {
                return;
            }
            if (!id || !/^[a-z0-9-]+$/.test(id)) {
                return;
            }
            const target = prose.querySelector(`#${id}`);
            if (target) {
                target.scrollIntoView({ behavior: "smooth", block: "start" });
            }
        },
        onReticulumFrameLoad() {
            const frame = this.$refs.docsFrame;
            if (frame && frame.style) {
                frame.style.opacity = "1";
            }
        },
        async switchVersion(version) {
            try {
                await window.api.post("/api/v1/docs/switch", { version });
                this.showVersions = false;
                this.selectedReticulumPath = null;
                this.fetchStatus();
                // reload iframe if in reticulum tab
                if (this.activeTab === "reticulum") {
                    const iframe = this.$refs.docsFrame;
                    if (iframe) {
                        iframe.contentWindow.location.reload();
                    }
                }
            } catch (error) {
                console.error("Failed to switch docs version:", error);
            }
        },
        async deleteVersion(version) {
            if (!(await DialogUtils.confirm(this.$t("docs.confirm_delete_version", { version })))) {
                return;
            }

            try {
                await window.api.delete(`/api/v1/docs/version/${encodeURIComponent(version)}`);
                this.fetchStatus();
                ToastUtils.success(`Version ${version} deleted`);
            } catch (error) {
                console.error("Failed to delete docs version:", error);
                ToastUtils.error("Failed to delete version: " + (error.response?.data?.error || error.message));
            }
        },
        async handleZipUpload(event) {
            const file = event.target.files[0];
            if (!file) return;

            const defaultName = `upload-${Date.now()}`;
            const version = await DialogUtils.prompt(this.$t("docs.prompt_version_name"), defaultName);
            // Reset input so the same file can be chosen again after cancel.
            event.target.value = "";
            if (version === null || !String(version).trim()) {
                return;
            }

            const formData = new FormData();
            formData.append("file", file);

            try {
                await window.api.post(
                    `/api/v1/docs/upload?version=${encodeURIComponent(String(version).trim())}`,
                    formData,
                    {
                        headers: {
                            "Content-Type": "multipart/form-data",
                        },
                    }
                );
                this.fetchStatus();
                this.reticulumDocsCacheBust = Date.now();
                ToastUtils.success(this.$t("docs.upload_success"));
            } catch (error) {
                console.error("Failed to upload docs zip:", error);
                const message = error.response?.data?.error || error.message || "";
                DialogUtils.alert(this.$t("docs.failed_upload_alert", { message }), "error");
            }
        },
        async exportDocs() {
            window.location.href = "/api/v1/docs/export";
        },
        async exportReticulumDocs() {
            window.location.href = "/api/v1/docs/export/reticulum";
        },
        copyDocLink() {
            if (!this.selectedDocPath) return;
            const htmlPath = this.selectedDocPath.replace(/\.(md|txt)$/, ".html");
            const url = `${window.location.origin}/meshchatx-docs/${htmlPath}`;

            navigator.clipboard
                .writeText(url)
                .then(() => {
                    ToastUtils.success(this.$t("docs.docs_link_copied"));
                })
                .catch(() => {
                    ToastUtils.error(this.$t("docs.failed_copy_link"));
                });
        },
        async setLanguage(langCode) {
            this.showLanguages = false;
            this.selectedReticulumPath = null;
            this.reticulumDocsLang = langCode;
            this.reticulumDocsCacheBust += 1;
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
            this.searchError = null;
            try {
                const response = await window.api.get("/api/v1/docs/search", {
                    params: {
                        q: this.searchQuery,
                        lang: this.currentLang,
                    },
                });
                this.searchResults = response.data?.results || [];
            } catch (error) {
                console.error("Search failed:", error);
                this.searchResults = [];
                this.searchError = error.response?.data?.error || this.$t("docs.search_failed");
            } finally {
                this.isSearching = false;
            }
        },
        clearSearch() {
            this.searchQuery = "";
            this.searchResults = [];
            this.searchError = null;
        },
        applyDocumentationRouteQuery() {
            const q = this.reticulumDocsQueryParam;
            if (q === undefined || q === null || q === "") {
                return;
            }
            const raw = Array.isArray(q) ? q[0] : q;
            if (typeof raw !== "string" || !raw.trim()) {
                return;
            }
            let path = raw.trim();
            try {
                path = decodeURIComponent(path);
            } catch {
                return;
            }
            path = path.replace(/^\/?(?:reticulum-docs\/)?/, "");
            if (!path) {
                return;
            }
            this.activeTab = "reticulum";
            this.selectedReticulumPath = path;
        },
        navigateTo(path) {
            if (path.startsWith("/meshchatx-docs/")) {
                this.activeTab = "meshchatx";
                const docPath = path.replace("/meshchatx-docs/", "");
                this.selectDoc(docPath);
            } else {
                this.activeTab = "reticulum";
                const cleanPath = path.replace("/reticulum-docs/", "");
                this.selectedReticulumPath = cleanPath;
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
            // eslint-disable-next-line security/detect-non-literal-regexp -- query is escaped above
            const regex = new RegExp(`(${query})`, "gi");
            return escapedText.replace(
                regex,
                '<span class="bg-blue-100 dark:bg-blue-900/40 text-blue-700 dark:text-blue-300 px-0.5 rounded-sm">$1</span>'
            );
        },
        handleDocClick(event) {
            const link = event.target.closest("a");
            if (!link) return;

            const href = link.getAttribute("href");
            if (!href) return;

            // If it's an external link, let the browser handle it (it will open in a new tab due to target="_blank" from renderer)
            if (href.startsWith("http") || href.startsWith("mailto:") || href.startsWith("/")) {
                return;
            }

            // If it's a hash link, use the smooth scroll helper
            if (href.startsWith("#")) {
                event.preventDefault();
                this.scrollToHeading(href.substring(1));
                return;
            }

            // If it's a relative link to another markdown file
            if (href.endsWith(".md") || href.endsWith(".txt")) {
                event.preventDefault();

                // Resolve relative path
                const currentPath = this.selectedDocPath || "";
                const parts = currentPath.split("/");
                parts.pop(); // remove current filename

                const hrefParts = href.split("/");
                for (const part of hrefParts) {
                    if (part === "..") {
                        parts.pop();
                    } else if (part !== ".") {
                        parts.push(part);
                    }
                }

                const newPath = parts.join("/");
                this.selectDoc(newPath);

                // Scroll to top
                if (this.$refs.docContentScroller) {
                    this.$refs.docContentScroller.scrollTop = 0;
                }
            }
        },
    },
};
</script>

<style scoped>
iframe {
    color-scheme: light dark;
}

:deep(.docs-prose) {
    color: var(--mc-text-secondary);
    font-size: 0.9375rem;
    line-height: 1.7;
}

:deep(.docs-prose h1) {
    letter-spacing: -0.02em;
}

:deep(.docs-prose h2 a),
:deep(.docs-prose h3 a) {
    color: inherit;
    text-decoration: none;
}

:deep(.docs-prose pre) {
    color: #f4f4f5 !important;
}

:deep(.docs-prose pre code) {
    color: inherit !important;
}

:deep(.docs-prose code) {
    font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, "Liberation Mono", "Courier New", monospace;
}

.dark :deep(.docs-prose p) {
    color: #e4e4e7;
}

.dark :deep(.docs-prose h1),
.dark :deep(.docs-prose h2),
.dark :deep(.docs-prose h3),
.dark :deep(.docs-prose h4) {
    color: #f4f4f5;
}

:deep(.docs-prose table) {
    width: 100%;
    border-collapse: collapse;
    margin: 1.25rem 0;
    font-size: 0.875rem;
}

:deep(.docs-prose th),
:deep(.docs-prose td) {
    border: 1px solid var(--mc-border);
    padding: 0.5rem 0.75rem;
    text-align: left;
}

:deep(.docs-prose th) {
    background-color: var(--mc-surface-muted);
    font-weight: 700;
}

:deep(.docs-prose tr:nth-child(even)) {
    background-color: color-mix(in srgb, var(--mc-surface-muted) 65%, transparent);
}

:deep(.docs-prose a) {
    text-decoration-thickness: 1px;
    text-underline-offset: 2px;
}

:deep(.docs-prose blockquote) {
    border-left-color: color-mix(in srgb, var(--mc-accent) 55%, transparent);
}
</style>
