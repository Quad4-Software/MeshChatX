// SPDX-License-Identifier: 0BSD

import { validatePluginManifest } from "./pluginManifest.js";
import { loadPluginLabelMap, resolvePluginUiString } from "./pluginLabels.js";
import { setPluginUiLabels, clearPluginUiLabels } from "./pluginUiRegistry.js";
import { registerNavItem, unregisterNavItem } from "../registries/navRegistry.js";
import { registerTool, unregisterTool } from "../registries/toolsRegistry.js";
import { onWsEvent, offWsEvent } from "../registries/wsEventRegistry.js";

/** @typedef {import('./pluginManifest.js').PluginManifest} PluginManifest */

const FAILURE_REPORT_INTERVAL_MS = 5000;
/** @type {Map<string, number>} */
const lastFailureReportAt = new Map();

export class PluginHost {
    constructor() {
        /** @type {Map<string, { worker: Worker, cleanup: Array<() => void>, manifest: PluginManifest, lastDescriptor: object | null, apiClient: ReturnType<import('../apiClient.js').createApiClient> | null }>} */
        this.instances = new Map();
    }

    /**
     * @param {ReturnType<import('../apiClient.js').createApiClient>} apiClient
     * @param {string} [locale]
     */
    async loadEnabledPlugins(apiClient, locale = "en") {
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
        const labels = await loadPluginLabelMap(apiClient, pluginId, locale, manifest);
        setPluginUiLabels(pluginId, labels);
        const assetUrl = `/api/v1/plugins/${encodeURIComponent(pluginId)}/asset/${manifest.frontend.entry}`;
        const sourceResponse = await apiClient.get(assetUrl, { responseType: "text" });
        const source =
            typeof sourceResponse.data === "string" ? sourceResponse.data : String(sourceResponse.data ?? "");
        const worker = new Worker(new URL("./pluginWorker.js", import.meta.url), { type: "module" });
        const cleanup = [];

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

        worker.postMessage({
            type: "init",
            pluginId,
            permissions: manifest.permissions || {},
            source,
            labels,
        });

        cleanup.push(...this.registerContributions(pluginId, manifest, labels));
        cleanup.push(() => clearPluginUiLabels(pluginId));
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
            apiClient,
        });
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
            if (instance) {
                instance.lastDescriptor = message.descriptor;
            }
            window.dispatchEvent(
                new CustomEvent("meshchatx-plugin-ui", {
                    detail: { pluginId, descriptor: message.descriptor },
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
