<!-- SPDX-License-Identifier: 0BSD -->

<script lang="ts">
    import { onMount } from "svelte";
    import MaterialDesignIcon from "../../ui/svelte/MaterialDesignIcon.svelte";
    import ToolsPageHeader from "../../ui/svelte/ToolsPageHeader.svelte";
    import MicronParser from "../../js/MicronParser.js";
    import { micronStorage } from "../../js/MicronStorage.js";
    import { preloadNomadMicronWasm, isMicronWasmBundled } from "../../js/MicronWasmLoader.js";
    import DialogUtils from "../../js/DialogUtils.js";
    import ToastUtils from "../../js/ToastUtils.js";
    import GlobalEmitter from "../../js/GlobalEmitter.js";
    import { t } from "../../js/i18n.js";
    import { STORAGE_KEY } from "./lib/constants.js";
    import { createDefaultTab, createGuideTab } from "./lib/defaultContent.js";
    import { downloadMicronFile } from "./lib/micronDownload.js";
    import {
        ensureNodeRunning,
        fetchNodePagesList,
        fetchPageNodesList,
        nomadPagePathForName,
        openNomadDestinationUrl,
        pageBaseWithExtension,
        pageNamesFromList,
        resolvePublishPageBase,
    } from "./lib/micronPublish.js";
    import type { LastPublishedInfo, MicronTab, PageNodeItem } from "./lib/types.js";
    import MicronEditorTabBar from "./components/MicronEditorTabBar.svelte";
    import MicronPublishDropdown from "./components/MicronPublishDropdown.svelte";
    import MicronPreviewPane from "./components/MicronPreviewPane.svelte";

    let tabs = $state<MicronTab[]>([]);
    let activeTabIndex = $state(0);
    let renderedContent = $state("");
    let showEditor = $state(true);
    let isMobileView = $state(false);

    let showPublishMenu = $state(false);
    let pageNodes = $state<PageNodeItem[]>([]);
    let publishBusy = $state(false);
    let lastPublished = $state<LastPublishedInfo | null>(null);

    let useWasm = $state(false);
    let wasmReady = $state(false);
    let wasmBundled = $state(isMicronWasmBundled());
    let wasmLoading = $state(false);

    export function handleResize(): void {
        if (typeof window === "undefined") return;
        isMobileView = window.innerWidth < 768;
        if (!isMobileView) {
            showEditor = true;
        }
    }

    export function renderActiveTab(): void {
        if (tabs.length === 0 || !tabs[activeTabIndex]) {
            renderedContent = "";
            return;
        }
        try {
            const parser = new MicronParser(true);
            renderedContent = parser.convertMicronToHtml(
                tabs[activeTabIndex].content,
                {},
                { useWasm: useWasm && wasmReady }
            );
        } catch (error: any) {
            console.error("Error rendering micron:", error);
            const msg = String(error?.message ?? error ?? "unknown error")
                .replace(/&/g, "&amp;")
                .replace(/</g, "&lt;")
                .replace(/>/g, "&gt;")
                .replace(/"/g, "&quot;");
            renderedContent = `<p style="color: red;">Error rendering: ${msg}</p>`;
        }
    }

    export async function saveContent(): Promise<void> {
        try {
            await micronStorage.saveTabs(tabs);
        } catch (error) {
            console.warn("Failed to save content to IndexedDB:", error);
        }
    }

    export async function loadContent(): Promise<void> {
        try {
            const savedTabs = await micronStorage.loadTabs();
            if (savedTabs && savedTabs.length > 0) {
                tabs = savedTabs;
            } else {
                let oldContent: string | null = null;
                try {
                    oldContent = localStorage.getItem(STORAGE_KEY);
                } catch {
                    // ignore
                }
                if (oldContent) {
                    tabs = [
                        {
                            id: Date.now(),
                            name: t("tools.micron_editor.main_tab"),
                            content: oldContent,
                        },
                        createGuideTab(Date.now() + 1),
                    ];
                    try {
                        localStorage.removeItem(STORAGE_KEY);
                    } catch {
                        // ignore
                    }
                    await micronStorage.saveTabs(tabs);
                } else {
                    tabs = [createDefaultTab(), createGuideTab(Date.now() + 1)];
                    await micronStorage.saveTabs(tabs);
                }
            }
        } catch (error) {
            console.warn("Failed to load content from IndexedDB:", error);
            tabs = [createDefaultTab(), createGuideTab(Date.now() + 1)];
        }
        activeTabIndex = 0;
    }

    export async function onIdentitySwitched(): Promise<void> {
        try {
            localStorage.removeItem(STORAGE_KEY);
        } catch {
            // ignore
        }
        try {
            await micronStorage.clearAll();
        } catch {
            // ignore
        }
        tabs = [createDefaultTab(), createGuideTab(Date.now() + 1)];
        activeTabIndex = 0;
        try {
            await micronStorage.saveTabs(tabs);
        } catch {
            // ignore
        }
        renderActiveTab();
    }

    export function handleInput(): void {
        renderActiveTab();
        void saveContent();
    }

    export function openNomadDestination(destination: string): void {
        openNomadDestinationUrl(destination, ({ destinationHash, path }) => {
            window.location.hash = `#/nomadnetwork/${encodeURIComponent(destinationHash)}?path=${encodeURIComponent(path)}`;
        });
    }

    export function toggleView(): void {
        showEditor = !showEditor;
    }

    export async function toggleWasmEngine(): Promise<void> {
        if (!wasmBundled) return;
        if (useWasm) {
            useWasm = false;
            renderActiveTab();
            return;
        }
        wasmLoading = true;
        try {
            const ready = await preloadNomadMicronWasm();
            wasmReady = ready === true && typeof (globalThis as any).micronConvert === "function";
            if (wasmReady) {
                useWasm = true;
                renderActiveTab();
            }
        } finally {
            wasmLoading = false;
        }
    }

    export function addTab(): void {
        const newTab: MicronTab = {
            id: Date.now(),
            name: `${t("tools.micron_editor.new_tab")} ${tabs.length + 1}`,
            content: "",
        };
        tabs.push(newTab);
        activeTabIndex = tabs.length - 1;
        void saveContent();
    }

    export async function removeTab(index: number): Promise<void> {
        if (await DialogUtils.confirm(t("tools.micron_editor.confirm_delete_tab"))) {
            tabs.splice(index, 1);
            if (activeTabIndex >= tabs.length) {
                activeTabIndex = Math.max(0, tabs.length - 1);
            }
            void saveContent();
        }
    }

    export function renameTab(index: number, newName: string): void {
        if (tabs[index]) {
            tabs[index].name = newName;
            void saveContent();
        }
    }

    export async function resetAll(): Promise<void> {
        if (await DialogUtils.confirm(t("tools.micron_editor.confirm_reset"))) {
            await micronStorage.clearAll();
            tabs = [createDefaultTab(), createGuideTab(Date.now() + 1)];
            activeTabIndex = 0;
            renderActiveTab();
            await saveContent();
        }
    }

    export function downloadFile(): void {
        const currentTab = tabs[activeTabIndex];
        if (!currentTab) return;
        downloadMicronFile(currentTab.name, currentTab.content);
    }

    export async function togglePublishMenu(): Promise<void> {
        showPublishMenu = !showPublishMenu;
        if (showPublishMenu) {
            try {
                pageNodes = await fetchPageNodesList();
            } catch {
                pageNodes = [];
            }
        }
    }

    export function rememberPublished(node: PageNodeItem, pageName: string): void {
        const destinationHash = (node?.destination_hash || "").trim();
        if (!destinationHash) return;
        lastPublished = {
            destinationHash,
            pagePath: nomadPagePathForName(pageName),
            pageName: pageName || "index.mu",
            serverName: node.name || "",
        };
    }

    export function openPublishedInNomadNet(): void {
        const published = lastPublished;
        if (!published?.destinationHash) return;
        showPublishMenu = false;
        window.location.hash = `#/nomadnetwork/${encodeURIComponent(published.destinationHash)}?path=${encodeURIComponent(published.pagePath || "/page/index.mu")}&newTab=1`;
    }

    export async function offerOpenInNomadNet(pageName: string, serverName: string): Promise<void> {
        if (!lastPublished?.destinationHash) {
            DialogUtils.alert(t("tools.micron_editor.publish_published", { page: pageName, server: serverName }));
            return;
        }
        const open = await DialogUtils.confirm(
            t("tools.micron_editor.publish_open_nomadnet_confirm", {
                page: pageName,
                server: serverName,
            })
        );
        if (open) {
            openPublishedInNomadNet();
        } else {
            ToastUtils.success(t("tools.micron_editor.publish_published", { page: pageName, server: serverName }));
        }
    }

    export async function createMeshServerAndPublish(): Promise<void> {
        if (publishBusy) return;
        const entered = await DialogUtils.prompt(t("tools.micron_editor.publish_create_prompt_name"), "Micron Pages");
        if (entered === null || !String(entered).trim()) return;
        const serverName = String(entered).trim();
        publishBusy = true;
        try {
            const createRes = await window.api.post("/api/v1/page-nodes", { name: serverName });
            const created = (createRes.data || {}) as PageNodeItem;
            if (!created.node_id) {
                throw new Error("create_failed");
            }
            const running = await ensureNodeRunning(created);
            pageNodes = [...pageNodes.filter((n) => n.node_id !== running.node_id), running];
            await publishToNode(running, { alreadyRunning: true });
        } catch (e: any) {
            showPublishMenu = false;
            DialogUtils.alert(e.response?.data?.message || t("tools.micron_editor.publish_failed_create"));
        } finally {
            publishBusy = false;
        }
    }

    export async function publishToNode(node: PageNodeItem, options: { alreadyRunning?: boolean } = {}): Promise<void> {
        if (publishBusy && !options.alreadyRunning) return;
        const tab = tabs[activeTabIndex];
        const busyOwned = !options.alreadyRunning;
        if (busyOwned) {
            publishBusy = true;
        }
        try {
            let running = node;
            if (!options.alreadyRunning) {
                running = await ensureNodeRunning(node);
            }
            const existingPages = await fetchNodePagesList(running.node_id);
            const pageBase = await resolvePublishPageBase(tab, existingPages, running.name);
            if (!pageBase) return;
            const publishName = pageBaseWithExtension(pageBase, tab);
            const response = await window.api.post(`/api/v1/page-nodes/${running.node_id}/pages`, {
                name: publishName,
                content: tab.content,
            });
            showPublishMenu = false;
            const savedName = (response.data as { name?: string })?.name || publishName;
            rememberPublished(running, savedName);
            await offerOpenInNomadNet(savedName, running.name);
        } catch (e: any) {
            DialogUtils.alert(
                e.response?.data?.message ||
                    (e.message === "missing_node"
                        ? t("tools.micron_editor.publish_failed")
                        : t("tools.micron_editor.publish_failed"))
            );
        } finally {
            if (busyOwned) {
                publishBusy = false;
            }
        }
    }

    export async function publishAllToNode(): Promise<void> {
        if (pageNodes.length === 0 || publishBusy) return;

        const nodeNames = pageNodes.map((n) => n.name);
        const nodeName = await DialogUtils.prompt(
            t("tools.micron_editor.publish_all_prompt_server", { servers: nodeNames.join(", ") })
        );
        if (!nodeName) return;

        const node = pageNodes.find((n) => n.name === nodeName);
        if (!node) {
            DialogUtils.alert(t("tools.micron_editor.publish_server_not_found", { server: nodeName }));
            return;
        }

        publishBusy = true;
        try {
            const running = await ensureNodeRunning(node);
            let existingPages = await fetchNodePagesList(running.node_id);
            let published = 0;
            let lastSavedName: string | null = null;
            for (const tab of tabs) {
                const pageBase = await resolvePublishPageBase(tab, existingPages, running.name);
                if (!pageBase) continue;
                const publishName = pageBaseWithExtension(pageBase, tab);
                try {
                    const response = await window.api.post(`/api/v1/page-nodes/${running.node_id}/pages`, {
                        name: publishName,
                        content: tab.content,
                    });
                    const savedName = (response.data as { name?: string })?.name || publishName;
                    lastSavedName = savedName;
                    const pageNames = pageNamesFromList(existingPages);
                    existingPages = [...new Set([...pageNames, savedName])];
                    published++;
                } catch {
                    console.error(`Failed to publish tab: ${tab.name}`);
                }
            }
            showPublishMenu = false;
            if (lastSavedName) {
                rememberPublished(running, lastSavedName);
            }
            DialogUtils.alert(
                t("tools.micron_editor.publish_all_done", {
                    published,
                    total: tabs.length,
                    server: running.name,
                })
            );
            if (published > 0 && lastPublished?.destinationHash && lastSavedName) {
                const open = await DialogUtils.confirm(
                    t("tools.micron_editor.publish_open_nomadnet_confirm", {
                        page: lastSavedName,
                        server: running.name,
                    })
                );
                if (open) {
                    openPublishedInNomadNet();
                }
            }
        } catch (e: any) {
            DialogUtils.alert(e.response?.data?.message || t("tools.micron_editor.publish_failed_start"));
        } finally {
            publishBusy = false;
        }
    }

    $effect(() => {
        if (activeTabIndex >= 0 && tabs[activeTabIndex]) {
            renderActiveTab();
        }
    });

    onMount(() => {
        GlobalEmitter.on("identity-switched", onIdentitySwitched);
        void loadContent().then(() => {
            renderActiveTab();
        });
        handleResize();
        window.addEventListener("resize", handleResize);

        return () => {
            GlobalEmitter.off("identity-switched", onIdentitySwitched);
            window.removeEventListener("resize", handleResize);
        };
    });
</script>

<div class="flex flex-col flex-1 overflow-hidden min-w-0 bg-sem-canvas" data-testid="micron-editor-page">
    <ToolsPageHeader
        icon="code-tags"
        title={t("tools.micron_editor.title")}
        description={t("tools.micron_editor.description")}
        accent="teal"
    >
        <button
            type="button"
            class="secondary-chip py-1! px-3! text-red-500! hover:bg-red-50! dark:hover:bg-red-900/20!"
            onclick={resetAll}
        >
            <MaterialDesignIcon iconName="refresh" class="w-3.5 h-3.5" />
            <span class="hidden sm:inline">{t("tools.micron_editor.reset")}</span>
        </button>
        <button type="button" class="secondary-chip py-1! px-3!" onclick={downloadFile}>
            <MaterialDesignIcon iconName="download" class="w-3.5 h-3.5" />
            <span class="hidden sm:inline">{t("tools.micron_editor.save")}</span>
        </button>

        <MicronPublishDropdown
            {showPublishMenu}
            {pageNodes}
            {publishBusy}
            {lastPublished}
            onTogglePublishMenu={togglePublishMenu}
            onCreateMeshServerAndPublish={createMeshServerAndPublish}
            onPublishToNode={publishToNode}
            onPublishAllToNode={publishAllToNode}
            onOpenPublishedInNomadNet={openPublishedInNomadNet}
            onCloseMenu={() => (showPublishMenu = false)}
        />

        {#if wasmBundled}
            <button
                type="button"
                class="secondary-chip py-1! px-2! gap-1 text-[11px]! {useWasm
                    ? 'text-teal-600! dark:text-teal-300! border-teal-300! dark:border-teal-700!'
                    : ''}"
                disabled={wasmLoading}
                title={t(useWasm ? "tools.micron_editor.wasm_active" : "tools.micron_editor.wasm_inactive")}
                onclick={toggleWasmEngine}
            >
                {#if wasmLoading}
                    <span class="w-3 h-3 rounded-full border-2 border-current border-t-transparent animate-spin"></span>
                {:else}
                    <MaterialDesignIcon
                        iconName={useWasm ? "lightning-bolt" : "lightning-bolt-outline"}
                        class="w-3.5 h-3.5"
                    />
                {/if}
                <span class="hidden sm:inline">{useWasm ? "WASM" : "JS"}</span>
            </button>
        {/if}

        {#if isMobileView}
            <button type="button" class="primary-chip py-1! px-3!" onclick={toggleView}>
                <MaterialDesignIcon iconName={showEditor ? "eye" : "pencil"} class="w-3.5 h-3.5" />
                {showEditor ? t("tools.micron_editor.view_preview") : t("tools.micron_editor.edit")}
            </button>
        {/if}
    </ToolsPageHeader>

    <MicronEditorTabBar
        {tabs}
        {activeTabIndex}
        onSelectTab={(idx) => (activeTabIndex = idx)}
        onAddTab={addTab}
        onRemoveTab={removeTab}
        onRenameTab={renameTab}
    />

    <div class="flex-1 flex overflow-hidden min-w-0 pb-[env(safe-area-inset-bottom)]">
        {#if tabs.length > 0 && tabs[activeTabIndex]}
            <div
                class="flex-1 overflow-hidden flex flex-col {isMobileView && !showEditor ? 'hidden' : ''} {!isMobileView
                    ? 'border-r border-sem-border'
                    : ''}"
            >
                <textarea
                    bind:value={tabs[activeTabIndex].content}
                    class="flex-1 w-full bg-sem-surface text-sem-fg p-4 font-mono text-sm resize-none focus:outline-hidden"
                    placeholder={t("tools.micron_editor.placeholder")}
                    oninput={handleInput}></textarea>
            </div>
        {/if}

        <MicronPreviewPane {renderedContent} {isMobileView} {showEditor} onNomadDestination={openNomadDestination} />
    </div>
</div>
