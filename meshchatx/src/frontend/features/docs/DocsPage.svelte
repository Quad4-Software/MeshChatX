<!-- SPDX-License-Identifier: 0BSD -->

<script lang="ts">
    import { onMount } from "svelte";
    import ToastUtils from "../../js/ToastUtils.js";
    import DialogUtils from "../../js/DialogUtils.js";
    import { t } from "../../js/i18n.js";
    import { bundledReticulumDocsUrl } from "../../js/reticulumDocsEntryUrl.js";
    import { DOCS_SEARCH_DEBOUNCE_MS, DOCS_STATUS_POLL_INTERVAL_MS, RETICULUM_LANGUAGES } from "./lib/constants.js";
    import {
        deleteDocsVersion,
        fetchDocContent,
        fetchDocsStatus,
        fetchMeshChatXDocsList,
        searchDocs,
        switchDocsVersion,
        uploadDocsZip,
    } from "./lib/docsApi.js";
    import { extractDocToc, resolveRelativeDocPath, scrollToHeadingInElement } from "./lib/docsToc.js";
    import type {
        DocContentResponse,
        DocItem,
        DocLanguage,
        DocSection,
        DocTocEntry,
        DocsActiveTab,
        DocsStatus,
        SearchResultItem,
    } from "./lib/types.js";
    import DocsSidebar from "./components/DocsSidebar.svelte";
    import DocsMobileControls from "./components/DocsMobileControls.svelte";
    import DocsSearchResults from "./components/DocsSearchResults.svelte";
    import DocsProseView from "./components/DocsProseView.svelte";
    import DocsReticulumView from "./components/DocsReticulumView.svelte";
    import DocsStatusOverlay from "./components/DocsStatusOverlay.svelte";

    let status = $state<DocsStatus>({
        status: "idle",
        progress: 0,
        last_error: null,
        has_docs: false,
        has_meshchatx_docs: false,
        versions: [],
        current_version: null,
    });

    let activeTab = $state<DocsActiveTab>("meshchatx");
    let searchQuery = $state("");
    let searchResults = $state<SearchResultItem[]>([]);
    let isSearching = $state(false);
    let searchError = $state<string | null>(null);

    let meshchatxDocs = $state<DocItem[]>([]);
    let docSections = $state<DocSection[]>([]);
    let docLanguages = $state<DocLanguage[]>([{ code: "en", name: "English" }]);
    let defaultDocsLanguage = $state("en");
    let reticulumDocsLang = $state("en");
    let meshchatxDocsLang = $state("en");
    let docToc = $state<DocTocEntry[]>([]);

    let meshchatxListError = $state<string | null>(null);
    let docLoadError = $state<string | null>(null);
    let manifestWarning = $state<string | null>(null);

    let selectedDocPath = $state<string | null>(null);
    let selectedDocContent = $state<DocContentResponse | null>(null);
    let selectedReticulumPath = $state<string | null>(null);
    let reticulumDocsCacheBust = $state(0);

    let proseViewComponent: DocsProseView | null = $state(null);
    let reticulumViewComponent: DocsReticulumView | null = $state(null);
    let statusInterval: ReturnType<typeof setInterval> | null = null;
    let searchTimeout: ReturnType<typeof setTimeout> | null = null;

    const allLanguages = $derived(
        Object.entries(RETICULUM_LANGUAGES).map(([code, name]) => ({
            code,
            name,
        }))
    );

    const localDocsUrl = $derived(
        (() => {
            let path: string;
            if (selectedReticulumPath) {
                path = `/reticulum-docs/${selectedReticulumPath}`;
            } else {
                path = bundledReticulumDocsUrl(reticulumDocsLang);
            }
            if (reticulumDocsCacheBust) {
                const sep = path.includes("?") ? "&" : "?";
                return `${path}${sep}v=${reticulumDocsCacheBust}`;
            }
            return path;
        })()
    );

    const visibleDocSections = $derived(
        (() => {
            const lang = meshchatxDocsLang;
            const fallback = defaultDocsLanguage || "en";
            return docSections
                .map((section) => ({
                    ...section,
                    items: (section.items || []).filter(
                        (item) => item.lang === lang || item.lang === fallback || lang === fallback
                    ),
                }))
                .filter((section) => section.items.length > 0);
        })()
    );

    const firstDocPath = $derived(
        (() => {
            for (const section of visibleDocSections) {
                if (section.items?.length) {
                    return section.items[0].path;
                }
            }
            return meshchatxDocs[0]?.path || null;
        })()
    );

    export async function fetchStatus(): Promise<void> {
        try {
            const data = await fetchDocsStatus();
            status = data;

            if (!status.has_docs && status.has_meshchatx_docs && activeTab === "reticulum") {
                activeTab = "meshchatx";
            } else if (status.has_docs && !status.has_meshchatx_docs && activeTab === "meshchatx") {
                activeTab = "reticulum";
            }
        } catch (error) {
            console.error("Failed to fetch docs status:", error);
        }
        applyDocumentationRouteQuery();
    }

    export function dismissError(): void {
        status = { ...status, last_error: null };
    }

    export async function fetchMeshChatXDocs(): Promise<void> {
        meshchatxListError = null;
        manifestWarning = null;
        try {
            const data = await fetchMeshChatXDocsList(meshchatxDocsLang);
            if (Array.isArray(data)) {
                meshchatxDocs = data;
                docSections = [];
                docLanguages = [{ code: "en", name: "English" }];
            } else {
                meshchatxDocs = data.docs || [];
                docSections = data.sections || [];
                docLanguages = data.languages || [{ code: "en", name: "English" }];
                defaultDocsLanguage = data.default_language || "en";
                if (data.manifest_error) {
                    manifestWarning = t("docs.manifest_warning");
                }
            }
            if (!docLanguages.some((l) => l.code === meshchatxDocsLang)) {
                meshchatxDocsLang = defaultDocsLanguage || "en";
            }
            if (meshchatxDocs.length > 0 && !selectedDocPath) {
                const start = firstDocPath;
                if (start) {
                    void selectDoc(start);
                }
            }
        } catch (error: any) {
            console.error("Failed to fetch MeshChatX docs list:", error);
            meshchatxDocs = [];
            docSections = [];
            meshchatxListError = error.response?.data?.error || t("docs.load_list_failed");
        }
    }

    export async function setMeshchatxDocsLang(langCode: string): Promise<void> {
        if (meshchatxDocsLang === langCode) {
            return;
        }
        meshchatxDocsLang = langCode;
        selectedDocPath = null;
        selectedDocContent = null;
        docToc = [];
        await fetchMeshChatXDocs();
    }

    export async function selectDoc(path: string): Promise<void> {
        if (!path) {
            return;
        }
        selectedDocPath = path;
        docLoadError = null;
        try {
            const data = await fetchDocContent(path);
            if (!data?.html && !data?.content) {
                throw new Error("Empty document response");
            }
            selectedDocContent = data;
            docToc = extractDocToc(selectedDocContent?.html || "");
        } catch (error: any) {
            console.error("Failed to fetch doc content:", error);
            docLoadError = error.response?.data?.error || t("docs.load_doc_failed");
            selectedDocContent = null;
            docToc = [];
        }
    }

    export function scrollToHeading(id: string): void {
        const prose = proseViewComponent?.getProseElement() || null;
        scrollToHeadingInElement(prose, id);
    }

    export async function switchVersion(version: string): Promise<void> {
        try {
            await switchDocsVersion(version);
            selectedReticulumPath = null;
            await fetchStatus();
            if (activeTab === "reticulum") {
                reticulumViewComponent?.reloadFrame();
            }
        } catch (error) {
            console.error("Failed to switch docs version:", error);
        }
    }

    export async function deleteVersion(version: string): Promise<void> {
        if (!(await DialogUtils.confirm(t("docs.confirm_delete_version", { version })))) {
            return;
        }
        try {
            await deleteDocsVersion(version);
            await fetchStatus();
            ToastUtils.success(`Version ${version} deleted`);
        } catch (error: any) {
            console.error("Failed to delete docs version:", error);
            ToastUtils.error("Failed to delete version: " + (error.response?.data?.error || error.message));
        }
    }

    export async function handleZipUpload(event: Event): Promise<void> {
        const input = event.target as HTMLInputElement;
        const file = input.files?.[0];
        if (!file) return;

        const defaultName = `upload-${Date.now()}`;
        const version = await DialogUtils.prompt(t("docs.prompt_version_name"), defaultName);
        input.value = "";
        if (version === null || !String(version).trim()) {
            return;
        }

        try {
            await uploadDocsZip(String(version).trim(), file);
            await fetchStatus();
            reticulumDocsCacheBust = Date.now();
            ToastUtils.success(t("docs.upload_success"));
        } catch (error: any) {
            console.error("Failed to upload docs zip:", error);
            const message = error.response?.data?.error || error.message || "";
            DialogUtils.alert(t("docs.failed_upload_alert", { message }), "error");
        }
    }

    export async function exportDocs(): Promise<void> {
        window.location.href = "/api/v1/docs/export";
    }

    export async function exportReticulumDocs(): Promise<void> {
        window.location.href = "/api/v1/docs/export/reticulum";
    }

    export function copyDocLink(): void {
        if (!selectedDocPath) return;
        const htmlPath = selectedDocPath.replace(/\.(md|txt)$/, ".html");
        const url = `${window.location.origin}/meshchatx-docs/${htmlPath}`;

        navigator.clipboard
            .writeText(url)
            .then(() => {
                ToastUtils.success(t("docs.docs_link_copied"));
            })
            .catch(() => {
                ToastUtils.error(t("docs.failed_copy_link"));
            });
    }

    export async function setLanguage(langCode: string): Promise<void> {
        selectedReticulumPath = null;
        reticulumDocsLang = langCode;
        reticulumDocsCacheBust += 1;
    }

    export function debounceSearch(): void {
        if (searchTimeout) clearTimeout(searchTimeout);
        if (!searchQuery) {
            searchResults = [];
            return;
        }
        searchTimeout = setTimeout(() => {
            void performSearch();
        }, DOCS_SEARCH_DEBOUNCE_MS);
    }

    export async function performSearch(): Promise<void> {
        if (!searchQuery) return;
        isSearching = true;
        searchError = null;
        try {
            searchResults = await searchDocs(searchQuery, reticulumDocsLang);
        } catch (error: any) {
            console.error("Search failed:", error);
            searchResults = [];
            searchError = error.response?.data?.error || t("docs.search_failed");
        } finally {
            isSearching = false;
        }
    }

    export function clearSearch(): void {
        searchQuery = "";
        searchResults = [];
        searchError = null;
    }

    export function applyDocumentationRouteQuery(): void {
        if (typeof window === "undefined") return;
        const hash = window.location.hash || "";
        const queryIdx = hash.indexOf("?");
        if (queryIdx < 0) return;
        const params = new URLSearchParams(hash.slice(queryIdx));
        const raw = params.get("reticulum");
        if (!raw || !raw.trim()) return;

        let path = raw.trim();
        try {
            path = decodeURIComponent(path);
        } catch {
            return;
        }
        path = path.replace(/^\/?(?:reticulum-docs\/)?/, "");
        if (!path) return;

        activeTab = "reticulum";
        selectedReticulumPath = path;
    }

    export function navigateTo(path: string): void {
        if (path.startsWith("/meshchatx-docs/")) {
            activeTab = "meshchatx";
            const docPath = path.replace("/meshchatx-docs/", "");
            void selectDoc(docPath);
        } else {
            activeTab = "reticulum";
            const cleanPath = path.replace("/reticulum-docs/", "");
            selectedReticulumPath = cleanPath;
        }
        clearSearch();
    }

    export function handleDocClick(event: MouseEvent): void {
        const link = (event.target as HTMLElement | null)?.closest("a");
        if (!link) return;

        const href = link.getAttribute("href");
        if (!href) return;

        if (href.startsWith("http") || href.startsWith("mailto:") || href.startsWith("/")) {
            return;
        }

        if (href.startsWith("#")) {
            event.preventDefault();
            scrollToHeading(href.substring(1));
            return;
        }

        if (href.endsWith(".md") || href.endsWith(".txt")) {
            event.preventDefault();
            const newPath = resolveRelativeDocPath(selectedDocPath || "", href);
            void selectDoc(newPath);
            proseViewComponent?.scrollToTop();
        }
    }

    onMount(() => {
        void fetchStatus();
        void fetchMeshChatXDocs();
        statusInterval = setInterval(fetchStatus, DOCS_STATUS_POLL_INTERVAL_MS);
        applyDocumentationRouteQuery();

        return () => {
            if (statusInterval) clearInterval(statusInterval);
            if (searchTimeout) clearTimeout(searchTimeout);
        };
    });
</script>

<div class="flex flex-col flex-1 overflow-hidden min-w-0 bg-sem-canvas" data-testid="docs-page">
    <DocsStatusOverlay {status} onDismissError={dismissError} onZipUpload={handleZipUpload} />

    <div class="flex-1 relative bg-sem-surface overflow-hidden flex min-h-0">
        <DocsSidebar
            {activeTab}
            {status}
            bind:searchQuery
            {isSearching}
            currentLang={reticulumDocsLang}
            {allLanguages}
            {meshchatxDocsLang}
            {docLanguages}
            {visibleDocSections}
            {selectedDocPath}
            {manifestWarning}
            {meshchatxListError}
            {localDocsUrl}
            onTabChange={(tab) => (activeTab = tab)}
            onSearchInput={() => debounceSearch()}
            onClearSearch={clearSearch}
            onSwitchVersion={switchVersion}
            onDeleteVersion={deleteVersion}
            onSetLanguage={setLanguage}
            onSetMeshchatxDocsLang={setMeshchatxDocsLang}
            onSelectDoc={selectDoc}
            onExportDocs={exportDocs}
            onExportReticulumDocs={exportReticulumDocs}
            onZipUpload={handleZipUpload}
        />

        <div class="flex-1 flex flex-col min-w-0 overflow-hidden relative">
            <DocsMobileControls
                {activeTab}
                {status}
                bind:searchQuery
                {isSearching}
                {visibleDocSections}
                {selectedDocPath}
                onTabChange={(tab) => (activeTab = tab)}
                onSearchInput={() => debounceSearch()}
                onClearSearch={clearSearch}
                onSelectDoc={selectDoc}
                onExportDocs={exportDocs}
                onZipUpload={handleZipUpload}
            />

            <DocsSearchResults
                {searchQuery}
                {searchResults}
                {isSearching}
                {searchError}
                onNavigate={navigateTo}
                onClearSearch={clearSearch}
            />

            {#if activeTab === "meshchatx" && !searchQuery}
                <DocsProseView
                    bind:this={proseViewComponent}
                    {selectedDocContent}
                    {docLoadError}
                    meshchatxDocsCount={meshchatxDocs.length}
                    {docToc}
                    onDocClick={handleDocClick}
                    onScrollToHeading={scrollToHeading}
                />
            {:else if activeTab === "reticulum" && !searchQuery}
                <DocsReticulumView
                    bind:this={reticulumViewComponent}
                    hasDocs={status.has_docs}
                    isExtracting={status.status === "extracting"}
                    {localDocsUrl}
                    onZipUpload={handleZipUpload}
                />
            {/if}
        </div>
    </div>
</div>
