<!-- SPDX-License-Identifier: 0BSD -->

<script lang="ts">
    import { onMount, onDestroy } from "svelte";
    import GlobalState, { mergeGlobalConfig } from "../../../js/GlobalState.js";
    import GlobalEmitter from "../../../js/GlobalEmitter.js";
    import DialogUtils from "../../../js/DialogUtils.js";
    import LinkUtils from "../../../js/LinkUtils.js";
    import ToastUtils from "../../../js/ToastUtils.js";
    import { onWsEvent, offWsEvent } from "../../../js/registries/wsEventRegistry.js";
    import { isMicronWasmBundled, preloadNomadMicronWasm } from "../../../js/MicronWasmLoader.js";
    import {
        getEffectiveMicronWasmReleaseLabel,
        resolveMicronWasmReleaseLabel,
    } from "../../../js/micronWasmVersion.js";
    import { patchServerConfig } from "../../../js/settings/settingsConfigService.js";
    import DestinationPathModal from "./DestinationPathModal.svelte";
    import { t } from "../../../js/i18n.js";
    import NomadPageHeader from "./NomadPageHeader.svelte";
    import NomadBrowserToolbar from "./NomadBrowserToolbar.svelte";
    import NomadFileDownloadBar from "./NomadFileDownloadBar.svelte";
    import NomadPageRendererHost from "./NomadPageRendererHost.svelte";
    import NomadBrowserContextMenu from "./NomadBrowserContextMenu.svelte";
    import { DEFAULT_PAGE_PATH, PAGE_LOAD_TIMEOUT_MS } from "../lib/constants.js";
    import { parseNomadUrl, resolveRelativeNomadPath, encodeNomadFormQuery } from "../lib/nomadPageNavigation.js";
    import {
        requestPageArchives,
        requestArchiveLoad,
        requestManualArchive,
        fetchArchiveContent,
    } from "../lib/nomadPageArchives.js";
    import {
        createPageDownloadRequestPayload,
        createFileDownloadRequestPayload,
        createCancelDownloadPayload,
        discardDownloadChunks,
        sendNomadWs,
        relativePagePathFromCombined,
        isCancelledPageContent,
        isFailedPageContent,
        type NomadChunkBuffers,
    } from "../lib/nomadPageDownloads.js";
    import {
        shouldShowCrashTabHost,
        resolveCrashTabPageContent,
        canRetryCrashTabRender as resolveCanRetryCrashTabRender,
        resolveNomadCrashTabContentClass,
    } from "../lib/nomadCrashTabHost.js";
    import {
        onNomadDownloadCancelledEvent,
        onNomadFileDownloadEvent,
        onNomadPageArchiveAddedEvent,
        onNomadPageArchivesEvent,
        onNomadPageDownloadEvent,
        type NomadPageDownloadAccess,
    } from "../lib/nomadPageDownloadEvents.js";
    import { runNomadPathFinder } from "../lib/nomadPagePathFinder.js";
    import { buildNomadBrowserRendererChip, shouldShowMicronRendererInMobileMenu } from "../lib/nomadRendererChip.js";
    import type {
        NomadContextMenuState,
        NomadDestinationPath,
        NomadFavourite,
        NomadNavigateEvent,
        NomadNode,
        NomadPageArchive,
        NomadPageStats,
        NomadTab,
    } from "../lib/types.js";

    interface Props {
        destinationHash?: string;
        pagePath?: string;
        active?: boolean;
        isPopout?: boolean;
        isPrivate?: boolean;
        tabState?: NomadTab | null;
        favourites?: NomadFavourite[];
        nodes?: Record<string, NomadNode>;
        bootstrapArchiveId?: string | number | null;
        onnavigate?: (hash: string, path?: string, isPrivate?: boolean) => void;
        ontabtitlechange?: (title: string) => void;
        onclose?: () => void;
        ontabactivity?: () => void;
        onfavouriteschanged?: () => void;
    }

    let {
        destinationHash = "",
        pagePath = "",
        active = true,
        isPopout: _isPopout = false,
        isPrivate = false,
        tabState: _tabState = null,
        favourites = [],
        nodes = {},
        bootstrapArchiveId = null,
        onnavigate,
        ontabtitlechange,
        onclose,
        ontabactivity,
        onfavouriteschanged,
    }: Props = $props();

    let rendererHost = $state<any>(null);

    let selectedNode = $state<NomadNode | null>(null);
    let nodePagePath = $state<string | null>(null);
    let nodePagePathUrlInput = $state<string>("");
    let nodePageContent = $state<string | null>(null);
    let isShowingNodePageSource = $state(false);

    let isLoadingNodePage = $state(false);
    let isDownloadingNodeFile = $state(false);
    let nodeFileProgress = $state(0);
    let nodeFilePath = $state<string | null>(null);
    let nodeFileDownloadSpeed = $state<number | null>(null);
    let isShowingArchivedVersion = $state(false);
    let pageArchives = $state<NomadPageArchive[]>([]);
    let isArchiveDropdownOpen = $state(false);
    let archivedAt = $state<string | null>(null);
    let pageLoadTimeout = $state<ReturnType<typeof setTimeout> | null>(null);
    let currentPageDownloadId = $state<number | string | null>(null);
    let currentFileDownloadId = $state<number | string | null>(null);
    let pageRequestSequence = $state(0);
    let pendingPageCancelWithoutId = $state(false);
    let pathfinderInProgress = $state(false);
    let selectedNodePath = $state<NomadDestinationPath | null>(null);
    let nodeContainerShellStyle = $state("");
    let nomadShellDark = $state(false);
    let nomadRenderedShellFullBleed = $state(false);
    let pageRenderAborted = $state(false);
    let isCrashTabRendering = $state(false);
    let multilineHintVisible = $state(false);
    let pagePartials = $state<Record<string, string>>({});
    let downloadBytesReceived = $state(0);
    let downloadTotalBytes = $state(0);
    let downloadStartTime = $state<number | null>(null);
    let pathHistory = $state<string[]>([]);
    let destinationPathModalShowing = $state(false);
    let selectedDestinationPathHash = $state("");
    let selectedDestinationPathHops = $state(0);
    let lastAppliedRouteKey = $state("");
    let lastLoadedKey = $state("");
    let nodePageCache = $state<Record<string, string>>({});
    let nomadMicronWasmReady = $state(false);
    let micronWasmReleaseLabel = $state(resolveMicronWasmReleaseLabel() || "");
    let nomadPageDownloadChunkBuffers: NomadChunkBuffers = {};
    let nomadFileDownloadChunkBuffers: NomadChunkBuffers = {};

    let contextMenu = $state<NomadContextMenuState>({
        show: false,
        justOpened: false,
        x: 0,
        y: 0,
        tabId: null,
    });

    const isFavouriteNode = $derived.by(() => {
        const hash = selectedNode?.destination_hash;
        if (!hash) return false;
        return favourites.some((f) => f.destination_hash === hash);
    });

    const selectedNodeIdentifiesOnConnect = $derived.by(() => {
        const hash = selectedNode?.destination_hash;
        if (!hash || isPrivate) return false;
        return favourites.some((f) => f.destination_hash === hash && Boolean(f.identify_on_connect));
    });

    const relativePagePath = $derived(relativePagePathFromCombined(nodePagePath));

    const navbarPageStats = $derived.by((): NomadPageStats | null => {
        if (!nodePageContent && !isLoadingNodePage) return null;
        let duration = "";
        if (downloadStartTime) {
            const sec = Math.max(0.1, (Date.now() - downloadStartTime) / 1000);
            duration = `${sec.toFixed(1)}s`;
        }
        const size = downloadTotalBytes || (nodePageContent ? nodePageContent.length : 0);
        const sizeLabel = size > 1024 ? `${(size / 1024).toFixed(1)} KB` : `${size} B`;
        return { duration, sizeLabel };
    });

    const nomadMicronWasmFeatureEffective = $derived(
        Boolean(isMicronWasmBundled()) && GlobalState.config?.nomad_micron_wasm_enabled === true
    );

    const nomadMicronWasmActive = $derived(
        Boolean(
            nomadMicronWasmFeatureEffective &&
            nomadMicronWasmReady &&
            typeof globalThis.micronConvert === "function" &&
            (GlobalState.config?.nomad_micron_default_engine || "js") === "wasm"
        )
    );

    const nomadBrowserRendererChip = $derived(
        buildNomadBrowserRendererChip({
            selectedNode,
            relativePagePath,
            isShowingNodePageSource,
            nomadMicronWasmActive,
            nomadMicronWasmFeatureEffective,
            nomadMicronWasmReady,
            defaultEngine: String(GlobalState.config?.nomad_micron_default_engine || "js"),
            micronGoRelease: micronWasmReleaseLabel,
            t,
        })
    );

    const showMicronRendererInMobileMenu = $derived(
        shouldShowMicronRendererInMobileMenu({
            wasmBundled: isMicronWasmBundled(),
            selectedNode,
            relativePagePath,
            isShowingNodePageSource,
        })
    );

    const nomadRenderOptions = $derived({
        renderMarkdown: GlobalState.config?.nomad_render_markdown_enabled !== false,
        renderHtml: GlobalState.config?.nomad_render_html_enabled !== false,
        renderPlaintext: GlobalState.config?.nomad_render_plaintext_enabled !== false,
        nomadDestinationHash: selectedNode?.destination_hash || null,
        nomad_micron_wasm_use: Boolean(nomadMicronWasmActive),
    });

    const nodePagePathIsMicronMu = $derived.by(() => {
        const [p] = String(relativePagePath || "").split("`");
        return (p || "").toLowerCase().endsWith(".mu");
    });

    const showCancelledPageState = $derived(
        pageRenderAborted ||
            isCancelledPageContent(nodePageContent) ||
            (nodePageContent === null && !isLoadingNodePage && !isDownloadingNodeFile && !!selectedNode)
    );
    const showEmptyPageState = $derived(!isLoadingNodePage && !isDownloadingNodeFile && nodePageContent === "");
    const showCrashTabHost = $derived(
        shouldShowCrashTabHost({
            selectedNode,
            nodePagePath,
            showCancelledPageState,
            nodePageContent,
            showEmptyPageState,
        })
    );
    const crashTabPageContent = $derived(
        resolveCrashTabPageContent({
            isLoadingNodePage,
            nodePageContent,
        })
    );
    const canRetryCrashTabRender = $derived(
        resolveCanRetryCrashTabRender({
            pageRenderAborted,
            nodePageContent,
        })
    );
    const nomadCrashTabContentClass = $derived(
        resolveNomadCrashTabContentClass({
            nodePagePath,
            isShowingNodePageSource,
            nomadRenderedShellFullBleed,
            nomadShellDark,
        })
    );
    const nomadCrashTabColor = $derived.by(() => {
        if (isShowingNodePageSource) {
            return "#dddddd";
        }
        if (nomadRenderedShellFullBleed) {
            return nomadShellDark ? "#f3f4f6" : "#111827";
        }
        if (!nodePagePath) {
            return "#dddddd";
        }
        const [p] = nodePagePath.split("`");
        const pl = (p || "").toLowerCase();
        if (pl.endsWith(".mu")) {
            return "#dddddd";
        }
        return "#f3f4f6";
    });
    // Do not feed shell-background postMessage into the iframe background prop.
    const nomadCrashTabBackground = "#000000";
    const showPageBusyBanner = $derived(isLoadingNodePage || isCrashTabRendering);
    const pageBusyBannerLine = $derived.by(() => {
        if (isLoadingNodePage) {
            return downloadTotalBytes > 0
                ? `${t("nomadnet.loading_page")} (${downloadBytesReceived}/${downloadTotalBytes} bytes)`
                : t("nomadnet.loading_page");
        }
        return t("nomadnet.load_phase_default");
    });

    function beginCrashTabRenderWait() {
        if (nodePageContent && !isFailedPageContent(nodePageContent) && !isCancelledPageContent(nodePageContent)) {
            isCrashTabRendering = true;
        }
    }

    function clearPageLoadTimeout() {
        if (pageLoadTimeout) {
            clearTimeout(pageLoadTimeout);
            pageLoadTimeout = null;
        }
    }

    function armPageLoadTimeout() {
        clearPageLoadTimeout();
        pageLoadTimeout = setTimeout(() => {
            if (isLoadingNodePage) {
                isLoadingNodePage = false;
                currentPageDownloadId = null;
                nodePageContent = t("nomadnet.failed_to_load_page");
            }
        }, PAGE_LOAD_TIMEOUT_MS);
    }

    async function setDestination(destHash: string, pPath: string = DEFAULT_PAGE_PATH) {
        if (!destHash) return;
        selectedNode = nodes[destHash] || {
            destination_hash: destHash,
            display_name: destHash.substring(0, 16),
        };
        await loadPage(destHash, pPath || DEFAULT_PAGE_PATH, { loadFromCache: true });
    }

    async function loadPage(destHash: string, pPath: string, options: { loadFromCache?: boolean } = {}) {
        if (!destHash) return;
        const loadFromCache = options.loadFromCache !== false;
        const relativePath = pPath || DEFAULT_PAGE_PATH;
        const cacheKey = `${destHash}:${relativePath}`;
        const loadKey = `${destHash}:${relativePath}:${isPrivate ? 1 : 0}`;

        if (loadFromCache && !isPrivate) {
            const cached = nodePageCache[cacheKey];
            if (cached != null) {
                pageRequestSequence += 1;
                pendingPageCancelWithoutId = false;
                pageRenderAborted = false;
                isCrashTabRendering = false;
                isLoadingNodePage = false;
                isShowingArchivedVersion = false;
                archivedAt = null;
                nodePageContent = cached;
                pageArchives = [];
                downloadStartTime = Date.now();
                downloadBytesReceived = 0;
                downloadTotalBytes = new TextEncoder().encode(cached).length;
                currentPageDownloadId = null;
                nodePagePath = cacheKey;
                nodePagePathUrlInput = nodePagePath;
                lastLoadedKey = loadKey;
                clearPageLoadTimeout();
                beginCrashTabRenderWait();
                requestPageArchives(destHash, relativePath);
                return;
            }
        }

        if (loadKey === lastLoadedKey && nodePageContent && !isLoadingNodePage && loadFromCache) {
            return;
        }
        lastLoadedKey = loadKey;

        pageRequestSequence += 1;
        const seq = pageRequestSequence;
        pendingPageCancelWithoutId = false;
        pageRenderAborted = false;
        isCrashTabRendering = false;
        isLoadingNodePage = true;
        isShowingArchivedVersion = false;
        archivedAt = null;
        nodePageContent = null;
        pageArchives = [];
        downloadStartTime = Date.now();
        downloadBytesReceived = 0;
        downloadTotalBytes = 0;
        if (currentPageDownloadId != null) {
            discardDownloadChunks(nomadPageDownloadChunkBuffers, currentPageDownloadId);
        }
        currentPageDownloadId = null;
        nodePagePath = `${destHash}:${relativePath}`;
        nodePagePathUrlInput = nodePagePath;

        armPageLoadTimeout();

        if (!isPrivate) {
            requestPageArchives(destHash, relativePath);
        }

        const payload = createPageDownloadRequestPayload(destHash, relativePath, isPrivate);
        const sent = sendNomadWs(payload);
        if (!sent) {
            if (seq !== pageRequestSequence) return;
            clearPageLoadTimeout();
            isLoadingNodePage = false;
            nodePageContent = t("nomadnet.failed_to_load_page");
            ToastUtils.error(t("nomadnet.websocket_not_connected"));
            return;
        }
        ontabactivity?.();
    }

    function reloadCurrentPage() {
        if (selectedNode?.destination_hash && relativePagePath) {
            lastLoadedKey = "";
            void loadPage(selectedNode.destination_hash, relativePagePath, { loadFromCache: false });
        }
    }

    const downloadAccess: NomadPageDownloadAccess = {
        get: () => ({
            active,
            isPrivate,
            currentPageDownloadId,
            pendingPageCancelWithoutId,
            currentFileDownloadId,
            nodeFilePath,
            selectedNode,
            relativePagePath,
            nodePagePath,
            nodePageCache,
            nomadPageDownloadChunkBuffers,
            nomadFileDownloadChunkBuffers,
        }),
        apply(patch) {
            if (patch.currentPageDownloadId !== undefined) currentPageDownloadId = patch.currentPageDownloadId;
            if (patch.pendingPageCancelWithoutId !== undefined) {
                pendingPageCancelWithoutId = patch.pendingPageCancelWithoutId;
            }
            if (patch.currentFileDownloadId !== undefined) currentFileDownloadId = patch.currentFileDownloadId;
            if (patch.downloadTotalBytes !== undefined) downloadTotalBytes = patch.downloadTotalBytes;
            if (patch.downloadBytesReceived !== undefined) downloadBytesReceived = patch.downloadBytesReceived;
            if (patch.nodePagePath !== undefined) nodePagePath = patch.nodePagePath;
            if (patch.nodePagePathUrlInput !== undefined) nodePagePathUrlInput = patch.nodePagePathUrlInput;
            if (patch.isShowingArchivedVersion !== undefined) {
                isShowingArchivedVersion = patch.isShowingArchivedVersion;
            }
            if (patch.archivedAt !== undefined) archivedAt = patch.archivedAt;
            if (patch.nodePageContent !== undefined) nodePageContent = patch.nodePageContent;
            if (patch.isLoadingNodePage !== undefined) isLoadingNodePage = patch.isLoadingNodePage;
            if (patch.nodePageCache !== undefined) nodePageCache = patch.nodePageCache;
            if (patch.isDownloadingNodeFile !== undefined) isDownloadingNodeFile = patch.isDownloadingNodeFile;
            if (patch.nodeFilePath !== undefined) nodeFilePath = patch.nodeFilePath;
            if (patch.nodeFileProgress !== undefined) nodeFileProgress = patch.nodeFileProgress;
            if (patch.nodeFileDownloadSpeed !== undefined) nodeFileDownloadSpeed = patch.nodeFileDownloadSpeed;
            if (patch.pageRenderAborted !== undefined) pageRenderAborted = patch.pageRenderAborted;
            if (patch.pageArchives !== undefined) pageArchives = patch.pageArchives;
            if (
                patch.nodePageContent !== undefined &&
                patch.isLoadingNodePage === false &&
                typeof patch.nodePageContent === "string"
            ) {
                beginCrashTabRenderWait();
            }
        },
        clearPageLoadTimeout,
        get ontabtitlechange() {
            return ontabtitlechange;
        },
    };

    async function runPathFinder(mode: "quick" | "force" | "drop_then_request") {
        const hash = selectedNode?.destination_hash;
        if (!hash || pathfinderInProgress) return;
        pathfinderInProgress = true;
        try {
            await runNomadPathFinder({
                destinationHash: hash,
                mode,
                onReload: reloadCurrentPage,
            });
        } finally {
            pathfinderInProgress = false;
        }
    }

    function onPageDownloadEvent(json: Record<string, unknown>) {
        onNomadPageDownloadEvent(downloadAccess, json);
    }

    function onFileDownloadEvent(json: Record<string, unknown>) {
        onNomadFileDownloadEvent(downloadAccess, json);
    }

    function onDownloadCancelledEvent(json: Record<string, unknown>) {
        onNomadDownloadCancelledEvent(downloadAccess, json);
    }

    function onPageArchivesEvent(json: Record<string, unknown>) {
        onNomadPageArchivesEvent(downloadAccess, json);
    }

    function onPageArchiveAddedEvent(json: Record<string, unknown>) {
        onNomadPageArchiveAddedEvent(downloadAccess, json);
    }

    function handleNavigate(e: NomadNavigateEvent) {
        if (!e.url) return;
        if (LinkUtils.httpUrlHrefOrNull(e.url)) {
            window.open(e.url, "_blank");
            return;
        }
        const { destinationHash: dHash, pagePath: pPath } = parseNomadUrl(e.url);
        if (dHash) {
            const targetPath = pPath || DEFAULT_PAGE_PATH;
            if (nodePagePath) pathHistory.push(nodePagePath);
            selectedNode = nodes[dHash] || {
                destination_hash: dHash,
                display_name: dHash.substring(0, 16),
            };
            void loadPage(dHash, targetPath, { loadFromCache: false });
            onnavigate?.(dHash, targetPath, isPrivate);
        } else if (selectedNode?.destination_hash && pPath) {
            const resolved = resolveRelativeNomadPath(relativePagePath || "/", pPath);
            if (e.fields && Object.keys(e.fields).length > 0) {
                const query = encodeNomadFormQuery(e.fields);
                const full = `${resolved}?${query}`;
                if (nodePagePath) pathHistory.push(nodePagePath);
                void loadPage(selectedNode.destination_hash, full, { loadFromCache: false });
            } else {
                if (nodePagePath) pathHistory.push(nodePagePath);
                void loadPage(selectedNode.destination_hash, resolved, { loadFromCache: false });
            }
        }
    }

    function handleUrlSubmit(url: string) {
        const { destinationHash: dHash, pagePath: pPath } = parseNomadUrl(url);
        if (dHash) {
            selectedNode = nodes[dHash] || {
                destination_hash: dHash,
                display_name: dHash.substring(0, 16),
            };
            void loadPage(dHash, pPath || DEFAULT_PAGE_PATH, { loadFromCache: false });
            onnavigate?.(dHash, pPath || DEFAULT_PAGE_PATH, isPrivate);
        }
    }

    function handleCancel() {
        const cancellingDownload =
            isLoadingNodePage ||
            currentPageDownloadId != null ||
            pendingPageCancelWithoutId ||
            isDownloadingNodeFile ||
            currentFileDownloadId != null;

        if (cancellingDownload) {
            if (currentPageDownloadId != null) {
                discardDownloadChunks(nomadPageDownloadChunkBuffers, currentPageDownloadId);
                sendNomadWs(createCancelDownloadPayload(currentPageDownloadId));
                currentPageDownloadId = null;
            } else if (isLoadingNodePage) {
                pendingPageCancelWithoutId = true;
            }
            if (currentFileDownloadId != null) {
                discardDownloadChunks(nomadFileDownloadChunkBuffers, currentFileDownloadId);
                sendNomadWs(createCancelDownloadPayload(currentFileDownloadId));
                currentFileDownloadId = null;
            }
            clearPageLoadTimeout();
            isLoadingNodePage = false;
            isDownloadingNodeFile = false;
            isCrashTabRendering = false;
            pageRenderAborted = false;
            if (!nodePageContent) {
                nodePageContent = "nomadnet.page_download_cancelled";
            }
            return;
        }

        if (isCrashTabRendering) {
            rendererHost?.abortRender();
            isCrashTabRendering = false;
        }
    }

    function handleBack() {
        if (pathHistory.length > 0) {
            const prev = pathHistory.pop();
            if (!prev) return;
            const { destinationHash: dHash, pagePath: pPath } = parseNomadUrl(
                prev.includes("://") ? prev : `nomadnet://${prev}`
            );
            if (dHash) {
                void loadPage(dHash, pPath || DEFAULT_PAGE_PATH, { loadFromCache: true });
            } else if (selectedNode?.destination_hash) {
                const relative = relativePagePathFromCombined(prev) || prev;
                void loadPage(selectedNode.destination_hash, relative, { loadFromCache: true });
            }
        }
    }

    function handleManualArchive() {
        if (isPrivate) {
            ToastUtils.info(t("nomadnet.private_browsing_hint"));
            return;
        }
        if (!selectedNode?.destination_hash || !relativePagePath || !nodePageContent) return;
        ToastUtils.info(t("nomadnet.archiving_page"));
        requestManualArchive(selectedNode.destination_hash, relativePagePath, nodePageContent);
    }

    function handleLoadArchivedPage(archiveId: string | number) {
        if (isPrivate) {
            ToastUtils.info(t("nomadnet.private_browsing_hint"));
            return;
        }
        isArchiveDropdownOpen = false;
        isLoadingNodePage = true;
        isShowingArchivedVersion = false;
        archivedAt = null;
        pageRenderAborted = false;
        armPageLoadTimeout();

        const archive = pageArchives.find((a) => String(a.id) === String(archiveId));
        if (archive) {
            nodePagePath = `${archive.destination_hash}:${archive.page_path}`;
            nodePagePathUrlInput = nodePagePath;
        }

        // Own the reply even when the local archive list is empty or stale.
        const downloadId = Math.floor(Math.random() * 1000000);
        currentPageDownloadId = downloadId;
        const sent = requestArchiveLoad(archiveId, downloadId);
        if (!sent) {
            clearPageLoadTimeout();
            isLoadingNodePage = false;
            currentPageDownloadId = null;
            ToastUtils.error(t("nomadnet.tab_restore_failed"));
        }
    }

    async function toggleIdentifyOnConnect() {
        if (isPrivate) {
            ToastUtils.info(t("nomadnet.private_browsing_hint"));
            return;
        }
        const destinationHashValue = selectedNode?.destination_hash;
        if (!destinationHashValue) return;
        const api = (window as any).api;
        if (!api) return;
        const currentlyOn = selectedNodeIdentifiesOnConnect;
        const enable = !currentlyOn;
        try {
            if (enable) {
                if (!(await DialogUtils.confirm(t("nomadnet.identify_confirm")))) {
                    return;
                }
            }
            const existing = favourites.find((f) => f.destination_hash === destinationHashValue);
            const displayName =
                selectedNode?.custom_display_name ||
                selectedNode?.display_name ||
                existing?.custom_display_name ||
                existing?.display_name ||
                t("nomadnet.unknown_node");
            await api.post(`/api/v1/favourites/${destinationHashValue}/identify-on-connect`, {
                enabled: enable,
                display_name: displayName,
                aspect: "nomadnetwork.node",
            });
            onfavouriteschanged?.();
            GlobalEmitter.emit("nomadnet-favourites-changed");
            if (enable && relativePagePath) {
                lastLoadedKey = "";
                await loadPage(destinationHashValue, relativePagePath, { loadFromCache: false });
            }
        } catch (e: any) {
            ToastUtils.error(e?.response?.data?.message ?? t("nomadnet.identify_on_connect_failed"));
        }
    }

    async function applyBootstrapArchive(archiveId: string | number) {
        const api = (window as any).api;
        if (!api) {
            handleLoadArchivedPage(archiveId);
            return;
        }
        try {
            const result = await fetchArchiveContent(api, archiveId);
            if (result && result.content) {
                if (result.page_path && selectedNode?.destination_hash) {
                    nodePagePath = `${selectedNode.destination_hash}:${result.page_path}`;
                    nodePagePathUrlInput = nodePagePath;
                }
                nodePageContent = result.content;
                isShowingArchivedVersion = true;
                archivedAt = result.created_at || null;
                isLoadingNodePage = false;
                clearPageLoadTimeout();
                if (selectedNode?.destination_hash && relativePagePath) {
                    requestPageArchives(selectedNode.destination_hash, relativePagePath);
                }
                return;
            }
        } catch {
            // fall through to WS load
        }
        handleLoadArchivedPage(archiveId);
    }

    function handleContextMenu(e: MouseEvent) {
        e.preventDefault();
        contextMenu = {
            show: true,
            justOpened: true,
            x: e.clientX,
            y: e.clientY,
            tabId: null,
        };
        setTimeout(() => {
            contextMenu.justOpened = false;
        }, 50);
    }

    function forceMicronPageRerender() {
        if (!nodePageContent || !nodePagePathIsMicronMu) return;
        const content = nodePageContent;
        nodePageContent = null;
        queueMicrotask(() => {
            nodePageContent = content;
        });
    }

    async function applyNomadMicronDefaultEngine(engine: string) {
        if (!isMicronWasmBundled()) return;
        if (!GlobalState.config?.nomad_micron_wasm_enabled) return;
        const next = engine === "wasm" ? "wasm" : "js";
        if ((GlobalState.config?.nomad_micron_default_engine || "js") === next) return;
        try {
            const cfg = await patchServerConfig({ nomad_micron_default_engine: next }, window.api);
            mergeGlobalConfig(cfg);
            forceMicronPageRerender();
        } catch (e) {
            console.error("Failed to update Micron default engine", e);
            ToastUtils.error(t("nomadnet.renderer_setting_failed"));
        }
    }

    function openNomadnetPopout() {
        if (isPrivate || !selectedNode?.destination_hash) return;
        const encodedHash = encodeURIComponent(selectedNode.destination_hash);
        const url = `${window.location.origin}${window.location.pathname}#/popout/nomadnetwork/${encodedHash}`;
        window.open(url, "_blank", "width=1100,height=800,noopener");
    }

    $effect(() => {
        if (!active) return;
        const nextHash = destinationHash || "";
        const nextPath = pagePath || DEFAULT_PAGE_PATH;
        const archiveId = bootstrapArchiveId;
        const routeKey = `${nextHash}|${nextPath}|${archiveId ?? ""}|${isPrivate ? 1 : 0}`;
        if (!nextHash || routeKey === lastAppliedRouteKey) return;
        lastAppliedRouteKey = routeKey;
        void (async () => {
            await setDestination(nextHash, nextPath);
            if (archiveId != null) {
                await applyBootstrapArchive(archiveId);
            }
        })();
    });

    onMount(() => {
        onWsEvent("nomadnet.page.download", onPageDownloadEvent);
        onWsEvent("nomadnet.file.download", onFileDownloadEvent);
        onWsEvent("nomadnet.download.cancelled", onDownloadCancelledEvent);
        onWsEvent("nomadnet.page.archives", onPageArchivesEvent);
        onWsEvent("nomadnet.page.archive.added", onPageArchiveAddedEvent);
        if (isMicronWasmBundled() && GlobalState.config?.nomad_micron_wasm_enabled === true) {
            void preloadNomadMicronWasm().then((ok) => {
                nomadMicronWasmReady = ok === true;
                if (ok) forceMicronPageRerender();
            });
        }
        void getEffectiveMicronWasmReleaseLabel().then((label) => {
            if (label) micronWasmReleaseLabel = label;
        });
    });

    onDestroy(() => {
        offWsEvent("nomadnet.page.download", onPageDownloadEvent);
        offWsEvent("nomadnet.file.download", onFileDownloadEvent);
        offWsEvent("nomadnet.download.cancelled", onDownloadCancelledEvent);
        offWsEvent("nomadnet.page.archives", onPageArchivesEvent);
        offWsEvent("nomadnet.page.archive.added", onPageArchiveAddedEvent);
        clearPageLoadTimeout();
    });
</script>

<div
    class="flex-1 min-h-0 flex flex-col bg-black text-white relative {!destinationHash ? 'max-sm:hidden' : ''}"
    class:hidden={!active}
>
    {#if selectedNode}
        <NomadPageHeader
            {selectedNode}
            {isPrivate}
            {isFavouriteNode}
            {selectedNodePath}
            {navbarPageStats}
            rendererChip={nomadBrowserRendererChip}
            {isLoadingNodePage}
            {showMicronRendererInMobileMenu}
            {pageArchives}
            {nodePageContent}
            {isArchiveDropdownOpen}
            identifiesOnConnect={selectedNodeIdentifiesOnConnect}
            isShowingSource={isShowingNodePageSource}
            ontogglefavourite={() => {
                if (isFavouriteNode) {
                    GlobalEmitter.emit("nomadnet-remove-favourite", selectedNode);
                } else {
                    GlobalEmitter.emit("nomadnet-add-favourite", selectedNode);
                }
            }}
            onpathclick={(p) => {
                if (selectedNode?.destination_hash) {
                    selectedDestinationPathHash = selectedNode.destination_hash;
                    selectedDestinationPathHops = Number(p?.hops ?? 0);
                    destinationPathModalShowing = true;
                }
            }}
            ontogglearchivedropdown={() => {
                isArchiveDropdownOpen = !isArchiveDropdownOpen;
            }}
            onmanualarchive={handleManualArchive}
            onloadarchivedpage={(id) => handleLoadArchivedPage(id)}
            ontoggleidentifyonconnect={() => void toggleIdentifyOnConnect()}
            onpopout={() => openNomadnetPopout()}
            onclosenode={() => {
                selectedNode = null;
                lastAppliedRouteKey = "";
                nodePageContent = null;
                nodePagePath = "";
                onnavigate?.("", DEFAULT_PAGE_PATH, isPrivate);
            }}
            ontogglesource={() => {
                isShowingNodePageSource = !isShowingNodePageSource;
            }}
            onapplymicronengine={(eng) => {
                void applyNomadMicronDefaultEngine(eng);
            }}
        />

        <NomadBrowserToolbar
            {selectedNode}
            urlInput={nodePagePathUrlInput}
            isShowingSource={isShowingNodePageSource}
            hasHistory={pathHistory.length > 0}
            {pathfinderInProgress}
            hasArchives={pageArchives.length > 0}
            {isPrivate}
            onhome={() => {
                if (selectedNode?.destination_hash) {
                    lastLoadedKey = "";
                    void loadPage(selectedNode.destination_hash, DEFAULT_PAGE_PATH, { loadFromCache: true });
                }
            }}
            onrefresh={() => {
                reloadCurrentPage();
            }}
            ontogglesource={() => {
                isShowingNodePageSource = !isShowingNodePageSource;
            }}
            onback={handleBack}
            onurlsubmit={handleUrlSubmit}
            onurlchange={(v) => {
                nodePagePathUrlInput = v;
            }}
            onpathfinderquick={() => {
                void runPathFinder("quick");
            }}
            onpathfinderforce={() => {
                void runPathFinder("force");
            }}
            onpathfinderdrop={() => {
                void runPathFinder("drop_then_request");
            }}
            onloadlatestarchive={() => {
                if (pageArchives.length > 0) {
                    handleLoadArchivedPage(pageArchives[0].id);
                }
            }}
        />

        <NomadFileDownloadBar
            isDownloading={isDownloadingNodeFile}
            filePath={nodeFilePath}
            progress={nodeFileProgress}
            downloadSpeed={nodeFileDownloadSpeed}
            oncancel={handleCancel}
        />

        <NomadPageRendererHost
            bind:this={rendererHost}
            {selectedNode}
            {nodePagePath}
            {nodePageContent}
            {isShowingArchivedVersion}
            {archivedAt}
            {showPageBusyBanner}
            {pageBusyBannerLine}
            {showCancelledPageState}
            {pageRenderAborted}
            {canRetryCrashTabRender}
            hasArchivesForCurrentPage={pageArchives.length > 0}
            {isPrivate}
            {showEmptyPageState}
            {showCrashTabHost}
            {crashTabPageContent}
            {isShowingNodePageSource}
            {pagePartials}
            {nomadRenderOptions}
            {nomadCrashTabContentClass}
            {nomadCrashTabColor}
            {nomadCrashTabBackground}
            {active}
            {multilineHintVisible}
            {nomadRenderedShellFullBleed}
            {nomadShellDark}
            {nodeContainerShellStyle}
            onreload={() => {
                reloadCurrentPage();
            }}
            oncancelbusy={handleCancel}
            onretrycrashtab={() => {
                pageRenderAborted = false;
                isCrashTabRendering = true;
                rendererHost?.reloadFrame();
            }}
            ontogglearchive={() => {
                if (pageArchives.length > 0) {
                    handleLoadArchivedPage(pageArchives[0].id);
                }
            }}
            oncontentcontextmenu={handleContextMenu}
            oncrashtabnavigate={handleNavigate}
            oncrashtabpartials={(_p) => {}}
            onviewsource={() => {
                isShowingNodePageSource = !isShowingNodePageSource;
            }}
            oncrashtabhung={() => {
                isCrashTabRendering = false;
                ToastUtils.warning(t("nomadnet.crash_tab_hung_toast"));
            }}
            oncrashtabrenderstarted={() => {
                isCrashTabRendering = true;
            }}
            oncrashtabrenderdone={() => {
                isCrashTabRendering = false;
            }}
            oncrashtababorted={() => {
                isCrashTabRendering = false;
                pageRenderAborted = true;
                ToastUtils.info(t("nomadnet.crash_tab_render_cancelled"));
            }}
        />
    {:else}
        <div class="flex-1 flex items-center justify-center text-sem-fg-muted p-8 text-center">
            <div>
                <div class="text-xl font-semibold mb-2">{t("nomadnet.welcome_to_nomadnet")}</div>
                <div class="text-sm max-w-md">{t("nomadnet.select_node_or_enter_url")}</div>
            </div>
        </div>
    {/if}

    <NomadBrowserContextMenu
        show={contextMenu.show}
        x={contextMenu.x}
        y={contextMenu.y}
        justOpened={contextMenu.justOpened}
        hasActivePage={!!nodePageContent}
        canFavourite={!!selectedNode && !isPrivate}
        isFavourite={isFavouriteNode}
        canDownloadPage={!!nodePageContent && !isPrivate}
        showTabActions={false}
        contextTabIsPrivate={isPrivate}
        onclose={() => {
            contextMenu.show = false;
        }}
        onviewsource={() => {
            isShowingNodePageSource = !isShowingNodePageSource;
        }}
        onreload={() => {
            reloadCurrentPage();
        }}
        onfavorite={() => {
            if (selectedNode) {
                GlobalEmitter.emit("nomadnet-add-favourite", selectedNode);
            }
        }}
        ondownloadpage={() => {
            if (selectedNode?.destination_hash && relativePagePath) {
                sendNomadWs(
                    createFileDownloadRequestPayload(selectedNode.destination_hash, relativePagePath, isPrivate)
                );
            }
        }}
        onnewprivatetab={() => {
            onnavigate?.(destinationHash, pagePath, true);
        }}
    />

    {#if destinationPathModalShowing}
        <DestinationPathModal
            destinationHash={selectedDestinationPathHash}
            hops={selectedDestinationPathHops}
            onclose={() => {
                destinationPathModalShowing = false;
            }}
        />
    {/if}
</div>
