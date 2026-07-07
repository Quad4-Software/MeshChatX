// SPDX-License-Identifier: 0BSD

import { validatePluginManifest } from "./pluginManifest.js";
import { buildPluginLabelMap } from "./pluginLabels.js";
import { registerNavItem, unregisterNavItem } from "../registries/navRegistry.js";
import { registerTool, unregisterTool } from "../registries/toolsRegistry.js";
import { onWsEvent, offWsEvent } from "../registries/wsEventRegistry.js";

/** @typedef {import('./pluginManifest.js').PluginManifest} PluginManifest */

export class PluginHost {
    constructor() {
        /** @type {Map<string, { worker: Worker, cleanup: Array<() => void>, manifest: PluginManifest, lastDescriptor: object | null }>} */
        this.instances = new Map();
    }

    /**
     * @param {(key: string) => string} [translate]
     */
    async loadEnabledPlugins(apiClient, translate) {
        const response = await apiClient.get("/api/v1/plugins");
        const plugins = response.data?.plugins || [];
        const labels = typeof translate === "function" ? buildPluginLabelMap(translate) : {};
        for (const plugin of plugins) {
            if (!plugin.enabled) {
                continue;
            }
            await this.loadPlugin(plugin, apiClient, labels);
        }
    }

    /**
     * @param {Record<string, unknown>} plugin
     * @param {ReturnType<import('../apiClient.js').createApiClient>} apiClient
     */
    async loadPlugin(plugin, apiClient, labels = {}) {
        const pluginId = plugin.id;
        if (this.instances.has(pluginId)) {
            return;
        }
        const manifest = validatePluginManifest(plugin.manifest);
        if (!manifest.frontend) {
            return;
        }
        const assetUrl = `/api/v1/plugins/${encodeURIComponent(pluginId)}/asset/${manifest.frontend.entry}`;
        const sourceResponse = await apiClient.get(assetUrl, { responseType: "text" });
        const source = typeof sourceResponse.data === "string" ? sourceResponse.data : String(sourceResponse.data ?? "");
        const worker = new Worker(new URL("./pluginWorker.js", import.meta.url), { type: "module" });
        const cleanup = [];

        worker.onmessage = (event) => {
            this.handleWorkerMessage(pluginId, event.data);
        };
        worker.onerror = () => {
            this.unloadPlugin(pluginId);
        };

        worker.postMessage({
            type: "init",
            pluginId,
            permissions: manifest.permissions || {},
            source,
            labels,
        });

        cleanup.push(...this.registerContributions(pluginId, manifest));
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

        this.instances.set(pluginId, { worker, cleanup, manifest, lastDescriptor: null });
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
     */
    registerContributions(pluginId, manifest) {
        const cleanup = [];
        const contributes = manifest.contributes || {};
        for (const item of contributes.navItems || []) {
            registerNavItem({ ...item, pluginId });
            cleanup.push(() => unregisterNavItem(item.id));
        }
        for (const item of contributes.toolsPageEntries || []) {
            registerTool({ ...item, pluginId });
            cleanup.push(() => unregisterTool(item.name));
        }
        return cleanup;
    }

    /**
     * @param {string} pluginId
     * @param {unknown} message
     */
    handleWorkerMessage(pluginId, message) {
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
            window.dispatchEvent(
                new CustomEvent("meshchatx-plugin-error", {
                    detail: { pluginId, message: message.message },
                })
            );
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
