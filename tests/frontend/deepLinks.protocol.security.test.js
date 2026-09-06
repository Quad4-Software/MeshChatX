// SPDX-License-Identifier: 0BSD

import { describe, it, expect, vi, beforeEach } from "vitest";
import { handleProtocolLink } from "../../meshchatx/src/frontend/features/app-shell/lib/appShellLinks.js";
import { handleLxmIngestUriResult } from "../../meshchatx/src/frontend/js/ingestUriResultNavigation.js";
import LiveTransport from "../../meshchatx/src/frontend/js/liveTransport.js";
import ToastUtils from "../../meshchatx/src/frontend/js/ToastUtils";

vi.mock("../../meshchatx/src/frontend/js/ToastUtils", () => ({
    default: {
        success: vi.fn(),
        error: vi.fn(),
        info: vi.fn(),
        warning: vi.fn(),
    },
}));

vi.mock("../../meshchatx/src/frontend/js/liveTransport.js", () => ({
    default: {
        send: vi.fn(),
        connect: vi.fn(),
        on: vi.fn(),
        off: vi.fn(),
        destroy: vi.fn(),
    },
}));

describe("app-shell deep link protocol handling (security-oriented)", () => {
    beforeEach(() => {
        vi.clearAllMocks();
    });

    it("routes meshchatx://docs with reticulum query to documentation page", () => {
        const push = vi.fn();
        handleProtocolLink({ push }, "meshchatx://docs?reticulum=" + encodeURIComponent("manual/interfaces.html#foo"));
        expect(push).toHaveBeenCalledWith({
            name: "documentation",
            query: {
                reticulum: encodeURIComponent("manual/interfaces.html#foo"),
            },
        });
        push.mockClear();
        handleProtocolLink({ push }, "meshchat://docs?path=manual/index.html");
        expect(push).toHaveBeenCalledWith({
            name: "documentation",
            query: { reticulum: encodeURIComponent("manual/index.html") },
        });
    });

    it("routes meshchatx://docs without query to documentation index", () => {
        const push = vi.fn();
        handleProtocolLink({ push }, "meshchatx://docs");
        expect(push).toHaveBeenCalledWith({ name: "documentation" });
    });

    it("sends map deep links to lxm.ingest_uri unchanged over WebSocket", () => {
        const uri = "meshchatx://map?lat=1&lon=2&z=4&label=" + encodeURIComponent("<img src=x onerror=alert(1)>");
        handleProtocolLink({ push: vi.fn() }, uri);
        expect(LiveTransport.send).toHaveBeenCalledTimes(1);
        const payload = JSON.parse(LiveTransport.send.mock.calls[0][0]);
        expect(payload.type).toBe("lxm.ingest_uri");
        expect(payload.uri).toBe(uri);
    });

    it("does not router-push for meshchat map links (server resolves map_query)", () => {
        const push = vi.fn();
        handleProtocolLink({ push }, "meshchatx://map?lat=0&lon=0&z=1");
        expect(push).not.toHaveBeenCalled();
    });

    it("routes lxmf paper URIs through WebSocket ingest", () => {
        handleProtocolLink({ push: vi.fn() }, "lxmf://%3Cinjection%3E");
        expect(LiveTransport.send).toHaveBeenCalled();
        const payload = JSON.parse(LiveTransport.send.mock.calls[0][0]);
        expect(payload.type).toBe("lxm.ingest_uri");
    });

    it("routes rns:// only when hash segment is exactly 32 chars", () => {
        const push = vi.fn();
        const h = "a".repeat(32);
        handleProtocolLink({ push }, `rns://${h}`);
        expect(push).toHaveBeenCalledWith({
            name: "messages",
            params: { destinationHash: h },
        });
        push.mockClear();
        handleProtocolLink({ push }, `rns://${"b".repeat(31)}`);
        expect(push).not.toHaveBeenCalled();
    });

    it("routes meshchatx://app/messages/<hash> to that conversation", () => {
        const push = vi.fn();
        const h = "abcdef0123456789abcdef0123456789";
        handleProtocolLink({ push }, `meshchatx://app/messages/${h}`);
        expect(push).toHaveBeenCalledWith({
            name: "messages",
            params: { destinationHash: h },
        });
        push.mockClear();
        handleProtocolLink({ push }, "meshchatx://app/messages");
        expect(push).toHaveBeenCalledWith({ name: "messages" });
        push.mockClear();
        handleProtocolLink({ push }, "meshchatx://app/messages/not-hex!!");
        expect(push).toHaveBeenCalledWith({ name: "messages" });
    });

    it("onWebsocketMessage map_view passes label and layers as opaque query strings", async () => {
        const push = vi.fn().mockResolvedValue(undefined);
        const marker = "<svg/onload=alert(1)>";
        const handled = await handleLxmIngestUriResult(
            {
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
            },
            { router: { push }, toast: ToastUtils }
        );
        expect(handled).toBe(true);
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
