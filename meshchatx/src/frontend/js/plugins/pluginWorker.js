// SPDX-License-Identifier: 0BSD

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
            permissions: message.permissions || {},
            ui: null,
            inputValues: {},
            actionHandler: null,
            eventHandlers: new Map(),
        };

        const api = {
            t(key) {
                return message.labels?.[key] || key;
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
            getInputValue(id) {
                return state.inputValues[id] ?? "";
            },
        };

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

self.onmessage = (event) => {
    handleWorkerMessage(event, (payload) => self.postMessage(payload));
};
