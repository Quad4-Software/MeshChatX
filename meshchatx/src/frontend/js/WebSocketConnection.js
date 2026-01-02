import mitt from "mitt";

class WebSocketConnection {
    constructor() {
        this.emitter = mitt();
        this.ws = null;
        this.pingInterval = null;
        this.initialized = false;
        this.connect();
    }

    async connect() {
        if (typeof window === "undefined" || !window.axios) {
            setTimeout(() => this.connect(), 100);
            return;
        }

        this.initialized = true;
        this.reconnect();
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
        if (!this.initialized) {
            return;
        }

        // connect to websocket
        const wsUrl = location.origin.replace(/^https/, "wss").replace(/^http/, "ws") + "/ws";
        this.ws = new WebSocket(wsUrl);

        // auto reconnect when websocket closes
        this.ws.addEventListener("close", () => {
            setTimeout(() => {
                this.reconnect();
            }, 1000);
        });

        // emit data received from websocket
        this.ws.onmessage = (message) => {
            this.emit("message", message);
        };
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
