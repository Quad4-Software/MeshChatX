<!-- SPDX-License-Identifier: 0BSD -->

<script lang="ts">
    import { onMount, onDestroy } from "svelte";
    import ToolsPageHeader from "../../ui/svelte/ToolsPageHeader.svelte";
    import RNCPSendTab from "./components/RNCPSendTab.svelte";
    import RNCPFetchTab from "./components/RNCPFetchTab.svelte";
    import RNCPListenTab from "./components/RNCPListenTab.svelte";
    import DialogUtils from "../../js/DialogUtils.js";
    import ElectronUtils from "../../js/ElectronUtils.js";
    import MarkdownRenderer from "../../js/MarkdownRenderer.js";
    import { handleRichHtmlLinkClick } from "../../js/NomadRichHtmlLinks.js";
    import ToastUtils from "../../js/ToastUtils.js";
    import { onWsEvent, offWsEvent } from "../../js/registries/wsEventRegistry.js";
    import { t } from "../../js/i18n.js";
    import { loadRncpListenPrefs, saveRncpListenPrefs } from "./lib/rncpPrefs.js";

    let activeTab = $state<"send" | "fetch" | "listen">("send");

    let sendDestinationHash = $state("");
    let sendFilePath = $state("");
    let sendTimeout = $state(30);
    let sendNoCompress = $state(false);
    let sendInProgress = $state(false);
    let sendProgress = $state(0);
    let sendResult = $state<{ success: boolean; message: string; filePath?: string } | null>(null);
    let sendTransferId = $state<string | null>(null);

    let fetchDestinationHash = $state("");
    let fetchFilePath = $state("");
    let fetchSavePath = $state("");
    let fetchTimeout = $state(30);
    let fetchAllowOverwrite = $state(false);
    let fetchInProgress = $state(false);
    let fetchProgress = $state(0);
    let fetchResult = $state<{ success: boolean; message: string; savedPath?: string } | null>(null);
    let fetchTransferId = $state<string | null>(null);

    let listenAllowedHashes = $state("");
    let listenFetchJail = $state<string | null>(null);
    let listenFetchAllowed = $state(false);
    let listenAllowOverwrite = $state(false);
    let listenActive = $state(false);
    let listenDestinationHash = $state<string | null>(null);
    let listenResult = $state<{ success: boolean; message: string } | null>(null);
    let receiveDirectory = $state<string | null>(null);
    let lastReceiveEvent = $state<{ status: string; saved_path?: string; error?: string } | null>(null);

    $effect(() => {
        saveRncpListenPrefs({
            listenAllowedHashes,
            listenFetchJail,
            listenFetchAllowed,
            listenAllowOverwrite,
        });
    });

    function notifyRncp(title: string, body: string): void {
        const text = body || title;
        ToastUtils.success(text);
        if (ElectronUtils.isElectron()) {
            ElectronUtils.showNotification(title, body || "");
        }
    }

    function notifyRncpError(title: string, body: string): void {
        ToastUtils.error(body || title);
        if (ElectronUtils.isElectron()) {
            ElectronUtils.showNotification(title, body || "", true);
        }
    }

    async function openPathInOs(filePath: string): Promise<void> {
        if (!filePath) {
            return;
        }
        const ok = await ElectronUtils.revealPathInFolderOrCopy(filePath, () => ToastUtils.success(t("common.copied")));
        if (!ok) {
            DialogUtils.alert(filePath);
        }
    }

    async function openReceiveDirectory(): Promise<void> {
        if (!receiveDirectory) {
            await syncListenerStatusFromServer();
        }
        if (!receiveDirectory) {
            return;
        }
        const ok = await ElectronUtils.openDirectoryOrCopy(receiveDirectory, () =>
            ToastUtils.success(t("common.copied"))
        );
        if (!ok) {
            DialogUtils.alert(receiveDirectory);
        }
    }

    function onTransferProgress(data: any): void {
        const tid = data?.transfer_id;
        const p = typeof data?.progress === "number" ? data.progress : 0;
        if (sendInProgress) {
            if (!sendTransferId && tid) {
                sendTransferId = tid;
            }
            if (tid && sendTransferId === tid) {
                sendProgress = p;
            }
        } else if (fetchInProgress) {
            if (!fetchTransferId && tid) {
                fetchTransferId = tid;
            }
            if (tid && fetchTransferId === tid) {
                fetchProgress = p;
            }
        }
    }

    function onReceiveCompleted(data: any): void {
        lastReceiveEvent = {
            status: data?.status || "",
            saved_path: data?.saved_path,
            error: data?.error,
        };
        if (data?.status === "completed" && data.saved_path) {
            notifyRncp(t("rncp.received_file"), data.saved_path);
        } else if (data?.status !== "completed") {
            notifyRncpError(t("rncp.receive_failed"), data?.error || data?.status || "");
        }
    }

    async function syncListenerStatusFromServer(): Promise<void> {
        try {
            const response = await window.api.get("/api/v1/rncp/status");
            const s = (response as any)?.data as any;
            receiveDirectory = s?.receive_directory || null;
            if (!s?.listening) {
                return;
            }
            listenActive = true;
            listenDestinationHash = s.destination_hash || null;
            if (Array.isArray(s.allowed_hashes) && s.allowed_hashes.length) {
                listenAllowedHashes = s.allowed_hashes.join("\n");
            }
            listenFetchAllowed = Boolean(s.fetch_allowed);
            listenFetchJail = s.fetch_jail || null;
            listenAllowOverwrite = Boolean(s.allow_overwrite);
        } catch (e) {
            console.error(e);
        }
    }

    async function sendFile(): Promise<void> {
        if (!sendDestinationHash || sendDestinationHash.length !== 32) {
            DialogUtils.alert(t("rncp.invalid_hash"));
            return;
        }
        if (!sendFilePath) {
            DialogUtils.alert(t("rncp.provide_file_path"));
            return;
        }

        sendInProgress = true;
        sendProgress = 0;
        sendResult = null;
        sendTransferId = null;

        try {
            const response = await window.api.post("/api/v1/rncp/send", {
                destination_hash: sendDestinationHash,
                file_path: sendFilePath,
                timeout: sendTimeout,
                no_compress: sendNoCompress,
            });

            sendTransferId = response.data.transfer_id;
            sendProgress = 1;
            const fp = response.data.file_path;
            sendResult = {
                success: true,
                message: t("rncp.file_sent_successfully", { id: (response as any)?.data?.transfer_id }),
                filePath: fp,
            };
            notifyRncp(t("rncp.send_complete"), fp || "");
        } catch (e: any) {
            console.error(e);
            sendResult = {
                success: false,
                message: e?.response?.data?.message || t("rncp.failed_to_send"),
            };
        } finally {
            sendInProgress = false;
        }
    }

    async function cancelSend(): Promise<void> {
        const transferId = sendTransferId;
        sendInProgress = false;
        sendProgress = 0;
        try {
            await window.api.post("/api/v1/rncp/cancel", {
                transfer_id: transferId || undefined,
            });
        } catch (e) {
            console.error(e);
        }
    }

    async function fetchFile(): Promise<void> {
        if (!fetchDestinationHash || fetchDestinationHash.length !== 32) {
            DialogUtils.alert(t("rncp.invalid_hash"));
            return;
        }
        if (!fetchFilePath) {
            DialogUtils.alert(t("rncp.provide_remote_file_path"));
            return;
        }

        fetchInProgress = true;
        fetchProgress = 0;
        fetchResult = null;
        fetchTransferId = null;

        try {
            const response = await window.api.post("/api/v1/rncp/fetch", {
                destination_hash: fetchDestinationHash,
                file_path: fetchFilePath,
                timeout: fetchTimeout,
                save_path: fetchSavePath || null,
                allow_overwrite: fetchAllowOverwrite,
            });

            fetchProgress = 1;
            const saved = (response as any)?.data?.file_path;
            fetchResult = {
                success: true,
                message: t("rncp.file_fetched_successfully", {
                    path: saved || "current directory",
                }),
                savedPath: saved,
            };
            notifyRncp(t("rncp.fetch_complete"), saved || "");
        } catch (e: any) {
            console.error(e);
            fetchResult = {
                success: false,
                message: e?.response?.data?.message || t("rncp.failed_to_fetch"),
            };
        } finally {
            fetchInProgress = false;
        }
    }

    async function cancelFetch(): Promise<void> {
        const transferId = fetchTransferId;
        fetchInProgress = false;
        fetchProgress = 0;
        try {
            await window.api.post("/api/v1/rncp/cancel", {
                transfer_id: transferId || undefined,
            });
        } catch (e) {
            console.error(e);
        }
    }

    async function startListen(): Promise<void> {
        const allowedHashes = listenAllowedHashes
            .split("\n")
            .map((h) => h.trim())
            .filter((h) => h.length === 32);

        if (allowedHashes.length === 0) {
            DialogUtils.alert(t("rncp.provide_allowed_hash"));
            return;
        }

        listenResult = null;

        try {
            const response = await window.api.post("/api/v1/rncp/listen", {
                allowed_hashes: allowedHashes,
                fetch_allowed: listenFetchAllowed,
                fetch_jail: listenFetchJail || null,
                allow_overwrite: listenAllowOverwrite,
            });

            listenActive = true;
            listenDestinationHash = (response as any)?.data?.destination_hash;
            listenResult = {
                success: true,
                message: (response as any)?.data?.message,
            };
        } catch (e: any) {
            console.error(e);
            listenResult = {
                success: false,
                message: e?.response?.data?.message || t("rncp.failed_to_start_listener"),
            };
        }
    }

    async function stopListen(): Promise<void> {
        try {
            await window.api.post("/api/v1/rncp/stop");
        } catch (e: any) {
            console.error(e);
            listenResult = {
                success: false,
                message: e?.response?.data?.message || t("rncp.failed_to_stop_listener"),
            };
            return;
        }
        listenActive = false;
        listenDestinationHash = null;
        listenResult = null;
    }

    function renderMarkdown(text: string): string {
        return MarkdownRenderer.render(text || "");
    }

    function handleMessageClick(event: MouseEvent): void {
        const hex32 = /^[a-fA-F0-9]{32}$/;
        handleRichHtmlLinkClick(event, {
            onNomadUrl: (url: string) => {
                const [hash, ...pathParts] = url.split(":");
                const path = pathParts.join(":");
                if (hex32.test(hash)) {
                    window.location.hash = `#/nomadnetwork/${hash}${path ? `?path=${encodeURIComponent(path)}` : ""}`;
                }
            },
            onLxmfAddress: (address: string) => {
                window.location.hash = `#/messages/${address}`;
            },
        });
    }

    onMount(() => {
        onWsEvent("rncp.transfer.progress", onTransferProgress);
        onWsEvent("rncp.receive.completed", onReceiveCompleted);
        const prefs = loadRncpListenPrefs();
        listenAllowedHashes = prefs.listenAllowedHashes;
        listenFetchJail = prefs.listenFetchJail;
        listenFetchAllowed = prefs.listenFetchAllowed;
        listenAllowOverwrite = prefs.listenAllowOverwrite;
        syncListenerStatusFromServer();
    });

    onDestroy(() => {
        offWsEvent("rncp.transfer.progress", onTransferProgress);
        offWsEvent("rncp.receive.completed", onReceiveCompleted);
        void cancelSend();
        void cancelFetch();
    });
</script>

<div class="flex flex-col flex-1 overflow-hidden min-w-0 bg-sem-canvas">
    <ToolsPageHeader
        icon="swap-horizontal"
        title={t("rncp.title")}
        description={t("rncp.description")}
        eyebrow={t("rncp.file_transfer")}
        accent="green"
    />
    <div class="flex-1 overflow-y-auto w-full px-4 md:px-5 lg:px-8 py-6 pb-[max(1.5rem,env(safe-area-inset-bottom))]">
        <div class="space-y-4 w-full max-w-4xl mx-auto">
            <div class="glass-card space-y-5">
                <div
                    class="p-4 rounded-lg bg-blue-50/50 dark:bg-blue-900/10 border border-blue-100 dark:border-blue-900/20"
                >
                    <div class="text-xs font-bold uppercase tracking-wider text-sem-accent mb-2">
                        {t("rncp.usage_steps")}
                    </div>
                    <!-- svelte-ignore a11y_click_events_have_key_events -->
                    <!-- svelte-ignore a11y_no_noninteractive_element_interactions -->
                    <!-- eslint-disable svelte/no-at-html-tags -->
                    <div class="space-y-1.5" onclick={handleMessageClick} role="region">
                        <div class="text-xs text-blue-800/80 dark:text-blue-300/80 leading-relaxed">
                            {@html renderMarkdown(t("rncp.step_1"))}
                        </div>
                        <div class="text-xs text-blue-800/80 dark:text-blue-300/80 leading-relaxed">
                            {@html renderMarkdown(t("rncp.step_2"))}
                        </div>
                        <div class="text-xs text-blue-800/80 dark:text-blue-300/80 leading-relaxed">
                            {@html renderMarkdown(t("rncp.step_3"))}
                        </div>
                    </div>
                    <!-- eslint-enable svelte/no-at-html-tags -->
                </div>

                <div class="border-b border-sem-border overflow-x-auto overscroll-x-contain -mx-4 px-4 sm:mx-0 sm:px-0">
                    <div class="flex w-max min-w-full sm:w-auto gap-1 sm:gap-2">
                        <button
                            type="button"
                            class="shrink-0 px-3 sm:px-4 py-2 text-sm font-semibold transition cursor-pointer {activeTab ===
                            'send'
                                ? 'border-b-2 border-blue-500 text-sem-accent'
                                : 'text-gray-600 dark:text-gray-400'}"
                            onclick={() => (activeTab = "send")}
                        >
                            {t("rncp.send_file")}
                        </button>
                        <button
                            type="button"
                            class="shrink-0 px-3 sm:px-4 py-2 text-sm font-semibold transition cursor-pointer {activeTab ===
                            'fetch'
                                ? 'border-b-2 border-blue-500 text-sem-accent'
                                : 'text-gray-600 dark:text-gray-400'}"
                            onclick={() => (activeTab = "fetch")}
                        >
                            {t("rncp.fetch_file")}
                        </button>
                        <button
                            type="button"
                            class="shrink-0 px-3 sm:px-4 py-2 text-sm font-semibold transition cursor-pointer {activeTab ===
                            'listen'
                                ? 'border-b-2 border-blue-500 text-sem-accent'
                                : 'text-gray-600 dark:text-gray-400'}"
                            onclick={() => (activeTab = "listen")}
                        >
                            {t("rncp.listen")}
                        </button>
                    </div>
                </div>

                {#if activeTab === "send"}
                    <RNCPSendTab
                        bind:destinationHash={sendDestinationHash}
                        bind:filePath={sendFilePath}
                        bind:timeout={sendTimeout}
                        bind:noCompress={sendNoCompress}
                        inProgress={sendInProgress}
                        progress={sendProgress}
                        result={sendResult}
                        onsend={() => void sendFile()}
                        oncancel={() => void cancelSend()}
                        onopenpath={(fp) => void openPathInOs(fp)}
                    />
                {:else if activeTab === "fetch"}
                    <RNCPFetchTab
                        bind:destinationHash={fetchDestinationHash}
                        bind:filePath={fetchFilePath}
                        bind:savePath={fetchSavePath}
                        bind:timeout={fetchTimeout}
                        bind:allowOverwrite={fetchAllowOverwrite}
                        inProgress={fetchInProgress}
                        progress={fetchProgress}
                        result={fetchResult}
                        onfetch={() => void fetchFile()}
                        oncancel={() => void cancelFetch()}
                        onopenpath={(fp) => void openPathInOs(fp)}
                    />
                {:else if activeTab === "listen"}
                    <RNCPListenTab
                        bind:allowedHashes={listenAllowedHashes}
                        bind:fetchJail={listenFetchJail}
                        bind:fetchAllowed={listenFetchAllowed}
                        bind:allowOverwrite={listenAllowOverwrite}
                        {receiveDirectory}
                        {lastReceiveEvent}
                        {listenActive}
                        destinationHash={listenDestinationHash}
                        {listenResult}
                        onstart={() => void startListen()}
                        onstop={() => void stopListen()}
                        onopenreceivedir={() => void openReceiveDirectory()}
                        onopenpath={(fp) => void openPathInOs(fp)}
                    />
                {/if}
            </div>
        </div>
    </div>
</div>
