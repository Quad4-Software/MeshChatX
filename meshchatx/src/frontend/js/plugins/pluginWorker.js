// SPDX-License-Identifier: 0BSD

const PLUGIN_MAP_EVENTS = new Set(["click", "moveend", "featureclick"]);

/**
 * @param {MessageEvent} event
 * @param {(message: unknown) => void} post
 */
function handleWorkerMessage(event, post) {
    const message = event.data;
    if (!message || typeof message !== "object") {
        return;
    }

    if (message.type === "init") {
        const state = {
            pluginId: message.pluginId,
            permissions: Array.isArray(message.grantedPermissions)
                ? message.grantedPermissions.filter((permission) => typeof permission === "string")
                : [],
            labels: message.labels || {},
            theme: message.theme || null,
            allowHtmlFrame: Boolean(message.allowHtmlFrame),
            allowedWidgets: Array.isArray(message.allowedWidgets) ? message.allowedWidgets : [],
            ui: null,
            inputValues: {},
            actionHandler: null,
            inputHandler: null,
            eventHandlers: new Map(),
            refreshHandler: null,
            themeHandler: null,
            mapHandlers: new Map(),
            mapSubSeq: 0,
        };

        function requireMapPermission(mode) {
            if (!state.permissions.includes(`map:${mode}`)) {
                throw new Error(`map:${mode} permission not granted`);
            }
        }

        function requireStoragePermission() {
            if (!state.permissions.includes("storage:isolated")) {
                throw new Error("storage:isolated permission not granted");
            }
        }

        function postRequest(kind, payload) {
            return new Promise((resolve, reject) => {
                const requestId = `${Date.now()}-${Math.random()}`;
                const onReply = (replyEvent) => {
                    const reply = replyEvent.data;
                    if (!reply || reply.requestId !== requestId) {
                        return;
                    }
                    self.removeEventListener("message", onReply);
                    if (reply.error) {
                        reject(new Error(reply.error));
                        return;
                    }
                    resolve(reply.result);
                };
                self.addEventListener("message", onReply);
                post({ type: "request", requestId, kind, payload });
            });
        }

        const api = {
            t(key) {
                return state.labels[key] || key;
            },
            hasPermission(permissionId) {
                return state.permissions.includes(String(permissionId));
            },
            async invoke(method, args = {}) {
                if (method === "readPaths") {
                    return postRequest("manager", {
                        capability: "destinationPath.read",
                        args,
                    });
                }
                return postRequest("invoke", { method, args });
            },
            async callManager(capability, args = {}) {
                return postRequest("manager", { capability, args });
            },
            async clipboardWrite(text) {
                if (!state.permissions.includes("clipboard:write")) {
                    throw new Error("clipboard:write permission not granted");
                }
                return postRequest("clipboard", { text: String(text ?? "") });
            },
            async clipboardRead() {
                if (!state.permissions.includes("clipboard:read")) {
                    throw new Error("clipboard:read permission not granted");
                }
                const result = await postRequest("clipboard-read", {});
                return result?.text ?? "";
            },
            storage: {
                async get(key) {
                    requireStoragePermission();
                    const result = await postRequest("storage", {
                        action: "get",
                        key: String(key ?? ""),
                    });
                    return result?.value ?? null;
                },
                async set(key, value) {
                    requireStoragePermission();
                    await postRequest("storage", {
                        action: "set",
                        key: String(key ?? ""),
                        value: typeof value === "string" ? value : JSON.stringify(value ?? null),
                    });
                },
                async delete(key) {
                    requireStoragePermission();
                    const result = await postRequest("storage", {
                        action: "delete",
                        key: String(key ?? ""),
                    });
                    return Boolean(result?.deleted);
                },
                async keys() {
                    requireStoragePermission();
                    const result = await postRequest("storage", { action: "list" });
                    return Array.isArray(result?.keys) ? result.keys : [];
                },
                async clear() {
                    requireStoragePermission();
                    const result = await postRequest("storage", { action: "clear" });
                    return Number(result?.removed || 0);
                },
            },
            net: {
                async fetch(url, options = {}) {
                    if (!state.permissions.includes("network:fetch")) {
                        throw new Error("network:fetch permission not granted");
                    }
                    return postRequest("netfetch", {
                        url: String(url ?? ""),
                        method: options.method,
                        headers: options.headers,
                        body: options.body,
                    });
                },
            },
            app: {
                async navigate(route, params = {}) {
                    return postRequest("navigate", { route: String(route ?? ""), params });
                },
            },
            getTheme() {
                return state.theme;
            },
            async refreshTheme() {
                const theme = await postRequest("theme", {});
                state.theme = theme;
                return theme;
            },
            onThemeChange(handler) {
                state.themeHandler = handler;
            },
            setUi(descriptor) {
                state.ui = descriptor;
                post({ type: "ui", descriptor });
            },
            onAction(handler) {
                state.actionHandler = handler;
            },
            onEvent(eventName, handler) {
                state.eventHandlers.set(eventName, handler);
            },
            onInput(handler) {
                state.inputHandler = handler;
            },
            getInputValue(id) {
                return state.inputValues[id] ?? "";
            },
            setInputValue(id, value) {
                state.inputValues[id] = value == null ? "" : String(value);
            },
            onRefresh(handler) {
                state.refreshHandler = handler;
            },
            map: {
                isAvailable() {
                    return postRequest("map", { action: "isAvailable" });
                },
                async getState() {
                    requireMapPermission("read");
                    return postRequest("map", { action: "getState" });
                },
                async setView(view = {}) {
                    requireMapPermission("write");
                    return postRequest("map", { action: "setView", view });
                },
                async addLayer(options = {}) {
                    requireMapPermission("write");
                    return postRequest("map", {
                        action: "addLayer",
                        id: options.id,
                        layerId: options.layerId,
                        name: options.name,
                        data: options.data,
                    });
                },
                async setLayerData(layerId, data) {
                    requireMapPermission("write");
                    return postRequest("map", { action: "setLayerData", layerId, data });
                },
                async removeLayer(layerId) {
                    requireMapPermission("write");
                    return postRequest("map", { action: "removeLayer", layerId });
                },
                async clearLayers() {
                    requireMapPermission("write");
                    return postRequest("map", { action: "clearLayers" });
                },
                on(event, handler) {
                    requireMapPermission("read");
                    const name = String(event || "");
                    if (!PLUGIN_MAP_EVENTS.has(name)) {
                        throw new Error(`unknown_map_event:${name || "?"}`);
                    }
                    if (typeof handler !== "function") {
                        throw new Error("map.on requires a handler function");
                    }
                    const subscriptionId = `map-sub-${++state.mapSubSeq}`;
                    state.mapHandlers.set(subscriptionId, { event: name, handler });
                    post({ type: "map-subscribe", subscribe: true, events: [name] });
                    return subscriptionId;
                },
                off(subscriptionId) {
                    const entry = state.mapHandlers.get(subscriptionId);
                    if (!entry) {
                        return;
                    }
                    state.mapHandlers.delete(subscriptionId);
                    const stillUsed = [...state.mapHandlers.values()].some((h) => h.event === entry.event);
                    if (!stillUsed) {
                        post({ type: "map-subscribe", subscribe: false, events: [entry.event] });
                    }
                },
            },
            toast(message, type = "info", duration = 5000) {
                post({ type: "toast", message, toastType: type, duration });
            },
            download(filename, data) {
                post({ type: "download", filename, data });
            },
        };

        const source = `${message.source}\n//# sourceURL=plugin-${message.pluginId}.js`;
        const blob = new Blob([source], { type: "text/javascript" });
        const blobUrl = URL.createObjectURL(blob);
        import(/* @vite-ignore */ blobUrl)
            .then((module) => {
                URL.revokeObjectURL(blobUrl);
                if (typeof module.activate === "function") {
                    return module.activate(api);
                }
                throw new Error("Plugin must export activate(api)");
            })
            .catch((error) => {
                URL.revokeObjectURL(blobUrl);
                post({ type: "error", message: error.message || String(error) });
            });

        self.onmessage = (nextEvent) => {
            const next = nextEvent.data;
            if (!next || typeof next !== "object") {
                return;
            }
            if (next.type === "action") {
                if (typeof state.actionHandler === "function") {
                    void state.actionHandler(next.actionId);
                }
                return;
            }
            if (next.type === "input") {
                state.inputValues[next.id] = next.value;
                if (typeof state.inputHandler === "function") {
                    void state.inputHandler(next.id, next.value);
                }
                return;
            }
            if (next.type === "refresh-ui") {
                if (typeof state.refreshHandler === "function") {
                    void state.refreshHandler();
                }
                return;
            }
            if (next.type === "theme") {
                state.theme = next.theme || null;
                if (typeof state.themeHandler === "function") {
                    void state.themeHandler(state.theme);
                }
                return;
            }
            if (next.type === "event") {
                const handler = state.eventHandlers.get(next.event);
                if (typeof handler === "function") {
                    void handler(next.payload);
                }
                return;
            }
            if (next.type === "map-event") {
                for (const entry of state.mapHandlers.values()) {
                    if (entry.event === next.event && typeof entry.handler === "function") {
                        void entry.handler(next.payload);
                    }
                }
            }
        };
    }
}

self.onmessage = (event) => {
    handleWorkerMessage(event, (payload) => self.postMessage(payload));
};
