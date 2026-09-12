// @ts-check

import { ref } from "vue";

import DialogUtils from "../DialogUtils";
import ToastUtils from "../ToastUtils";
import { apiPath } from "../constants.js";

const NOMAD_DESTINATION_HASH = /^[a-fA-F0-9]{32}$/;
const PAGE_EXTENSIONS = [".mu", ".html", ".md", ".txt"];

function pageNamesFromList(pages) {
    return (pages || []).map((entry) => (typeof entry === "string" ? entry : entry?.name)).filter(Boolean);
}

/**
 * Publish-to-mesh-server state for MicronEditorPage: the publish dropdown,
 * site modal, page node list, busy flag and last-published marker, plus the
 * page/site publish flows.
 *
 * options.t is the host $t for dialog and toast strings. options.pushRoute
 * performs the $router.push for "open in NomadNet". options.getActiveTab
 * returns the host's active editor tab. options.uploadImages delegates to
 * the host's local image upload so referenced media reach the node.
 */
export function useMicronPublish(options = {}) {
    const {
        t = (key) => key,
        pushRoute = () => {},
        getActiveTab = () => undefined,
        uploadImages = () => Promise.resolve(),
    } = options;

    const showPublishMenu = ref(false);
    const showPublishSiteModal = ref(false);
    const pageNodes = ref([]);
    const publishBusy = ref(false);
    const lastPublished = ref(null);

    async function togglePublishMenu() {
        showPublishMenu.value = !showPublishMenu.value;
        if (showPublishMenu.value) {
            try {
                const response = await window.api.get(apiPath("/page-nodes"));
                pageNodes.value = response.data;
            } catch {
                pageNodes.value = [];
            }
        }
    }

    async function fetchNodePages(node) {
        const response = await window.api.get(apiPath(`/page-nodes/${node.node_id}/pages`));
        return response.data?.pages ?? [];
    }

    function tabNameToPageBase(tab) {
        let name = (tab.name || "").trim().replace(/\s+/g, "_");
        const lower = name.toLowerCase();
        for (const ext of PAGE_EXTENSIONS) {
            if (lower.endsWith(ext)) {
                return name.slice(0, -ext.length);
            }
        }
        return name;
    }

    function pageBaseWithExtension(base, tab) {
        const trimmed = String(base || "").trim();
        if (!trimmed) {
            return trimmed;
        }
        const lower = trimmed.toLowerCase();
        for (const ext of PAGE_EXTENSIONS) {
            if (lower.endsWith(ext)) {
                return trimmed;
            }
        }
        const tabName = (tab?.name || "").trim();
        const tabLower = tabName.toLowerCase();
        for (const ext of PAGE_EXTENSIONS) {
            if (tabLower.endsWith(ext)) {
                return `${trimmed}${ext}`;
            }
        }
        return trimmed;
    }

    function isUnsetMicronTabName(name) {
        const trimmed = (name || "").trim();
        if (!trimmed) {
            return true;
        }
        const newTabLabel = t("tools.micron_editor.new_tab");
        if (trimmed === newTabLabel) {
            return true;
        }
        const numberedPrefix = `${newTabLabel} `;
        if (!trimmed.startsWith(numberedPrefix)) {
            return false;
        }
        return /^\d+$/.test(trimmed.slice(numberedPrefix.length));
    }

    async function resolvePublishPageBase(tab, existingPages, serverName) {
        const pageNames = pageNamesFromList(existingPages);
        const hasIndex = pageNames.includes("index.mu");
        if (!hasIndex) {
            return "index";
        }
        if (!isUnsetMicronTabName(tab.name)) {
            const base = tabNameToPageBase(tab);
            return base || null;
        }
        const entered = await DialogUtils.prompt(t("tools.micron_editor.publish_prompt_name", { server: serverName }));
        if (entered === null || !String(entered).trim()) {
            return null;
        }
        let base = String(entered).trim().replace(/\s+/g, "_");
        const lower = base.toLowerCase();
        for (const ext of PAGE_EXTENSIONS) {
            if (lower.endsWith(ext)) {
                return base;
            }
        }
        return base || null;
    }

    async function ensureNodeRunning(node) {
        if (node?.running && node.destination_hash) {
            return node;
        }
        if (!node?.node_id) {
            throw new Error("missing_node");
        }
        const startRes = await window.api.post(apiPath(`/page-nodes/${node.node_id}/start`));
        const destinationHash = startRes.data?.destination_hash || node.destination_hash || "";
        return {
            ...node,
            running: true,
            destination_hash: destinationHash,
        };
    }

    function nomadPagePathForName(pageName) {
        const name = String(pageName || "index.mu").trim();
        if (!name) {
            return "/page/index.mu";
        }
        if (name.startsWith("/page/")) {
            return name;
        }
        if (name.startsWith("/")) {
            return name;
        }
        return `/page/${name}`;
    }

    function rememberPublished(node, pageName) {
        const destinationHash = (node?.destination_hash || "").trim();
        if (!destinationHash || !NOMAD_DESTINATION_HASH.test(destinationHash)) {
            return;
        }
        lastPublished.value = {
            destinationHash,
            pagePath: nomadPagePathForName(pageName),
            pageName: pageName || "index.mu",
            serverName: node.name || "",
        };
    }

    function openPublishedInNomadNet() {
        const published = lastPublished.value;
        if (!published?.destinationHash) {
            return;
        }
        showPublishMenu.value = false;
        pushRoute({
            name: "nomadnetwork",
            params: { destinationHash: published.destinationHash },
            query: {
                path: published.pagePath || "/page/index.mu",
                newTab: "1",
            },
        });
    }

    async function offerOpenInNomadNet(pageName, serverName) {
        if (!lastPublished.value?.destinationHash) {
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

    async function createMeshServerAndPublish() {
        if (publishBusy.value) {
            return;
        }
        const entered = await DialogUtils.prompt(t("tools.micron_editor.publish_create_prompt_name"), "Micron Pages");
        if (entered === null || !String(entered).trim()) {
            return;
        }
        const serverName = String(entered).trim();
        publishBusy.value = true;
        try {
            const createRes = await window.api.post(apiPath("/page-nodes"), { name: serverName });
            const created = createRes.data || {};
            if (!created.node_id) {
                throw new Error("create_failed");
            }
            const running = await ensureNodeRunning(created);
            pageNodes.value = [...pageNodes.value.filter((n) => n.node_id !== running.node_id), running];
            await publishToNode(running, { alreadyRunning: true });
        } catch (e) {
            showPublishMenu.value = false;
            DialogUtils.alert(e.response?.data?.message || t("tools.micron_editor.publish_failed_create"));
        } finally {
            publishBusy.value = false;
        }
    }

    async function publishToNode(node, publishOptions = {}) {
        if (publishBusy.value && !publishOptions.alreadyRunning) {
            return;
        }
        const tab = getActiveTab();
        const busyOwned = !publishOptions.alreadyRunning;
        if (busyOwned) {
            publishBusy.value = true;
        }
        try {
            let running = node;
            if (!publishOptions.alreadyRunning) {
                running = await ensureNodeRunning(node);
            }
            const existingPages = await fetchNodePages(running);
            const pageBase = await resolvePublishPageBase(tab, existingPages, running.name);
            if (!pageBase) {
                return;
            }
            const publishName = pageBaseWithExtension(pageBase, tab);
            const response = await window.api.post(apiPath(`/page-nodes/${running.node_id}/pages`), {
                name: publishName,
                content: tab.content,
            });
            showPublishMenu.value = false;
            const savedName = response.data?.name || publishName;
            await uploadImages(running, [tab.content]);
            rememberPublished(running, savedName);
            await offerOpenInNomadNet(savedName, running.name);
        } catch (e) {
            DialogUtils.alert(
                e.response?.data?.message ||
                    (e.message === "missing_node"
                        ? t("tools.micron_editor.publish_failed")
                        : t("tools.micron_editor.publish_failed"))
            );
        } finally {
            if (busyOwned) {
                publishBusy.value = false;
            }
        }
    }

    async function openPublishSite() {
        showPublishMenu.value = false;
        showPublishSiteModal.value = true;
        try {
            const response = await window.api.get(apiPath("/page-nodes"));
            pageNodes.value = response.data;
        } catch {
            pageNodes.value = [];
        }
    }

    function buildSiteIndexPage(destinationHash, pages) {
        const lines = [`>Links`, ""];
        for (const page of pages) {
            const label = String(page.label || page.name || "")
                .replace(/[`[\]]/g, "")
                .trim();
            const pageName = String(page.name || "").trim();
            if (!pageName) {
                continue;
            }
            lines.push(`[${label || pageName}\`${destinationHash}:/page/${pageName}]`);
        }
        lines.push("");
        return lines.join("\n");
    }

    async function publishSite(payload) {
        if (publishBusy.value) {
            return;
        }
        const pages = payload?.pages || [];
        if (pages.length === 0) {
            return;
        }
        publishBusy.value = true;
        try {
            let node = payload.nodeId ? pageNodes.value.find((n) => n.node_id === payload.nodeId) : null;
            if (!node) {
                if (!payload.newServerName) {
                    DialogUtils.alert(t("tools.micron_editor.publish_site_no_server"));
                    return;
                }
                const createRes = await window.api.post(apiPath("/page-nodes"), { name: payload.newServerName });
                node = createRes.data || {};
                if (!node.node_id) {
                    throw new Error("create_failed");
                }
            }
            const running = await ensureNodeRunning(node);
            pageNodes.value = [...pageNodes.value.filter((n) => n.node_id !== running.node_id), running];
            let published = 0;
            let lastSavedName = null;
            for (const page of pages) {
                try {
                    const response = await window.api.post(apiPath(`/page-nodes/${running.node_id}/pages`), {
                        name: page.name,
                        content: page.content,
                    });
                    lastSavedName = response.data?.name || page.name;
                    published++;
                } catch {
                    console.error(`Failed to publish page: ${page.name}`);
                }
            }
            await uploadImages(
                running,
                pages.map((page) => page.content)
            );
            if (payload.generateIndex && running.destination_hash && published > 0) {
                try {
                    const indexContent = buildSiteIndexPage(running.destination_hash, pages);
                    const indexRes = await window.api.post(apiPath(`/page-nodes/${running.node_id}/pages`), {
                        name: "index.mu",
                        content: indexContent,
                    });
                    lastSavedName = indexRes.data?.name || "index.mu";
                } catch {
                    console.error("Failed to publish generated index page");
                }
            }
            showPublishSiteModal.value = false;
            if (lastSavedName) {
                rememberPublished(running, lastSavedName);
            }
            if (published === 0) {
                DialogUtils.alert(t("tools.micron_editor.publish_failed"));
                return;
            }
            ToastUtils.success(
                t("tools.micron_editor.publish_site_done", {
                    published,
                    total: pages.length,
                    server: running.name,
                })
            );
            if (lastPublished.value?.destinationHash) {
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
        } catch (e) {
            DialogUtils.alert(e.response?.data?.message || t("tools.micron_editor.publish_failed"));
        } finally {
            publishBusy.value = false;
        }
    }

    return {
        showPublishMenu,
        showPublishSiteModal,
        pageNodes,
        publishBusy,
        lastPublished,
        togglePublishMenu,
        fetchNodePages,
        tabNameToPageBase,
        pageBaseWithExtension,
        isUnsetMicronTabName,
        resolvePublishPageBase,
        ensureNodeRunning,
        nomadPagePathForName,
        rememberPublished,
        openPublishedInNomadNet,
        offerOpenInNomadNet,
        createMeshServerAndPublish,
        publishToNode,
        openPublishSite,
        buildSiteIndexPage,
        publishSite,
    };
}
