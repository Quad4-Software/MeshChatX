import mitt from "mitt";

class WebSocketConnection {
    constructor() {
        this.emitter = mitt();
        this.isDemoMode = false;
        this.ws = null;
        this.pingInterval = null;
        this.initialized = false;
        this.checkDemoModeAndConnect();
    }

    async checkDemoModeAndConnect() {
        if (typeof window === "undefined" || !window.axios) {
            setTimeout(() => this.checkDemoModeAndConnect(), 100);
            return;
        }

        try {
            const response = await window.axios.get("/api/v1/app/info");
            this.isDemoMode = response.data.app_info?.is_demo === true;
        } catch (e) {
            // If we can't check, assume not demo mode and try to connect
        }

        this.initialized = true;

        if (!this.isDemoMode) {
            this.reconnect();
            this.pingInterval = setInterval(() => {
                this.ping();
            }, 30000);
        }
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
        if (!this.initialized || this.isDemoMode) {
            return;
        }

        // connect to websocket
        const wsUrl = location.origin.replace(/^https/, "wss").replace(/^http/, "ws") + "/ws";
        this.ws = new WebSocket(wsUrl);

        // auto reconnect when websocket closes
        this.ws.addEventListener("close", () => {
            if (!this.isDemoMode) {
                setTimeout(() => {
                    this.reconnect();
                }, 1000);
            }
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
        if (this.isDemoMode) {
            return;
        }
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
