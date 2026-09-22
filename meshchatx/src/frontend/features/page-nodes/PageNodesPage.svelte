<!-- SPDX-License-Identifier: 0BSD -->

<script lang="ts">
    import { onDestroy, onMount } from "svelte";
    import DialogUtils from "../../js/DialogUtils.js";
    import GlobalEmitter from "../../js/GlobalEmitter.js";
    import { t } from "../../js/i18n.js";
    import ToastUtils from "../../js/ToastUtils.js";
    import MaterialDesignIcon from "../../ui/svelte/MaterialDesignIcon.svelte";
    import ToolsPageHeader from "../../ui/svelte/ToolsPageHeader.svelte";
    import EmptyState from "../../ui/svelte/EmptyState.svelte";
    import LoadingState from "../../ui/svelte/LoadingState.svelte";
    import PageNodeCreateModal from "./components/PageNodeCreateModal.svelte";
    import PageNodeDetail from "./components/PageNodeDetail.svelte";
    import PageNodeItem from "./components/PageNodeItem.svelte";
    import PageNodeRenameModal from "./components/PageNodeRenameModal.svelte";
    import { DEFAULT_ANNOUNCE_INTERVAL_SECONDS, PAGE_NODE_TABS, type PageNodeDetailTab } from "./lib/constants.js";
    import {
        announcePageNode,
        createPage,
        createPageNode,
        deleteFile,
        deletePage,
        deletePageNode,
        fetchPage,
        fetchPageNodes,
        renamePageNode,
        savePage,
        startPageNode,
        stopPageNode,
        updateAnnounceSettings,
        uploadFile,
    } from "./lib/pageNodesApi.js";
    import {
        announceMinutesToSeconds,
        formatLastAnnounced,
        resolveAnnounceIntervalSeconds,
        secondsToAnnounceMinutes,
    } from "./lib/pageNodesFormat.js";
    import type { AnnounceSettingsForm, PageNode } from "./lib/types.js";

    let nodes = $state<PageNode[]>([]);
    let loading = $state(true);
    let selectedNode = $state<PageNode | null>(null);
    let detailTab = $state<PageNodeDetailTab>(PAGE_NODE_TABS.PAGES);
    let showCreateDialog = $state(false);
    let showRenameDialog = $state(false);

    let announceSettingsForm = $state<AnnounceSettingsForm>({
        announce_enabled: true,
        announce_interval_seconds: DEFAULT_ANNOUNCE_INTERVAL_SECONDS,
        executable_pages_enabled: false,
    });
    let announceIntervalMinutes = $state(15);

    let editingPage = $state<string | null>(null);
    let editingPageContent = $state("");
    let editingPageExecutable = $state(false);

    const lastAnnouncedText = $derived(selectedNode ? formatLastAnnounced(selectedNode.last_announced_at) : "");

    function onWebsocketReconnected() {
        void loadNodes();
    }

    onMount(() => {
        GlobalEmitter.on("websocket-reconnected", onWebsocketReconnected);
        void loadNodes();
    });

    onDestroy(() => {
        GlobalEmitter.off("websocket-reconnected", onWebsocketReconnected);
    });

    async function loadNodes() {
        loading = true;
        try {
            nodes = await fetchPageNodes();
            if (selectedNode) {
                const updated = nodes.find((n) => n.node_id === selectedNode?.node_id);
                if (updated) {
                    selectedNode = updated;
                } else {
                    selectedNode = null;
                }
            }
        } catch {
            ToastUtils.error(t("tools.mesh_server.failed_load"));
        } finally {
            loading = false;
        }
    }

    function selectNode(node: PageNode) {
        selectedNode = node;
        detailTab = PAGE_NODE_TABS.PAGES;
        editingPage = null;
        announceIntervalMinutes = secondsToAnnounceMinutes(node.announce_interval_seconds);
        announceSettingsForm = {
            announce_enabled: node.announce_enabled !== false,
            announce_interval_seconds: resolveAnnounceIntervalSeconds(node.announce_interval_seconds),
            executable_pages_enabled: node.executable_pages_enabled === true,
        };
    }

    async function handleCreateNode(name: string) {
        try {
            await createPageNode(name);
            showCreateDialog = false;
            ToastUtils.success(t("tools.mesh_server.created"));
            await loadNodes();
        } catch (e: unknown) {
            const err = e as { response?: { data?: { message?: string } } };
            ToastUtils.error(err.response?.data?.message || t("tools.mesh_server.failed_create"));
        }
    }

    async function handleDeleteNode(nodeId: string) {
        if (!(await DialogUtils.confirm(t("tools.mesh_server.delete_confirm")))) {
            return;
        }
        try {
            await deletePageNode(nodeId);
            if (selectedNode && selectedNode.node_id === nodeId) {
                selectedNode = null;
            }
            ToastUtils.success(t("tools.mesh_server.deleted"));
            await loadNodes();
        } catch {
            ToastUtils.error(t("tools.mesh_server.failed_delete"));
        }
    }

    async function handleStartNode(nodeId: string) {
        try {
            const response = await startPageNode(nodeId);
            ToastUtils.success(
                t("tools.mesh_server.started", {
                    hash: response.destination_hash,
                })
            );
            await loadNodes();
        } catch (e: unknown) {
            const err = e as { response?: { data?: { message?: string } } };
            ToastUtils.error(err.response?.data?.message || t("tools.mesh_server.failed_start"));
        }
    }

    async function handleStopNode(nodeId: string) {
        try {
            await stopPageNode(nodeId);
            ToastUtils.success(t("tools.mesh_server.stopped"));
            await loadNodes();
        } catch {
            ToastUtils.error(t("tools.mesh_server.failed_stop"));
        }
    }

    async function handleAnnounceNode(nodeId: string) {
        try {
            await announcePageNode(nodeId);
            ToastUtils.success(t("tools.mesh_server.announced"));
            await loadNodes();
        } catch {
            ToastUtils.error(t("tools.mesh_server.failed_announce"));
        }
    }

    async function handleSaveAnnounceSettings() {
        if (!selectedNode) return;
        try {
            const seconds = announceMinutesToSeconds(announceIntervalMinutes);
            const response = await updateAnnounceSettings(selectedNode.node_id, {
                announce_enabled: announceSettingsForm.announce_enabled,
                announce_interval_seconds: seconds,
                executable_pages_enabled: announceSettingsForm.executable_pages_enabled,
            });
            selectedNode = response;
            ToastUtils.success(t("tools.mesh_server.announce_settings_saved"));
            await loadNodes();
        } catch {
            ToastUtils.error(t("tools.mesh_server.announce_settings_failed"));
        }
    }

    async function handleRenameNode(newName: string) {
        if (!selectedNode) return;
        try {
            await renamePageNode(selectedNode.node_id, newName);
            showRenameDialog = false;
            ToastUtils.success(t("tools.mesh_server.renamed"));
            await loadNodes();
        } catch {
            ToastUtils.error(t("tools.mesh_server.failed_rename"));
        }
    }

    async function handleAddPage(pageName: string) {
        if (!selectedNode) return;
        try {
            await createPage(selectedNode.node_id, pageName);
            ToastUtils.success(t("tools.mesh_server.page_created"));
            await loadNodes();
        } catch {
            ToastUtils.error(t("tools.mesh_server.failed_page_create"));
        }
    }

    async function handleEditPage(pageName: string) {
        if (!selectedNode) return;
        try {
            const pageData = await fetchPage(selectedNode.node_id, pageName);
            editingPage = pageName;
            editingPageContent = pageData.content ?? "";
            editingPageExecutable = pageData.executable === true;
        } catch {
            ToastUtils.error(t("tools.mesh_server.failed_page_load"));
        }
    }

    async function handleSavePage() {
        if (!editingPage || !selectedNode) return;
        try {
            await savePage(selectedNode.node_id, editingPage, editingPageContent, editingPageExecutable);
            editingPage = null;
            editingPageContent = "";
            editingPageExecutable = false;
            ToastUtils.success(t("tools.mesh_server.page_saved"));
            await loadNodes();
        } catch {
            ToastUtils.error(t("tools.mesh_server.failed_page_save"));
        }
    }

    async function handleDeletePage(pageName: string) {
        if (!selectedNode) return;
        if (
            !(await DialogUtils.confirm(
                t("tools.mesh_server.delete_page_confirm", {
                    name: pageName,
                })
            ))
        ) {
            return;
        }
        try {
            await deletePage(selectedNode.node_id, pageName);
            if (editingPage === pageName) {
                editingPage = null;
            }
            ToastUtils.success(t("tools.mesh_server.page_deleted"));
            await loadNodes();
        } catch {
            ToastUtils.error(t("tools.mesh_server.failed_page_delete"));
        }
    }

    async function handleUploadFile(file: File) {
        if (!selectedNode) return;
        try {
            await uploadFile(selectedNode.node_id, file);
            ToastUtils.success(t("tools.mesh_server.file_uploaded"));
            await loadNodes();
        } catch {
            ToastUtils.error(t("tools.mesh_server.failed_file_upload"));
        }
    }

    async function handleDeleteFile(fileName: string) {
        if (!selectedNode) return;
        if (
            !(await DialogUtils.confirm(
                t("tools.mesh_server.delete_file_confirm", {
                    name: fileName,
                })
            ))
        ) {
            return;
        }
        try {
            await deleteFile(selectedNode.node_id, fileName);
            ToastUtils.success(t("tools.mesh_server.file_deleted"));
            await loadNodes();
        } catch {
            ToastUtils.error(t("tools.mesh_server.failed_file_delete"));
        }
    }

    function viewNode(node: PageNode) {
        if (node.destination_hash) {
            window.location.hash = `#/nomadnetwork/${encodeURIComponent(node.destination_hash)}`;
        }
    }
</script>

<div class="flex flex-col flex-1 overflow-hidden min-w-0 bg-sem-canvas">
    <ToolsPageHeader
        icon="server-network"
        title={t("tools.mesh_server.title")}
        description={t("tools.mesh_server.description")}
        accent="amber"
    >
        <button
            type="button"
            class="primary-chip focus-ring-sem px-4 py-2 text-sm shrink-0"
            onclick={() => (showCreateDialog = true)}
        >
            <MaterialDesignIcon iconName="plus" class="w-4 h-4" />
            {t("tools.mesh_server.create_node")}
        </button>
    </ToolsPageHeader>

    <div class="flex-1 overflow-y-auto overflow-x-hidden w-full px-3 sm:px-5 md:px-5 lg:px-8 py-3 sm:py-4 min-w-0">
        <div class="space-y-0 w-full max-w-6xl xl:max-w-7xl mx-auto min-w-0">
            {#if loading}
                <div class="w-full py-8 sm:py-12">
                    <LoadingState message={t("tools.mesh_server.loading")} />
                </div>
            {:else if nodes.length === 0}
                <div class="w-full py-8 sm:py-12">
                    <EmptyState
                        icon="server-network"
                        title={t("tools.mesh_server.empty_title")}
                        description={t("tools.mesh_server.empty_description")}
                    />
                </div>
            {:else}
                <div class="w-full divide-y divide-gray-200/60 dark:divide-zinc-800/60">
                    {#each nodes as node (node.node_id)}
                        <PageNodeItem
                            {node}
                            isSelected={selectedNode?.node_id === node.node_id}
                            onSelect={selectNode}
                            onStart={handleStartNode}
                            onStop={handleStopNode}
                            onAnnounce={handleAnnounceNode}
                            onView={viewNode}
                            onDelete={handleDeleteNode}
                        />
                    {/each}
                </div>
            {/if}

            {#if selectedNode}
                <PageNodeDetail
                    {selectedNode}
                    bind:detailTab
                    bind:announceEnabled={announceSettingsForm.announce_enabled}
                    bind:announceIntervalMinutes
                    bind:executablePagesEnabled={announceSettingsForm.executable_pages_enabled}
                    {lastAnnouncedText}
                    {editingPage}
                    bind:editingPageContent
                    bind:editingPageExecutable
                    onRenameClick={() => (showRenameDialog = true)}
                    onClose={() => (selectedNode = null)}
                    onViewNode={viewNode}
                    onSaveAnnounceSettings={handleSaveAnnounceSettings}
                    onTabChange={(tab) => (detailTab = tab)}
                    onAddPage={handleAddPage}
                    onEditPage={handleEditPage}
                    onDeletePage={handleDeletePage}
                    onSavePage={handleSavePage}
                    onCancelEditPage={() => (editingPage = null)}
                    onUploadFile={handleUploadFile}
                    onDeleteFile={handleDeleteFile}
                />
            {/if}
        </div>
    </div>

    <PageNodeCreateModal
        open={showCreateDialog}
        onClose={() => (showCreateDialog = false)}
        onCreate={handleCreateNode}
    />

    <PageNodeRenameModal
        open={showRenameDialog}
        placeholderName={selectedNode ? selectedNode.name : ""}
        onClose={() => (showRenameDialog = false)}
        onRename={handleRenameNode}
    />
</div>
