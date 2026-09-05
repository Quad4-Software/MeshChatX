<!-- SPDX-License-Identifier: 0BSD -->

<script lang="ts">
    import { onMount, onDestroy } from "svelte";
    import ToolsPageHeader from "../../ui/svelte/ToolsPageHeader.svelte";
    import ToastUtils from "../../js/ToastUtils.js";
    import ElectronUtils from "../../js/ElectronUtils.js";
    import GlobalEmitter from "../../js/GlobalEmitter.js";
    import { t } from "../../js/i18n.js";
    import { onWsEvent, offWsEvent } from "../../js/registries/wsEventRegistry.js";
    import {
        announceFilesyncNow,
        browseFilesyncPeer,
        connectFilesyncPeer,
        disconnectFilesyncPeer,
        downloadFilesyncRemoteFile,
        fetchFilesyncAcl,
        fetchFilesyncPeers,
        fetchFilesyncStatus,
        fetchSharedDirectorySuggestion,
        grantFilesyncAcl,
        startFilesyncService,
        stopFilesyncService,
        updateFilesyncSettings,
    } from "./lib/filesyncApi.js";
    import { FILESYNC_TABS } from "./lib/constants.js";
    import type {
        AclRules,
        FilesyncPeer,
        FilesyncProgressPayload,
        FilesyncRemoteFile,
        FilesyncStatus,
        FilesyncTabId,
    } from "./lib/types.js";
    import FilesyncFolderTab from "./components/FilesyncFolderTab.svelte";
    import FilesyncDevicesTab from "./components/FilesyncDevicesTab.svelte";
    import FilesyncFileManager from "./components/FilesyncFileManager.svelte";
    import FilesyncRemoteTab from "./components/FilesyncRemoteTab.svelte";
    import FilesyncSharingTab from "./components/FilesyncSharingTab.svelte";
    import FilesyncDirectoryBrowserModal from "./components/FilesyncDirectoryBrowserModal.svelte";

    let activeTab = $state<FilesyncTabId>("folder");
    let busy = $state(false);
    let status = $state<FilesyncStatus>({
        running: false,
        peers: 0,
        files: 0,
        destination_hash: null,
        sync_directory: "",
        storage_directory: "",
    });
    let syncDirectory = $state("");
    let announceInterval = $state(300);
    let monitor = $state(true);
    let connectHash = $state("");
    let peers = $state<FilesyncPeer[]>([]);
    let browsePeerId = $state("");
    let remoteFiles = $state<FilesyncRemoteFile[]>([]);
    let aclEnforce = $state(false);
    let aclHash = $state("");
    let aclRead = $state(true);
    let aclWrite = $state(false);
    let aclDelete = $state(false);
    let aclRules = $state<AclRules>({});
    let lastProgress = $state<FilesyncProgressPayload | null>(null);
    let directoryBrowserOpen = $state(false);

    let fileManagerRef = $state<ReturnType<typeof FilesyncFileManager> | null>(null);
    let wsHandlers: [string, (payload: any) => void][] = [];

    async function refreshStatus(): Promise<void> {
        try {
            const data = await fetchFilesyncStatus();
            status = data;
            if (data.sync_directory) {
                syncDirectory = data.sync_directory;
            }
            if (typeof data.announce_interval === "number") {
                announceInterval = data.announce_interval;
            }
            if (typeof data.monitor === "boolean") {
                monitor = data.monitor;
            }
        } catch (err: unknown) {
            const error = err as { message?: string };
            ToastUtils.error(error?.message || t("rns_filesync.error"));
        }
    }

    async function refreshPeers(): Promise<void> {
        try {
            peers = await fetchFilesyncPeers();
        } catch (err: unknown) {
            const error = err as { message?: string };
            ToastUtils.error(error?.message || t("rns_filesync.error"));
        }
    }

    async function refreshAcl(): Promise<void> {
        try {
            const data = await fetchFilesyncAcl();
            aclEnforce = data.enforce;
            aclRules = data.rules;
        } catch (err: unknown) {
            const error = err as { message?: string };
            ToastUtils.error(error?.message || t("rns_filesync.error"));
        }
    }

    async function refreshFileManager(): Promise<void> {
        if (fileManagerRef && typeof fileManagerRef.refresh === "function") {
            await fileManagerRef.refresh();
        }
    }

    async function refreshAll(): Promise<void> {
        await Promise.all([refreshStatus(), refreshPeers(), refreshAcl()]);
        await refreshFileManager();
    }

    function openDirectoryBrowser(): void {
        if (status.running) {
            ToastUtils.warning(t("rns_filesync.stop_before_change_folder"));
            return;
        }
        directoryBrowserOpen = true;
    }

    async function useSharedFolder(): Promise<void> {
        if (status.running) {
            ToastUtils.warning(t("rns_filesync.stop_before_change_folder"));
            return;
        }
        const win = typeof window !== "undefined" ? (window as any) : null;
        const bridge = win?.MeshChatXAndroid;
        if (bridge && typeof bridge.hasAllFilesAccess === "function") {
            let hasAccess = false;
            try {
                hasAccess = Boolean(bridge.hasAllFilesAccess());
            } catch {
                hasAccess = false;
            }
            if (!hasAccess && typeof bridge.requestAllFilesAccess === "function") {
                bridge.requestAllFilesAccess();
                ToastUtils.info(t("rns_filesync.shared_folder_permission_needed"));
                return;
            }
        }
        busy = true;
        try {
            const path = await fetchSharedDirectorySuggestion();
            if (!path) {
                ToastUtils.error(t("rns_filesync.error"));
                return;
            }
            syncDirectory = path;
            ToastUtils.success(t("rns_filesync.shared_folder_selected"));
        } catch (err: unknown) {
            const error = err as { message?: string };
            ToastUtils.error(error?.message || t("rns_filesync.error"));
        } finally {
            busy = false;
        }
    }

    function onDirectorySelected(path: string): void {
        const cleaned = String(path || "").trim();
        if (!cleaned) {
            return;
        }
        syncDirectory = cleaned;
        ToastUtils.success(t("rns_filesync.folder_selected"));
    }

    async function openSyncFolder(): Promise<void> {
        const path = String(syncDirectory || "").trim();
        if (!path) {
            return;
        }
        const ok = await ElectronUtils.openDirectoryOrCopy(path, () =>
            ToastUtils.success(t("rns_filesync.path_copied"))
        );
        if (!ok) {
            ToastUtils.info(path);
        }
    }

    async function handleStartService(): Promise<void> {
        busy = true;
        try {
            if (!status.running && syncDirectory) {
                await updateFilesyncSettings({
                    sync_directory: syncDirectory,
                    monitor,
                    announce_interval: announceInterval,
                });
            }
            await startFilesyncService({
                sync_directory: syncDirectory || undefined,
                monitor,
                announce_interval: announceInterval,
            });
            ToastUtils.success(t("rns_filesync.started"));
            await refreshAll();
        } catch (err: unknown) {
            const error = err as { message?: string };
            ToastUtils.error(error?.message || t("rns_filesync.error"));
        } finally {
            busy = false;
        }
    }

    async function handleStopService(): Promise<void> {
        busy = true;
        try {
            await stopFilesyncService();
            ToastUtils.success(t("rns_filesync.stopped"));
            await refreshAll();
        } catch (err: unknown) {
            const error = err as { message?: string };
            ToastUtils.error(error?.message || t("rns_filesync.error"));
        } finally {
            busy = false;
        }
    }

    async function handleAnnounceNow(): Promise<void> {
        busy = true;
        try {
            await announceFilesyncNow();
            ToastUtils.success(t("rns_filesync.announced"));
        } catch (err: unknown) {
            const error = err as { message?: string };
            ToastUtils.error(error?.message || t("rns_filesync.error"));
        } finally {
            busy = false;
        }
    }

    async function handleConnectPeer(): Promise<void> {
        busy = true;
        try {
            await connectFilesyncPeer(connectHash);
            ToastUtils.success(t("rns_filesync.connected"));
            connectHash = "";
            await refreshPeers();
            await refreshStatus();
        } catch (err: unknown) {
            const error = err as { message?: string };
            ToastUtils.error(error?.message || t("rns_filesync.error"));
        } finally {
            busy = false;
        }
    }

    async function handleDisconnectPeer(peerId: string): Promise<void> {
        busy = true;
        try {
            await disconnectFilesyncPeer(peerId);
            ToastUtils.success(t("rns_filesync.disconnected"));
            await refreshPeers();
            await refreshStatus();
        } catch (err: unknown) {
            const error = err as { message?: string };
            ToastUtils.error(error?.message || t("rns_filesync.error"));
        } finally {
            busy = false;
        }
    }

    async function handleBrowsePeer(): Promise<void> {
        busy = true;
        try {
            remoteFiles = await browseFilesyncPeer(browsePeerId);
            ToastUtils.success(t("rns_filesync.browse_done"));
        } catch (err: unknown) {
            const error = err as { message?: string };
            remoteFiles = [];
            ToastUtils.error(error?.message || t("rns_filesync.error"));
        } finally {
            busy = false;
        }
    }

    async function handleDownloadFile(path: string): Promise<void> {
        busy = true;
        try {
            await downloadFilesyncRemoteFile(browsePeerId, path);
            ToastUtils.info(t("rns_filesync.download_started"));
        } catch (err: unknown) {
            const error = err as { message?: string };
            ToastUtils.error(error?.message || t("rns_filesync.error"));
        } finally {
            busy = false;
        }
    }

    async function handleGrantAcl(): Promise<void> {
        const perms: string[] = [];
        if (aclRead) perms.push("read");
        if (aclWrite) perms.push("write");
        if (aclDelete) perms.push("delete");
        busy = true;
        try {
            await grantFilesyncAcl({
                identity_hash: aclHash,
                perms,
                enforce: aclEnforce,
            });
            ToastUtils.success(t("rns_filesync.acl_updated"));
            aclHash = "";
            await refreshAcl();
        } catch (err: unknown) {
            const error = err as { message?: string };
            ToastUtils.error(error?.message || t("rns_filesync.error"));
        } finally {
            busy = false;
        }
    }

    async function handleSaveEnforce(): Promise<void> {
        busy = true;
        try {
            await grantFilesyncAcl({
                enforce: aclEnforce,
            });
            ToastUtils.success(t("rns_filesync.acl_updated"));
            await refreshAcl();
        } catch (err: unknown) {
            const error = err as { message?: string };
            ToastUtils.error(error?.message || t("rns_filesync.error"));
        } finally {
            busy = false;
        }
    }

    function bindWs(): void {
        const bind = (type: string, handler: (payload: any) => void) => {
            onWsEvent(type, handler);
            wsHandlers.push([type, handler]);
        };
        bind("filesync.sync.progress", (payload) => {
            lastProgress = payload && typeof payload === "object" ? payload : { status: String(payload) };
        });
        bind("filesync.peer.connected", async () => {
            await refreshPeers();
            await refreshStatus();
        });
        bind("filesync.peer.disconnected", async () => {
            await refreshPeers();
            await refreshStatus();
        });
        bind("filesync.file.updated", async () => {
            await refreshFileManager();
            ToastUtils.info(t("rns_filesync.file_updated"));
        });
        bind("filesync.file.deleted", async () => {
            await refreshFileManager();
            ToastUtils.info(t("rns_filesync.file_deleted"));
        });
        bind("filesync.error", (payload) => {
            const detail = payload?.error || payload?.message || "";
            ToastUtils.error(`${t("rns_filesync.error")}${detail ? ": " + detail : ""}`);
        });
    }

    onMount(() => {
        bindWs();
        GlobalEmitter.on("websocket-reconnected", () => {
            void refreshAll();
        });
        void refreshAll();
    });

    onDestroy(() => {
        GlobalEmitter.off("websocket-reconnected", () => {
            void refreshAll();
        });
        for (const [type, handler] of wsHandlers) {
            offWsEvent(type, handler);
        }
        wsHandlers = [];
    });
</script>

<div class="flex flex-col flex-1 overflow-hidden min-w-0 bg-sem-canvas">
    <ToolsPageHeader
        icon="folder-sync"
        title={t("rns_filesync.title")}
        description={t("rns_filesync.description")}
        eyebrow={t("rns_filesync.eyebrow")}
        accent="green"
    />
    <div class="flex-1 overflow-y-auto w-full px-4 md:px-5 lg:px-8 py-6 pb-[max(1.5rem,env(safe-area-inset-bottom))]">
        <div class="space-y-4 w-full max-w-4xl mx-auto">
            <div class="glass-card space-y-5">
                <div
                    class="p-4 rounded-lg bg-emerald-50/50 dark:bg-emerald-900/10 border border-emerald-100 dark:border-emerald-900/20"
                >
                    <div class="text-xs font-bold uppercase tracking-wider text-emerald-600 dark:text-emerald-400 mb-2">
                        {t("rns_filesync.usage_steps")}
                    </div>
                    <div class="space-y-1.5 text-xs text-emerald-800/80 dark:text-emerald-300/80 leading-relaxed">
                        <p>{t("rns_filesync.step_1")}</p>
                        <p>{t("rns_filesync.step_2")}</p>
                        <p>{t("rns_filesync.step_3")}</p>
                    </div>
                </div>

                <div class="border-b border-sem-border overflow-x-auto overscroll-x-contain -mx-4 px-4 sm:mx-0 sm:px-0">
                    <div class="flex w-max min-w-full sm:w-auto gap-1 sm:gap-2">
                        {#each FILESYNC_TABS as tab (tab.id)}
                            <button
                                type="button"
                                class="shrink-0 px-3 sm:px-4 py-2 text-sm font-semibold transition {activeTab === tab.id
                                    ? 'border-b-2 border-emerald-500 text-emerald-600 dark:text-emerald-400'
                                    : 'text-sem-fg-muted'}"
                                onclick={() => (activeTab = tab.id)}
                            >
                                {t(tab.labelKey)}
                            </button>
                        {/each}
                    </div>
                </div>

                {#if activeTab === "folder"}
                    <FilesyncFolderTab
                        {status}
                        bind:syncDirectory
                        bind:announceInterval
                        bind:monitor
                        {busy}
                        {lastProgress}
                        onOpenBrowser={openDirectoryBrowser}
                        onUseSharedFolder={useSharedFolder}
                        onOpenFolder={openSyncFolder}
                        onStart={handleStartService}
                        onStop={handleStopService}
                        onAnnounce={handleAnnounceNow}
                        onRefresh={refreshStatus}
                    />
                {:else if activeTab === "devices"}
                    <FilesyncDevicesTab
                        {status}
                        {peers}
                        bind:connectHash
                        {busy}
                        onConnect={handleConnectPeer}
                        onDisconnect={handleDisconnectPeer}
                        onRefresh={refreshPeers}
                    />
                {:else if activeTab === "files"}
                    <div class="space-y-4">
                        <FilesyncFileManager bind:this={fileManagerRef} {syncDirectory} onOpenFolder={openSyncFolder} />
                    </div>
                {:else if activeTab === "remote"}
                    <FilesyncRemoteTab
                        {status}
                        {peers}
                        bind:browsePeerId
                        {remoteFiles}
                        {busy}
                        onBrowse={handleBrowsePeer}
                        onDownload={handleDownloadFile}
                    />
                {:else if activeTab === "sharing"}
                    <FilesyncSharingTab
                        bind:aclEnforce
                        bind:aclHash
                        bind:aclRead
                        bind:aclWrite
                        bind:aclDelete
                        {aclRules}
                        {busy}
                        onGrant={handleGrantAcl}
                        onSaveEnforce={handleSaveEnforce}
                    />
                {/if}
            </div>
        </div>
    </div>

    <FilesyncDirectoryBrowserModal
        open={directoryBrowserOpen}
        initialPath={syncDirectory}
        onClose={() => (directoryBrowserOpen = false)}
        onSelect={onDirectorySelected}
    />
</div>
