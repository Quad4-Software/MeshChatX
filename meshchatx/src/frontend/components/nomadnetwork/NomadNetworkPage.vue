<template>
    <div class="flex flex-1 min-w-0 h-full overflow-hidden">
        <!-- nomadnetwork sidebar -->
        <NomadNetworkSidebar
            v-if="!isPopoutMode"
            :class="{ 'hidden sm:flex': selectedNode }"
            :nodes="nodes"
            :favourites="favourites"
            :selected-destination-hash="selectedNode?.destination_hash"
            :nodes-search-term="nodesSearchTerm"
            :total-nodes-count="totalNodesCount"
            :is-loading-more-nodes="isLoadingMoreNodes"
            :has-more-nodes="hasMoreNodes"
            @node-click="onNodeClick"
            @rename-favourite="onRenameFavourite"
            @remove-favourite="onRemoveFavourite"
            @add-favourite="addFavourite"
            @nodes-search-changed="onNodesSearchChanged"
            @load-more-nodes="loadMoreNodes"
        />

        <div
            class="flex-col flex-1 overflow-hidden min-w-0 dark:bg-zinc-950"
            :class="selectedNode ? 'flex' : 'hidden sm:flex'"
        >
            <!-- node -->
            <div
                v-if="selectedNode"
                class="flex flex-col h-full min-h-0 bg-white dark:bg-zinc-950 overflow-hidden sm:m-0 sm:border-0 relative"
            >
                <!-- banished overlay -->
                <div
                    v-if="GlobalState.config.banished_effect_enabled && isSelectedNodeBlocked"
                    class="banished-overlay"
                    :style="{ background: GlobalState.config.banished_color + '33' }"
                >
                    <span
                        class="banished-text !opacity-100 !text-white !shadow-lg !bg-red-600 !px-4 !py-2 !rounded-xl !border-2 !tracking-widest"
                        :style="{
                            'background-color': GlobalState.config.banished_color,
                            'border-color': GlobalState.config.banished_color,
                        }"
                        >{{ GlobalState.config.banished_text }}</span
                    >
                </div>

                <!-- header -->
                <div class="flex items-center gap-1 p-2 border-b border-gray-300 dark:border-zinc-800 min-w-0">
                    <!-- favourite button -->
                    <div class="my-auto shrink-0 mr-1">
                        <IconButton
                            v-if="isFavourite(selectedNode.destination_hash)"
                            class="text-yellow-500 dark:text-yellow-300"
                            :title="$t('nomadnet.remove_favourite')"
                            @click="removeFavourite(selectedNode)"
                        >
                            <MaterialDesignIcon icon-name="star" class="size-5" />
                        </IconButton>
                        <IconButton
                            v-else
                            class="text-gray-700 dark:text-gray-300"
                            :title="$t('nomadnet.add_favourite')"
                            @click="addFavourite(selectedNode)"
                        >
                            <MaterialDesignIcon icon-name="star-outline" class="size-5" />
                        </IconButton>
                    </div>

                    <!-- node info -->
                    <div class="my-auto dark:text-gray-100 flex-1 min-w-0 flex items-baseline gap-1 overflow-hidden">
                        <span
                            class="font-semibold truncate inline-block min-w-0 max-w-[min(100%,12rem)] sm:max-w-xs md:max-w-sm"
                            :title="selectedNode.display_name"
                            >{{ selectedNode.display_name }}</span
                        >
                        <span
                            v-if="selectedNodePath"
                            class="text-sm cursor-pointer whitespace-nowrap flex-shrink-0 hidden sm:inline"
                            @click="onDestinationPathClick(selectedNodePath)"
                        >
                            - {{ selectedNodePath.hops }}
                            {{ selectedNodePath.hops === 1 ? $t("app.hop") : $t("app.hops_plural") }}
                            {{ $t("nomadnet.path_away_suffix") }}
                            <template v-if="navbarPageStats">
                                <span class="text-gray-500 dark:text-gray-400 font-normal">
                                    - {{ navbarPageStats.duration }} - {{ navbarPageStats.sizeLabel }}
                                </span>
                            </template>
                        </span>
                    </div>

                    <!-- archive button -->
                    <div v-if="pageArchives.length > 0 || nodePageContent" class="my-auto shrink-0 relative">
                        <IconButton
                            class="text-gray-700 dark:text-gray-300"
                            :class="{ 'text-blue-500 dark:text-blue-400': pageArchives.length > 0 }"
                            :title="$t('app.archives')"
                            @click="toggleArchiveDropdown"
                        >
                            <MaterialDesignIcon icon-name="archive" class="size-5" />
                        </IconButton>
                        <!-- archive dropdown -->
                        <div
                            v-if="isArchiveDropdownOpen"
                            class="absolute right-0 mt-2 w-64 bg-white dark:bg-zinc-900 border border-gray-200 dark:border-zinc-800 rounded-lg shadow-lg z-50 overflow-hidden"
                        >
                            <div
                                class="p-2 border-b border-gray-100 dark:border-zinc-800 font-semibold text-xs text-gray-500 dark:text-gray-400 uppercase tracking-wider flex justify-between items-center"
                            >
                                <span>{{ $t("nomadnet.page_archives") }}</span>
                                <button
                                    v-if="nodePageContent"
                                    :title="$t('nomadnet.archive_current_version')"
                                    class="text-blue-500 hover:text-blue-600 dark:text-blue-400 dark:hover:text-blue-300"
                                    @click.stop="manualArchive"
                                >
                                    <MaterialDesignIcon icon-name="plus" class="size-4" />
                                </button>
                            </div>
                            <div class="max-h-64 overflow-y-auto">
                                <div
                                    v-if="pageArchives.length === 0"
                                    class="p-3 text-sm text-gray-500 dark:text-gray-400 text-center"
                                >
                                    {{ $t("nomadnet.no_archives_for_this_page") }}
                                </div>
                                <div
                                    v-for="archive in pageArchives"
                                    v-else
                                    :key="archive.id"
                                    class="p-2 hover:bg-gray-50 dark:hover:bg-zinc-800 cursor-pointer border-b last:border-b-0 border-gray-100 dark:border-zinc-800"
                                    @click="loadArchivedPage(archive.id)"
                                >
                                    <div class="text-sm font-medium dark:text-gray-200">
                                        {{ formatDate(archive.created_at) }}
                                    </div>
                                    <div class="text-xs text-gray-500 dark:text-gray-400 truncate">
                                        {{ archive.hash.substring(0, 16) }}...
                                    </div>
                                </div>
                            </div>
                        </div>
                    </div>

                    <IconButton
                        class="md:hidden shrink-0 text-gray-700 dark:text-gray-300"
                        :title="$t('nomadnet.identify')"
                        @click="identify(selectedNode.destination_hash)"
                    >
                        <MaterialDesignIcon icon-name="fingerprint" class="size-5" />
                    </IconButton>

                    <div class="hidden md:flex items-center gap-1 shrink-0">
                        <IconButton
                            class="text-gray-700 dark:text-gray-300"
                            :title="$t('nomadnet.identify')"
                            @click="identify(selectedNode.destination_hash)"
                        >
                            <MaterialDesignIcon icon-name="fingerprint" class="size-5" />
                        </IconButton>
                        <IconButton
                            class="text-gray-700 dark:text-gray-300"
                            :title="$t('nomadnet.pop_out_browser')"
                            @click="openNomadnetPopout"
                        >
                            <MaterialDesignIcon icon-name="open-in-new" class="size-5" />
                        </IconButton>
                        <IconButton
                            class="text-gray-700 dark:text-gray-300"
                            :title="$t('common.cancel')"
                            @click="onCloseNodeViewer"
                        >
                            <MaterialDesignIcon icon-name="close" class="w-5 h-5" />
                        </IconButton>
                    </div>

                    <DropDownMenu class="md:hidden shrink-0">
                        <template #button>
                            <IconButton :title="$t('messages.more_actions')" class="text-gray-700 dark:text-gray-300">
                                <MaterialDesignIcon icon-name="dots-horizontal" class="size-5" />
                            </IconButton>
                        </template>
                        <template #items>
                            <DropDownMenuItem @click="openNomadnetPopout">
                                <MaterialDesignIcon icon-name="open-in-new" class="size-5" />
                                <span>{{ $t("nomadnet.pop_out_browser") }}</span>
                            </DropDownMenuItem>
                            <DropDownMenuItem @click="onCloseNodeViewer">
                                <MaterialDesignIcon icon-name="close" class="size-5" />
                                <span>{{ $t("common.cancel") }}</span>
                            </DropDownMenuItem>
                        </template>
                    </DropDownMenu>
                </div>

                <!-- browser navigation -->
                <div
                    class="flex items-center w-full min-w-0 border-gray-300 dark:border-zinc-800 border-b p-2 gap-0.5 overflow-x-auto"
                >
                    <IconButton
                        class="shrink-0"
                        title="Home"
                        @click="loadNodePage(selectedNode.destination_hash, defaultNodePagePath)"
                    >
                        <MaterialDesignIcon icon-name="home" class="w-5 h-5" />
                    </IconButton>
                    <IconButton class="shrink-0" :title="$t('common.refresh')" @click="reloadNodePage">
                        <MaterialDesignIcon icon-name="refresh" class="w-5 h-5" />
                    </IconButton>
                    <IconButton
                        class="shrink-0"
                        :title="$t('app.toggle_source')"
                        :class="{ 'bg-green-500/10 text-green-600 dark:text-green-400': isShowingNodePageSource }"
                        @click="toggleNodePageSource"
                    >
                        <MaterialDesignIcon icon-name="code-tags" class="size-5" />
                    </IconButton>
                    <IconButton
                        class="shrink-0"
                        title="Back"
                        :disabled="nodePagePathHistory.length === 0"
                        @click="loadPreviousNodePage"
                    >
                        <MaterialDesignIcon icon-name="arrow-left" class="w-5 h-5" />
                    </IconButton>
                    <div class="my-auto mx-1 min-w-0 flex-1">
                        <input
                            v-model="nodePagePathUrlInput"
                            type="text"
                            :placeholder="$t('nomadnet.enter_nomadnet_url')"
                            class="bg-gray-50 dark:bg-zinc-900 border border-gray-300 dark:border-zinc-700 text-gray-900 dark:text-gray-100 text-sm rounded-lg focus:ring-blue-500 focus:border-blue-500 block w-full px-2.5 py-1.5 dark:placeholder-gray-400"
                            @keyup.enter="onNodePageUrlClick(nodePagePathUrlInput)"
                        />
                    </div>
                    <IconButton class="shrink-0" title="Go" @click="onNodePageUrlClick(nodePagePathUrlInput)">
                        <MaterialDesignIcon icon-name="arrow-right" class="w-5 h-5" />
                    </IconButton>
                </div>

                <!-- page content -->
                <div class="flex-1 overflow-y-auto p-3 bg-black text-white nodeContainer relative">
                    <!-- archived version notice -->
                    <div
                        v-if="isShowingArchivedVersion"
                        class="mb-4 p-2 bg-yellow-900/40 border border-yellow-700/50 rounded flex items-center justify-between text-yellow-200"
                    >
                        <div class="flex items-center gap-2">
                            <MaterialDesignIcon icon-name="clock" class="size-4" />
                            <span v-if="archivedAt" class="text-sm font-medium">{{
                                $t("nomadnet.viewing_archived_version_from", { time: formatDate(archivedAt) })
                            }}</span>
                            <span v-else class="text-sm font-medium">{{
                                $t("nomadnet.viewing_archived_version")
                            }}</span>
                        </div>
                        <button
                            class="text-xs bg-yellow-700/50 hover:bg-yellow-700 px-2 py-1 rounded transition"
                            @click="reloadNodePage"
                        >
                            {{ $t("nomadnet.load_live") }}
                        </button>
                    </div>

                    <div v-if="isLoadingNodePage" class="flex">
                        <div class="my-auto">
                            <svg
                                class="animate-spin -ml-1 mr-3 h-5 w-5 text-white"
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
                        <div class="my-auto flex-1">{{ nomadnetPageLoadingLine }}</div>
                        <button
                            type="button"
                            class="my-auto text-white bg-red-600 hover:bg-red-700 dark:bg-red-700 dark:hover:bg-red-800 rounded px-3 py-1 text-sm font-semibold cursor-pointer ml-3"
                            @click="cancelPageDownload"
                        >
                            {{ $t("common.cancel") }}
                        </button>
                    </div>
                    <div
                        v-else-if="
                            nodePageContent === 'request_failed' ||
                            (nodePageContent && nodePageContent.includes('failure'))
                        "
                        class="flex flex-col items-center justify-center h-full text-center space-y-4"
                    >
                        <div class="text-red-400 font-semibold text-lg">{{ $t("nomadnet.failed_to_load_page") }}</div>
                        <div class="text-gray-400 text-sm max-w-md">{{ nodePageContent }}</div>

                        <div v-if="hasArchivesForCurrentPage" class="space-y-2">
                            <div class="text-sm text-gray-300">{{ $t("nomadnet.archived_version_available") }}</div>
                            <button
                                class="inline-flex items-center gap-2 rounded-lg bg-blue-600 px-4 py-2 text-sm font-semibold text-white shadow hover:bg-blue-500 transition"
                                @click="toggleArchiveDropdown"
                            >
                                <MaterialDesignIcon icon-name="archive" class="size-4" />
                                {{ $t("nomadnet.view_archive") }}
                            </button>
                        </div>
                    </div>
                    <!-- eslint-disable-next-line vue/no-v-html -->
                    <pre v-else class="h-full break-words whitespace-pre-wrap" v-html="renderedNodePageContent()"></pre>
                </div>

                <!-- file download bottom bar -->
                <div
                    v-if="isDownloadingNodeFile"
                    class="flex w-full border-gray-300 dark:border-zinc-800 border-t p-2 dark:text-gray-100"
                >
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
                        class="my-auto text-white bg-red-600 hover:bg-red-700 dark:bg-red-700 dark:hover:bg-red-800 rounded px-3 py-1 text-sm font-semibold cursor-pointer"
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
                        class="my-auto inline-flex items-center gap-x-1 rounded-md bg-gray-500 px-2 py-1 text-sm font-semibold text-white shadow-sm hover:bg-gray-400 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-gray-500 dark:bg-zinc-800 dark:text-white dark:hover:bg-zinc-700 dark:focus-visible:outline-zinc-500"
                        @click.stop="openUrl"
                    >
                        {{ $t("nomadnet.open_nomadnet_url") }}
                    </button>
                </div>
            </div>
        </div>
    </div>
</template>

<script>
import MicronParser from "../../js/MicronParser";
import DialogUtils from "../../js/DialogUtils";
import WebSocketConnection from "../../js/WebSocketConnection";
import NomadNetworkSidebar from "./NomadNetworkSidebar.vue";
import Utils from "../../js/Utils";
import ToastUtils from "../../js/ToastUtils";
import MaterialDesignIcon from "../MaterialDesignIcon.vue";
import IconButton from "../IconButton.vue";
import DropDownMenu from "../DropDownMenu.vue";
import DropDownMenuItem from "../DropDownMenuItem.vue";
import GlobalState from "../../js/GlobalState";

export default {
    name: "NomadNetworkPage",
    components: {
        NomadNetworkSidebar,
        MaterialDesignIcon,
        IconButton,
        DropDownMenu,
        DropDownMenuItem,
    },
    props: {
        destinationHash: {
            type: String,
            required: true,
        },
    },
    data() {
        return {
            GlobalState,
            reloadInterval: null,
            nodesRefreshTimeout: null,
            abortController: new AbortController(),

            nodes: {},
            totalNodesCount: 0,
            hasMoreNodes: true,
            isLoadingMoreNodes: false,
            nodesSearchTerm: "",
            pageSize: 50,
            selectedNode: null,
            selectedNodePath: null,

            favourites: [],

            isLoadingNodePage: false,
            isShowingNodePageSource: false,
            defaultNodePagePath: "/page/index.mu",
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

            pageArchives: [],
            isArchiveDropdownOpen: false,
            isLoadingArchives: false,
            hasArchivesForCurrentPage: false,
            isShowingArchivedVersion: false,
            archivedAt: null,
            isSelectedNodeBlocked: false,

            pagePartials: {},
            partialIdsByKey: {},
            partialRefreshByKey: {},
            partialRefreshTimers: {},
        };
    },
    computed: {
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
            const phase = this.nodePageLoadPhase || "finding_path";
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
    },
    watch: {
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
    updated() {
        this.$nextTick(() => this.processPartials());
    },
    beforeUnmount() {
        if (this.nodesRefreshTimeout) clearTimeout(this.nodesRefreshTimeout);
        clearInterval(this.reloadInterval);
        this.abortController.abort();
        this.clearPartials();

        WebSocketConnection.off("message", this.onWebsocketMessage);
        window.document.removeEventListener("click", this.onElementClick);
    },
    mounted() {
        // listen for websocket messages
        WebSocketConnection.on("message", this.onWebsocketMessage);

        // listen for element clicks
        window.document.addEventListener("click", this.onElementClick);

        // load nomadnetwork node if a destination hash was provided on page load
        if (this.destinationHash) {
            (async () => {
                // fetch updated announce as we are probably loading node page before we loaded the announces list
                await this.getNomadnetworkNodeAnnounce(this.destinationHash);

                // set selected node so the viewer shows up
                if (this.nodes[this.destinationHash]) {
                    this.selectedNode = this.nodes[this.destinationHash];
                } else {
                    // if no announce found, create a placeholder node so we can still view archives
                    this.selectedNode = {
                        destination_hash: this.destinationHash,
                        display_name: "Unknown Node",
                        aspect: "nomadnetwork.node",
                    };
                }

                // get path to destination
                this.getNodePath(this.destinationHash);

                // check if we have a path or archive_id in query params
                const path = this.$route.query.path;
                const archiveId = this.$route.query.archive_id;

                if (archiveId) {
                    await this.loadArchivedPage(archiveId);
                } else if (path) {
                    await this.onNodePageUrlClick(`${this.destinationHash}:${path}`);
                } else {
                    await this.onNodePageUrlClick(`${this.destinationHash}:${this.defaultNodePagePath}`);
                }
            })();
        }

        this.getFavourites();
        this.getNomadnetworkNodeAnnounces();

        // update info every few seconds
        this.reloadInterval = setInterval(() => {
            this.getFavourites();
        }, 5000);
    },
    methods: {
        openNomadnetPopout() {
            if (!this.selectedNode) {
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
        onElementClick(event) {
            const element = event.target.closest('[data-action="openNode"]');
            if (!element) {
                return;
            }

            event.preventDefault();
            event.stopPropagation();

            const destination = element.getAttribute("data-destination");
            const fields = element.getAttribute("data-fields");

            this.onNodePageUrlClick(destination, fields);
        },
        async onWebsocketMessage(message) {
            const json = JSON.parse(message.data);
            switch (json.type) {
                case "announce": {
                    const aspect = json.announce.aspect;
                    if (aspect === "nomadnetwork.node") {
                        this.updateNodeFromAnnounce(json.announce);
                    }
                    break;
                }
                case "nomadnet.page.download": {
                    // get data from server
                    const nomadnetPageDownload = json.nomadnet_page_download;
                    const downloadId = json.download_id;

                    // get response page path
                    const responsePagePath = `${nomadnetPageDownload.destination_hash}:${nomadnetPageDownload.page_path}`;

                    // handle success for archived versions first (before path check)
                    if (nomadnetPageDownload.status === "success" && nomadnetPageDownload.is_archived_version) {
                        this.nodePagePath = responsePagePath;
                        this.nodePagePathUrlInput = responsePagePath;
                        this.isShowingArchivedVersion = true;
                        this.archivedAt = nomadnetPageDownload.archived_at;
                        this.nodePageContent = nomadnetPageDownload.page_content;
                        this.nodePageProgress = 100;
                        this.isLoadingNodePage = false;
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

                    // handle started status
                    if (nomadnetPageDownload.status === "started") {
                        this.currentPageDownloadId = downloadId;
                        this.nodePageLoadPhase = "finding_path";
                        return;
                    }

                    if (nomadnetPageDownload.status === "phase") {
                        if (this.currentPageDownloadId !== downloadId) {
                            return;
                        }
                        if (this.nodePagePath && responsePagePath !== this.nodePagePath) {
                            return;
                        }
                        this.nodePageLoadPhase = nomadnetPageDownload.load_phase || "finding_path";
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
                        this.currentPageDownloadId = null;
                        return;
                    }

                    // handle failure
                    if (nomadnetPageDownload.status === "failure" && nomadnetPageDownloadCallback.onFailureCallback) {
                        this.hasArchivesForCurrentPage = nomadnetPageDownload.has_archives;
                        nomadnetPageDownloadCallback.onFailureCallback(nomadnetPageDownload.failure_reason);
                        delete this.nomadnetPageDownloadCallbacks[getNomadnetPageDownloadCallbackKey];
                        this.currentPageDownloadId = null;
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
                    // get data from server
                    const nomadnetFileDownload = json.nomadnet_file_download;
                    const downloadId = json.download_id;

                    // handle started status
                    if (nomadnetFileDownload.status === "started") {
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
                        this.isLoadingNodePage = false;
                        this.nodePageContent = "Download cancelled";
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
        isFavourite(destinationHash) {
            return (
                this.favourites.find((favourite) => {
                    return favourite.destination_hash === destinationHash;
                }) != null
            );
        },
        async addFavourite(node) {
            // add to favourites
            try {
                await window.api.post("/api/v1/favourites/add", {
                    destination_hash: node.destination_hash,
                    display_name: node.display_name,
                    aspect: "nomadnetwork.node",
                });
            } catch (e) {
                console.log(e);
            }

            // update favourites
            this.getFavourites();
        },
        async removeFavourite(node) {
            // remove from favourites
            try {
                await window.api.delete(`/api/v1/favourites/${node.destination_hash}`);
            } catch (e) {
                console.log(e);
            }

            // update favourites
            this.getFavourites();
        },
        async getNomadnetworkNodeAnnounces(append = false) {
            try {
                const offset = append ? Object.keys(this.nodes).length : 0;
                const response = await window.api.get(`/api/v1/announces`, {
                    params: {
                        aspect: "nomadnetwork.node",
                        limit: this.pageSize,
                        offset: offset,
                        search: this.nodesSearchTerm,
                    },
                    signal: this.abortController.signal,
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
            }
        },
        async loadMoreNodes() {
            if (this.isLoadingMoreNodes || !this.hasMoreNodes) return;
            this.isLoadingMoreNodes = true;
            await this.getNomadnetworkNodeAnnounces(true);
        },
        onNodesSearchChanged(term) {
            this.nodesSearchTerm = term;
            if (this.nodesRefreshTimeout) {
                clearTimeout(this.nodesRefreshTimeout);
            }
            this.nodesRefreshTimeout = setTimeout(() => {
                this.getNomadnetworkNodeAnnounces();
            }, 500);
        },
        async getNomadnetworkNodeAnnounce(destinationHash) {
            try {
                const response = await window.api.get(`/api/v1/announces`, {
                    params: {
                        destination_hash: destinationHash,
                        limit: 1,
                    },
                    signal: this.abortController.signal,
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
        async loadNodePage(destinationHash, pagePath, fieldData = null, addToHistory = true, loadFromCache = true) {
            // update current route
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

            // get new sequence for this page load
            const seq = ++this.nodePageRequestSequence;

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
            this.nodePageLoadPhase = "finding_path";
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

            // check if we can load this page from the cache
            if (loadFromCache) {
                // load from cache
                const nodePagePathCacheKey = `${destinationHash}:${pagePath}`;
                const cachedNodePageContent = this.nodePageCache[nodePagePathCacheKey];

                // if page is cache, we can just return it now
                if (cachedNodePageContent != null) {
                    this.nodePageContent = cachedNodePageContent;
                    this.isLoadingNodePage = false;
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

                    // update cache
                    const nodePagePathCacheKey = `${destinationHash}:${pagePath}`;
                    this.nodePageCache[nodePagePathCacheKey] = this.nodePageContent;

                    // update status
                    this.isLoadingNodePage = false;
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
                }
            );
        },
        clearPartials() {
            Object.values(this.partialRefreshTimers).forEach((t) => clearTimeout(t));
            this.partialRefreshTimers = {};
            this.pagePartials = {};
            this.partialIdsByKey = {};
            this.partialRefreshByKey = {};
        },
        processPartials() {
            if (!this.selectedNode || !this.nodePagePath || !this.nodePageContent || this.isShowingNodePageSource)
                return;
            const [pagePathWithoutData] = this.nodePagePath.split("`");
            if (!pagePathWithoutData.endsWith(".mu")) return;

            const container = this.$el.querySelector(".nodeContainer");
            if (!container) return;

            const placeholders = container.querySelectorAll(".mu-partial");
            if (placeholders.length === 0) return;

            const idsByKey = {};
            const refreshByKey = {};
            const needLoad = new Set();

            const fieldsByKey = {};
            placeholders.forEach((el) => {
                const id = el.getAttribute("data-partial-id");
                const dest = el.getAttribute("data-dest");
                const path = el.getAttribute("data-path");
                const refreshAttr = el.getAttribute("data-refresh");
                const refresh = refreshAttr ? parseInt(refreshAttr, 10) : null;
                const fieldsStr = el.getAttribute("data-fields");
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
                if (!this.pagePartials[id]) needLoad.add(key);
            });

            this.partialIdsByKey = idsByKey;
            this.partialRefreshByKey = refreshByKey;

            const muParser = new MicronParser();
            const updatePartialDom = (html, ids) => {
                const container = this.$el.querySelector(".nodeContainer");
                if (!container) return;
                for (const { id } of ids) {
                    const el = container.querySelector(`[data-partial-id="${id}"]`);
                    if (el) {
                        el.innerHTML = html;
                    }
                }
            };
            needLoad.forEach((key) => {
                const colon = key.indexOf(":");
                const dest = key.slice(0, colon);
                const path = colon >= 0 ? key.slice(colon + 1) : "";
                const fields = fieldsByKey[key] || [];
                this.downloadNomadNetPage(
                    dest,
                    path,
                    fields,
                    (pageContent) => {
                        const html = muParser.convertMicronToHtml(pageContent);
                        const ids = this.partialIdsByKey[key];
                        if (ids) {
                            updatePartialDom(html, ids);
                        }
                        const refreshSec = this.partialRefreshByKey[key];
                        if (refreshSec != null && refreshSec > 0) {
                            const scheduleRefresh = () => {
                                this.partialRefreshTimers[key] = setTimeout(() => {
                                    this.downloadNomadNetPage(dest, path, fields, (content) => {
                                        const h = muParser.convertMicronToHtml(content);
                                        const idList = this.partialIdsByKey[key];
                                        if (idList) {
                                            updatePartialDom(h, idList);
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
        renderPageContent(path, content) {
            // render page content if we aren't viewing source
            if (!this.isShowingNodePageSource) {
                // check if page url ends with .mu but remove page data first
                // address:/page/index.mu`Data=123
                const [pagePathWithoutData] = path.split("`");

                // convert micron to html if page ends with .mu extension
                if (pagePathWithoutData.endsWith(".mu")) {
                    const muParser = new MicronParser();
                    return muParser.convertMicronToHtml(content, this.pagePartials);
                }
            }

            // otherwise, we will just serve the raw content, making sure to prevent injecting html
            return content
                .replace(/&/g, "&amp;")
                .replace(/</g, "&lt;")
                .replace(/>/g, "&gt;")
                .replace(/"/g, "&quot;")
                .replace(/'/g, "&#039;");
        },
        toggleNodePageSource() {
            this.isShowingNodePageSource = !this.isShowingNodePageSource;
        },
        async reloadNodePage() {
            // reload current node page without adding to history and without using cache
            this.onNodePageUrlClick(this.nodePagePath, null, false, false);
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

                return {
                    destination_hash: null, // node hash was not in provided url
                    path: path,
                };
            }

            // parse absolute urls such as 00000000000000000000000000000000:/page/index.mu
            if (url.includes(":")) {
                // parse destination hash and url
                const [destinationHash, ...relativeUrl] = url.split(":");

                // ensure destination is expected length
                if (destinationHash.length === 32) {
                    return {
                        destination_hash: destinationHash,
                        path: relativeUrl.join(":"),
                    };
                }
            }

            // parse node id only
            if (url.length === 32) {
                return {
                    destination_hash: url,
                    path: this.defaultNodePagePath,
                };
            }

            // unsupported url
            return null;
        },
        async onNodePageUrlClick(url, options = null, addToHistory = true, useCache = false) {
            let fieldData = [];

            if (options === "*") {
                useCache = false; // we want to send another request with the field data
                const inputs = document.querySelectorAll(".nodeContainer input");

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

                // Select inputs within the container
                const inputs = document.querySelectorAll(".nodeContainer input");

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

            console.log(fieldData);

            // open http urls in new tab
            if (url.startsWith("http://") || url.startsWith("https://")) {
                window.open(url, "_blank");
                return;
            }

            // lxmf urls should open the conversation
            if (url.startsWith("lxmf@")) {
                const destinationHash = url.replace("lxmf@", "");
                if (destinationHash.length === 32) {
                    const routeName = this.isPopoutMode ? "messages-popout" : "messages";
                    await this.$router.push({
                        name: routeName,
                        params: {
                            destinationHash: destinationHash,
                        },
                    });
                    return;
                }
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
                const destinationHash = parsedUrl.destination_hash || this.selectedNode.destination_hash;

                // download file
                if (parsedUrl.path.startsWith("/file/")) {
                    // prevent simultaneous downloads
                    if (this.isDownloadingNodeFile) {
                        ToastUtils.warning(this.$t("nomadnet.existing_download_in_progress"));
                        return;
                    }

                    // update ui
                    this.isDownloadingNodeFile = true;
                    this.nodeFilePath = parsedUrl.path.split("/").pop();
                    this.nodeFileProgress = 0;
                    this.nodeFileDownloadStartTime = Date.now();
                    this.nodeFileLastProgressTime = Date.now();
                    this.nodeFileLastProgressValue = 0;
                    this.nodeFileDownloadSpeed = null;

                    // start file download
                    this.downloadNomadNetFile(
                        destinationHash,
                        parsedUrl.path,
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
                this.selectedNode = this.nodes[destinationHash] || {
                    display_name: this.$t("nomadnet.unknown_node"),
                    destination_hash: destinationHash,
                };

                // navigate to node page
                this.loadNodePage(destinationHash, parsedUrl.path, fieldData, addToHistory, useCache);
                return;
            }

            // unsupported url
            ToastUtils.warning(this.$t("nomadnet.unsupported_url") + url);
        },
        downloadFileFromBase64: async function (fileName, fileBytesBase64) {
            // create blob from base64 encoded file bytes
            const byteCharacters = atob(fileBytesBase64);
            const byteNumbers = new Array(byteCharacters.length);
            for (let i = 0; i < byteCharacters.length; i++) {
                byteNumbers[i] = byteCharacters.charCodeAt(i);
            }
            const byteArray = new Uint8Array(byteNumbers);
            const blob = new Blob([byteArray]);

            // create object url for blob
            const objectUrl = URL.createObjectURL(blob);

            // create link element to download blob
            const link = document.createElement("a");
            link.href = objectUrl;
            link.download = fileName;
            link.style.display = "none";
            document.body.append(link);

            // click link to download file in browser
            link.click();

            // link element is no longer needed
            link.remove();

            // revoke object url to clear memory
            setTimeout(() => URL.revokeObjectURL(objectUrl), 10000);
        },
        formatBytesPerSecond: function (bytesPerSecond) {
            return Utils.formatBytesPerSecond(bytesPerSecond);
        },
        onNodeClick: function (node) {
            // update selected node
            this.selectedNode = node;

            // load default node page
            this.loadNodePage(node.destination_hash, this.defaultNodePagePath);
        },
        async onRenameFavourite(favourite) {
            // ask user for new display name
            const displayName = await DialogUtils.prompt(this.$t("nomadnet.rename_favourite"));
            if (displayName == null) {
                return;
            }

            try {
                // rename on server
                await window.api.post(`/api/v1/favourites/${favourite.destination_hash}/rename`, {
                    display_name: displayName,
                });

                // reload favourites
                await this.getFavourites();
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
        toggleArchiveDropdown() {
            this.isArchiveDropdownOpen = !this.isArchiveDropdownOpen;
            if (this.isArchiveDropdownOpen) {
                this.fetchArchives();
            }
        },
        fetchArchives() {
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
            this.isArchiveDropdownOpen = false;
            this.isLoadingNodePage = true;
            this.isShowingArchivedVersion = false;
            this.archivedAt = null;
            this.nodePageProgress = 0;
            this.pageLoadStartedAt = Date.now();
            this.nodePageLoadPhase = "finding_path";

            const archive = this.pageArchives.find((a) => a.id === archiveId);
            if (archive) {
                this.nodePagePath = `${archive.destination_hash}:${archive.page_path}`;
                this.nodePagePathUrlInput = this.nodePagePath;
            }

            WebSocketConnection.send(
                JSON.stringify({
                    type: "nomadnet.page.archive.load",
                    archive_id: archiveId,
                    download_id: Math.floor(Math.random() * 1000000),
                })
            );
        },
        manualArchive() {
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
            // clear previous known path
            this.selectedNodePath = null;

            try {
                // get path to destination
                const response = await window.api.get(`/api/v1/destination/${destinationHash}/path`);

                // update ui
                this.selectedNodePath = response.data.path;
            } catch (e) {
                console.log(e);
            }
        },
        async identify(destinationHash) {
            try {
                // ask user to confirm
                if (!(await DialogUtils.confirm(this.$t("nomadnet.identify_confirm")))) {
                    return;
                }

                // identify self to nomadnetwork node
                await window.api.post(`/api/v1/nomadnetwork/${destinationHash}/identify`);

                // reload page
                this.reloadNodePage();
            } catch (e) {
                ToastUtils.error(e.response?.data?.message ?? "Failed to identify!");
            }
        },
        getHashPopoutValue() {
            const hash = window.location.hash || "";
            const match = hash.match(/popout=([^&]+)/);
            return match ? decodeURIComponent(match[1]) : null;
        },
        downloadNomadNetFile(destinationHash, filePath, onSuccessCallback, onFailureCallback, onProgressCallback) {
            try {
                // set callbacks for nomadnet filePath download
                this.nomadnetFileDownloadCallbacks[this.getNomadnetFileDownloadCallbackKey(destinationHash, filePath)] =
                    {
                        onSuccessCallback: onSuccessCallback,
                        onFailureCallback: onFailureCallback,
                        onProgressCallback: onProgressCallback,
                    };

                // ask reticulum to download file from nomadnet
                WebSocketConnection.send(
                    JSON.stringify({
                        type: "nomadnet.file.download",
                        nomadnet_file_download: {
                            destination_hash: destinationHash,
                            file_path: filePath,
                        },
                    })
                );
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
            onProgressCallback
        ) {
            try {
                // set callbacks for nomadnet page download
                this.nomadnetPageDownloadCallbacks[this.getNomadnetPageDownloadCallbackKey(destinationHash, pagePath)] =
                    {
                        onSuccessCallback: onSuccessCallback,
                        onFailureCallback: onFailureCallback,
                        onProgressCallback: onProgressCallback,
                    };

                // ask reticulum to download page from nomadnet
                WebSocketConnection.send(
                    JSON.stringify({
                        type: "nomadnet.page.download",
                        nomadnet_page_download: {
                            destination_hash: destinationHash,
                            page_path: pagePath,
                            field_data: fieldData,
                        },
                    })
                );
            } catch (e) {
                console.error(e);
            }
        },
        renderedNodePageContent() {
            return this.renderPageContent(this.nodePagePath, this.nodePageContent);
        },
        cancelPageDownload() {
            if (this.currentPageDownloadId !== null) {
                WebSocketConnection.send(
                    JSON.stringify({
                        type: "nomadnet.download.cancel",
                        download_id: this.currentPageDownloadId,
                    })
                );
            }
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
.nodeContainer {
    font-family: "Roboto Mono Nerd Font", ui-monospace, monospace;
    letter-spacing: normal;
    font-variant-ligatures: none;
    font-feature-settings: normal;
}

.nodeContainer pre {
    font-family: inherit;
    line-height: normal;
    letter-spacing: inherit;
    font-variant-ligatures: inherit;
    font-feature-settings: inherit;
}

pre.text-wrap > div {
    display: flex;
    white-space: pre;
}

pre.text-wrap > div > :last-child {
    width: 100%;
    white-space: pre-wrap;
}

.nodeContainer pre a:hover {
    text-decoration: underline;
}

.nodeContainer input[type="text"],
.nodeContainer input[type="password"] {
    font-family: inherit;
    font-size: 1em;
    line-height: 1;
    padding: 0;
    margin: 0;
    border: 0;
    border-bottom: 1px solid currentColor;
    border-radius: 0;
    background: transparent;
    color: inherit;
    box-sizing: content-box;
}
</style>
