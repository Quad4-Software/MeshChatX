<!-- SPDX-License-Identifier: 0BSD AND MIT -->

<template>
    <div class="flex flex-1 min-w-0 h-full overflow-hidden">
        <!-- nomadnetwork sidebar -->
        <NomadNetworkSidebar
            v-if="!isPopoutMode"
            :class="{ 'hidden sm:flex': selectedNode }"
            :collapsed="nomadNetworkSidebarCollapsed"
            :nodes="nodes"
            :favourites="favourites"
            :selected-destination-hash="selectedNode?.destination_hash || ''"
            :nodes-search-term="nodesSearchTerm"
            :total-nodes-count="totalNodesCount"
            :is-loading-more-nodes="isLoadingMoreNodes"
            :is-searching-nodes="isSearchingNodes"
            :has-more-nodes="hasMoreNodes"
            @node-click="onNodeClick"
            @rename-favourite="onRenameFavourite"
            @remove-favourite="onRemoveFavourite"
            @add-favourite="addFavourite"
            @toggle-identify-on-connect="toggleIdentifyOnConnect"
            @bulk-remove-favourites="onBulkRemoveFavourites"
            @bulk-add-favourites="onBulkAddFavouritesFromAnnounces"
            @nodes-search-changed="onNodesSearchChanged"
            @load-more-nodes="loadMoreNodes"
            @toggle-collapse="nomadNetworkSidebarCollapsed = !nomadNetworkSidebarCollapsed"
        />

        <div
            class="flex-col flex-1 overflow-hidden min-w-0 bg-sem-canvas"
            :class="selectedNode ? 'flex' : 'hidden sm:flex'"
        >
            <!-- node -->
            <div
                v-if="selectedNode"
                class="flex flex-col h-full min-h-0 bg-sem-surface overflow-hidden sm:m-0 sm:border-0 relative"
            >
                <!-- banished overlay -->
                <div
                    v-if="GlobalState.config.banished_effect_enabled && isSelectedNodeBlocked"
                    class="banished-overlay"
                    :style="{ background: GlobalState.config.banished_color + '33' }"
                >
                    <span
                        class="banished-text opacity-100! text-white! shadow-lg! bg-red-600! px-4! py-2! rounded-xl! border-2! tracking-widest!"
                        :style="{
                            'background-color': GlobalState.config.banished_color,
                            'border-color': GlobalState.config.banished_color,
                        }"
                        >{{ GlobalState.config.banished_text }}</span
                    >
                </div>

                <!-- header -->
                <div
                    class="flex min-w-0 items-center gap-1 border-b px-2 py-0.5 sm:px-3"
                    :class="
                        isPrivate
                            ? 'border-purple-500/50 bg-[#1a0b33] text-purple-100'
                            : 'border-sem-border bg-sem-surface'
                    "
                >
                    <div
                        v-if="isPrivate"
                        class="my-auto flex shrink-0 items-center gap-1 rounded px-1.5 py-0.5 text-xs font-medium text-purple-200"
                        :title="$t('nomadnet.private_browsing_hint')"
                    >
                        <MaterialDesignIcon icon-name="incognito" class="size-4 text-purple-300" />
                        <span class="hidden sm:inline">{{ $t("nomadnet.private_tab") }}</span>
                    </div>
                    <!-- favourite button -->
                    <div v-if="!isPrivate" class="my-auto shrink-0">
                        <IconButton
                            v-if="isFavourite(selectedNode.destination_hash)"
                            class="nomad-icon-btn text-yellow-500 dark:text-yellow-300"
                            :title="$t('nomadnet.remove_favourite')"
                            @click="removeFavourite(selectedNode)"
                        >
                            <MaterialDesignIcon icon-name="star" class="size-5" />
                        </IconButton>
                        <IconButton
                            v-else
                            class="nomad-icon-btn text-sem-fg-muted"
                            :title="$t('nomadnet.add_favourite')"
                            @click="addFavourite(selectedNode)"
                        >
                            <MaterialDesignIcon icon-name="star-outline" class="size-5" />
                        </IconButton>
                    </div>

                    <!-- node info -->
                    <div class="my-auto text-sem-fg flex-1 min-w-0 flex items-center gap-2 overflow-hidden">
                        <span
                            class="font-medium truncate inline-block min-w-0 max-w-[min(100%,12rem)] sm:max-w-xs md:max-w-sm"
                            :title="selectedNode.custom_display_name || selectedNode.display_name"
                            >{{ selectedNode.custom_display_name || selectedNode.display_name }}</span
                        >
                        <span
                            v-if="selectedNodePath"
                            class="text-xs text-sem-fg-muted cursor-pointer whitespace-nowrap shrink-0 hidden sm:inline"
                            @click="onDestinationPathClick(selectedNodePath)"
                        >
                            {{ selectedNodePath.hops }}
                            {{ selectedNodePath.hops === 1 ? $t("app.hop") : $t("app.hops_plural") }}
                            <template v-if="navbarPageStats">
                                · {{ navbarPageStats.duration }} · {{ navbarPageStats.sizeLabel }}
                            </template>
                        </span>
                        <ClickPopover v-if="nomadBrowserRendererChip && !isLoadingNodePage">
                            <template #activator>
                                <span
                                    class="shrink-0 hidden sm:inline-flex sm:items-center max-w-[7.5rem] md:max-w-[9rem] truncate rounded px-1 py-0.5 text-[11px] font-medium leading-tight text-sem-fg-muted cursor-pointer outline-hidden focus-visible:ring-2 focus-visible:ring-blue-500 dark:focus-visible:ring-blue-400"
                                    tabindex="0"
                                    role="button"
                                    >{{ nomadBrowserRendererChip.label }}</span
                                >
                            </template>
                            <div
                                class="rounded-lg border border-[var(--mc-border-strong)] bg-[var(--mc-surface)] px-3 py-2 text-xs leading-snug text-[var(--mc-text-secondary)] shadow-lg"
                            >
                                <template v-if="nomadBrowserRendererChip.popoverVariant === 'wasm_active'">
                                    <span>{{ $t("nomadnet.renderer_popover_micron_wasm_powered") }}</span>
                                    <a
                                        class="font-medium text-[var(--mc-text-secondary)] underline underline-offset-2 hover:opacity-90"
                                        :href="micronParserGoRepoUrl"
                                        target="_blank"
                                        rel="noopener noreferrer"
                                        @click.stop
                                        >{{ $t("settings.nomad_micron_wasm_link_label") }}</a
                                    ><span>{{
                                        $t("nomadnet.renderer_popover_micron_wasm_active_tail", {
                                            version: nomadBrowserRendererChip.micronGoRelease,
                                        })
                                    }}</span>
                                </template>
                                <template v-else-if="nomadBrowserRendererChip.popoverVariant === 'wasm_pending'">
                                    <a
                                        class="font-medium text-[var(--mc-text-secondary)] underline underline-offset-2 hover:opacity-90"
                                        :href="micronParserGoRepoUrl"
                                        target="_blank"
                                        rel="noopener noreferrer"
                                        @click.stop
                                        >{{ $t("settings.nomad_micron_wasm_link_label") }}</a
                                    ><span>{{
                                        $t("nomadnet.renderer_popover_micron_wasm_pending_tail", {
                                            version: nomadBrowserRendererChip.micronGoRelease,
                                        })
                                    }}</span>
                                </template>
                                <template v-else>
                                    {{ nomadBrowserRendererChip.tooltipBody }}
                                </template>

                                <div
                                    v-if="showMicronRendererInMobileMenu"
                                    class="mt-2 pt-2 border-t border-[var(--mc-border-strong)] flex flex-col gap-1.5"
                                >
                                    <div
                                        class="text-[10px] font-bold uppercase tracking-wider text-[var(--mc-text-secondary)] opacity-80"
                                    >
                                        {{ $t("nomadnet.renderer_switch_title") }}
                                    </div>
                                    <div class="flex gap-1">
                                        <button
                                            class="flex-1 rounded px-2 py-1 text-[10px] font-bold transition-colors"
                                            :class="
                                                (GlobalState.config.nomad_micron_default_engine || 'js') === 'js'
                                                    ? 'bg-blue-600 text-white dark:bg-blue-500'
                                                    : 'bg-[var(--mc-surface-hover)] text-[var(--mc-text-secondary)] hover:bg-[var(--mc-border-strong)]'
                                            "
                                            :disabled="!GlobalState.config.nomad_micron_wasm_enabled"
                                            @click.stop="
                                                (GlobalState.config.nomad_micron_default_engine || 'js') === 'js'
                                                    ? null
                                                    : applyNomadMicronDefaultEngine('js')
                                            "
                                        >
                                            JS
                                        </button>
                                        <button
                                            class="flex-1 rounded px-2 py-1 text-[10px] font-bold transition-colors"
                                            :class="
                                                (GlobalState.config.nomad_micron_default_engine || 'js') === 'wasm'
                                                    ? 'bg-blue-600 text-white dark:bg-blue-500'
                                                    : 'bg-[var(--mc-surface-hover)] text-[var(--mc-text-secondary)] hover:bg-[var(--mc-border-strong)]'
                                            "
                                            :disabled="!GlobalState.config.nomad_micron_wasm_enabled"
                                            @click.stop="
                                                (GlobalState.config.nomad_micron_default_engine || 'js') === 'wasm'
                                                    ? null
                                                    : applyNomadMicronDefaultEngine('wasm')
                                            "
                                        >
                                            WASM
                                        </button>
                                    </div>
                                </div>
                            </div>
                        </ClickPopover>
                    </div>

                    <!-- archive button -->
                    <div
                        v-if="!isPrivate && (pageArchives.length > 0 || nodePageContent)"
                        class="my-auto shrink-0 relative"
                    >
                        <IconButton
                            class="nomad-icon-btn text-sem-fg-muted"
                            :class="{ 'text-sem-accent': pageArchives.length > 0 }"
                            :title="$t('app.archives')"
                            @click="toggleArchiveDropdown"
                        >
                            <MaterialDesignIcon icon-name="archive" class="size-5" />
                        </IconButton>
                        <!-- archive dropdown -->
                        <div
                            v-if="isArchiveDropdownOpen"
                            class="absolute right-0 mt-2 w-64 bg-sem-surface border border-sem-border rounded-lg shadow-lg z-50 overflow-hidden"
                        >
                            <div
                                class="p-2 border-b border-sem-border font-semibold text-xs text-sem-fg-muted uppercase tracking-wider flex justify-between items-center"
                            >
                                <span>{{ $t("nomadnet.page_archives") }}</span>
                                <button
                                    v-if="nodePageContent"
                                    :title="$t('nomadnet.archive_current_version')"
                                    class="text-blue-500 hover:text-sem-accent dark:hover:text-blue-300"
                                    @click.stop="manualArchive"
                                >
                                    <MaterialDesignIcon icon-name="plus" class="size-5" />
                                </button>
                            </div>
                            <div class="max-h-64 overflow-y-auto">
                                <div v-if="pageArchives.length === 0" class="p-3 text-sm text-sem-fg-muted text-center">
                                    {{ $t("nomadnet.no_archives_for_this_page") }}
                                </div>
                                <div
                                    v-for="archive in pageArchives"
                                    v-else
                                    :key="archive.id"
                                    class="p-2 hover:bg-sem-surface-muted cursor-pointer border-b last:border-b-0 border-sem-border"
                                    @click="loadArchivedPage(archive.id)"
                                >
                                    <div class="text-sm font-medium dark:text-gray-200">
                                        {{ formatDate(archive.created_at) }}
                                    </div>
                                    <div class="text-xs text-sem-fg-muted truncate">
                                        {{ archive.hash.substring(0, 16) }}...
                                    </div>
                                </div>
                            </div>
                        </div>
                    </div>

                    <IconButton
                        v-if="!isPrivate"
                        class="nomad-icon-btn shrink-0 lg:hidden"
                        :class="selectedNodeIdentifiesOnConnect ? 'text-sem-accent' : 'text-sem-fg-muted'"
                        :title="
                            selectedNodeIdentifiesOnConnect
                                ? $t('nomadnet.identify_on_connect_on')
                                : $t('nomadnet.identify_on_connect_off')
                        "
                        :aria-pressed="selectedNodeIdentifiesOnConnect ? 'true' : 'false'"
                        @click="toggleIdentifyOnConnect(selectedNode.destination_hash)"
                    >
                        <MaterialDesignIcon icon-name="fingerprint" class="size-5" />
                    </IconButton>

                    <div class="hidden shrink-0 items-center gap-0 lg:flex">
                        <IconButton
                            v-if="!isPrivate"
                            class="nomad-icon-btn"
                            :class="selectedNodeIdentifiesOnConnect ? 'text-sem-accent' : 'text-sem-fg-muted'"
                            :title="
                                selectedNodeIdentifiesOnConnect
                                    ? $t('nomadnet.identify_on_connect_on')
                                    : $t('nomadnet.identify_on_connect_off')
                            "
                            :aria-pressed="selectedNodeIdentifiesOnConnect ? 'true' : 'false'"
                            @click="toggleIdentifyOnConnect(selectedNode.destination_hash)"
                        >
                            <MaterialDesignIcon icon-name="fingerprint" class="size-5" />
                        </IconButton>
                        <IconButton
                            v-if="!isPrivate"
                            class="nomad-icon-btn text-sem-fg-muted"
                            :title="$t('nomadnet.pop_out_browser')"
                            @click="openNomadnetPopout"
                        >
                            <MaterialDesignIcon icon-name="open-in-new" class="size-5" />
                        </IconButton>
                        <IconButton
                            class="nomad-icon-btn text-sem-fg-muted"
                            :title="$t('common.cancel')"
                            @click="onCloseNodeViewer"
                        >
                            <MaterialDesignIcon icon-name="close" class="size-5" />
                        </IconButton>
                    </div>

                    <DropDownMenu class="shrink-0 lg:hidden">
                        <template #button>
                            <IconButton :title="$t('messages.more_actions')" class="nomad-icon-btn text-sem-fg-muted">
                                <MaterialDesignIcon icon-name="dots-horizontal" class="size-5" />
                            </IconButton>
                        </template>
                        <template #items>
                            <DropDownMenuItem @click="toggleNodePageSource">
                                <MaterialDesignIcon icon-name="code-tags" class="size-5" />
                                <span>{{
                                    isShowingNodePageSource ? $t("nomadnet.hide_source") : $t("app.toggle_source")
                                }}</span>
                            </DropDownMenuItem>
                            <DropDownMenuItem
                                v-if="showMicronRendererInMobileMenu"
                                @click="applyNomadMicronDefaultEngine('js')"
                            >
                                <MaterialDesignIcon icon-name="language-javascript" class="size-5" />
                                <span>{{ $t("nomadnet.renderer_menu_js") }}</span>
                            </DropDownMenuItem>
                            <DropDownMenuItem
                                v-if="showMicronRendererInMobileMenu"
                                @click="applyNomadMicronDefaultEngine('wasm')"
                            >
                                <MaterialDesignIcon icon-name="memory" class="size-5" />
                                <span>{{ $t("nomadnet.renderer_menu_wasm") }}</span>
                            </DropDownMenuItem>
                        </template>
                    </DropDownMenu>

                    <IconButton
                        class="nomad-icon-btn shrink-0 text-sem-fg-muted lg:hidden"
                        :title="$t('common.cancel')"
                        @click="onCloseNodeViewer"
                    >
                        <MaterialDesignIcon icon-name="close" class="size-5" />
                    </IconButton>
                </div>

                <!-- browser navigation -->
                <div
                    class="nomad-browser-chrome flex w-full min-w-0 items-center gap-0.5 overflow-x-auto border-b border-sem-border bg-sem-surface px-2 py-0.5 sm:gap-1 sm:px-3"
                >
                    <IconButton
                        class="nomad-icon-btn shrink-0"
                        :title="$t('nomadnet.nav_home')"
                        @click="loadNodePage(selectedNode.destination_hash, defaultNodePagePath)"
                    >
                        <MaterialDesignIcon icon-name="home" class="size-5" />
                    </IconButton>
                    <IconButton class="nomad-icon-btn shrink-0" :title="$t('common.refresh')" @click="reloadNodePage">
                        <MaterialDesignIcon icon-name="refresh" class="size-5" />
                    </IconButton>
                    <IconButton
                        class="nomad-icon-btn hidden lg:inline-flex shrink-0"
                        :title="$t('app.toggle_source')"
                        :class="{ 'bg-green-500/10 text-green-600 dark:text-green-400': isShowingNodePageSource }"
                        @click="toggleNodePageSource"
                    >
                        <MaterialDesignIcon icon-name="code-tags" class="size-5" />
                    </IconButton>
                    <IconButton
                        class="nomad-icon-btn shrink-0"
                        :title="$t('nomadnet.nav_back')"
                        :disabled="nodePagePathHistory.length === 0"
                        @click="loadPreviousNodePage"
                    >
                        <MaterialDesignIcon icon-name="arrow-left" class="size-5" />
                    </IconButton>
                    <div class="my-auto min-w-0 flex-1 px-0.5 sm:px-1">
                        <input
                            v-model="nodePagePathUrlInput"
                            type="text"
                            :placeholder="$t('nomadnet.enter_nomadnet_url')"
                            class="nomad-url-input block w-full min-w-0"
                            @keyup.enter="onNodePageUrlClick(nodePagePathUrlInput)"
                        />
                    </div>
                    <IconButton
                        class="nomad-icon-btn shrink-0"
                        :title="$t('nomadnet.nav_go')"
                        @click="onNodePageUrlClick(nodePagePathUrlInput)"
                    >
                        <MaterialDesignIcon icon-name="arrow-right" class="size-5" />
                    </IconButton>

                    <DropDownMenu v-if="selectedNode" class="shrink-0">
                        <template #button>
                            <IconButton
                                :title="$t('nomadnet.path_finder')"
                                class="nomad-icon-btn text-sem-accent"
                                :disabled="pathfinderInProgress"
                            >
                                <MaterialDesignIcon
                                    :icon-name="pathfinderInProgress ? 'loading' : 'map-marker-path'"
                                    :class="['w-5 h-5', pathfinderInProgress ? 'animate-spin' : '']"
                                />
                            </IconButton>
                        </template>
                        <template #items>
                            <DropDownMenuItem @click="runPathFinderQuickRequest">
                                <MaterialDesignIcon icon-name="flash" class="size-5" />
                                <span>{{ $t("nomadnet.path_finder_quick_request") }}</span>
                            </DropDownMenuItem>
                            <DropDownMenuItem @click="runPathFinderForceFind">
                                <MaterialDesignIcon icon-name="map-marker-radius" class="size-5" />
                                <span>{{ $t("nomadnet.path_finder_force_find") }}</span>
                            </DropDownMenuItem>
                            <DropDownMenuItem @click="runPathFinderDropAndRequest">
                                <MaterialDesignIcon icon-name="reload-alert" class="size-5" />
                                <span>{{ $t("nomadnet.path_finder_drop_and_request") }}</span>
                            </DropDownMenuItem>
                            <DropDownMenuItem
                                v-if="!isPrivate && (hasArchivesForCurrentPage || pageArchives.length > 0)"
                                @click="loadLatestArchiveSnapshot"
                            >
                                <MaterialDesignIcon icon-name="archive-clock" class="size-5" />
                                <span>{{ $t("nomadnet.path_finder_load_archive") }}</span>
                            </DropDownMenuItem>
                        </template>
                    </DropDownMenu>
                </div>

                <!-- page content: capture-phase clicks so <a href> is handled before browser default navigation -->
                <div
                    :class="[
                        'flex-1 min-h-0 min-w-0 overflow-y-auto overflow-x-hidden nodeContainer relative contain-[layout_paint]',
                        nomadRenderedShellFullBleed
                            ? 'p-0 bg-transparent min-h-full text-gray-900 dark:text-gray-100'
                            : 'p-3 bg-black text-white',
                        nomadShellDark ? 'nomad-shell-dark' : '',
                    ]"
                    :style="nodeContainerShellStyle"
                    @click.capture="onElementClick"
                    @auxclick.capture="onElementClick"
                    @contextmenu="onPageContextMenu"
                >
                    <!-- archived version notice -->
                    <div
                        v-if="isShowingArchivedVersion"
                        :class="[
                            'mb-4 flex min-w-0 items-center justify-between gap-2 rounded-sm border border-yellow-700/50 bg-yellow-900/40 p-2 text-yellow-200',
                            nomadRenderedShellFullBleed ? 'mx-3 mt-3' : '',
                        ]"
                    >
                        <div class="flex min-w-0 items-center gap-2">
                            <MaterialDesignIcon icon-name="clock" class="size-5 shrink-0" />
                            <span v-if="archivedAt" class="min-w-0 text-sm font-medium wrap-break-word">{{
                                $t("nomadnet.viewing_archived_version_from", { time: formatDate(archivedAt) })
                            }}</span>
                            <span v-else class="min-w-0 text-sm font-medium wrap-break-word">{{
                                $t("nomadnet.viewing_archived_version")
                            }}</span>
                        </div>
                        <button
                            class="shrink-0 text-xs bg-yellow-700/50 hover:bg-yellow-700 px-2 py-1 rounded-sm transition"
                            @click="reloadNodePage"
                        >
                            {{ $t("nomadnet.load_live") }}
                        </button>
                    </div>

                    <div v-if="showPageBusyBanner" class="flex min-w-0" role="status" aria-live="polite">
                        <div class="my-auto">
                            <svg
                                class="animate-spin mr-3 h-5 w-5 text-white"
                                xmlns="http://www.w3.org/2000/svg"
                                fill="none"
                                viewBox="0 0 24 24"
                                aria-hidden="true"
                            >
                                <circle
                                    class="opacity-25"
                                    cx="12"
                                    cy="12"
                                    r="10"
                                    stroke="currentColor"
                                    stroke-width="4"
                                ></circle>
                                <path
                                    class="opacity-75"
                                    fill="currentColor"
                                    d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"
                                ></path>
                            </svg>
                        </div>
                        <div class="my-auto min-w-0 flex-1 truncate">{{ pageBusyBannerLine }}</div>
                        <button
                            type="button"
                            class="my-auto text-white bg-red-600 hover:bg-red-700 dark:bg-red-700 dark:hover:bg-red-800 rounded-sm px-3 py-1 text-sm font-semibold cursor-pointer ml-3"
                            @click="cancelPageBusy"
                        >
                            {{ $t("common.cancel") }}
                        </button>
                    </div>
                    <div v-else-if="showCancelledPageState" class="flex" role="status">
                        <div class="my-auto flex-1">
                            <div>
                                {{
                                    pageRenderAborted
                                        ? $t("nomadnet.crash_tab_render_cancelled")
                                        : $t("nomadnet.page_download_cancelled")
                                }}
                            </div>
                            <div class="text-sm text-sem-fg-muted">{{ $t("nomadnet.page_stopped_hint") }}</div>
                        </div>
                        <button
                            v-if="pageRenderAborted && canRetryCrashTabRender"
                            type="button"
                            class="my-auto text-white bg-blue-600 hover:bg-blue-700 dark:bg-blue-700 dark:hover:bg-blue-800 rounded-sm px-3 py-1 text-sm font-semibold cursor-pointer ml-3"
                            @click="retryCrashTabRender"
                        >
                            {{ $t("nomadnet.crash_tab_reload") }}
                        </button>
                        <button
                            v-else-if="selectedNode?.destination_hash && nodePagePath"
                            type="button"
                            class="my-auto text-white bg-blue-600 hover:bg-blue-700 dark:bg-blue-700 dark:hover:bg-blue-800 rounded-sm px-3 py-1 text-sm font-semibold cursor-pointer ml-3"
                            @click="reloadNodePage"
                        >
                            {{ $t("common.refresh") }}
                        </button>
                    </div>
                    <div
                        v-else-if="isFailedPageContent(nodePageContent)"
                        class="flex flex-col items-center justify-center h-full text-center space-y-4"
                        role="alert"
                    >
                        <div class="text-red-400 font-semibold text-lg">{{ $t("nomadnet.failed_to_load_page") }}</div>
                        <div class="text-sem-fg-muted text-sm max-w-md break-words">{{ nodePageContent }}</div>

                        <div v-if="!isPrivate && hasArchivesForCurrentPage" class="space-y-2">
                            <div class="text-sm text-sem-fg-muted">{{ $t("nomadnet.archived_version_available") }}</div>
                            <button
                                type="button"
                                class="inline-flex items-center gap-2 rounded-lg bg-blue-600 px-4 py-2 text-sm font-semibold text-white shadow-sm hover:bg-blue-500"
                                @click="toggleArchiveDropdown"
                            >
                                <MaterialDesignIcon icon-name="archive" class="size-5" />
                                {{ $t("nomadnet.view_archive") }}
                            </button>
                        </div>
                        <button
                            v-else-if="selectedNode?.destination_hash"
                            type="button"
                            class="my-auto text-white bg-blue-600 hover:bg-blue-700 dark:bg-blue-700 dark:hover:bg-blue-800 rounded-sm px-3 py-1 text-sm font-semibold cursor-pointer"
                            @click="reloadNodePage"
                        >
                            {{ $t("common.refresh") }}
                        </button>
                    </div>
                    <div v-else-if="showEmptyPageState" class="flex">
                        <div class="my-auto flex-1">
                            <div>{{ $t("nomadnet.page_empty_title") }}</div>
                            <div class="text-sm text-sem-fg-muted">{{ $t("nomadnet.page_empty_body") }}</div>
                        </div>
                        <button
                            v-if="selectedNode?.destination_hash"
                            type="button"
                            class="my-auto text-white bg-blue-600 hover:bg-blue-700 dark:bg-blue-700 dark:hover:bg-blue-800 rounded-sm px-3 py-1 text-sm font-semibold cursor-pointer ml-3"
                            @click="reloadNodePage"
                        >
                            {{ $t("common.refresh") }}
                        </button>
                    </div>
                    <div
                        v-if="showCrashTabHost"
                        class="relative min-h-0 w-full min-w-0 overflow-hidden bg-black"
                        :class="
                            showPageBusyBanner ||
                            showCancelledPageState ||
                            isFailedPageContent(nodePageContent) ||
                            showEmptyPageState
                                ? 'pointer-events-none absolute inset-0 opacity-0'
                                : 'h-full'
                        "
                    >
                        <NomadCrashTab
                            ref="crashTab"
                            class="absolute inset-0 h-full min-h-0 w-full min-w-0"
                            :path="nodePagePath || ''"
                            :content="crashTabPageContent"
                            :show-source="isShowingNodePageSource"
                            :page-partials="pagePartials"
                            :render-options="nomadRenderOptions"
                            :content-class="nomadCrashTabContentClass"
                            :color="nomadCrashTabColor"
                            :background="nomadCrashTabBackground"
                            :active="isActive"
                            :reveal="!showPageBusyBanner"
                            @navigate="onCrashTabNavigate"
                            @partials="onCrashTabPartials"
                            @view-source="showPageSource"
                            @hung="onCrashTabHung"
                            @render-started="onCrashTabRenderStarted"
                            @render-done="onCrashTabRenderDone"
                            @aborted="onCrashTabAborted"
                            @shell-background="onCrashTabShellBackground"
                        />
                    </div>
                    <Teleport to="body">
                        <div
                            v-if="multilineHintVisible"
                            class="multiline-hint pointer-events-none fixed z-200 bottom-[max(0.75rem,env(safe-area-inset-bottom))] right-[max(0.75rem,env(safe-area-inset-right))] px-2 py-1 rounded text-xs bg-amber-300 text-zinc-900 shadow"
                        >
                            {{ $t("nomadnet.multiline_hint") }}
                        </div>
                    </Teleport>
                </div>

                <!-- file download bottom bar -->
                <div v-if="isDownloadingNodeFile" class="flex w-full border-sem-border border-t p-2 dark:text-gray-100">
                    <div class="my-auto mr-2">
                        <svg
                            class="animate-spin h-5 w-5"
                            xmlns="http://www.w3.org/2000/svg"
                            fill="none"
                            viewBox="0 0 24 24"
                        >
                            <circle
                                class="opacity-25"
                                cx="12"
                                cy="12"
                                r="10"
                                stroke="currentColor"
                                stroke-width="4"
                            ></circle>
                            <path
                                class="opacity-75"
                                fill="currentColor"
                                d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"
                            ></path>
                        </svg>
                    </div>
                    <div class="my-auto flex-1">
                        Downloading: {{ nodeFilePath }} ({{ nodeFileProgress }}%)
                        <span v-if="nodeFileDownloadSpeed !== null" class="ml-2 text-sm">
                            - {{ formatBytesPerSecond(nodeFileDownloadSpeed) }}
                        </span>
                    </div>
                    <button
                        type="button"
                        class="my-auto text-white bg-red-600 hover:bg-red-700 dark:bg-red-700 dark:hover:bg-red-800 rounded-sm px-3 py-1 text-sm font-semibold cursor-pointer"
                        @click="cancelFileDownload"
                    >
                        {{ $t("common.cancel") }}
                    </button>
                </div>
            </div>

            <!-- no node selected -->
            <div v-else class="flex flex-col mx-auto my-auto text-center leading-5 dark:text-gray-100">
                <div class="mx-auto mb-1">
                    <MaterialDesignIcon icon-name="earth" class="w-6 h-6 dark:text-gray-300" />
                </div>
                <div class="font-semibold">{{ $t("nomadnet.no_active_node") }}</div>
                <div>{{ $t("nomadnet.select_node_to_browse") }}</div>
                <div class="mx-auto mt-2">
                    <button
                        type="button"
                        class="my-auto inline-flex items-center gap-x-1 rounded-md bg-blue-600 px-2.5 py-1 text-sm font-medium text-white hover:bg-blue-500 dark:bg-blue-600 dark:hover:bg-blue-500"
                        @click.stop="openUrl"
                    >
                        {{ $t("nomadnet.open_nomadnet_url") }}
                    </button>
                </div>
            </div>
        </div>

        <NomadBrowserContextMenu
            v-if="!embedded"
            :show="standaloneContextMenu.show"
            :x="standaloneContextMenu.x"
            :y="standaloneContextMenu.y"
            :just-opened="standaloneContextMenu.justOpened"
            :has-active-page="standaloneContextHasActivePage"
            :can-favourite="!isPrivate && Boolean(selectedNode?.destination_hash)"
            :is-favourite="selectedNode ? isFavourite(selectedNode.destination_hash) : false"
            :can-download-page="standaloneContextCanDownloadPage"
            :show-tab-actions="false"
            @close="closeStandaloneContextMenu"
            @view-source="onStandaloneContextViewSource"
            @reload="onStandaloneContextReload"
            @favorite="onStandaloneContextFavorite"
            @download-page="onStandaloneContextDownloadPage"
        />
    </div>
</template>

<script>
import MicronParser from "../../js/MicronParser";
import LinkUtils from "../../js/LinkUtils";
import { handleRichHtmlLinkClick } from "../../js/NomadRichHtmlLinks.js";
import {
    renderNomadPageByPath,
    resolveNomadPageShellBackground,
    isolateNomadLinksInHtml,
} from "../../js/NomadPageRenderer";
import DialogUtils from "../../js/DialogUtils";
import WebSocketConnection from "../../js/WebSocketConnection";
import { onWsEvent, offWsEvent } from "../../js/registries/wsEventRegistry.js";
import NomadNetworkSidebar from "./NomadNetworkSidebar.vue";
import NomadBrowserContextMenu from "./NomadBrowserContextMenu.vue";
import NomadCrashTab from "./NomadCrashTab.vue";
import Utils from "../../js/Utils";
import DownloadUtils from "../../js/DownloadUtils";
import ToastUtils from "../../js/ToastUtils";
import { openAppContextMenuUnlessTextSelection } from "../../js/contextMenuUtils.js";
import { getDestinationPath, runDestinationPathFinder } from "../../js/reticulumPathfinding.js";
import MaterialDesignIcon from "../MaterialDesignIcon.vue";
import IconButton from "../IconButton.vue";
import DropDownMenu from "../DropDownMenu.vue";
import DropDownMenuItem from "../DropDownMenuItem.vue";
import GlobalState, { mergeGlobalConfig } from "../../js/GlobalState";
import GlobalEmitter from "../../js/GlobalEmitter";
import { shouldPollKeepAliveEmbedded } from "../../js/keepAlivePoll.js";
import { patchServerConfig } from "../../js/settings/settingsConfigService";
import {
    preloadNomadMicronWasm,
    invalidateNomadMicronWasmPreload,
    isMicronWasmBundled,
} from "../../js/MicronWasmLoader";
import { getEffectiveMicronWasmReleaseLabel, MICRON_WASM_OVERRIDE_CHANGED_EVENT } from "../../js/micronWasmVersion.js";
import ClickPopover from "../ClickPopover.vue";
import { loadFeatureSidebarCollapsed, saveFeatureSidebarCollapsed } from "../../js/browserLayoutStore";
import { isUnknownNodeDisplayName, resolveFavouriteUpsertDisplayName } from "../../js/nomadUnknownNodeName.js";

export default {
    name: "NomadNetworkPage",
    components: {
        NomadNetworkSidebar,
        NomadBrowserContextMenu,
        NomadCrashTab,
        ClickPopover,
        MaterialDesignIcon,
        IconButton,
        DropDownMenu,
        DropDownMenuItem,
    },
    inject: {
        nomadBrowserTabActions: {
            default: null,
        },
    },
    props: {
        destinationHash: {
            type: String,
            required: false,
            default: "",
        },
        embedded: {
            type: Boolean,
            default: false,
        },
        tabsEnabled: {
            type: Boolean,
            default: false,
        },
        isActive: {
            type: Boolean,
            default: true,
        },
        isPrivate: {
            type: Boolean,
            default: false,
        },
        initialPath: {
            type: String,
            required: false,
            default: null,
        },
    },
    emits: ["navigate", "open-node", "close-tab"],
    data() {
        return {
            GlobalState,
            reloadInterval: null,
            nodesRefreshTimeout: null,
            nodesListAbortController: null,
            nodeDetailAbortController: null,

            nomadNetworkSidebarCollapsed: loadFeatureSidebarCollapsed("nomadnetwork") ?? false,
            nodes: {},
            totalNodesCount: 0,
            hasMoreNodes: true,
            isLoadingMoreNodes: false,
            isSearchingNodes: false,
            nodesSearchTerm: "",
            pageSize: 50,
            selectedNode: null,
            selectedNodePath: null,

            favourites: [],

            isLoadingNodePage: false,
            isShowingNodePageSource: false,
            nodePageRequestSequence: 0,
            nodePagePath: null,
            nodePagePathUrlInput: null,
            nodePageContent: null,
            nodePageProgress: 0,
            nodePageLoadPhase: null,
            pageLoadStartedAt: null,
            lastPageLoadDurationMs: null,
            lastPageContentBytes: null,
            nodePagePathHistory: [],
            nodePageCache: {},
            currentPageDownloadId: null,
            pendingNomadPageCancelWithoutId: false,
            pageRenderAborted: false,

            isDownloadingNodeFile: false,
            nodeFilePath: null,
            nodeFileProgress: 0,
            nodeFileDownloadStartTime: null,
            nodeFileLastProgressTime: null,
            nodeFileLastProgressValue: 0,
            nodeFileDownloadSpeed: null,
            currentFileDownloadId: null,

            nomadnetPageDownloadCallbacks: {},
            nomadnetFileDownloadCallbacks: {},
            nomadPageDownloadChunkBuffers: {},
            nomadFileDownloadChunkBuffers: {},

            pageArchives: [],
            isArchiveDropdownOpen: false,
            isLoadingArchives: false,
            hasArchivesForCurrentPage: false,
            isShowingArchivedVersion: false,
            archivedAt: null,
            isSelectedNodeBlocked: false,

            pagePartials: {},
            loadedPartialIds: {},
            partialIdsByKey: {},
            partialRefreshByKey: {},
            partialRefreshTimers: {},
            processPartialsRaf: null,
            crashTabPartials: [],
            isCrashTabRendering: false,
            multilineCleanup: null,
            multilineHintVisible: false,

            pathfinderInProgress: false,
            pendingLoadLatestArchive: false,

            nomadMicronWasmReady: false,
            micronWasmReleaseLabel: null,
            wasmBundled: isMicronWasmBundled(),
            pageShellBackground: null,
            standaloneContextMenu: {
                show: false,
                justOpened: false,
                x: 0,
                y: 0,
            },
        };
    },
    computed: {
        defaultNodePagePath() {
            const p = GlobalState.config?.nomad_default_page_path;
            return typeof p === "string" && p.startsWith("/page/") ? p : "/page/index.mu";
        },
        standaloneContextHasActivePage() {
            return Boolean(this.selectedNode && this.nodePagePath);
        },
        selectedNodeIdentifiesOnConnect() {
            const hash = this.selectedNode?.destination_hash;
            if (!hash) {
                return false;
            }
            return this.identifiesOnConnect(hash);
        },
        standaloneContextCanDownloadPage() {
            return Boolean(
                this.nodePageContent &&
                this.nodePagePath &&
                !this.isFailedPageContent(this.nodePageContent) &&
                !this.isCancelledPageContent(this.nodePageContent) &&
                !this.pageRenderAborted
            );
        },
        showCancelledPageState() {
            if (this.isLoadingNodePage || this.isCrashTabRendering) {
                return false;
            }
            return this.pageRenderAborted || this.isCancelledPageContent(this.nodePageContent);
        },
        showEmptyPageState() {
            if (this.isLoadingNodePage || this.isCrashTabRendering || this.showCancelledPageState) {
                return false;
            }
            if (this.isFailedPageContent(this.nodePageContent)) {
                return false;
            }
            return this.nodePageContent == null || this.nodePageContent === "";
        },
        showPageBusyBanner() {
            return this.isLoadingNodePage || this.isCrashTabRendering;
        },
        pageBusyBannerLine() {
            if (this.isLoadingNodePage) {
                return this.nomadnetPageLoadingLine;
            }
            return this.$t("nomadnet.load_phase_default");
        },
        showCrashTabHost() {
            if (!this.selectedNode || !this.nodePagePath) {
                return false;
            }
            if (this.showCancelledPageState) {
                return false;
            }
            if (this.isFailedPageContent(this.nodePageContent)) {
                return false;
            }
            if (this.showEmptyPageState) {
                return false;
            }
            // Keep the iframe mounted during download/render so it stays warm and dark.
            return true;
        },
        crashTabPageContent() {
            if (this.isLoadingNodePage) {
                return "";
            }
            if (this.isCancelledPageContent(this.nodePageContent) || this.isFailedPageContent(this.nodePageContent)) {
                return "";
            }
            return this.nodePageContent || "";
        },
        canRetryCrashTabRender() {
            return Boolean(
                this.pageRenderAborted &&
                this.nodePageContent &&
                !this.isCancelledPageContent(this.nodePageContent) &&
                !this.isFailedPageContent(this.nodePageContent)
            );
        },
        nomadMicronWasmFeatureEffective() {
            return isMicronWasmBundled() && (GlobalState.config || {}).nomad_micron_wasm_enabled === true;
        },
        micronParserGoRepoUrl() {
            return "https://github.com/Quad4-Software/micron-parser-go";
        },
        nomadMicronWasmActive() {
            const engineWasm = (GlobalState.config?.nomad_micron_default_engine || "js") === "wasm";
            return (
                this.nomadMicronWasmFeatureEffective &&
                this.nomadMicronWasmReady === true &&
                typeof globalThis.micronConvert === "function" &&
                engineWasm
            );
        },
        nomadRenderOptions() {
            const c = GlobalState.config || {};
            const engineWasm = (c.nomad_micron_default_engine || "js") === "wasm";
            return {
                renderMarkdown: c.nomad_render_markdown_enabled !== false,
                renderHtml: c.nomad_render_html_enabled !== false,
                renderPlaintext: c.nomad_render_plaintext_enabled !== false,
                nomadDestinationHash: this.selectedNode?.destination_hash || null,
                nomad_micron_wasm_use:
                    this.nomadMicronWasmFeatureEffective && this.nomadMicronWasmReady === true && engineWasm,
            };
        },
        /**
         * Active page renderer label for the toolbar chip (.mu uses Micron JS vs WASM).
         */
        nomadBrowserRendererChip() {
            if (!this.selectedNode || !this.nodePagePath) {
                return null;
            }
            if (this.isShowingNodePageSource) {
                return null;
            }
            const [p] = this.nodePagePath.split("`");
            const pathLower = (p || "").toLowerCase();
            const micronGoRelease = this.micronWasmReleaseLabel || "\u2014";
            const plainChip = (labelKey, detailKey, detailParams) => {
                const detail = detailKey ? this.$t(detailKey, detailParams ?? {}) : "";
                return {
                    label: this.$t(labelKey),
                    popoverVariant: null,
                    tooltipBody: detail,
                };
            };
            if (pathLower.endsWith(".mu")) {
                if (this.nomadMicronWasmActive) {
                    return {
                        label: this.$t("nomadnet.renderer_chip_micron_wasm"),
                        popoverVariant: "wasm_active",
                        micronGoRelease,
                    };
                }
                const wasmPreferred =
                    this.nomadMicronWasmFeatureEffective &&
                    (GlobalState.config?.nomad_micron_default_engine || "js") === "wasm";
                if (wasmPreferred && !this.nomadMicronWasmReady) {
                    return {
                        label: this.$t("nomadnet.renderer_chip_micron_js"),
                        popoverVariant: "wasm_pending",
                        micronGoRelease,
                    };
                }
                return plainChip("nomadnet.renderer_chip_micron_js", "nomadnet.renderer_hint_micron_js");
            }
            if (pathLower.endsWith(".md")) {
                return plainChip("nomadnet.renderer_chip_markdown", "nomadnet.renderer_hint_markdown");
            }
            if (pathLower.endsWith(".html")) {
                return plainChip("nomadnet.renderer_chip_html", "nomadnet.renderer_hint_html");
            }
            if (pathLower.endsWith(".txt")) {
                return plainChip("nomadnet.renderer_chip_plaintext", "nomadnet.renderer_hint_plaintext");
            }
            return null;
        },
        /**
         * True when the loaded Nomad URL points at a .mu page. Strips Nomad ` suffix
         * (e.g. /page/foo.mu`g=reticulum|...) so engine switching matches the renderer chip.
         */
        nodePagePathIsMicronMu() {
            if (!this.nodePagePath) {
                return false;
            }
            const [p] = this.nodePagePath.split("`");
            return (p || "").toLowerCase().endsWith(".mu");
        },
        showMicronRendererInMobileMenu() {
            if (!this.wasmBundled || !this.selectedNode || !this.nodePagePath || this.isShowingNodePageSource) {
                return false;
            }
            return this.nodePagePathIsMicronMu;
        },
        blockedDestinations() {
            return GlobalState.blockedDestinations;
        },
        popoutRouteType() {
            if (this.$route?.meta?.popoutType) {
                return this.$route.meta.popoutType;
            }
            return this.$route?.query?.popout ?? this.getHashPopoutValue();
        },
        isPopoutMode() {
            return this.popoutRouteType === "nomad";
        },
        navbarPageStats() {
            if (this.lastPageLoadDurationMs == null || this.lastPageContentBytes == null || !this.selectedNodePath) {
                return null;
            }
            return {
                duration: this.formatShortDuration(this.lastPageLoadDurationMs),
                sizeLabel: Utils.formatBytes(this.lastPageContentBytes),
            };
        },
        nomadnetPageLoadingLine() {
            const phase = this.nodePageLoadPhase;
            if (!phase) {
                return this.$t("nomadnet.load_phase_default");
            }
            const key = `nomadnet.load_phase_${phase}`;
            const translated = this.$t(key);
            const base =
                typeof translated === "string" && translated !== key
                    ? translated
                    : this.$t("nomadnet.load_phase_default");
            if (this.nodePageProgress > 0 && (phase === "transferring" || phase === "requesting_page")) {
                return `${base} (${this.nodePageProgress}%)`;
            }
            return base;
        },
        crashTabContentKey() {
            // Change detector only. Do not Micron-parse on the shell thread.
            if (!this.nodePagePath || this.nodePageContent == null) {
                return "";
            }
            return `${this.isShowingNodePageSource ? "src" : "page"}:${this.nodePagePath}:${this.nodePageContent.length}`;
        },
        nomadCrashTabContentClass() {
            if (this.isShowingNodePageSource) {
                return "source bg-black";
            }
            if (!this.nodePagePath) {
                return "";
            }
            const [p] = this.nodePagePath.split("`");
            const pl = (p || "").toLowerCase();
            const classes = [];
            if (pl.endsWith(".mu") || pl.endsWith(".md") || pl.endsWith(".html")) {
                classes.push("nomad-page-rich");
            }
            if (pl.endsWith(".html")) {
                classes.push("nomad-page-html-host");
            } else if (pl.endsWith(".md")) {
                classes.push("nomad-markdown-host");
            } else if (pl.endsWith(".mu")) {
                classes.push("bg-black");
            } else {
                classes.push("plaintext-page");
            }
            if (this.nomadRenderedShellFullBleed) {
                classes.push("pad");
                if (this.nomadShellDark) {
                    classes.push("nomad-shell-dark");
                }
            }
            return classes.join(" ");
        },
        nomadCrashTabColor() {
            if (this.isShowingNodePageSource) {
                return "#dddddd";
            }
            if (this.nomadRenderedShellFullBleed) {
                return this.nomadShellDark ? "#f3f4f6" : "#111827";
            }
            if (!this.nodePagePath) {
                return "#dddddd";
            }
            const [p] = this.nodePagePath.split("`");
            const pl = (p || "").toLowerCase();
            if (pl.endsWith(".mu")) {
                // Match micron-parser DEFAULT_FG_DARK.
                return "#dddddd";
            }
            return "#f3f4f6";
        },
        nomadCrashTabBackground() {
            // Do not feed pageShellBackground (from shell-background postMessage) back
            // into the iframe. That re-triggered full renders and stuck Loading page.
            if (this.isShowingNodePageSource) {
                return "#000000";
            }
            if (!this.nodePagePath) {
                return "#000000";
            }
            const [p] = this.nodePagePath.split("`");
            const pl = (p || "").toLowerCase();
            if (pl.endsWith(".mu")) {
                const fromHeader = this.micronHeaderBackgroundCss;
                if (fromHeader) {
                    return fromHeader;
                }
                return "#000000";
            }
            if (pl.endsWith(".txt") || !pl.includes(".")) {
                return "#000000";
            }
            return "transparent";
        },
        micronHeaderBackgroundCss() {
            if (!this.nodePageContent || typeof this.nodePageContent !== "string") {
                return null;
            }
            if (!this.nodePagePath) {
                return null;
            }
            const [p] = this.nodePagePath.split("`");
            if (!(p || "").toLowerCase().endsWith(".mu")) {
                return null;
            }
            try {
                const { bg } = MicronParser.prototype.parseHeaderTags.call(null, this.nodePageContent);
                if (!bg || bg === "default") {
                    return null;
                }
                return MicronParser.prototype.colorToCss.call(null, bg);
            } catch (e) {
                console.warn("nomadnet: parse micron #!bg= failed", e);
            }
            return null;
        },
        hasPageLoadFailed() {
            if (this.isLoadingNodePage) {
                return false;
            }
            if (!this.selectedNode) {
                return false;
            }
            return this.isFailedPageContent(this.nodePageContent);
        },
        nodeContainerShellStyle() {
            if (this.nomadRenderedShellFullBleed && this.pageShellBackground) {
                return { background: this.pageShellBackground };
            }
            const muBg = this.micronHeaderBackgroundCss;
            if (muBg) {
                return { background: muBg };
            }
            return null;
        },
        nomadShellDark() {
            if (!this.nomadRenderedShellFullBleed) {
                return true;
            }
            const bg = this.pageShellBackground;
            if (!bg || typeof bg !== "string") {
                return false;
            }
            const lower = bg.toLowerCase().replace(/\s/g, "");
            if (lower === "#000" || lower === "#000000" || lower === "black" || lower === "rgb(0,0,0)") {
                return true;
            }
            const rgbMatch = lower.match(/^rgba?\((\d+),(\d+),(\d+)/);
            if (rgbMatch) {
                const r = Number(rgbMatch[1]);
                const g = Number(rgbMatch[2]);
                const b = Number(rgbMatch[3]);
                const luminance = (0.299 * r + 0.587 * g + 0.114 * b) / 255;
                return luminance < 0.45;
            }
            return false;
        },
        nomadRenderedShellFullBleed() {
            if (!this.nodePagePath || this.isShowingNodePageSource) {
                return false;
            }
            if (this.isLoadingNodePage) {
                return false;
            }
            if (this.isFailedPageContent(this.nodePageContent) || this.isCancelledPageContent(this.nodePageContent)) {
                return false;
            }
            if (this.pageRenderAborted) {
                return false;
            }
            const [p] = this.nodePagePath.split("`");
            if ((p || "").toLowerCase().endsWith(".mu")) {
                return false;
            }
            return true;
        },
        nomadPageContentClasses() {
            if (!this.nodePagePath || this.isShowingNodePageSource) {
                return ["h-full", "wrap-break-word", "whitespace-pre-wrap", "text-gray-100"];
            }
            const [p] = this.nodePagePath.split("`");
            const pl = (p || "").toLowerCase();
            const isRich = pl.endsWith(".mu") || pl.endsWith(".md") || pl.endsWith(".html");
            const isHtml = pl.endsWith(".html");
            const isMd = pl.endsWith(".md");
            const classes = ["h-full", "wrap-break-word"];
            if (this.nomadRenderedShellFullBleed && !isHtml) {
                classes.push("px-3", "py-3");
            }
            if (isRich) {
                classes.push("nomad-page-rich");
            } else {
                classes.push("whitespace-pre-wrap");
            }
            if (isHtml) {
                classes.push("nomad-page-html-host");
            } else if (pl.endsWith(".mu")) {
                classes.push("text-gray-100");
            } else {
                classes.push("text-gray-900", "dark:text-gray-100");
            }
            if (isMd) {
                classes.push("nomad-markdown-host");
            }
            return classes;
        },
    },
    watch: {
        nomadNetworkSidebarCollapsed(collapsed) {
            saveFeatureSidebarCollapsed("nomadnetwork", collapsed);
        },
        crashTabContentKey() {
            this.loadedPartialIds = {};
            this.crashTabPartials = [];
        },
        nomadRenderedShellFullBleed() {
            this.syncPageShellBackground();
        },
        selectedNode: {
            handler() {
                this.checkIfSelectedNodeBlocked();
            },
            deep: true,
        },
        blockedDestinations: {
            handler() {
                this.checkIfSelectedNodeBlocked();
            },
            deep: true,
        },
    },
    beforeUnmount() {
        if (this.processPartialsRaf != null) {
            cancelAnimationFrame(this.processPartialsRaf);
            this.processPartialsRaf = null;
        }
        if (this.nodesRefreshTimeout) clearTimeout(this.nodesRefreshTimeout);
        clearInterval(this.reloadInterval);
        this.nodesListAbortController?.abort();
        this.nodeDetailAbortController?.abort();
        this.clearPartials();
        this.teardownMultilineExpansion();

        offWsEvent("announce", this.onNomadAnnounceEvent);
        offWsEvent("nomadnet.page.download", this.onNomadPageDownloadEvent);
        offWsEvent("nomadnet.file.download", this.onNomadFileDownloadEvent);
        offWsEvent("nomadnet.download.cancelled", this.onNomadDownloadCancelledEvent);
        offWsEvent("nomadnet.page.archives", this.onNomadPageArchivesEvent);
        offWsEvent("nomadnet.page.archive.added", this.onNomadPageArchiveAddedEvent);
        GlobalEmitter.off("identity-switched", this.onIdentitySwitched);
        GlobalEmitter.off(MICRON_WASM_OVERRIDE_CHANGED_EVENT, this.refreshMicronWasmReleaseLabel);
    },
    mounted() {
        // listen for websocket messages
        onWsEvent("announce", this.onNomadAnnounceEvent);
        onWsEvent("nomadnet.page.download", this.onNomadPageDownloadEvent);
        onWsEvent("nomadnet.file.download", this.onNomadFileDownloadEvent);
        onWsEvent("nomadnet.download.cancelled", this.onNomadDownloadCancelledEvent);
        onWsEvent("nomadnet.page.archives", this.onNomadPageArchivesEvent);
        onWsEvent("nomadnet.page.archive.added", this.onNomadPageArchiveAddedEvent);
        GlobalEmitter.on("identity-switched", this.onIdentitySwitched);
        GlobalEmitter.on(MICRON_WASM_OVERRIDE_CHANGED_EVENT, this.refreshMicronWasmReleaseLabel);
        this.refreshMicronWasmReleaseLabel();

        this.$watch(
            () => GlobalState.config?.nomad_micron_wasm_enabled,
            async (enabled) => {
                if (!isMicronWasmBundled()) {
                    this.nomadMicronWasmReady = false;
                    return;
                }
                if (!enabled) {
                    this.nomadMicronWasmReady = false;
                    return;
                }
                invalidateNomadMicronWasmPreload();
                this.nomadMicronWasmReady = await preloadNomadMicronWasm();
            }
        );

        this.$watch(
            () => GlobalState.config?.nomad_micron_default_engine,
            () => {
                if (this.nodePageContent && this.nodePagePathIsMicronMu) {
                    const content = this.nodePageContent;
                    this.nodePageContent = null;
                    this.$nextTick(() => {
                        this.nodePageContent = content;
                        this.beginCrashTabRenderWait();
                    });
                }
            }
        );

        if (isMicronWasmBundled() && GlobalState.config?.nomad_micron_wasm_enabled === true) {
            preloadNomadMicronWasm().then((ok) => {
                this.nomadMicronWasmReady = ok === true;
            });
        }

        // load nomadnetwork node if a destination hash was provided on page load
        const bootstrapHash = (this.destinationHash || "").trim();
        if (bootstrapHash) {
            const bootstrapPath = this.embedded ? this.initialPath : this.$route.query.path;
            const bootstrapArchiveId = this.embedded ? null : this.$route.query.archive_id;
            (async () => {
                await this.getNomadnetworkNodeAnnounce(bootstrapHash);

                this.selectedNode = this.resolveNodeForHash(bootstrapHash);

                this.getNodePath(bootstrapHash);

                if (bootstrapArchiveId) {
                    await this.loadArchivedPage(bootstrapArchiveId);
                } else if (bootstrapPath) {
                    await this.onNodePageUrlClick(`${bootstrapHash}:${bootstrapPath}`);
                } else {
                    await this.onNodePageUrlClick(`${bootstrapHash}:${this.defaultNodePagePath}`);
                }
            })();
        }

        this.getFavourites();
        this.getNomadnetworkNodeAnnounces();

        // update info every few seconds
        this.reloadInterval = setInterval(() => {
            if (this.shouldPollFavourites()) {
                this.getFavourites();
            }
        }, 5000);

        this.$nextTick(() => this.scheduleProcessPartials());
    },
    methods: {
        shouldPollFavourites() {
            return shouldPollKeepAliveEmbedded(this.embedded, this.isActive);
        },
        onIdentitySwitched() {
            this.favourites = [];
            this.nodePageCache = {};
            this.nodes = {};
            this.selectedNode = null;
            this.nodePageContent = null;
            this.clearPartials?.();
            this.getFavourites();
            this.getNomadnetworkNodeAnnounces();
        },
        async refreshMicronWasmReleaseLabel() {
            if (!isMicronWasmBundled()) {
                this.micronWasmReleaseLabel = null;
                return;
            }
            this.micronWasmReleaseLabel = await getEffectiveMicronWasmReleaseLabel();
        },
        getEmbeddedTabStateHash() {
            return (this.selectedNode?.destination_hash || "").trim();
        },
        async restoreEmbeddedTabState(destinationHash, pagePath = null) {
            const hash = (destinationHash || "").trim();
            if (!this.embedded || !hash) {
                return;
            }
            try {
                await this.getNomadnetworkNodeAnnounce(hash);
                this.selectedNode = this.resolveNodeForHash(hash);
                const path = typeof pagePath === "string" && pagePath.length > 0 ? pagePath : this.defaultNodePagePath;
                await this.loadNodePage(hash, path, null, false, true);
            } catch (e) {
                console.error(e);
                ToastUtils.error(this.$t("nomadnet.tab_restore_failed"));
            }
        },
        ownsNomadPageDownloadEvent(nomadnetPageDownload, downloadId) {
            const responsePagePath = `${nomadnetPageDownload.destination_hash}:${nomadnetPageDownload.page_path}`;
            const callbackKey = this.getNomadnetPageDownloadCallbackKey(
                nomadnetPageDownload.destination_hash,
                nomadnetPageDownload.page_path
            );
            if (this.nomadnetPageDownloadCallbacks[callbackKey]) {
                return true;
            }
            if (this.currentPageDownloadId !== null && this.currentPageDownloadId === downloadId) {
                return true;
            }
            if (!this.nodePagePath || this.nodePagePath !== responsePagePath) {
                return false;
            }
            if (this.isLoadingNodePage) {
                return true;
            }
            return !this.embedded || this.isActive;
        },
        ownsNomadFileDownloadEvent(nomadnetFileDownload, downloadId) {
            const callbackKey = this.getNomadnetFileDownloadCallbackKey(
                nomadnetFileDownload.destination_hash,
                nomadnetFileDownload.file_path
            );
            if (this.nomadnetFileDownloadCallbacks[callbackKey]) {
                return true;
            }
            if (this.currentFileDownloadId !== null && this.currentFileDownloadId === downloadId) {
                return true;
            }
            return !this.embedded || this.isActive;
        },
        /**
         * Returns true if the given page content represents a failed load.
         * Matches the explicit "request_failed" sentinel and the user-facing
         * "Failed loading page: ..." string set when a download callback fires
         * with a failure reason (e.g. "Could not establish link to destination.").
         */
        isFailedPageContent(content) {
            if (content == null) {
                return false;
            }
            if (content === "request_failed") {
                return true;
            }
            if (typeof content !== "string") {
                return false;
            }
            return content.startsWith("Failed loading page:");
        },
        /**
         * Cancelled downloads use a stable sentinel so the crash-tab renderer
         * never mounts an empty white iframe for status text.
         */
        isCancelledPageContent(content) {
            if (content == null || typeof content !== "string") {
                return false;
            }
            if (content === "page_download_cancelled") {
                return true;
            }
            try {
                return content === this.$t("nomadnet.page_download_cancelled");
            } catch {
                return false;
            }
        },
        applyPageDownloadCancelledUi() {
            this.pageRenderAborted = false;
            this.isCrashTabRendering = false;
            this.isLoadingNodePage = false;
            this.nodePageLoadPhase = null;
            this.nodePageProgress = 0;
            this.nodePageContent = "page_download_cancelled";
        },
        async applyNomadMicronDefaultEngine(engine) {
            if (!isMicronWasmBundled()) {
                return;
            }
            if (!GlobalState.config?.nomad_micron_wasm_enabled) {
                return;
            }
            const next = engine === "wasm" ? "wasm" : "js";
            if ((GlobalState.config?.nomad_micron_default_engine || "js") === next) {
                return;
            }
            try {
                const cfg = await patchServerConfig({ nomad_micron_default_engine: next }, window.api);
                mergeGlobalConfig(cfg);
                if (this.nodePageContent && this.nodePagePathIsMicronMu) {
                    const content = this.nodePageContent;
                    this.nodePageContent = null;
                    this.$nextTick(() => {
                        this.nodePageContent = content;
                        this.beginCrashTabRenderWait();
                    });
                }
            } catch (e) {
                console.error("Failed to update Micron default engine", e);
                ToastUtils.error(this.$t("nomadnet.renderer_setting_failed"));
            }
        },
        scheduleProcessPartials() {
            if (this.processPartialsRaf != null) {
                cancelAnimationFrame(this.processPartialsRaf);
            }
            this.processPartialsRaf = requestAnimationFrame(() => {
                this.processPartialsRaf = null;
                this.processPartials();
            });
        },
        teardownMultilineExpansion() {
            if (typeof this.multilineCleanup === "function") {
                try {
                    this.multilineCleanup();
                } catch (e) {
                    console.warn("nomadnet: multiline cleanup failed", e);
                }
            }
            this.multilineCleanup = null;
            this.multilineHintVisible = false;
        },
        refreshMultilineExpansion() {
            this.teardownMultilineExpansion();
            if (this.isShowingNodePageSource) return;
            if (this.nomadMicronWasmActive) return;
            const path = this.nodePagePath || "";
            const [pagePathWithoutData] = path.split("`");
            if (!pagePathWithoutData.toLowerCase().endsWith(".mu")) return;
            const container = this.$el?.querySelector?.(".nodeContainer");
            if (!container) return;
            const onArmed = (e) => {
                e.detail?.element?.classList?.add("Mu-armed");
                this.multilineHintVisible = true;
            };
            const onDisarmed = (e) => {
                e.detail?.element?.classList?.remove("Mu-armed");
                this.multilineHintVisible = false;
            };
            const onExpanded = (e) => {
                e.detail?.element?.classList?.add("Mu-multiline");
                this.multilineHintVisible = false;
            };
            container.addEventListener("micron-multiline-armed", onArmed);
            container.addEventListener("micron-multiline-disarmed", onDisarmed);
            container.addEventListener("micron-field-multiline-enabled", onExpanded);
            const detach = MicronParser.enableDoubleEnterMultiline(container, {
                windowMs: 500,
                rows: 4,
            });
            this.multilineCleanup = () => {
                container.removeEventListener("micron-multiline-armed", onArmed);
                container.removeEventListener("micron-multiline-disarmed", onDisarmed);
                container.removeEventListener("micron-field-multiline-enabled", onExpanded);
                if (typeof detach === "function") detach();
            };
        },
        openNomadnetPopout() {
            if (this.isPrivate || !this.selectedNode) {
                return;
            }
            const destinationHash = this.selectedNode.destination_hash || "";
            const encodedHash = encodeURIComponent(destinationHash);
            const url = `${window.location.origin}${window.location.pathname}#/popout/nomadnetwork/${encodedHash}`;
            window.open(url, "_blank", "width=1100,height=800,noopener");
        },
        checkIfSelectedNodeBlocked() {
            if (!this.selectedNode) {
                this.isSelectedNodeBlocked = false;
                return;
            }
            const identityHash = this.selectedNode.identity_hash || this.selectedNode.destination_hash;
            this.isSelectedNodeBlocked = GlobalState.blockedDestinations.some(
                (b) => b.destination_hash === identityHash
            );
        },
        getLinkNavOptions(event) {
            const modifierClick = event.ctrlKey || event.metaKey;
            const middleClick = event.button === 1;
            return {
                forceNewTab: modifierClick || middleClick,
                activate: !modifierClick && !middleClick,
            };
        },
        shouldOpenInNewTab(destinationHash, navOptions = {}) {
            if (!this.embedded || !this.tabsEnabled) {
                return false;
            }
            if (navOptions.forceNewTab) {
                return true;
            }
            if (!destinationHash || !this.destinationHash) {
                return false;
            }
            return destinationHash !== this.destinationHash;
        },
        emitOpenNode(destinationHash, pagePath, title = null, navOptions = {}) {
            this.$emit("open-node", {
                destinationHash,
                pagePath,
                title,
                activate: navOptions.activate !== false,
                forceNewTab: navOptions.forceNewTab === true,
            });
        },
        onElementClick(event) {
            handleRichHtmlLinkClick(event, {
                onNomadUrl: (url) => {
                    this.onNodePageUrlClick(url, null, true, false, this.getLinkNavOptions(event));
                },
                onLxmfAddress: (address) => {
                    const routeName = this.isPopoutMode ? "messages-popout" : "messages";
                    this.$router.push({
                        name: routeName,
                        params: { destinationHash: address },
                    });
                },
                onOpenNode: (destination, fields) => {
                    this.onNodePageUrlClick(destination, fields, true, false, this.getLinkNavOptions(event));
                },
            });
        },
        onNomadAnnounceEvent(json) {
            if (json?.announce?.aspect === "nomadnetwork.node") {
                this.updateNodeFromAnnounce(json.announce);
            }
        },
        async onWebsocketMessage(message) {
            const raw = typeof message === "string" ? message : message?.data;
            const json = typeof raw === "string" ? JSON.parse(raw) : message;
            await this._handleNomadWsPayload(json);
        },
        async onNomadPageDownloadEvent(json) {
            await this._handleNomadWsPayload({ ...json, type: "nomadnet.page.download" });
        },
        async onNomadFileDownloadEvent(json) {
            await this._handleNomadWsPayload({ ...json, type: "nomadnet.file.download" });
        },
        onNomadDownloadCancelledEvent(json) {
            return this._handleNomadWsPayload({ ...json, type: "nomadnet.download.cancelled" });
        },
        onNomadPageArchivesEvent(json) {
            return this._handleNomadWsPayload({ ...json, type: "nomadnet.page.archives" });
        },
        onNomadPageArchiveAddedEvent(json) {
            return this._handleNomadWsPayload({ ...json, type: "nomadnet.page.archive.added" });
        },
        async _handleNomadWsPayload(json) {
            switch (json.type) {
                case "announce": {
                    const aspect = json.announce.aspect;
                    if (aspect === "nomadnetwork.node") {
                        this.updateNodeFromAnnounce(json.announce);
                    }
                    break;
                }
                case "nomadnet.page.download": {
                    let nomadnetPageDownload = json.nomadnet_page_download;
                    const downloadId = json.download_id;

                    if (!this.ownsNomadPageDownloadEvent(nomadnetPageDownload, downloadId)) {
                        break;
                    }

                    if (nomadnetPageDownload.status === "chunk") {
                        this.appendDownloadChunk(this.nomadPageDownloadChunkBuffers, downloadId, nomadnetPageDownload);
                        break;
                    }

                    if (nomadnetPageDownload.status === "success" && nomadnetPageDownload.chunked) {
                        nomadnetPageDownload = {
                            ...nomadnetPageDownload,
                            page_content: this.consumeDownloadChunksAsText(
                                this.nomadPageDownloadChunkBuffers,
                                downloadId
                            ),
                        };
                    }

                    const responsePagePath = `${nomadnetPageDownload.destination_hash}:${nomadnetPageDownload.page_path}`;

                    if (nomadnetPageDownload.status === "success" && nomadnetPageDownload.is_archived_version) {
                        this.nodePagePath = responsePagePath;
                        this.nodePagePathUrlInput = responsePagePath;
                        this.isShowingArchivedVersion = true;
                        this.archivedAt = nomadnetPageDownload.archived_at;
                        this.nodePageContent = nomadnetPageDownload.page_content;
                        this.nodePageProgress = 100;
                        this.isLoadingNodePage = false;
                        this.beginCrashTabRenderWait();
                        this.nodePageLoadPhase = null;
                        this.currentPageDownloadId = null;
                        {
                            const pc = nomadnetPageDownload.page_content || "";
                            this.lastPageLoadDurationMs =
                                this.pageLoadStartedAt != null ? Date.now() - this.pageLoadStartedAt : 0;
                            this.lastPageContentBytes = new TextEncoder().encode(pc).length;
                        }
                        this.fetchArchives();
                        return;
                    }

                    if (
                        nomadnetPageDownload.status === "failure" &&
                        this.isLoadingNodePage &&
                        this.currentPageDownloadId === downloadId &&
                        !this.nomadnetPageDownloadCallbacks[
                            this.getNomadnetPageDownloadCallbackKey(
                                nomadnetPageDownload.destination_hash,
                                nomadnetPageDownload.page_path
                            )
                        ]
                    ) {
                        this.isLoadingNodePage = false;
                        this.nodePageLoadPhase = null;
                        this.currentPageDownloadId = null;
                        this.nodePageProgress = 0;
                        ToastUtils.error(this.$t("nomadnet.failed_to_load_page"));
                        this.nodePageContent = `Failed loading page: ${
                            nomadnetPageDownload.failure_reason || "archive not found"
                        }`;
                        return;
                    }

                    // ignore response if it's for a different page than currently requested/viewed
                    // but allow responses for partial pages (they have registered callbacks)
                    if (this.nodePagePath && responsePagePath !== this.nodePagePath) {
                        const callbackKey = this.getNomadnetPageDownloadCallbackKey(
                            nomadnetPageDownload.destination_hash,
                            nomadnetPageDownload.page_path
                        );
                        if (!this.nomadnetPageDownloadCallbacks[callbackKey]) {
                            return;
                        }
                    }

                    if (nomadnetPageDownload.status === "started") {
                        const startedCallbackKey = this.getNomadnetPageDownloadCallbackKey(
                            nomadnetPageDownload.destination_hash,
                            nomadnetPageDownload.page_path
                        );
                        const startedCallback = this.nomadnetPageDownloadCallbacks[startedCallbackKey];
                        if (!startedCallback) {
                            break;
                        }
                        if (this.pendingNomadPageCancelWithoutId && startedCallback.primary) {
                            this.pendingNomadPageCancelWithoutId = false;
                            WebSocketConnection.send(
                                JSON.stringify({
                                    type: "nomadnet.download.cancel",
                                    download_id: downloadId,
                                })
                            );
                            return;
                        }
                        // Partials must not steal currentPageDownloadId from the main page load.
                        if (startedCallback.primary) {
                            this.currentPageDownloadId = downloadId;
                        }
                        return;
                    }

                    if (nomadnetPageDownload.status === "phase") {
                        if (this.currentPageDownloadId !== downloadId) {
                            return;
                        }
                        if (this.nodePagePath && responsePagePath !== this.nodePagePath) {
                            return;
                        }
                        this.nodePageLoadPhase = nomadnetPageDownload.load_phase || null;
                        return;
                    }

                    // find download callbacks
                    const getNomadnetPageDownloadCallbackKey = this.getNomadnetPageDownloadCallbackKey(
                        nomadnetPageDownload.destination_hash,
                        nomadnetPageDownload.page_path
                    );
                    const nomadnetPageDownloadCallback =
                        this.nomadnetPageDownloadCallbacks[getNomadnetPageDownloadCallbackKey];

                    // if no callback found for other statuses, return
                    if (!nomadnetPageDownloadCallback) {
                        return;
                    }

                    // handle success
                    if (nomadnetPageDownload.status === "success") {
                        if (nomadnetPageDownloadCallback.onSuccessCallback) {
                            nomadnetPageDownloadCallback.onSuccessCallback(nomadnetPageDownload.page_content);
                        }
                        delete this.nomadnetPageDownloadCallbacks[getNomadnetPageDownloadCallbackKey];
                        if (this.currentPageDownloadId === downloadId) {
                            this.currentPageDownloadId = null;
                        }
                        return;
                    }

                    // handle failure
                    if (nomadnetPageDownload.status === "failure" && nomadnetPageDownloadCallback.onFailureCallback) {
                        this.hasArchivesForCurrentPage = this.isPrivate ? false : nomadnetPageDownload.has_archives;
                        nomadnetPageDownloadCallback.onFailureCallback(nomadnetPageDownload.failure_reason);
                        delete this.nomadnetPageDownloadCallbacks[getNomadnetPageDownloadCallbackKey];
                        if (this.currentPageDownloadId === downloadId) {
                            this.currentPageDownloadId = null;
                        }
                        return;
                    }

                    // handle progress
                    if (nomadnetPageDownload.status === "progress" && nomadnetPageDownloadCallback.onProgressCallback) {
                        nomadnetPageDownloadCallback.onProgressCallback(nomadnetPageDownload.progress);
                        return;
                    }

                    break;
                }
                case "nomadnet.file.download": {
                    let nomadnetFileDownload = json.nomadnet_file_download;
                    const downloadId = json.download_id;

                    if (!this.ownsNomadFileDownloadEvent(nomadnetFileDownload, downloadId)) {
                        break;
                    }

                    if (nomadnetFileDownload.status === "chunk") {
                        this.appendDownloadChunk(this.nomadFileDownloadChunkBuffers, downloadId, nomadnetFileDownload);
                        break;
                    }

                    if (nomadnetFileDownload.status === "success" && nomadnetFileDownload.chunked) {
                        nomadnetFileDownload = {
                            ...nomadnetFileDownload,
                            file_bytes: this.consumeDownloadChunksAsBase64(
                                this.nomadFileDownloadChunkBuffers,
                                downloadId
                            ),
                        };
                    }

                    if (nomadnetFileDownload.status === "started") {
                        const fileCallbackKey = this.getNomadnetFileDownloadCallbackKey(
                            nomadnetFileDownload.destination_hash,
                            nomadnetFileDownload.file_path
                        );
                        if (!this.nomadnetFileDownloadCallbacks[fileCallbackKey]) {
                            break;
                        }
                        this.currentFileDownloadId = downloadId;
                        return;
                    }

                    // find download callbacks
                    const getNomadnetFileDownloadCallbackKey = this.getNomadnetFileDownloadCallbackKey(
                        nomadnetFileDownload.destination_hash,
                        nomadnetFileDownload.file_path
                    );
                    const nomadnetFileDownloadCallback =
                        this.nomadnetFileDownloadCallbacks[getNomadnetFileDownloadCallbackKey];
                    if (!nomadnetFileDownloadCallback) {
                        console.log(
                            "did not find nomadnet file download callback for key: " +
                                getNomadnetFileDownloadCallbackKey
                        );
                        return;
                    }

                    // handle success
                    if (nomadnetFileDownload.status === "success" && nomadnetFileDownloadCallback.onSuccessCallback) {
                        nomadnetFileDownloadCallback.onSuccessCallback(
                            nomadnetFileDownload.file_name,
                            nomadnetFileDownload.file_bytes
                        );
                        delete this.nomadnetFileDownloadCallbacks[getNomadnetFileDownloadCallbackKey];
                        this.currentFileDownloadId = null;
                        return;
                    }

                    // handle failure
                    if (nomadnetFileDownload.status === "failure" && nomadnetFileDownloadCallback.onFailureCallback) {
                        nomadnetFileDownloadCallback.onFailureCallback(nomadnetFileDownload.failure_reason);
                        delete this.nomadnetFileDownloadCallbacks[getNomadnetFileDownloadCallbackKey];
                        this.currentFileDownloadId = null;
                        return;
                    }

                    // handle progress
                    if (nomadnetFileDownload.status === "progress" && nomadnetFileDownloadCallback.onProgressCallback) {
                        nomadnetFileDownloadCallback.onProgressCallback(nomadnetFileDownload.progress);
                        return;
                    }

                    break;
                }
                case "nomadnet.download.cancelled": {
                    // handle download cancellation
                    const downloadId = json.download_id;

                    // clear page download if it matches
                    if (this.currentPageDownloadId === downloadId) {
                        this.currentPageDownloadId = null;
                        this.pendingNomadPageCancelWithoutId = false;
                        this.applyPageDownloadCancelledUi();
                    } else if (this.isCancelledPageContent(this.nodePageContent)) {
                        this.pendingNomadPageCancelWithoutId = false;
                    }

                    // clear file download if it matches
                    if (this.currentFileDownloadId === downloadId) {
                        this.currentFileDownloadId = null;
                        this.isDownloadingNodeFile = false;
                        this.nodeFileDownloadSpeed = null;
                    }

                    break;
                }
                case "nomadnet.page.archives": {
                    const currentRelativePath = this.nodePagePath?.includes(":")
                        ? this.nodePagePath.split(":").slice(1).join(":")
                        : this.nodePagePath;

                    if (
                        this.selectedNode &&
                        json.destination_hash === this.selectedNode.destination_hash &&
                        (json.page_path === this.nodePagePath || json.page_path === currentRelativePath)
                    ) {
                        this.pageArchives = json.archives;
                        this.isLoadingArchives = false;

                        if (this.pendingLoadLatestArchive) {
                            this.pendingLoadLatestArchive = false;
                            if (this.pageArchives.length > 0) {
                                this.loadArchivedPage(this.pageArchives[0].id);
                            } else {
                                ToastUtils.info(this.$t("nomadnet.no_archives_for_this_page"));
                            }
                        }
                    }
                    break;
                }
                case "nomadnet.page.archive.added": {
                    const currentRelativePath = this.nodePagePath?.includes(":")
                        ? this.nodePagePath.split(":").slice(1).join(":")
                        : this.nodePagePath;

                    if (
                        this.selectedNode &&
                        json.destination_hash === this.selectedNode.destination_hash &&
                        (json.page_path === this.nodePagePath || json.page_path === currentRelativePath)
                    ) {
                        ToastUtils.success(this.$t("nomadnet.page_archived_successfully"));
                        this.fetchArchives();
                    }
                    break;
                }
            }
        },
        onDestinationPathClick: function (path) {
            ToastUtils.info(
                `${path.hops} ${path.hops === 1 ? this.$t("app.hop") : this.$t("app.hops_plural")} away via ${path.next_hop_interface}`
            );
        },
        async getFavourites() {
            try {
                const response = await window.api.get("/api/v1/favourites", {
                    params: {
                        aspect: "nomadnetwork.node",
                    },
                });
                this.favourites = response.data.favourites;
            } catch (e) {
                // do nothing if failed to load favourites
                console.log(e);
            }
        },
        isUnknownNodeName(name) {
            return isUnknownNodeDisplayName(name, this.$t("nomadnet.unknown_node"));
        },
        resolveNodeForHash(destinationHash) {
            const hash = (destinationHash || "").trim();
            if (!hash) {
                return null;
            }
            const cached = this.nodes[hash];
            const favourite = this.favourites.find((f) => f.destination_hash === hash);
            const favouriteName = favourite?.custom_display_name || favourite?.display_name || "";
            if (cached) {
                const cachedName = cached.custom_display_name || cached.display_name || "";
                if (this.isUnknownNodeName(cachedName) && favouriteName && !this.isUnknownNodeName(favouriteName)) {
                    return {
                        ...cached,
                        display_name: favouriteName,
                        custom_display_name: favourite?.custom_display_name || favouriteName,
                    };
                }
                return cached;
            }
            if (favouriteName && !this.isUnknownNodeName(favouriteName)) {
                return {
                    ...favourite,
                    display_name: favouriteName,
                    aspect: favourite.aspect || "nomadnetwork.node",
                };
            }
            const selectedHash = this.selectedNode?.destination_hash;
            if (selectedHash && Object.is(selectedHash, hash)) {
                const existingName = this.selectedNode.custom_display_name || this.selectedNode.display_name;
                if (existingName && !this.isUnknownNodeName(existingName)) {
                    return this.selectedNode;
                }
            }
            return {
                destination_hash: hash,
                display_name: this.$t("nomadnet.unknown_node"),
                aspect: "nomadnetwork.node",
            };
        },
        isFavourite(destinationHash) {
            return (
                this.favourites.find((favourite) => {
                    return favourite.destination_hash === destinationHash;
                }) != null
            );
        },
        identifiesOnConnect(destinationHash) {
            const favourite = this.favourites.find((f) => f.destination_hash === destinationHash);
            return Boolean(favourite?.identify_on_connect);
        },
        async addFavourite(node) {
            if (this.isPrivate) {
                return false;
            }
            try {
                const existing = this.favourites.find(
                    (favourite) => favourite.destination_hash === node.destination_hash
                );
                const displayName = resolveFavouriteUpsertDisplayName(node, existing, this.$t("nomadnet.unknown_node"));
                await window.api.post("/api/v1/favourites/add", {
                    destination_hash: node.destination_hash,
                    display_name: displayName,
                    aspect: "nomadnetwork.node",
                });
                await this.getFavourites();
                return true;
            } catch (e) {
                console.log(e);
                return false;
            }
        },
        async removeFavourite(node) {
            if (this.isPrivate) {
                return false;
            }
            try {
                await window.api.delete(`/api/v1/favourites/${node.destination_hash}`);
                await this.getFavourites();
                return true;
            } catch (e) {
                console.log(e);
                return false;
            }
        },
        async onBulkRemoveFavourites(hashes) {
            if (!Array.isArray(hashes) || hashes.length === 0) {
                return;
            }
            let removed = 0;
            for (const h of hashes) {
                try {
                    await window.api.delete(`/api/v1/favourites/${h}`);
                    removed += 1;
                } catch (e) {
                    console.log(e);
                }
            }
            await this.getFavourites();
            if (removed > 0) {
                ToastUtils.success(this.$t("nomadnet.bulk_remove_favourites_done", { count: removed }));
            }
        },
        async onBulkAddFavouritesFromAnnounces(nodes) {
            if (!Array.isArray(nodes) || nodes.length === 0) {
                return;
            }
            let added = 0;
            for (const node of nodes) {
                if (this.isFavourite(node.destination_hash)) {
                    continue;
                }
                try {
                    const displayName = resolveFavouriteUpsertDisplayName(node, null, this.$t("nomadnet.unknown_node"));
                    await window.api.post("/api/v1/favourites/add", {
                        destination_hash: node.destination_hash,
                        display_name: displayName,
                        aspect: "nomadnetwork.node",
                    });
                    added += 1;
                } catch (e) {
                    console.log(e);
                }
            }
            await this.getFavourites();
            if (added > 0) {
                ToastUtils.success(this.$t("nomadnet.bulk_add_favourites_done", { count: added }));
            }
        },
        async getNomadnetworkNodeAnnounces(append = false) {
            // capture the controller that belongs to *this* call so a later,
            // superseding call can't have its own finally block clear the
            // loading state for an in-flight search out from under it.
            let myController = this.nodesListAbortController;
            try {
                if (!append) {
                    if (this.nodesListAbortController) {
                        this.nodesListAbortController.abort();
                    }
                    this.nodesListAbortController = new AbortController();
                    myController = this.nodesListAbortController;
                    this.isSearchingNodes = true;
                } else if (!this.nodesListAbortController) {
                    this.nodesListAbortController = new AbortController();
                    myController = this.nodesListAbortController;
                }
                const offset = append ? Object.keys(this.nodes).length : 0;
                const response = await window.api.get(`/api/v1/announces`, {
                    params: {
                        aspect: "nomadnetwork.node",
                        limit: this.pageSize,
                        offset: offset,
                        search: this.nodesSearchTerm,
                    },
                    signal: myController.signal,
                });

                const nodeAnnounces = response.data.announces;
                if (!append) {
                    this.nodes = {};
                }

                this.totalNodesCount = response.data.total_count || 0;

                for (const nodeAnnounce of nodeAnnounces) {
                    this.updateNodeFromAnnounce(nodeAnnounce);
                }

                this.hasMoreNodes = nodeAnnounces.length === this.pageSize;
            } catch (e) {
                if (window.api.isCancel?.(e)) return;
                console.log(e);
            } finally {
                this.isLoadingMoreNodes = false;
                if (!append && this.nodesListAbortController === myController) {
                    this.isSearchingNodes = false;
                }
            }
        },
        async loadMoreNodes() {
            if (this.isLoadingMoreNodes || !this.hasMoreNodes) return;
            this.isLoadingMoreNodes = true;
            await this.getNomadnetworkNodeAnnounces(true);
        },
        onNodesSearchChanged(term) {
            this.nodesSearchTerm = term;
            this.isSearchingNodes = true;
            if (this.nodesRefreshTimeout) {
                clearTimeout(this.nodesRefreshTimeout);
            }
            this.nodesRefreshTimeout = setTimeout(() => {
                this.getNomadnetworkNodeAnnounces();
            }, 500);
        },
        async getNomadnetworkNodeAnnounce(destinationHash) {
            try {
                if (this.nodeDetailAbortController) {
                    this.nodeDetailAbortController.abort();
                }
                this.nodeDetailAbortController = new AbortController();
                const response = await window.api.get(`/api/v1/announces`, {
                    params: {
                        destination_hash: destinationHash,
                        limit: 1,
                    },
                    signal: this.nodeDetailAbortController.signal,
                });

                const nodeAnnounces = response.data.announces;
                for (const nodeAnnounce of nodeAnnounces) {
                    this.updateNodeFromAnnounce(nodeAnnounce);
                }
            } catch (e) {
                if (window.api.isCancel?.(e)) return;
                console.log(e);
            }
        },
        updateNodeFromAnnounce: function (announce) {
            this.nodes[announce.destination_hash] = announce;
        },
        async openUrl() {
            // ask for url
            const url = await DialogUtils.prompt(this.$t("nomadnet.enter_nomadnet_url"));
            if (!url) {
                return;
            }

            // navigate to the url
            await this.onNodePageUrlClick(url);
        },
        async loadNodePage(
            destinationHash,
            pagePath,
            fieldData = null,
            addToHistory = true,
            loadFromCache = true,
            navOptions = {}
        ) {
            if (this.shouldOpenInNewTab(destinationHash, navOptions)) {
                this.emitOpenNode(
                    destinationHash,
                    pagePath,
                    this.selectedNode?.custom_display_name || this.selectedNode?.display_name || null,
                    navOptions
                );
                return;
            }

            // update current route (skipped while embedded, as the browser shell owns routing)
            if (this.embedded) {
                this.$emit("navigate", {
                    destinationHash: destinationHash,
                    pagePath: pagePath,
                    title: this.selectedNode?.custom_display_name || this.selectedNode?.display_name || null,
                });
            } else if (!this.isPrivate) {
                const routeName = this.isPopoutMode ? "nomadnetwork-popout" : "nomadnetwork";
                const routeOptions = {
                    name: routeName,
                    params: {
                        destinationHash: destinationHash,
                    },
                };
                if (!this.isPopoutMode && this.$route?.query) {
                    routeOptions.query = { ...this.$route.query };
                }
                this.$router.replace(routeOptions);
            } else if (this.$route?.params?.destinationHash || this.$route?.query?.path) {
                // Private non-embedded: strip any leaked hash/path from the URL bar.
                const routeName = this.isPopoutMode ? "nomadnetwork-popout" : "nomadnetwork";
                const routeOptions = { name: routeName, params: {} };
                if (!this.isPopoutMode && this.$route?.query) {
                    routeOptions.query = { ...this.$route.query };
                    delete routeOptions.query.path;
                    delete routeOptions.query.archive_id;
                    delete routeOptions.query.newTab;
                }
                this.$router.replace(routeOptions);
            }

            // get new sequence for this page load
            const seq = ++this.nodePageRequestSequence;

            this.pendingNomadPageCancelWithoutId = false;
            this.pageRenderAborted = false;
            this.isCrashTabRendering = false;

            // get previous page path
            const previousNodePagePath = this.nodePagePath;

            // update ui
            this.isLoadingNodePage = true;
            this.isShowingArchivedVersion = false;
            this.archivedAt = null;
            this.nodePagePath = `${destinationHash}:${pagePath}`;
            this.nodePageContent = null;
            this.pageArchives = [];
            this.nodePageProgress = 0;
            this.nodePageLoadPhase = null;
            this.pageLoadStartedAt = Date.now();
            this.lastPageLoadDurationMs = null;
            this.lastPageContentBytes = null;
            this.clearPartials();

            // update url bar
            this.nodePagePathUrlInput = this.nodePagePath;

            // update node path
            this.getNodePath(destinationHash);

            // add to previous page to history if we are not loading that previous page
            if (addToHistory && previousNodePagePath != null && previousNodePagePath !== this.nodePagePath) {
                this.nodePagePathHistory.push(previousNodePagePath);
            }

            // check if we can load this page from the cache (never in private browse)
            if (loadFromCache && !this.isPrivate) {
                // load from cache
                const nodePagePathCacheKey = `${destinationHash}:${pagePath}`;
                const cachedNodePageContent = this.nodePageCache[nodePagePathCacheKey];

                // if page is cache, we can just return it now
                if (cachedNodePageContent != null) {
                    this.nodePageContent = cachedNodePageContent;
                    this.isLoadingNodePage = false;
                    this.beginCrashTabRenderWait();
                    this.nodePageLoadPhase = null;
                    this.lastPageLoadDurationMs = 0;
                    this.lastPageContentBytes = new TextEncoder().encode(cachedNodePageContent).length;
                    this.fetchArchives();
                    return;
                }
            }

            this.downloadNomadNetPage(
                destinationHash,
                pagePath,
                fieldData,
                (pageContent) => {
                    // do nothing if callback is for a previous request
                    if (seq !== this.nodePageRequestSequence) {
                        return;
                    }

                    // update page content
                    this.nodePageContent = pageContent;

                    // update cache (never for private browse)
                    if (!this.isPrivate) {
                        const nodePagePathCacheKey = `${destinationHash}:${pagePath}`;
                        this.nodePageCache[nodePagePathCacheKey] = this.nodePageContent;
                    }

                    // update status
                    this.isLoadingNodePage = false;
                    this.beginCrashTabRenderWait();
                    this.nodePageLoadPhase = null;
                    if (this.pageLoadStartedAt != null) {
                        this.lastPageLoadDurationMs = Date.now() - this.pageLoadStartedAt;
                    }
                    this.lastPageContentBytes = new TextEncoder().encode(pageContent).length;

                    // update node path
                    this.getNodePath(destinationHash);

                    // check if this page has archives
                    this.fetchArchives();
                },
                (failureReason) => {
                    // do nothing if callback is for a previous request
                    if (seq !== this.nodePageRequestSequence) {
                        return;
                    }

                    // update page content
                    this.nodePageContent = `Failed loading page: ${failureReason}`;
                    this.isLoadingNodePage = false;
                    this.nodePageLoadPhase = null;
                    this.lastPageLoadDurationMs = null;
                    this.lastPageContentBytes = null;

                    // update node path
                    this.getNodePath(destinationHash);
                },
                (progress) => {
                    // do nothing if callback is for a previous request
                    if (seq !== this.nodePageRequestSequence) {
                        return;
                    }

                    // update page content
                    this.nodePageProgress = Math.round(progress * 100);
                },
                { primary: true }
            );
        },
        clearPartials() {
            Object.values(this.partialRefreshTimers).forEach((t) => clearTimeout(t));
            this.partialRefreshTimers = {};
            this.pagePartials = {};
            this.loadedPartialIds = {};
            this.partialIdsByKey = {};
            this.partialRefreshByKey = {};
            this.cancelPendingNomadPageSends();
        },
        cancelPendingNomadPageSends() {
            const callbacks = this.nomadnetPageDownloadCallbacks || {};
            for (const key of Object.keys(callbacks)) {
                const entry = callbacks[key];
                if (entry && typeof entry.cancelPendingSend === "function") {
                    entry.cancelPendingSend();
                }
            }
        },
        processPartials() {
            if (!this.selectedNode || !this.nodePagePath || !this.nodePageContent || this.isShowingNodePageSource)
                return;
            const [pagePathWithoutData] = this.nodePagePath.split("`");
            if (!pagePathWithoutData.endsWith(".mu")) return;
            if (!this.nodePageContent.includes("`{")) {
                return;
            }

            const placeholders = this.crashTabPartials || [];
            if (placeholders.length === 0) return;

            // Hostile pages can emit many partials / 1s refresh loops. Cap fan-out
            // and floor refresh so browsing cannot coerce unbounded mesh traffic.
            const MAX_PARTIAL_PLACEHOLDERS = 32;
            const MAX_PARTIAL_FETCHES_PER_PASS = 8;
            const MIN_PARTIAL_REFRESH_SEC = 5;

            const idsByKey = {};
            const refreshByKey = {};
            const needLoad = new Set();

            const fieldsByKey = {};
            let seenPlaceholders = 0;
            placeholders.forEach((el) => {
                if (seenPlaceholders >= MAX_PARTIAL_PLACEHOLDERS) {
                    return;
                }
                seenPlaceholders += 1;
                const id = el.id;
                const dest = el.dest;
                const path = el.path;
                const refreshAttr = el.refresh;
                let refresh = refreshAttr ? parseInt(refreshAttr, 10) : null;
                if (Number.isFinite(refresh) && refresh > 0) {
                    refresh = Math.max(refresh, MIN_PARTIAL_REFRESH_SEC);
                } else {
                    refresh = null;
                }
                const fieldsStr = el.fields;
                const key = dest + ":" + path;
                if (!idsByKey[key]) idsByKey[key] = [];
                idsByKey[key].push({ id, refresh });
                if (refresh != null && refresh > 0) {
                    refreshByKey[key] = Math.min(refreshByKey[key] ?? Infinity, refresh);
                }
                if (fieldsStr && !fieldsByKey[key]) {
                    const fieldData = {};
                    for (const part of fieldsStr.split("|")) {
                        const eq = part.indexOf("=");
                        if (eq > 0) {
                            let name = part.slice(0, eq);
                            if (name.startsWith("field_")) name = name.slice(6);
                            fieldData[name] = part.slice(eq + 1);
                        }
                    }
                    fieldsByKey[key] = fieldData;
                }
                if (!this.loadedPartialIds[id]) needLoad.add(key);
            });

            this.partialIdsByKey = idsByKey;
            this.partialRefreshByKey = refreshByKey;

            const micronOpts = {
                useWasm: this.nomadMicronWasmActive,
            };

            const muParser = new MicronParser();
            const updatePartialDom = (html, ids) => {
                const crashTab = this.$refs.crashTab;
                if (!crashTab || typeof crashTab.setPartialHtml !== "function") {
                    return;
                }
                for (const { id } of ids) {
                    if (id) {
                        crashTab.setPartialHtml(id, html);
                    }
                }
            };
            let fetchBudget = MAX_PARTIAL_FETCHES_PER_PASS;
            needLoad.forEach((key) => {
                if (fetchBudget <= 0) {
                    return;
                }
                fetchBudget -= 1;
                const colon = key.indexOf(":");
                const dest = key.slice(0, colon);
                const path = colon >= 0 ? key.slice(colon + 1) : "";
                const fields = fieldsByKey[key] || [];
                this.downloadNomadNetPage(
                    dest,
                    path,
                    fields,
                    (pageContent) => {
                        let html = muParser.convertMicronToHtml(pageContent, {}, micronOpts);
                        html = isolateNomadLinksInHtml(html, dest);
                        const ids = this.partialIdsByKey[key];
                        if (ids) {
                            updatePartialDom(html, ids);
                            for (const { id } of ids) {
                                if (id) {
                                    this.loadedPartialIds[id] = true;
                                }
                            }
                            this.$nextTick(() => this.scheduleProcessPartials());
                        }
                        const refreshSec = this.partialRefreshByKey[key];
                        if (refreshSec != null && refreshSec > 0) {
                            const scheduleRefresh = () => {
                                this.partialRefreshTimers[key] = setTimeout(() => {
                                    this.downloadNomadNetPage(dest, path, fields, (content) => {
                                        let h = muParser.convertMicronToHtml(content, {}, micronOpts);
                                        h = isolateNomadLinksInHtml(h, dest);
                                        const idList = this.partialIdsByKey[key];
                                        if (idList) {
                                            updatePartialDom(h, idList);
                                            for (const { id } of idList) {
                                                if (id) {
                                                    this.loadedPartialIds[id] = true;
                                                }
                                            }
                                            this.$nextTick(() => this.scheduleProcessPartials());
                                        }
                                        scheduleRefresh();
                                    });
                                }, refreshSec * 1000);
                            };
                            scheduleRefresh();
                        }
                    },
                    () => {}
                );
            });
        },
        syncPageShellBackground() {
            if (!this.nomadRenderedShellFullBleed) {
                this.pageShellBackground = null;
                return;
            }
            // Crash-tab content lives in an opaque iframe. Background comes from
            // the shell-background postMessage, not DOM probing in the parent.
            if (this.$refs.crashTab) {
                return;
            }
            const container = this.$el?.querySelector?.(".nodeContainer");
            if (!container) {
                this.pageShellBackground = null;
                return;
            }
            const root = container.querySelector(".nomad-html-root");
            this.pageShellBackground = root ? resolveNomadPageShellBackground(root) : null;
        },
        onCrashTabShellBackground(background) {
            if (!this.nomadRenderedShellFullBleed) {
                return;
            }
            this.pageShellBackground = background || null;
        },
        onCrashTabPartials(partials) {
            this.crashTabPartials = Array.isArray(partials) ? partials : [];
            this.scheduleProcessPartials();
            this.$nextTick(() => {
                this.refreshMultilineExpansion();
                this.syncPageShellBackground();
            });
        },
        onCrashTabHung() {
            this.isCrashTabRendering = false;
            ToastUtils.warning(this.$t("nomadnet.crash_tab_hung_toast"));
        },
        onCrashTabNavigate(payload) {
            if (!payload || !payload.kind) {
                return;
            }
            const navOptions = {
                forceNewTab: payload.ctrlKey || payload.metaKey || payload.button === 1,
                activate: !(payload.ctrlKey || payload.metaKey || payload.button === 1),
            };
            if (payload.kind === "nomad") {
                this.onNodePageUrlClick(payload.url, null, true, false, navOptions);
                return;
            }
            if (payload.kind === "lxmf") {
                const address = payload.url;
                if (!address || !/^[a-fA-F0-9]{32}$/.test(address)) {
                    return;
                }
                const routeName = this.isPopoutMode ? "messages-popout" : "messages";
                this.$router.push({
                    name: routeName,
                    params: { destinationHash: address },
                });
                return;
            }
            if (payload.kind === "http") {
                const httpHref = LinkUtils.httpUrlHrefOrNull(String(payload.url || "").trim());
                if (httpHref) {
                    window.open(httpHref, "_blank", "noopener,noreferrer");
                }
                return;
            }
            if (payload.kind === "openNode") {
                const destination = payload.url;
                if (!destination) {
                    return;
                }
                const fields = payload.fields;
                const fieldSpec = payload.fieldSpec;
                if (fields && typeof fields === "object") {
                    this.onNodePageUrlClick(destination, fields, true, false, navOptions);
                } else {
                    this.onNodePageUrlClick(destination, fieldSpec, true, false, navOptions);
                }
            }
        },
        renderPageContent(path, content) {
            // Used for partials and tests. Full page paint runs in NomadCrashTab.
            if (!this.isShowingNodePageSource) {
                const [pagePathWithoutData] = path.split("`");
                return renderNomadPageByPath(
                    pagePathWithoutData,
                    content,
                    this.pagePartials,
                    MicronParser,
                    this.nomadRenderOptions
                );
            }

            return String(content ?? "")
                .replace(/&/g, "&amp;")
                .replace(/</g, "&lt;")
                .replace(/>/g, "&gt;")
                .replace(/"/g, "&quot;")
                .replace(/'/g, "&#039;");
        },
        cancelCrashTabRender() {
            const crashTab = this.$refs.crashTab;
            if (crashTab && typeof crashTab.abortRender === "function") {
                crashTab.abortRender();
            }
            this.isCrashTabRendering = false;
        },
        cancelPageBusy() {
            if (this.isLoadingNodePage) {
                this.cancelPageDownload();
                return;
            }
            if (this.isCrashTabRendering) {
                this.cancelCrashTabRender();
            }
        },
        onCrashTabRenderStarted() {
            this.isCrashTabRendering = true;
        },
        onCrashTabRenderDone() {
            this.isCrashTabRendering = false;
        },
        beginCrashTabRenderWait() {
            if (
                this.nodePageContent &&
                !this.isFailedPageContent(this.nodePageContent) &&
                !this.isCancelledPageContent(this.nodePageContent)
            ) {
                this.isCrashTabRendering = true;
            }
        },
        onCrashTabAborted() {
            this.isCrashTabRendering = false;
            this.pageRenderAborted = true;
            ToastUtils.info(this.$t("nomadnet.crash_tab_render_cancelled"));
        },
        retryCrashTabRender() {
            this.pageRenderAborted = false;
            this.isCrashTabRendering = true;
        },
        toggleNodePageSource() {
            this.isShowingNodePageSource = !this.isShowingNodePageSource;
        },
        showPageSource() {
            if (!this.nodePagePath) {
                ToastUtils.warning(this.$t("nomadnet.view_source_unavailable"));
                return false;
            }
            this.isShowingNodePageSource = true;
            return true;
        },
        async toggleFavouriteFromContext() {
            if (this.isPrivate) {
                ToastUtils.info(this.$t("nomadnet.private_browsing_hint"));
                return false;
            }
            if (!this.selectedNode?.destination_hash) {
                ToastUtils.warning(this.$t("nomadnet.context_menu_page_unavailable"));
                return false;
            }
            const wasFavourite = this.isFavourite(this.selectedNode.destination_hash);
            const ok = wasFavourite
                ? await this.removeFavourite(this.selectedNode)
                : await this.addFavourite(this.selectedNode);
            if (!ok) {
                ToastUtils.error(this.$t("nomadnet.context_menu_favourite_failed"));
                return false;
            }
            ToastUtils.success(
                wasFavourite ? this.$t("nomadnet.favourite_removed") : this.$t("nomadnet.favourite_added")
            );
            return true;
        },
        async downloadPageToDisk() {
            if (
                !this.nodePageContent ||
                !this.nodePagePath ||
                this.isFailedPageContent(this.nodePageContent) ||
                this.isCancelledPageContent(this.nodePageContent)
            ) {
                ToastUtils.warning(this.$t("nomadnet.download_page_unavailable"));
                return false;
            }
            const parsed = this.parseNomadnetworkUrl(this.nodePagePath);
            const pathPart = parsed?.pagePath || this.nodePagePath;
            const segments = String(pathPart).split("/").filter(Boolean);
            const filename = segments.length > 0 ? segments[segments.length - 1] : "nomad-page.txt";
            try {
                const blob = new Blob([this.nodePageContent], { type: "text/plain;charset=utf-8" });
                await DownloadUtils.downloadFile(filename, blob);
                ToastUtils.success(this.$t("nomadnet.download_page_started"));
                return true;
            } catch (error) {
                console.error("nomad page download failed", error);
                ToastUtils.error(this.$t("nomadnet.download_page_failed"));
                return false;
            }
        },
        onPageContextMenu(event) {
            openAppContextMenuUnlessTextSelection(event, (ev) => {
                if (this.embedded && this.nomadBrowserTabActions) {
                    this.nomadBrowserTabActions.openContextMenu(ev);
                    return;
                }
                this.openStandaloneContextMenu(ev);
            });
        },
        openStandaloneContextMenu(event) {
            this.standaloneContextMenu = {
                show: true,
                justOpened: true,
                x: event.clientX,
                y: event.clientY,
            };
            setTimeout(() => {
                this.standaloneContextMenu.justOpened = false;
            }, 50);
        },
        closeStandaloneContextMenu() {
            this.standaloneContextMenu.show = false;
        },
        async runStandaloneContextAction(actionFn) {
            try {
                await actionFn();
            } catch (error) {
                console.error("nomad page context menu action failed", error);
                ToastUtils.error(this.$t("nomadnet.context_menu_action_failed"));
            } finally {
                this.closeStandaloneContextMenu();
            }
        },
        onStandaloneContextViewSource() {
            this.runStandaloneContextAction(() => this.showPageSource());
        },
        onStandaloneContextReload() {
            this.runStandaloneContextAction(() => this.reloadNodePage());
        },
        onStandaloneContextFavorite() {
            this.runStandaloneContextAction(() => this.toggleFavouriteFromContext());
        },
        onStandaloneContextDownloadPage() {
            this.runStandaloneContextAction(() => this.downloadPageToDisk());
        },
        async reloadNodePage() {
            // reload current node page without adding to history and without using cache
            this.onNodePageUrlClick(this.nodePagePath, null, false, false);
        },
        async runPathFinderQuickRequest() {
            const hash = this.selectedNode?.destination_hash;
            if (!hash || this.pathfinderInProgress) return;
            this.pathfinderInProgress = true;
            try {
                await runDestinationPathFinder(window.api, hash, "quick");
                ToastUtils.success(this.$t("nomadnet.path_finder_request_sent"));
                await this.reloadNodePage();
            } catch (e) {
                console.error("path finder quick request failed", e);
                ToastUtils.error(this.$t("nomadnet.path_finder_failed"));
            } finally {
                this.pathfinderInProgress = false;
            }
        },
        async runPathFinderForceFind() {
            const hash = this.selectedNode?.destination_hash;
            if (!hash || this.pathfinderInProgress) return;
            this.pathfinderInProgress = true;
            try {
                const { path } = await runDestinationPathFinder(window.api, hash, "force", {
                    forceTimeout: 15,
                });
                if (path) {
                    ToastUtils.success(this.$t("nomadnet.path_finder_found"));
                    await this.reloadNodePage();
                } else {
                    ToastUtils.error(this.$t("nomadnet.path_finder_not_found"));
                }
            } catch (e) {
                console.error("path finder force find failed", e);
                ToastUtils.error(this.$t("nomadnet.path_finder_failed"));
            } finally {
                this.pathfinderInProgress = false;
            }
        },
        async runPathFinderDropAndRequest() {
            const hash = this.selectedNode?.destination_hash;
            if (!hash || this.pathfinderInProgress) return;
            this.pathfinderInProgress = true;
            try {
                await runDestinationPathFinder(window.api, hash, "drop_then_request", {
                    onDropPathError: (e) => console.warn("drop-path failed (continuing)", e),
                });
                ToastUtils.success(this.$t("nomadnet.path_finder_dropped_and_requested"));
                await this.reloadNodePage();
            } catch (e) {
                console.error("path finder drop+request failed", e);
                ToastUtils.error(this.$t("nomadnet.path_finder_failed"));
            } finally {
                this.pathfinderInProgress = false;
            }
        },
        loadLatestArchiveSnapshot() {
            if (this.isPrivate) {
                return;
            }
            if (this.pageArchives && this.pageArchives.length > 0) {
                this.loadArchivedPage(this.pageArchives[0].id);
                return;
            }
            this.pendingLoadLatestArchive = true;
            this.fetchArchives();
            ToastUtils.info(this.$t("nomadnet.path_finder_archive_loading"));
        },
        async loadPreviousNodePage() {
            // get the previous path from history, or do nothing
            const previousNodePagePath = this.nodePagePathHistory.pop();
            if (!previousNodePagePath) {
                return;
            }

            // load the page
            this.onNodePageUrlClick(previousNodePagePath, null, null, true);
        },
        parseNomadnetworkUrl: function (url) {
            // parse relative urls
            if (url.startsWith(":")) {
                // remove leading ":"
                var path = url.substring(1);

                // if page path is empty we should load default page path
                if (path === "") {
                    path = this.defaultNodePagePath;
                }

                const queryIndex = path.indexOf("?");
                return {
                    destination_hash: null, // node hash was not in provided url
                    path: queryIndex >= 0 ? path.substring(0, queryIndex) : path,
                    query: queryIndex >= 0 ? path.substring(queryIndex + 1) : null,
                };
            }

            // parse absolute urls such as 00000000000000000000000000000000:/page/index.mu
            if (url.includes(":")) {
                // parse destination hash and url
                const [destinationHash, ...relativeUrl] = url.split(":");

                // ensure destination is expected length
                if (destinationHash.length === 32) {
                    const joined = relativeUrl.join(":");
                    const queryIndex = joined.indexOf("?");
                    return {
                        destination_hash: destinationHash,
                        path: queryIndex >= 0 ? joined.substring(0, queryIndex) : joined,
                        query: queryIndex >= 0 ? joined.substring(queryIndex + 1) : null,
                    };
                }
            }

            // parse relative page/file urls (e.g. /file/artifact`g=reticulum|r=lxmf)
            if (url.startsWith("/page/") || url.startsWith("/file/")) {
                const queryIndex = url.indexOf("?");
                return {
                    destination_hash: null,
                    path: queryIndex >= 0 ? url.substring(0, queryIndex) : url,
                    query: queryIndex >= 0 ? url.substring(queryIndex + 1) : null,
                };
            }

            // parse node id only
            if (url.length === 32) {
                return {
                    destination_hash: url,
                    path: this.defaultNodePagePath,
                    query: null,
                };
            }

            // unsupported url
            return null;
        },
        async onNodePageUrlClick(url, options = null, addToHistory = true, useCache = false, navOptions = {}) {
            let fieldData = [];

            if (options && typeof options === "object" && !Array.isArray(options)) {
                useCache = false;
                fieldData = options;
            } else if (options === "*") {
                useCache = false; // we want to send another request with the field data
                // Scope to this tab only. Inactive tabs stay mounted with v-show.
                const inputs = this.$el.querySelectorAll(".nodeContainer input, .nodeContainer textarea");

                const inputValues = {};

                for (const input of inputs) {
                    if (input.type === "radio" || input.type === "checkbox") {
                        // Only add if the input is checked
                        if (input.checked) {
                            inputValues[input.name] = input.value;
                        }
                    } else {
                        // For other input types, just get the value
                        inputValues[input.name || input.id || input.type] = input.value;
                    }
                }

                fieldData = inputValues;
            } else if (options !== null && options !== "") {
                useCache = false;
                // split options into an array of names
                const validNames = options.split("|");

                // Select inputs within this tab's container only
                const inputs = this.$el.querySelectorAll(".nodeContainer input, .nodeContainer textarea");

                const inputValues = {};

                // Filter inputs by name and handle their values
                for (const input of inputs) {
                    if (validNames.includes(input.name)) {
                        if (input.type === "radio" || input.type === "checkbox") {
                            // Only add if the input is checked
                            if (input.checked) {
                                inputValues[input.name] = input.value;
                            }
                        } else {
                            // For other input types, just get the value
                            inputValues[input.name] = input.value;
                        }
                    }
                }

                fieldData = inputValues;
            }

            const httpHref = typeof url === "string" ? LinkUtils.httpUrlHrefOrNull(url.trim()) : null;
            if (httpHref) {
                window.open(httpHref, "_blank", "noopener,noreferrer");
                return;
            }

            // lxmf urls should open the conversation (not a Nomad node tab)
            const urlTrimmed = typeof url === "string" ? url.trim() : "";
            const normalizedLxmf = Utils.normalizeMeshchatHashHex(urlTrimmed);
            const lxmfLower = urlTrimmed.toLowerCase();
            if (normalizedLxmf.length === 32 && (lxmfLower.startsWith("lxmf@") || lxmfLower.startsWith("lxmf://"))) {
                const destinationHash = normalizedLxmf;
                const routeName = this.isPopoutMode ? "messages-popout" : "messages";
                await this.$router.push({
                    name: routeName,
                    params: {
                        destinationHash: destinationHash,
                    },
                });
                return;
            }

            // attempt to parse url
            const parsedUrl = this.parseNomadnetworkUrl(url);
            if (parsedUrl != null) {
                // reset archive states
                this.isShowingArchivedVersion = false;
                this.archivedAt = null;
                this.hasArchivesForCurrentPage = false;
                this.pageArchives = [];
                this.isArchiveDropdownOpen = false;

                // use parsed destination hash, or fallback to selected node destination hash
                const destinationHash = parsedUrl.destination_hash || this.selectedNode?.destination_hash || null;
                if (!destinationHash) {
                    ToastUtils.warning(this.$t("nomadnet.select_node_to_browse"));
                    return;
                }

                // download file
                if (parsedUrl.path.startsWith("/file/")) {
                    // prevent simultaneous downloads
                    if (this.isDownloadingNodeFile) {
                        ToastUtils.warning(this.$t("nomadnet.existing_download_in_progress"));
                        return;
                    }

                    // NomadNet file URLs may use backticks to separate path from parameters
                    let filePath = parsedUrl.path;
                    let fileData = parsedUrl.query;
                    const pathBacktickIndex = filePath.indexOf("`");
                    if (pathBacktickIndex >= 0) {
                        fileData = filePath.substring(pathBacktickIndex + 1);
                        filePath = filePath.substring(0, pathBacktickIndex);
                    }

                    // update ui
                    this.isDownloadingNodeFile = true;
                    this.nodeFilePath = filePath.split("/").pop();
                    this.nodeFileProgress = 0;
                    this.nodeFileDownloadStartTime = Date.now();
                    this.nodeFileLastProgressTime = Date.now();
                    this.nodeFileLastProgressValue = 0;
                    this.nodeFileDownloadSpeed = null;

                    // start file download
                    this.downloadNomadNetFile(
                        destinationHash,
                        filePath,
                        fileData,
                        (fileName, fileBytesBase64) => {
                            // Calculate final download speed based on actual file size
                            if (this.nodeFileDownloadStartTime) {
                                const totalTime = (Date.now() - this.nodeFileDownloadStartTime) / 1000; // seconds
                                const fileSizeBytes = atob(fileBytesBase64).length;
                                if (totalTime > 0) {
                                    this.nodeFileDownloadSpeed = fileSizeBytes / totalTime;
                                }
                            }

                            // no longer downloading
                            this.isDownloadingNodeFile = false;

                            // download file to browser
                            this.downloadFileFromBase64(fileName, fileBytesBase64);

                            // Clear speed after a moment
                            setTimeout(() => {
                                this.nodeFileDownloadSpeed = null;
                            }, 2000);
                        },
                        (failureReason) => {
                            // no longer downloading
                            this.isDownloadingNodeFile = false;
                            this.nodeFileDownloadSpeed = null;

                            // show error message
                            ToastUtils.error(`Failed to download file: ${failureReason}`);
                        },
                        (progress) => {
                            const currentTime = Date.now();
                            const progressValue = progress;
                            this.nodeFileProgress = Math.round(progressValue * 100);

                            // Calculate estimated download speed based on progress rate
                            if (this.nodeFileDownloadStartTime && progressValue > 0) {
                                const elapsedTime = (currentTime - this.nodeFileDownloadStartTime) / 1000; // seconds
                                if (elapsedTime > 0.5) {
                                    // Only calculate after at least 0.5 seconds
                                    // Estimate total file size based on progress rate
                                    // If we've downloaded progressValue in elapsedTime, estimate total time
                                    // const estimatedTotalTime = elapsedTime / progressValue;
                                    // Estimate file size based on average download speed assumption
                                    // We'll refine this when download completes with actual size
                                    // For now, estimate based on typical mesh network file sizes (100KB-10MB range)
                                    // Use a conservative estimate that will be updated when download completes
                                    const estimatedFileSize = 500 * 1024; // Start with 500KB estimate
                                    const estimatedBytesDownloaded = estimatedFileSize * progressValue;
                                    const estimatedSpeed = estimatedBytesDownloaded / elapsedTime;

                                    // Only update if we have a reasonable estimate
                                    if (estimatedSpeed > 0 && estimatedSpeed < 100 * 1024 * 1024) {
                                        // Cap at 100MB/s
                                        this.nodeFileDownloadSpeed = estimatedSpeed;
                                    }
                                }
                            }

                            this.nodeFileLastProgressTime = currentTime;
                            this.nodeFileLastProgressValue = progressValue;
                        }
                    );

                    return;
                }

                // update selected node, so relative urls work correctly when returned by the new node
                this.selectedNode = this.resolveNodeForHash(destinationHash);

                // navigate to node page
                this.loadNodePage(destinationHash, parsedUrl.path, fieldData, addToHistory, useCache, navOptions);
                return;
            }

            // unsupported url
            ToastUtils.warning(this.$t("nomadnet.unsupported_url") + url);
        },
        downloadFileFromBase64: async function (fileName, fileBytesBase64) {
            DownloadUtils.downloadFromBase64(fileName, fileBytesBase64);
        },
        formatBytesPerSecond: function (bytesPerSecond) {
            return Utils.formatBytesPerSecond(bytesPerSecond);
        },
        onNodeClick: function (node) {
            const hash = node?.destination_hash;
            const resolved = hash ? this.resolveNodeForHash(hash) : node;
            const title =
                resolved?.custom_display_name ||
                resolved?.display_name ||
                node?.custom_display_name ||
                node?.display_name ||
                null;
            if (this.shouldOpenInNewTab(hash, {})) {
                this.emitOpenNode(hash, this.defaultNodePagePath, title, { activate: true });
                return;
            }

            this.selectedNode = resolved || node;
            this.loadNodePage(hash, this.defaultNodePagePath);
        },
        async onRenameFavourite(favourite) {
            // ask user for new display name
            const displayName = await DialogUtils.prompt(this.$t("nomadnet.rename_favourite"));
            if (displayName == null) {
                return;
            }
            const trimmed = typeof displayName === "string" ? displayName.trim() : "";
            if (!trimmed) {
                return;
            }

            try {
                // rename on server
                await window.api.post(`/api/v1/favourites/${favourite.destination_hash}/rename`, {
                    display_name: trimmed,
                });

                // reload favourites
                await this.getFavourites();

                const dh = favourite.destination_hash;
                if (this.nodes[dh]) {
                    this.nodes[dh] = {
                        ...this.nodes[dh],
                        custom_display_name: trimmed,
                        display_name: trimmed,
                    };
                }
                if (this.selectedNode?.destination_hash === dh) {
                    this.selectedNode = {
                        ...this.selectedNode,
                        custom_display_name: trimmed,
                        display_name: trimmed,
                    };
                }
            } catch (e) {
                console.log(e);
                ToastUtils.error(this.$t("nomadnet.failed_rename_favourite"));
            }
        },
        async onRemoveFavourite(favourite) {
            // ask user to confirm
            if (!(await DialogUtils.confirm(this.$t("nomadnet.remove_favourite_confirm")))) {
                return;
            }

            this.removeFavourite(favourite);
        },
        onCloseNodeViewer: function () {
            // clear selected node
            this.selectedNode = null;

            if (this.embedded) {
                this.$emit("close-tab");
                return;
            }

            if (this.isPopoutMode) {
                window.close();
                return;
            }

            // update current route
            const routeName = this.isPopoutMode ? "nomadnetwork-popout" : "nomadnetwork";
            const routeOptions = { name: routeName };
            if (!this.isPopoutMode && this.$route?.query) {
                routeOptions.query = { ...this.$route.query };
            }
            this.$router.replace(routeOptions);
        },
        getNomadnetPageDownloadCallbackKey: function (destinationHash, pagePath) {
            return `${destinationHash}:${pagePath}`;
        },
        getNomadnetFileDownloadCallbackKey: function (destinationHash, filePath) {
            return `${destinationHash}:${filePath}`;
        },
        decodeBase64ToBytes(base64) {
            const binary = atob(base64 || "");
            const bytes = new Uint8Array(binary.length);
            for (let i = 0; i < binary.length; i++) {
                bytes[i] = binary.charCodeAt(i);
            }
            return bytes;
        },
        appendDownloadChunk(chunkBuffers, downloadId, chunkPayload) {
            if (downloadId == null) {
                return;
            }
            const entry = chunkBuffers[downloadId] || { chunks: [] };
            entry.chunks.push(this.decodeBase64ToBytes(chunkPayload.chunk_b64));
            chunkBuffers[downloadId] = entry;
        },
        consumeDownloadChunkBytes(chunkBuffers, downloadId) {
            const entry = chunkBuffers[downloadId];
            delete chunkBuffers[downloadId];
            const chunks = entry?.chunks || [];
            const totalLength = chunks.reduce((sum, chunk) => sum + chunk.length, 0);
            const merged = new Uint8Array(totalLength);
            let offset = 0;
            for (const chunk of chunks) {
                merged.set(chunk, offset);
                offset += chunk.length;
            }
            return merged;
        },
        consumeDownloadChunksAsText(chunkBuffers, downloadId) {
            return new TextDecoder("utf-8").decode(this.consumeDownloadChunkBytes(chunkBuffers, downloadId));
        },
        consumeDownloadChunksAsBase64(chunkBuffers, downloadId) {
            return Utils.arrayBufferToBase64(this.consumeDownloadChunkBytes(chunkBuffers, downloadId));
        },
        toggleArchiveDropdown() {
            this.isArchiveDropdownOpen = !this.isArchiveDropdownOpen;
            if (this.isArchiveDropdownOpen) {
                this.fetchArchives();
            }
        },
        fetchArchives() {
            if (this.isPrivate) {
                this.pageArchives = [];
                this.isLoadingArchives = false;
                return;
            }
            if (!this.selectedNode || !this.nodePagePath) return;
            this.isLoadingArchives = true;

            const parsed = this.parseNomadnetworkUrl(this.nodePagePath);
            if (!parsed) return;

            WebSocketConnection.send(
                JSON.stringify({
                    type: "nomadnet.page.archives.get",
                    destination_hash: this.selectedNode.destination_hash,
                    page_path: parsed.path,
                })
            );
        },
        loadArchivedPage(archiveId) {
            if (this.isPrivate) {
                return;
            }
            this.isArchiveDropdownOpen = false;
            this.isLoadingNodePage = true;
            this.isShowingArchivedVersion = false;
            this.archivedAt = null;
            this.nodePageProgress = 0;
            this.pageLoadStartedAt = Date.now();
            this.nodePageLoadPhase = null;

            const archive = this.pageArchives.find((a) => a.id === archiveId);
            if (archive) {
                this.nodePagePath = `${archive.destination_hash}:${archive.page_path}`;
                this.nodePagePathUrlInput = this.nodePagePath;
            }

            // Own the reply even when the local archive list is empty or stale.
            // Without this, ownsNomadPageDownloadEvent rejects path-mismatched
            // archive payloads and isLoadingNodePage stays true forever.
            const downloadId = Math.floor(Math.random() * 1000000);
            this.currentPageDownloadId = downloadId;

            const sent = WebSocketConnection.send(
                JSON.stringify({
                    type: "nomadnet.page.archive.load",
                    archive_id: archiveId,
                    download_id: downloadId,
                })
            );
            if (sent === false) {
                this.isLoadingNodePage = false;
                this.nodePageLoadPhase = null;
                this.currentPageDownloadId = null;
                ToastUtils.error(this.$t("nomadnet.tab_restore_failed"));
            }
        },
        manualArchive() {
            if (this.isPrivate) {
                ToastUtils.info(this.$t("nomadnet.private_browsing_hint"));
                return;
            }
            if (!this.selectedNode || !this.nodePagePath || !this.nodePageContent) return;
            ToastUtils.info(this.$t("nomadnet.archiving_page"));

            const parsed = this.parseNomadnetworkUrl(this.nodePagePath);
            if (!parsed) return;

            WebSocketConnection.send(
                JSON.stringify({
                    type: "nomadnet.page.archive.add",
                    destination_hash: this.selectedNode.destination_hash,
                    page_path: parsed.path,
                    content: this.nodePageContent,
                })
            );
        },
        formatDate(dateStr) {
            if (!dateStr) return "Unknown Date";
            const date = new Date(dateStr);
            if (isNaN(date.getTime())) return "Invalid Date";
            return date.toLocaleString();
        },
        formatShortDuration(ms) {
            if (ms == null || ms < 0) {
                return "";
            }
            if (ms < 1000) {
                return `${Math.round(ms)} ms`;
            }
            const s = ms / 1000;
            if (s < 60) {
                return s < 10 ? `${s.toFixed(1)} s` : `${Math.round(s)} s`;
            }
            const m = Math.floor(s / 60);
            const rs = Math.round(s - m * 60);
            return `${m}m ${rs}s`;
        },
        async getNodePath(destinationHash) {
            this.selectedNodePath = null;

            try {
                const response = await getDestinationPath(window.api, destinationHash, {});

                this.selectedNodePath = response.data.path;
            } catch (e) {
                console.log(e);
            }
        },
        async identify(destinationHash) {
            await this.toggleIdentifyOnConnect(destinationHash);
        },
        async toggleIdentifyOnConnect(destinationHash) {
            if (this.isPrivate) {
                ToastUtils.info(this.$t("nomadnet.private_browsing_hint"));
                return;
            }
            if (!destinationHash) {
                return;
            }
            const currentlyOn = this.favourites.some(
                (favourite) => favourite.destination_hash === destinationHash && Boolean(favourite.identify_on_connect)
            );
            const enable = !currentlyOn;
            try {
                if (enable) {
                    if (!(await DialogUtils.confirm(this.$t("nomadnet.identify_confirm")))) {
                        return;
                    }
                }
                const node = this.selectedNode?.destination_hash === destinationHash ? this.selectedNode : null;
                const existing = this.favourites.find((favourite) => favourite.destination_hash === destinationHash);
                const displayName = resolveFavouriteUpsertDisplayName(
                    node || existing || { destination_hash: destinationHash },
                    existing,
                    this.$t("nomadnet.unknown_node")
                );
                await window.api.post(`/api/v1/favourites/${destinationHash}/identify-on-connect`, {
                    enabled: enable,
                    display_name: displayName,
                    aspect: "nomadnetwork.node",
                });
                await this.getFavourites();
                if (enable) {
                    this.reloadNodePage();
                }
            } catch (e) {
                ToastUtils.error(e.response?.data?.message ?? this.$t("nomadnet.identify_on_connect_failed"));
            }
        },
        getHashPopoutValue() {
            const hash = window.location.hash || "";
            const match = hash.match(/popout=([^&]+)/);
            return match ? decodeURIComponent(match[1]) : null;
        },
        downloadNomadNetFile(
            destinationHash,
            filePath,
            data,
            onSuccessCallback,
            onFailureCallback,
            onProgressCallback
        ) {
            try {
                // set callbacks for nomadnet filePath download
                this.nomadnetFileDownloadCallbacks[this.getNomadnetFileDownloadCallbackKey(destinationHash, filePath)] =
                    {
                        onSuccessCallback: onSuccessCallback,
                        onFailureCallback: onFailureCallback,
                        onProgressCallback: onProgressCallback,
                    };

                // ask reticulum to download file from nomadnet
                const payload = {
                    type: "nomadnet.file.download",
                    nomadnet_file_download: {
                        destination_hash: destinationHash,
                        file_path: filePath,
                        private: Boolean(this.isPrivate),
                    },
                };
                if (data != null) {
                    payload.nomadnet_file_download.data = data;
                }
                WebSocketConnection.send(JSON.stringify(payload));
            } catch (e) {
                console.error(e);
            }
        },
        downloadNomadNetPage(
            destinationHash,
            pagePath,
            fieldData,
            onSuccessCallback,
            onFailureCallback,
            onProgressCallback,
            options = {}
        ) {
            const primary = options.primary === true;
            const callbackKey = this.getNomadnetPageDownloadCallbackKey(destinationHash, pagePath);
            const previous = this.nomadnetPageDownloadCallbacks[callbackKey];
            if (previous && typeof previous.cancelPendingSend === "function") {
                previous.cancelPendingSend();
            }

            const payload = JSON.stringify({
                type: "nomadnet.page.download",
                nomadnet_page_download: {
                    destination_hash: destinationHash,
                    page_path: pagePath,
                    field_data: fieldData,
                    private: Boolean(this.isPrivate),
                },
            });

            let pendingTimer = null;
            let onWsRetry = null;
            let pendingCancelled = false;
            const requestToken = Symbol("nomad-page-download");
            const cancelPendingSend = () => {
                pendingCancelled = true;
                if (pendingTimer != null) {
                    clearTimeout(pendingTimer);
                    pendingTimer = null;
                }
                if (onWsRetry) {
                    WebSocketConnection.off("connected", onWsRetry);
                    WebSocketConnection.off("ready", onWsRetry);
                    onWsRetry = null;
                }
            };

            const entry = {
                onSuccessCallback: onSuccessCallback,
                onFailureCallback: onFailureCallback,
                onProgressCallback: onProgressCallback,
                primary,
                requestToken,
                cancelPendingSend,
            };
            this.nomadnetPageDownloadCallbacks[callbackKey] = entry;

            const isCurrentEntry = () => {
                const current = this.nomadnetPageDownloadCallbacks[callbackKey];
                return Boolean(current) && current.requestToken === requestToken && !pendingCancelled;
            };

            const failNotConnected = () => {
                const stillCurrent = this.nomadnetPageDownloadCallbacks[callbackKey]?.requestToken === requestToken;
                cancelPendingSend();
                if (!stillCurrent) {
                    return;
                }
                delete this.nomadnetPageDownloadCallbacks[callbackKey];
                const reason =
                    typeof this.$t === "function"
                        ? this.$t("nomadnet.websocket_not_connected")
                        : "websocket_not_connected";
                if (onFailureCallback) {
                    onFailureCallback(reason);
                    return;
                }
                if (primary && this.isLoadingNodePage) {
                    this.isLoadingNodePage = false;
                    this.nodePageLoadPhase = null;
                    this.currentPageDownloadId = null;
                    this.nodePageContent = `Failed loading page: ${reason}`;
                    ToastUtils.error(this.$t("nomadnet.failed_to_load_page"));
                }
            };

            const trySend = () => {
                if (WebSocketConnection.send(payload)) {
                    cancelPendingSend();
                    return true;
                }
                return false;
            };

            try {
                if (trySend()) {
                    return;
                }
                // Bootstrap / reconnect race: queue until the socket is usable.
                onWsRetry = () => {
                    if (!isCurrentEntry()) {
                        cancelPendingSend();
                        return;
                    }
                    if (!trySend()) {
                        failNotConnected();
                    }
                };
                WebSocketConnection.on("connected", onWsRetry);
                WebSocketConnection.on("ready", onWsRetry);
                pendingTimer = setTimeout(() => {
                    pendingTimer = null;
                    if (!isCurrentEntry()) {
                        cancelPendingSend();
                        return;
                    }
                    if (typeof WebSocketConnection.isOpen === "function" && WebSocketConnection.isOpen()) {
                        onWsRetry();
                        return;
                    }
                    failNotConnected();
                }, 20000);
            } catch (e) {
                console.error(e);
                failNotConnected();
            }
        },
        cancelPageDownload() {
            if (!this.isLoadingNodePage && this.currentPageDownloadId === null) {
                this.cancelCrashTabRender();
                return;
            }

            const downloadId = this.currentPageDownloadId;
            const parsed = this.parseNomadnetworkUrl(this.nodePagePath || "");
            const dh = parsed?.destination_hash || this.selectedNode?.destination_hash;
            const pathPart = parsed?.path;
            if (dh && pathPart) {
                const key = this.getNomadnetPageDownloadCallbackKey(dh, pathPart);
                const entry = this.nomadnetPageDownloadCallbacks[key];
                if (entry && typeof entry.cancelPendingSend === "function") {
                    entry.cancelPendingSend();
                }
                delete this.nomadnetPageDownloadCallbacks[key];
            }

            this.nodePageRequestSequence += 1;
            if (downloadId !== null) {
                this.pendingNomadPageCancelWithoutId = false;
                this.currentPageDownloadId = null;
                WebSocketConnection.send(
                    JSON.stringify({
                        type: "nomadnet.download.cancel",
                        download_id: downloadId,
                    })
                );
            } else {
                this.pendingNomadPageCancelWithoutId = true;
            }
            this.applyPageDownloadCancelledUi();
        },
        cancelFileDownload() {
            if (this.currentFileDownloadId !== null) {
                WebSocketConnection.send(
                    JSON.stringify({
                        type: "nomadnet.download.cancel",
                        download_id: this.currentFileDownloadId,
                    })
                );
            }
        },
    },
};
</script>

<style>
@import "../../css/nomad-page-chrome.css";

.nomad-icon-btn {
    border-radius: 10px !important;
    border: none !important;
    background: transparent !important;
}

.nomad-icon-btn:hover {
    background: color-mix(in srgb, var(--mc-surface-hover, #27272a) 65%, transparent) !important;
}

.nomad-url-input {
    border-radius: 0.5rem;
    border: 1px solid var(--mc-border, #27272a);
    background: color-mix(in srgb, var(--mc-surface-muted, #18181b) 85%, transparent);
    padding: 0.35rem 0.75rem;
    font-size: 0.8125rem;
    color: var(--mc-text, #f3f4f6);
    outline: none;
    transition:
        border-color 120ms ease,
        box-shadow 120ms ease;
}

@media (max-height: 700px) {
    .nomad-url-input {
        padding: 0.2rem 0.6rem;
        font-size: 0.75rem;
    }
}

.nomad-url-input:focus {
    border-color: var(--mc-accent, #60a5fa);
    box-shadow: 0 0 0 2px color-mix(in srgb, var(--mc-accent, #60a5fa) 25%, transparent);
}
</style>
