// SPDX-License-Identifier: 0BSD

import type { ApiClient } from "../apiClient.js";
import type { PluginManifest } from "./pluginManifest.js";
import { validatePluginManifest } from "./pluginManifest.js";
import { loadPluginLabelMap, resolvePluginUiString } from "./pluginLabels.js";
import { setPluginUiLabels, clearPluginUiLabels } from "./pluginUiRegistry.js";
import { validateUiDescriptor } from "./pluginUiDescriptor.js";
import { isKnownHostWidget } from "./pluginHostWidgets.js";
import type { NavEntry } from "../registries/coreNavEntries.js";
import type { ToolEntry } from "../registries/coreToolsEntries.js";
import { registerNavItem, unregisterNavItem } from "../registries/navRegistry.js";
import { registerTool, unregisterTool } from "../registries/toolsRegistry.js";
import { onWsEvent, offWsEvent } from "../registries/wsEventRegistry.js";
import ToastUtils from "../ToastUtils.js";
import { getThemeSnapshot } from "../../theme/themeEngine.js";
import GlobalState from "../GlobalState.js";

/** Minimal router surface used by PluginHost (hashRouter facade). */
export type MeshHashRouter = {
    push: (target: unknown) => Promise<unknown> | unknown;
    replace?: (target: unknown) => Promise<unknown> | unknown;
    currentRoute?: { value: unknown };
    hasRoute: (name: string) => boolean;
    addRoute: (record: any) => void;
    removeRoute: (name: string) => void;
};

export type PluginListEntry = {
    id: string;
    enabled?: boolean;
    manifest: unknown;
};

export type PluginHostInstance = {
    worker: Worker;
    cleanup: Array<() => void>;
    manifest: PluginManifest;
    lastDescriptor: Record<string, unknown> | null;
    lastUiError: string;
    apiClient: ApiClient | null;
    allowHtmlFrame: boolean;
    allowedWidgets: string[];
    routeName: string | null;
};

type WorkerOutboundMessage = {
    type?: string;
    descriptor?: unknown;
    message?: string;
    toastType?: string;
    duration?: number;
    data?: BlobPart;
    filename?: string;
    requestId?: string;
    kind?: string;
    payload?: Record<string, unknown>;
};

type WorkerRequestMessage = {
    type: "request";
    requestId: string;
    kind?: string;
    payload?: Record<string, unknown>;
};

const FAILURE_REPORT_INTERVAL_MS = 5000;
const lastFailureReportAt = new Map<string, number>();

export function pluginRouteName(pluginId: string): string {
    return `plugin-${String(pluginId).replace(/[^a-zA-Z0-9_-]/g, "-")}`;
}

export function pluginRoutePath(pluginId: string): string {
    return `/plugins/${encodeURIComponent(pluginId)}`;
}

export class PluginHost {
    instances: Map<string, PluginHostInstance>;
    router: MeshHashRouter | null;
    _themeListener: ((event: CustomEvent) => void) | null;

    constructor() {
        this.instances = new Map();
        this.router = null;
        this._themeListener = null;
    }

    attachRouter(router: MeshHashRouter): void {
        this.router = router;
    }

    ensureThemeBridge(): void {
        if (this._themeListener || typeof window === "undefined") {
            return;
        }
        this._themeListener = (event: CustomEvent) => {
            const snapshot = event.detail || getThemeSnapshot(GlobalState.config);
            for (const instance of this.instances.values()) {
                instance.worker.postMessage({ type: "theme", theme: snapshot });
            }
        };
        window.addEventListener("meshchatx-theme-changed", this._themeListener as EventListener);
    }

    async loadEnabledPlugins(apiClient: ApiClient, locale = "en"): Promise<void> {
        this.ensureThemeBridge();
        const response = await apiClient.get<{ plugins?: PluginListEntry[] }>("/api/v1/plugins");
        const plugins = response.data?.plugins || [];
        for (const plugin of plugins) {
            if (!plugin.enabled) {
                continue;
            }
            await this.loadPlugin(plugin, apiClient, locale);
        }
    }

    async loadPlugin(plugin: PluginListEntry, apiClient: ApiClient, locale = "en"): Promise<void> {
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
        const cleanup: (() => void)[] = [];

        const ui = manifest.ui || {};
        const declaredWidgets = Array.isArray(ui.widgets) ? ui.widgets.filter((w) => isKnownHostWidget(w)) : [];
        const allowHtmlFrame = Boolean(
            manifest.permissions?.ui === "sandboxed-html" ||
            (Array.isArray(manifest.permissions?.ui) && manifest.permissions.ui.includes("sandboxed-html")) ||
            manifest.permissions?.["ui:sandboxed-html"] === true
        );

        worker.onmessage = (event: MessageEvent) => {
            this.handleWorkerMessage(pluginId, event.data, apiClient);
        };
        worker.onerror = (event: ErrorEvent) => {
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
            const eventHandler = (payload: { plugin_id?: string; event?: string; payload?: unknown }) => {
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

        const requestHandler = async (message: WorkerRequestMessage | WorkerOutboundMessage) => {
            if (!message || message.type !== "request") {
                return;
            }
            try {
                let result: unknown;
                if (message.kind === "invoke") {
                    const response = await apiClient.post(`/api/v1/plugins/${encodeURIComponent(pluginId)}/invoke`, {
                        method: message.payload?.method,
                        args: message.payload?.args,
                    });
                    result = (response.data as { result?: unknown })?.result;
                } else if (message.kind === "manager") {
                    const response = await apiClient.post(`/api/v1/plugins/${encodeURIComponent(pluginId)}/invoke`, {
                        method: "callManager",
                        args: message.payload,
                    });
                    result = (response.data as { result?: unknown })?.result;
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
            } catch (error: unknown) {
                const err = error as { message?: string };
                worker.postMessage({
                    requestId: message.requestId,
                    error: err?.message || String(error),
                });
            }
        };
        worker.addEventListener("message", (event: MessageEvent) => {
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

    ensurePluginRoute(pluginId: string): string | null {
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
            meta: {
                featureLoad: () => import("../../features/plugins/PluginPage.svelte"),
            },
            props: { pluginId },
        });
        return name;
    }

    removePluginRoute(pluginId: string, routeName: string): void {
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

    async reportPluginFailure(
        pluginId: string,
        reason: string,
        apiClient: ApiClient,
        source = "frontend"
    ): Promise<void> {
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

    getLastDescriptor(pluginId: string): Record<string, unknown> | null {
        return this.instances.get(pluginId)?.lastDescriptor ?? null;
    }

    getLastUiError(pluginId: string): string {
        return this.instances.get(pluginId)?.lastUiError || "";
    }

    getPluginUiCaps(pluginId: string): { allowedWidgets: string[]; allowHtmlFrame: boolean } {
        const instance = this.instances.get(pluginId);
        return {
            allowedWidgets: instance?.allowedWidgets || [],
            allowHtmlFrame: Boolean(instance?.allowHtmlFrame),
        };
    }

    requestUiRefresh(pluginId: string): void {
        const instance = this.instances.get(pluginId);
        if (!instance) {
            return;
        }
        instance.worker.postMessage({ type: "refresh-ui" });
    }

    registerContributions(
        pluginId: string,
        manifest: PluginManifest,
        labels: Record<string, string>
    ): Array<() => void> {
        const cleanup: (() => void)[] = [];
        const contributes = manifest.contributes || {};
        for (const item of contributes.navItems || []) {
            registerNavItem({
                ...(item as unknown as NavEntry),
                pluginId,
                label: resolvePluginUiString(labels, String(item.labelKey ?? ""), manifest),
            });
            cleanup.push(() => unregisterNavItem(String(item.id)));
        }
        for (const item of contributes.toolsPageEntries || []) {
            registerTool({
                ...(item as unknown as ToolEntry),
                pluginId,
                title: resolvePluginUiString(labels, String(item.titleKey ?? ""), manifest),
                description: resolvePluginUiString(labels, String(item.descriptionKey ?? ""), manifest),
            });
            cleanup.push(() => unregisterTool(String(item.name)));
        }
        return cleanup;
    }

    handleWorkerMessage(pluginId: string, message: unknown, apiClient?: ApiClient): void {
        if (!message || typeof message !== "object") {
            return;
        }
        const msg = message as WorkerOutboundMessage;
        if (msg.type === "ui") {
            const instance = this.instances.get(pluginId);
            const validated = validateUiDescriptor(msg.descriptor, {
                pluginId,
                allowHtmlFrame: Boolean(instance?.allowHtmlFrame),
                allowedWidgets: instance?.allowedWidgets || [],
            });
            if (validated.ok === false) {
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
        if (msg.type === "error") {
            const client = apiClient || this.instances.get(pluginId)?.apiClient;
            if (client) {
                void this.reportPluginFailure(pluginId, msg.message || "Plugin activation failed", client);
            }
            window.dispatchEvent(
                new CustomEvent("meshchatx-plugin-error", {
                    detail: { pluginId, message: msg.message },
                })
            );
            this.unloadPlugin(pluginId);
        }
        if (msg.type === "toast") {
            ToastUtils.show(msg.message || "", msg.toastType || "info", msg.duration ?? 5000);
        }
        if (msg.type === "download") {
            try {
                const blob = new Blob([msg.data || ""], {
                    type: "application/json",
                });
                const url = URL.createObjectURL(blob);
                const a = document.createElement("a");
                a.href = url;
                a.download = msg.filename || "download.json";
                document.body.appendChild(a);
                a.click();
                document.body.removeChild(a);
                URL.revokeObjectURL(url);
            } catch (e) {
                console.error("Plugin download failed:", e);
            }
        }
    }

    unloadPlugin(pluginId: string): void {
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

    postAction(pluginId: string, actionId: string): void {
        const instance = this.instances.get(pluginId);
        if (!instance) {
            return;
        }
        instance.worker.postMessage({ type: "action", actionId });
    }

    postInput(pluginId: string, id: string, value: unknown): void {
        const instance = this.instances.get(pluginId);
        if (!instance) {
            return;
        }
        instance.worker.postMessage({ type: "input", id, value });
    }
}

export const pluginHost = new PluginHost();
