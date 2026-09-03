// SPDX-License-Identifier: 0BSD

import { validatePluginManifest } from "./pluginManifest.js";
import { loadPluginLabelMap, resolvePluginUiString } from "./pluginLabels.js";
import { setPluginUiLabels, clearPluginUiLabels } from "./pluginUiRegistry.js";
import { validateUiDescriptor } from "./pluginUiDescriptor.js";
import { isKnownHostWidget } from "./pluginHostWidgets.js";
import { registerNavItem, unregisterNavItem } from "../registries/navRegistry.js";
import { registerTool, unregisterTool } from "../registries/toolsRegistry.js";
import { onWsEvent, offWsEvent } from "../registries/wsEventRegistry.js";
import ToastUtils from "../ToastUtils.js";
import { getThemeSnapshot } from "../../theme/themeEngine.js";
import { GlobalState } from "../GlobalState.js";

/** @typedef {import('./pluginManifest.js').PluginManifest} PluginManifest */

const FAILURE_REPORT_INTERVAL_MS = 5000;
/** @type {Map<string, number>} */
const lastFailureReportAt = new Map();

/**
 * @param {string} pluginId
 * @returns {string}
 */
export function pluginRouteName(pluginId) {
    return `plugin-${String(pluginId).replace(/[^a-zA-Z0-9_-]/g, "-")}`;
}

/**
 * @param {string} pluginId
 * @returns {string}
 */
export function pluginRoutePath(pluginId) {
    return `/plugins/${encodeURIComponent(pluginId)}`;
}

export class PluginHost {
    constructor() {
        /** @type {Map<string, { worker: Worker, cleanup: Array<() => void>, manifest: PluginManifest, lastDescriptor: object | null, lastUiError: string, apiClient: ReturnType<import('../apiClient.js').createApiClient> | null, allowHtmlFrame: boolean, allowedWidgets: string[], routeName: string | null }>} */
        this.instances = new Map();
        /** @type {import('vue-router').Router | null} */
        this.router = null;
        this._themeListener = null;
    }

    /**
     * @param {import('vue-router').Router} router
     */
    attachRouter(router) {
        this.router = router;
    }

    ensureThemeBridge() {
        if (this._themeListener || typeof window === "undefined") {
            return;
        }
        this._themeListener = (event) => {
            const snapshot = event.detail || getThemeSnapshot(GlobalState.config);
            for (const instance of this.instances.values()) {
                instance.worker.postMessage({ type: "theme", theme: snapshot });
            }
        };
        window.addEventListener("meshchatx-theme-changed", this._themeListener);
    }

    /**
     * @param {ReturnType<import('../apiClient.js').createApiClient>} apiClient
     * @param {string} [locale]
     */
    async loadEnabledPlugins(apiClient, locale = "en") {
        this.ensureThemeBridge();
        const response = await apiClient.get("/api/v1/plugins");
        const plugins = response.data?.plugins || [];
        for (const plugin of plugins) {
            if (!plugin.enabled) {
                continue;
            }
            await this.loadPlugin(plugin, apiClient, locale);
        }
    }

    /**
     * @param {Record<string, unknown>} plugin
     * @param {ReturnType<import('../apiClient.js').createApiClient>} apiClient
     * @param {string} [locale]
     */
    async loadPlugin(plugin, apiClient, locale = "en") {
        const pluginId = plugin.id;
        if (this.instances.has(pluginId)) {
            return;
        }
        const manifest = validatePluginManifest(plugin.manifest);
        if (!manifest.frontend) {
            return;
        }
        if (manifest.frontend.type === "wasm") {
            throw new Error("Plugin frontend.type wasm is not implemented yet");
        }
        const labels = await loadPluginLabelMap(apiClient, pluginId, locale, manifest);
        setPluginUiLabels(pluginId, labels);
        const assetUrl = `/api/v1/plugins/${encodeURIComponent(pluginId)}/asset/${manifest.frontend.entry}?v=${encodeURIComponent(manifest.version || "1")}`;
        const sourceResponse = await apiClient.get(assetUrl, { responseType: "text" });
        const source =
            typeof sourceResponse.data === "string" ? sourceResponse.data : String(sourceResponse.data ?? "");
        const worker = new Worker(new URL("./pluginWorker.js", import.meta.url), { type: "module" });
        const cleanup = [];

        const ui = manifest.ui || {};
        const declaredWidgets = Array.isArray(ui.widgets) ? ui.widgets.filter((w) => isKnownHostWidget(w)) : [];
        const allowHtmlFrame = Boolean(
            manifest.permissions?.ui === "sandboxed-html" ||
            (Array.isArray(manifest.permissions?.ui) && manifest.permissions.ui.includes("sandboxed-html")) ||
            manifest.permissions?.["ui:sandboxed-html"] === true
        );

        worker.onmessage = (event) => {
            this.handleWorkerMessage(pluginId, event.data, apiClient);
        };
        worker.onerror = (event) => {
            void this.reportPluginFailure(
                pluginId,
                event.message || "Plugin worker crashed",
                apiClient,
                "frontend-worker"
            );
            this.unloadPlugin(pluginId);
        };

        const theme = getThemeSnapshot(GlobalState.config);
        worker.postMessage({
            type: "init",
            pluginId,
            permissions: manifest.permissions || {},
            source,
            labels,
            theme,
            allowHtmlFrame,
            allowedWidgets: declaredWidgets,
        });

        cleanup.push(...this.registerContributions(pluginId, manifest, labels));
        cleanup.push(() => clearPluginUiLabels(pluginId));
        const routeName = this.ensurePluginRoute(pluginId);
        if (routeName) {
            cleanup.push(() => this.removePluginRoute(pluginId, routeName));
        }

        if ((manifest.permissions?.hooks || []).length > 0) {
            const eventHandler = (payload) => {
                if (payload?.plugin_id !== pluginId) {
                    return;
                }
                worker.postMessage({
                    type: "event",
                    event: payload?.event,
                    payload: payload?.payload,
                });
            };
            onWsEvent("plugin.event", eventHandler);
            cleanup.push(() => offWsEvent("plugin.event", eventHandler));
        }

        const requestHandler = async (message) => {
            if (!message || message.type !== "request") {
                return;
            }
            try {
                let result;
                if (message.kind === "invoke") {
                    const response = await apiClient.post(`/api/v1/plugins/${encodeURIComponent(pluginId)}/invoke`, {
                        method: message.payload.method,
                        args: message.payload.args,
                    });
                    result = response.data?.result;
                } else if (message.kind === "manager") {
                    const response = await apiClient.post(`/api/v1/plugins/${encodeURIComponent(pluginId)}/invoke`, {
                        method: "callManager",
                        args: message.payload,
                    });
                    result = response.data?.result;
                } else if (message.kind === "clipboard") {
                    const text = String(message.payload?.text || "");
                    if (typeof navigator !== "undefined" && navigator.clipboard?.writeText) {
                        await navigator.clipboard.writeText(text);
                        result = { ok: true };
                    } else {
                        throw new Error("Clipboard unavailable");
                    }
                } else if (message.kind === "theme") {
                    result = getThemeSnapshot(GlobalState.config);
                }
                worker.postMessage({ requestId: message.requestId, result });
            } catch (error) {
                worker.postMessage({
                    requestId: message.requestId,
                    error: error?.message || String(error),
                });
            }
        };
        worker.addEventListener("message", (event) => {
            void requestHandler(event.data);
        });

        this.instances.set(pluginId, {
            worker,
            cleanup,
            manifest,
            lastDescriptor: null,
            lastUiError: "",
            apiClient,
            allowHtmlFrame,
            allowedWidgets: declaredWidgets,
            routeName,
        });
    }

    /**
     * @param {string} pluginId
     * @returns {string | null}
     */
    ensurePluginRoute(pluginId) {
        if (!this.router) {
            return null;
        }
        const name = pluginRouteName(pluginId);
        if (this.router.hasRoute(name)) {
            return name;
        }
        this.router.addRoute({
            name,
            path: pluginRoutePath(pluginId),
            component: () => import("../../components/plugins/PluginPage.vue"),
            props: { pluginId },
        });
        return name;
    }

    /**
     * @param {string} pluginId
     * @param {string} routeName
     */
    removePluginRoute(pluginId, routeName) {
        if (!this.router) {
            return;
        }
        // Keep bundled Bug Reports route stable for deep links.
        if (pluginId === "com.meshchatx.mcx-bugs" && routeName === "plugin-mcx-bugs") {
            return;
        }
        if (pluginId === "com.meshchatx.mcx-bugs") {
            return;
        }
        if (this.router.hasRoute(routeName)) {
            this.router.removeRoute(routeName);
        }
    }

    /**
     * @param {string} pluginId
     * @param {string} reason
     * @param {ReturnType<import('../apiClient.js').createApiClient>} apiClient
     * @param {string} [source]
     */
    async reportPluginFailure(pluginId, reason, apiClient, source = "frontend") {
        const now = Date.now();
        const last = lastFailureReportAt.get(pluginId) || 0;
        if (now - last < FAILURE_REPORT_INTERVAL_MS) {
            return;
        }
        lastFailureReportAt.set(pluginId, now);
        try {
            await apiClient.post(`/api/v1/plugins/${encodeURIComponent(pluginId)}/report-failure`, {
                reason,
                source,
            });
        } catch (error) {
            console.debug("Plugin failure report failed:", error);
        }
    }

    getLastDescriptor(pluginId) {
        return this.instances.get(pluginId)?.lastDescriptor ?? null;
    }

    getLastUiError(pluginId) {
        return this.instances.get(pluginId)?.lastUiError || "";
    }

    getPluginUiCaps(pluginId) {
        const instance = this.instances.get(pluginId);
        return {
            allowedWidgets: instance?.allowedWidgets || [],
            allowHtmlFrame: Boolean(instance?.allowHtmlFrame),
        };
    }

    requestUiRefresh(pluginId) {
        const instance = this.instances.get(pluginId);
        if (!instance) {
            return;
        }
        instance.worker.postMessage({ type: "refresh-ui" });
    }

    /**
     * @param {string} pluginId
     * @param {PluginManifest} manifest
     * @param {Record<string, string>} labels
     */
    registerContributions(pluginId, manifest, labels) {
        const cleanup = [];
        const contributes = manifest.contributes || {};
        for (const item of contributes.navItems || []) {
            registerNavItem({
                ...item,
                pluginId,
                label: resolvePluginUiString(labels, item.labelKey, manifest),
            });
            cleanup.push(() => unregisterNavItem(item.id));
        }
        for (const item of contributes.toolsPageEntries || []) {
            registerTool({
                ...item,
                pluginId,
                title: resolvePluginUiString(labels, item.titleKey, manifest),
                description: resolvePluginUiString(labels, item.descriptionKey, manifest),
            });
            cleanup.push(() => unregisterTool(item.name));
        }
        return cleanup;
    }

    /**
     * @param {string} pluginId
     * @param {unknown} message
     * @param {ReturnType<import('../apiClient.js').createApiClient>} [apiClient]
     */
    handleWorkerMessage(pluginId, message, apiClient) {
        if (!message || typeof message !== "object") {
            return;
        }
        if (message.type === "ui") {
            const instance = this.instances.get(pluginId);
            const validated = validateUiDescriptor(message.descriptor, {
                pluginId,
                allowHtmlFrame: Boolean(instance?.allowHtmlFrame),
                allowedWidgets: instance?.allowedWidgets || [],
            });
            if (!validated.ok) {
                if (instance) {
                    instance.lastUiError = validated.error;
                }
                window.dispatchEvent(
                    new CustomEvent("meshchatx-plugin-ui-error", {
                        detail: { pluginId, message: validated.error, uiError: true },
                    })
                );
                window.dispatchEvent(
                    new CustomEvent("meshchatx-plugin-ui", {
                        detail: {
                            pluginId,
                            descriptor: instance?.lastDescriptor || null,
                            error: validated.error,
                        },
                    })
                );
                return;
            }
            if (instance) {
                instance.lastDescriptor = validated.descriptor;
                instance.lastUiError = "";
            }
            window.dispatchEvent(
                new CustomEvent("meshchatx-plugin-ui", {
                    detail: { pluginId, descriptor: validated.descriptor, error: "" },
                })
            );
        }
        if (message.type === "error") {
            const client = apiClient || this.instances.get(pluginId)?.apiClient;
            if (client) {
                void this.reportPluginFailure(pluginId, message.message || "Plugin activation failed", client);
            }
            window.dispatchEvent(
                new CustomEvent("meshchatx-plugin-error", {
                    detail: { pluginId, message: message.message },
                })
            );
            this.unloadPlugin(pluginId);
        }
        if (message.type === "toast") {
            ToastUtils.show(message.message || "", message.toastType || "info", message.duration ?? 5000);
        }
        if (message.type === "download") {
            try {
                const blob = new Blob([message.data || ""], {
                    type: "application/json",
                });
                const url = URL.createObjectURL(blob);
                const a = document.createElement("a");
                a.href = url;
                a.download = message.filename || "download.json";
                document.body.appendChild(a);
                a.click();
                document.body.removeChild(a);
                URL.revokeObjectURL(url);
            } catch (e) {
                console.error("Plugin download failed:", e);
            }
        }
    }

    unloadPlugin(pluginId) {
        const instance = this.instances.get(pluginId);
        if (!instance) {
            return;
        }
        instance.worker.terminate();
        for (const fn of instance.cleanup) {
            fn();
        }
        this.instances.delete(pluginId);
        lastFailureReportAt.delete(pluginId);
    }

    postAction(pluginId, actionId) {
        const instance = this.instances.get(pluginId);
        if (!instance) {
            return;
        }
        instance.worker.postMessage({ type: "action", actionId });
    }

    postInput(pluginId, id, value) {
        const instance = this.instances.get(pluginId);
        if (!instance) {
            return;
        }
        instance.worker.postMessage({ type: "input", id, value });
    }
}

export const pluginHost = new PluginHost();
