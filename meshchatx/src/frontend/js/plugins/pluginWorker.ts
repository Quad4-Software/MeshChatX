// SPDX-License-Identifier: 0BSD

type WorkerPostFn = (message: unknown) => void;

type PluginWorkerState = {
    pluginId: string;
    permissions: Record<string, unknown>;
    labels: Record<string, string>;
    theme: unknown;
    allowHtmlFrame: boolean;
    allowedWidgets: string[];
    ui: unknown;
    inputValues: Record<string, string>;
    actionHandler: ((actionId: string) => void | Promise<void>) | null;
    inputHandler: ((id: string, value: string) => void | Promise<void>) | null;
    eventHandlers: Map<string, (payload: unknown) => void | Promise<void>>;
    refreshHandler: (() => void | Promise<void>) | null;
    themeHandler: ((theme: unknown) => void | Promise<void>) | null;
};

type InitMessage = {
    type: "init";
    pluginId: string;
    permissions?: Record<string, unknown>;
    labels?: Record<string, string>;
    theme?: unknown;
    allowHtmlFrame?: boolean;
    allowedWidgets?: string[];
    source: string;
};

function handleWorkerMessage(event: MessageEvent, post: WorkerPostFn): void {
    const message = event.data as InitMessage | Record<string, unknown> | null;
    if (!message || typeof message !== "object") {
        return;
    }

    if (message.type === "init") {
        const init = message as InitMessage;
        const state: PluginWorkerState = {
            pluginId: init.pluginId,
            permissions: init.permissions || {},
            labels: init.labels || {},
            theme: init.theme || null,
            allowHtmlFrame: Boolean(init.allowHtmlFrame),
            allowedWidgets: Array.isArray(init.allowedWidgets) ? init.allowedWidgets : [],
            ui: null,
            inputValues: {},
            actionHandler: null,
            inputHandler: null,
            eventHandlers: new Map(),
            refreshHandler: null,
            themeHandler: null,
        };

        function postRequest(kind: string, payload: unknown): Promise<unknown> {
            return new Promise((resolve, reject) => {
                const requestId = `${Date.now()}-${Math.random()}`;
                const onReply = (replyEvent: MessageEvent) => {
                    const reply = replyEvent.data as {
                        requestId?: string;
                        error?: string;
                        result?: unknown;
                    };
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
            t(key: string): string {
                return state.labels[key] || key;
            },
            async invoke(method: string, args: Record<string, unknown> = {}): Promise<unknown> {
                if (method === "readPaths") {
                    return postRequest("manager", {
                        capability: "destinationPath.read",
                        args,
                    });
                }
                return postRequest("invoke", { method, args });
            },
            async callManager(capability: string, args: Record<string, unknown> = {}): Promise<unknown> {
                return postRequest("manager", { capability, args });
            },
            async clipboardWrite(text: unknown): Promise<unknown> {
                return postRequest("clipboard", { text: String(text ?? "") });
            },
            getTheme(): unknown {
                return state.theme;
            },
            async refreshTheme(): Promise<unknown> {
                const theme = await postRequest("theme", {});
                state.theme = theme;
                return theme;
            },
            onThemeChange(handler: (theme: unknown) => void | Promise<void>): void {
                state.themeHandler = handler;
            },
            setUi(descriptor: unknown): void {
                state.ui = descriptor;
                post({ type: "ui", descriptor });
            },
            onAction(handler: (actionId: string) => void | Promise<void>): void {
                state.actionHandler = handler;
            },
            onEvent(eventName: string, handler: (payload: unknown) => void | Promise<void>): void {
                state.eventHandlers.set(eventName, handler);
            },
            onInput(handler: (id: string, value: string) => void | Promise<void>): void {
                state.inputHandler = handler;
            },
            getInputValue(id: string): string {
                return state.inputValues[id] ?? "";
            },
            setInputValue(id: string, value: unknown): void {
                state.inputValues[id] = value == null ? "" : String(value);
            },
            onRefresh(handler: () => void | Promise<void>): void {
                state.refreshHandler = handler;
            },
            toast(messageText: string, type = "info", duration = 5000): void {
                post({ type: "toast", message: messageText, toastType: type, duration });
            },
            download(filename: string, data: unknown): void {
                post({ type: "download", filename, data });
            },
        };

        const source = `${init.source}\n//# sourceURL=plugin-${init.pluginId}.js`;
        const blob = new Blob([source], { type: "text/javascript" });
        const blobUrl = URL.createObjectURL(blob);
        import(/* @vite-ignore */ blobUrl)
            .then((module: { activate?: (pluginApi: typeof api) => unknown }) => {
                URL.revokeObjectURL(blobUrl);
                if (typeof module.activate === "function") {
                    return module.activate(api);
                }
                throw new Error("Plugin must export activate(api)");
            })
            .catch((error: { message?: string }) => {
                URL.revokeObjectURL(blobUrl);
                post({ type: "error", message: error.message || String(error) });
            });

        self.onmessage = (nextEvent: MessageEvent) => {
            const next = nextEvent.data as Record<string, any> | null;
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
            }
        };
    }
}

self.onmessage = (event: MessageEvent) => {
    handleWorkerMessage(event, (payload) => self.postMessage(payload));
};
