import mitt from "mitt";

class WebSocketConnection {
    constructor() {
        this.emitter = mitt();
        this.ws = null;
        this.pingInterval = null;
        this.reconnectTimeout = null;
        this.initialized = false;
        this.destroyed = false;
    }

    async connect() {
        this.destroyed = false;

        if (typeof window === "undefined" || !window.axios) {
            setTimeout(() => this.connect(), 100);
            return;
        }

        this.initialized = true;
        this.reconnect();
        if (this.pingInterval) clearInterval(this.pingInterval);
        this.pingInterval = setInterval(() => {
            this.ping();
        }, 30000);
    }

    // add event listener
    on(event, handler) {
        this.emitter.on(event, handler);
    }

    // remove event listener
    off(event, handler) {
        this.emitter.off(event, handler);
    }

    // emit event
    emit(type, event) {
        this.emitter.emit(type, event);
    }

    reconnect() {
        if (!this.initialized || this.destroyed || typeof window === "undefined" || !window.location) {
            return;
        }

        // connect to websocket
        const wsUrl = window.location.origin.replace(/^https/, "wss").replace(/^http/, "ws") + "/ws";
        this.ws = new WebSocket(wsUrl);

        // auto reconnect when websocket closes
        this.ws.addEventListener("close", () => {
            if (this.destroyed) return;
            this.reconnectTimeout = setTimeout(() => {
                if (!this.destroyed) {
                    this.reconnect();
                }
            }, 1000);
        });

        // emit data received from websocket
        this.ws.onmessage = (message) => {
            this.emit("message", message);
        };
    }

    destroy() {
        this.destroyed = true;
        this.initialized = false;
        if (this.pingInterval) {
            clearInterval(this.pingInterval);
            this.pingInterval = null;
        }
        if (this.reconnectTimeout) {
            clearTimeout(this.reconnectTimeout);
            this.reconnectTimeout = null;
        }
        if (this.ws) {
            this.ws.close();
            this.ws = null;
        }
    }

    send(message) {
        if (this.ws != null && this.ws.readyState === WebSocket.OPEN) {
            this.ws.send(message);
        }
    }

    ping() {
        try {
            this.send(
                JSON.stringify({
                    type: "ping",
                })
            );
        } catch {
            // ignore error
        }
    }
}

export default new WebSocketConnection();
