<!-- SPDX-License-Identifier: 0BSD -->

<script lang="ts">
    import { onMount, onDestroy } from "svelte";
    import GlobalState from "../../../js/GlobalState.js";
    import GlobalEmitter from "../../../js/GlobalEmitter.js";
    import WebSocketConnection from "../../../js/WebSocketConnection.js";
    import DialogUtils from "../../../js/DialogUtils.js";
    import LinkUtils from "../../../js/LinkUtils.js";
    import DestinationPathModal from "./DestinationPathModal.svelte";
    import { t } from "../../../js/i18n.js";
    import NomadPageHeader from "./NomadPageHeader.svelte";
    import NomadBrowserToolbar from "./NomadBrowserToolbar.svelte";
    import NomadFileDownloadBar from "./NomadFileDownloadBar.svelte";
    import NomadPageRendererHost from "./NomadPageRendererHost.svelte";
    import NomadBrowserContextMenu from "./NomadBrowserContextMenu.svelte";
    import { DEFAULT_PAGE_PATH, PAGE_LOAD_TIMEOUT_MS } from "../lib/constants.js";
    import {
        parseNomadUrl,
        buildNomadUrl,
        resolveRelativeNomadPath,
        encodeNomadFormQuery,
    } from "../lib/nomadPageNavigation.js";
    import { fetchPageArchives, createManualArchive, fetchArchiveContent } from "../lib/nomadPageArchives.js";
    import {
        createPageDownloadRequestPayload,
        createFileDownloadRequestPayload,
        createCancelDownloadPayload,
    } from "../lib/nomadPageDownloads.js";
    import type {
        NomadContextMenuState,
        NomadDestinationPath,
        NomadFavourite,
        NomadNavigateEvent,
        NomadNode,
        NomadPageArchive,
        NomadPageRendererChip,
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
        onnavigate?: (hash: string, path?: string, isPrivate?: boolean) => void;
        ontabtitlechange?: (title: string) => void;
        onclose?: () => void;
        ontabactivity?: () => void;
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
        onnavigate,
        ontabtitlechange,
        onclose,
        ontabactivity,
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
    let downloadRequestId = $state<string | null>(null);
    let pathfinderInProgress = $state(false);
    let selectedNodePath = $state<NomadDestinationPath | null>(null);
    let selectedNodeIdentifiesOnConnect = $state(false);
    let nodeContainerShellStyle = $state("");
    let nomadShellDark = $state(false);
    let nomadCrashTabColor = $state("");
    let nomadCrashTabBackground = $state("#000000");
    let nomadRenderedShellFullBleed = $state(false);
    let nomadCrashTabContentClass = $state("");
    let pageRenderAborted = $state(false);
    let multilineHintVisible = $state(false);
    let pagePartials = $state<Record<string, string>>({});
    let downloadBytesReceived = $state(0);
    let downloadTotalBytes = $state(0);
    let downloadStartTime = $state<number | null>(null);
    let pathHistory = $state<string[]>([]);
    let destinationPathModalShowing = $state(false);
    let selectedDestinationPathHash = $state("");
    let selectedDestinationPathHops = $state(0);

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

    const nomadBrowserRendererChip = $derived.by((): NomadPageRendererChip | null => {
        const engine = GlobalState.config?.nomad_micron_default_engine || "js";
        const wasmEnabled = !!GlobalState.config?.nomad_micron_wasm_enabled;
        return {
            label: engine === "wasm" && wasmEnabled ? "Micron WASM" : "Micron JS",
            popoverVariant: engine === "wasm" && wasmEnabled ? "wasm_active" : "js_active",
            micronGoRelease: "v0.1.0",
            tooltipBody: t("nomadnet.renderer_tooltip"),
        };
    });

    const showMicronRendererInMobileMenu = $derived(!!GlobalState.config?.nomad_micron_wasm_enabled);

    const nomadRenderOptions = $derived({
        engine: GlobalState.config?.nomad_micron_default_engine || "js",
        wasmEnabled: !!GlobalState.config?.nomad_micron_wasm_enabled,
    });

    const showPageBusyBanner = $derived(isLoadingNodePage && !nodePageContent);
    const pageBusyBannerLine = $derived(
        downloadTotalBytes > 0
            ? `${t("nomadnet.loading_page")} (${downloadBytesReceived}/${downloadTotalBytes} bytes)`
            : t("nomadnet.loading_page")
    );
    const showCancelledPageState = $derived(
        pageRenderAborted ||
            (nodePageContent === null && !isLoadingNodePage && !isDownloadingNodeFile && !!selectedNode)
    );
    const showEmptyPageState = $derived(!isLoadingNodePage && !isDownloadingNodeFile && nodePageContent === "");
    const showCrashTabHost = $derived(!!nodePageContent && !isLoadingNodePage && !showCancelledPageState);

    async function setDestination(destHash: string, pPath: string = DEFAULT_PAGE_PATH) {
        if (!destHash) return;
        selectedNode = nodes[destHash] || {
            destination_hash: destHash,
            display_name: destHash.substring(0, 16),
        };
        nodePagePath = pPath || DEFAULT_PAGE_PATH;
        nodePagePathUrlInput = buildNomadUrl(destHash, nodePagePath);
        await loadPage(destHash, nodePagePath);
    }

    async function loadPage(destHash: string, pPath: string) {
        if (!destHash) return;
        isLoadingNodePage = true;
        pageRenderAborted = false;
        nodePageContent = null;
        downloadStartTime = Date.now();
        downloadBytesReceived = 0;
        downloadTotalBytes = 0;

        if (pageLoadTimeout) clearTimeout(pageLoadTimeout);
        pageLoadTimeout = setTimeout(() => {
            if (isLoadingNodePage) {
                isLoadingNodePage = false;
                nodePageContent = t("nomadnet.failed_to_load_page");
            }
        }, PAGE_LOAD_TIMEOUT_MS);

        if (!isPrivate) {
            fetchArchives(destHash, pPath);
        }

        const payload = createPageDownloadRequestPayload(destHash, pPath, isPrivate);
        downloadRequestId = payload.request_id;
        WebSocketConnection.send(payload);
        ontabactivity?.();
    }

    async function fetchArchives(destHash: string, pPath: string) {
        const api = (window as any).api;
        if (!api) return;
        try {
            pageArchives = await fetchPageArchives(api, destHash, pPath);
        } catch {
            pageArchives = [];
        }
    }

    function handleWsMessage(event: CustomEvent) {
        const data = event.detail;
        if (!data) return;

        if (data.type === "nomadnet.page_download_progress" && data.request_id === downloadRequestId) {
            downloadBytesReceived = data.bytes_received || 0;
            downloadTotalBytes = data.total_bytes || 0;
        } else if (data.type === "nomadnet.page_download_completed" && data.request_id === downloadRequestId) {
            if (pageLoadTimeout) clearTimeout(pageLoadTimeout);
            isLoadingNodePage = false;
            nodePageContent = data.content || "";
            isShowingArchivedVersion = false;
            ontabtitlechange?.(selectedNode?.custom_display_name || selectedNode?.display_name || "Nomad");
        } else if (data.type === "nomadnet.page_download_failed" && data.request_id === downloadRequestId) {
            if (pageLoadTimeout) clearTimeout(pageLoadTimeout);
            isLoadingNodePage = false;
            nodePageContent = data.error || t("nomadnet.failed_to_load_page");
        } else if (data.type === "nomadnet.file_download_progress" && data.request_id === downloadRequestId) {
            isDownloadingNodeFile = true;
            nodeFileProgress = data.progress || 0;
            nodeFilePath = data.file_path || "";
            nodeFileDownloadSpeed = data.speed || null;
        } else if (data.type === "nomadnet.file_download_completed" && data.request_id === downloadRequestId) {
            isDownloadingNodeFile = false;
            DialogUtils.alert(t("nomadnet.file_download_complete", { path: data.file_path }));
        }
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
            setDestination(dHash, targetPath);
            onnavigate?.(dHash, targetPath, isPrivate);
        } else if (selectedNode?.destination_hash && pPath) {
            const resolved = resolveRelativeNomadPath(nodePagePath || "/", pPath);
            if (e.fields && Object.keys(e.fields).length > 0) {
                const query = encodeNomadFormQuery(e.fields);
                const full = `${resolved}?${query}`;
                if (nodePagePath) pathHistory.push(nodePagePath);
                loadPage(selectedNode.destination_hash, full);
            } else {
                if (nodePagePath) pathHistory.push(nodePagePath);
                loadPage(selectedNode.destination_hash, resolved);
            }
        }
    }

    function handleUrlSubmit(url: string) {
        const { destinationHash: dHash, pagePath: pPath } = parseNomadUrl(url);
        if (dHash) {
            setDestination(dHash, pPath || DEFAULT_PAGE_PATH);
            onnavigate?.(dHash, pPath || DEFAULT_PAGE_PATH, isPrivate);
        }
    }

    function handleCancel() {
        if (downloadRequestId) {
            WebSocketConnection.send(createCancelDownloadPayload({ downloadId: downloadRequestId }));
        }
        if (pageLoadTimeout) clearTimeout(pageLoadTimeout);
        isLoadingNodePage = false;
        isDownloadingNodeFile = false;
    }

    function handleBack() {
        if (pathHistory.length > 0 && selectedNode?.destination_hash) {
            const prev = pathHistory.pop();
            if (prev) loadPage(selectedNode.destination_hash, prev);
        }
    }

    async function handleManualArchive() {
        const api = (window as any).api;
        if (!api || !selectedNode?.destination_hash || !nodePagePath || !nodePageContent) return;
        const res = await createManualArchive(api, selectedNode.destination_hash, nodePagePath, nodePageContent);
        if (res) {
            DialogUtils.alert(t("nomadnet.archive_created"));
            void fetchArchives(selectedNode.destination_hash, nodePagePath);
        }
    }

    async function handleLoadArchivedPage(archiveId: string | number) {
        const api = (window as any).api;
        if (!api) return;
        isArchiveDropdownOpen = false;
        const arch = pageArchives.find((a) => String(a.id) === String(archiveId));
        if (arch) {
            const result = await fetchArchiveContent(api, arch.id);
            if (result !== null) {
                nodePageContent = typeof result === "string" ? result : result.content;
                isShowingArchivedVersion = true;
                archivedAt = typeof result === "object" && result.created_at ? result.created_at : arch.created_at;
            }
        }
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

    $effect(() => {
        if (destinationHash && destinationHash !== selectedNode?.destination_hash) {
            setDestination(destinationHash, pagePath || DEFAULT_PAGE_PATH);
        }
    });

    onMount(() => {
        GlobalEmitter.on("ws-message", handleWsMessage);
        if (destinationHash) {
            setDestination(destinationHash, pagePath || DEFAULT_PAGE_PATH);
        }
    });

    onDestroy(() => {
        GlobalEmitter.off("ws-message", handleWsMessage);
        if (pageLoadTimeout) clearTimeout(pageLoadTimeout);
    });
</script>

<div class="flex-1 min-h-0 flex flex-col bg-black text-white relative">
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
            onmanualarchive={() => void handleManualArchive()}
            onloadarchivedpage={(id) => void handleLoadArchivedPage(id)}
            ontoggleidentifyonconnect={() => {
                selectedNodeIdentifiesOnConnect = !selectedNodeIdentifiesOnConnect;
            }}
            onpopout={() => {
                const target = `/popout/nomadnetwork/${selectedNode?.destination_hash}`;
                window.open(target, "_blank", "width=960,height=720");
            }}
            onclosenode={() => onclose?.()}
            ontogglesource={() => {
                isShowingNodePageSource = !isShowingNodePageSource;
            }}
            onapplymicronengine={(eng) => {
                if (GlobalState.config) {
                    GlobalState.config.nomad_micron_default_engine = eng;
                }
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
                    loadPage(selectedNode.destination_hash, DEFAULT_PAGE_PATH);
                }
            }}
            onrefresh={() => {
                if (selectedNode?.destination_hash && nodePagePath) {
                    loadPage(selectedNode.destination_hash, nodePagePath);
                }
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
                if (selectedNode?.destination_hash) {
                    WebSocketConnection.send({
                        type: "path_probe.request_path",
                        destination_hash: selectedNode.destination_hash,
                    });
                }
            }}
            onpathfinderforce={() => {
                if (selectedNode?.destination_hash) {
                    WebSocketConnection.send({
                        type: "path_probe.force_path",
                        destination_hash: selectedNode.destination_hash,
                    });
                }
            }}
            onpathfinderdrop={() => {
                if (selectedNode?.destination_hash) {
                    WebSocketConnection.send({
                        type: "path_probe.drop_path",
                        destination_hash: selectedNode.destination_hash,
                    });
                }
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
            canRetryCrashTabRender={true}
            hasArchivesForCurrentPage={pageArchives.length > 0}
            {isPrivate}
            {showEmptyPageState}
            {showCrashTabHost}
            crashTabPageContent={nodePageContent || ""}
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
                if (selectedNode?.destination_hash && nodePagePath) {
                    loadPage(selectedNode.destination_hash, nodePagePath);
                }
            }}
            oncancelbusy={handleCancel}
            onretrycrashtab={() => {
                rendererHost?.reloadFrame();
            }}
            ontogglearchive={() => {
                if (pageArchives.length > 0) {
                    handleLoadArchivedPage(pageArchives[0].id);
                }
            }}
            oncontentcontextmenu={handleContextMenu}
            oncrashtabnavigate={handleNavigate}
            oncrashtabpartials={(_p) => {
                // handle partial updates
            }}
            onviewsource={() => {
                isShowingNodePageSource = !isShowingNodePageSource;
            }}
            oncrashtabshellbackground={(bg) => {
                nomadCrashTabBackground = bg || "#000000";
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
        canFavourite={!!selectedNode}
        isFavourite={isFavouriteNode}
        canDownloadPage={!!nodePageContent}
        showTabActions={false}
        contextTabIsPrivate={isPrivate}
        onclose={() => {
            contextMenu.show = false;
        }}
        onviewsource={() => {
            isShowingNodePageSource = !isShowingNodePageSource;
        }}
        onreload={() => {
            if (selectedNode?.destination_hash && nodePagePath) {
                loadPage(selectedNode.destination_hash, nodePagePath);
            }
        }}
        onfavorite={() => {
            if (selectedNode) {
                GlobalEmitter.emit("nomadnet-add-favourite", selectedNode);
            }
        }}
        ondownloadpage={() => {
            if (selectedNode?.destination_hash && nodePagePath) {
                const payload = createFileDownloadRequestPayload(selectedNode.destination_hash, nodePagePath);
                WebSocketConnection.send(payload);
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
