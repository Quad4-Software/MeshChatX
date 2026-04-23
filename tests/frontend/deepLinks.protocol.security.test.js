// SPDX-License-Identifier: 0BSD

import { describe, it, expect, vi, beforeEach } from "vitest";
import App from "../../meshchatx/src/frontend/components/App.vue";
import WebSocketConnection from "../../meshchatx/src/frontend/js/WebSocketConnection";
import ToastUtils from "../../meshchatx/src/frontend/js/ToastUtils";

vi.mock("../../meshchatx/src/frontend/js/ToastUtils", () => ({
    default: {
        success: vi.fn(),
        error: vi.fn(),
        info: vi.fn(),
        warning: vi.fn(),
    },
}));

vi.mock("../../meshchatx/src/frontend/js/WebSocketConnection", () => ({
    default: {
        send: vi.fn(),
        connect: vi.fn(),
        on: vi.fn(),
        off: vi.fn(),
        destroy: vi.fn(),
    },
}));

describe("App.vue deep link protocol handling (security-oriented)", () => {
    beforeEach(() => {
        vi.clearAllMocks();
    });

    it("sends map deep links to lxm.ingest_uri unchanged over WebSocket", () => {
        const uri =
            "meshchatx://map?lat=1&lon=2&z=4&label=" +
            encodeURIComponent("<img src=x onerror=alert(1)>");
        App.methods.handleProtocolLink.call({ $router: { push: vi.fn() } }, uri);
        expect(WebSocketConnection.send).toHaveBeenCalledTimes(1);
        const payload = JSON.parse(WebSocketConnection.send.mock.calls[0][0]);
        expect(payload.type).toBe("lxm.ingest_uri");
        expect(payload.uri).toBe(uri);
    });

    it("does not router-push for meshchat map links (server resolves map_query)", () => {
        const push = vi.fn();
        App.methods.handleProtocolLink.call({ $router: { push } }, "meshchatx://map?lat=0&lon=0&z=1");
        expect(push).not.toHaveBeenCalled();
    });

    it("routes lxmf paper URIs through WebSocket ingest", () => {
        App.methods.handleProtocolLink.call({ $router: { push: vi.fn() } }, "lxmf://%3Cinjection%3E");
        expect(WebSocketConnection.send).toHaveBeenCalled();
        const payload = JSON.parse(WebSocketConnection.send.mock.calls[0][0]);
        expect(payload.type).toBe("lxm.ingest_uri");
    });

    it("routes rns:// only when hash segment is exactly 32 chars", () => {
        const push = vi.fn();
        const h = "a".repeat(32);
        App.methods.handleProtocolLink.call({ $router: { push } }, `rns://${h}`);
        expect(push).toHaveBeenCalledWith({
            name: "messages",
            params: { destinationHash: h },
        });
        push.mockClear();
        App.methods.handleProtocolLink.call({ $router: { push } }, `rns://${"b".repeat(31)}`);
        expect(push).not.toHaveBeenCalled();
    });

    it("onWebsocketMessage map_view passes label and layers as opaque query strings", async () => {
        const push = vi.fn().mockResolvedValue(undefined);
        const marker = "<svg/onload=alert(1)>";
        await App.methods.onWebsocketMessage.call(
            { $router: { push } },
            {
                data: JSON.stringify({
                    type: "lxm.ingest_uri.result",
                    status: "success",
                    ingest_type: "map_view",
                    message: "Opening map view.",
                    map_query: {
                        lat: 3,
                        lon: 4,
                        zoom: 5,
                        layers: "discovered",
                        label: marker,
                    },
                }),
            },
        );
        expect(push).toHaveBeenCalledWith({
            name: "map",
            query: {
                lat: "3",
                lon: "4",
                zoom: "5",
                layers: "discovered",
                label: marker,
            },
        });
        expect(ToastUtils.info).toHaveBeenCalled();
    });
});
