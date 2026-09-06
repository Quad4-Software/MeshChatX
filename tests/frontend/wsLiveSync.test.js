// SPDX-License-Identifier: 0BSD

import { describe, expect, it, vi } from "vitest";
import {
    chooseLiveTransport,
    clearLastSeq,
    loadLastSeq,
    nextLastSeqFromPayload,
    saveLastSeq,
    syncSubscribeRequiresResync,
    installWsLiveSync,
} from "../../meshchatx/src/frontend/js/wsLiveSync.js";
import { encodeWtJsonLine, feedWtJsonLines } from "../../meshchatx/src/frontend/js/wtJsonFraming.js";

describe("wsLiveSync oracles", () => {
    it("tracks max seq", () => {
        expect(nextLastSeqFromPayload({ seq: 3 }, 1)).toBe(3);
        expect(nextLastSeqFromPayload({ seq: 2 }, 5)).toBe(5);
        expect(nextLastSeqFromPayload({}, 4)).toBe(4);
    });

    it("resync when gap or resync flag", () => {
        expect(syncSubscribeRequiresResync({ status: "ok" })).toBe(false);
        expect(syncSubscribeRequiresResync({ status: "gap", resync: true })).toBe(true);
        expect(syncSubscribeRequiresResync({ resync: true })).toBe(true);
    });

    it("chooseLiveTransport table", () => {
        expect(
            chooseLiveTransport({
                mode: "websocket",
                clientSupportsWebTransport: true,
                serverAvailable: true,
                webTransportConnectOk: null,
            })
        ).toBe("websocket");
        expect(
            chooseLiveTransport({
                mode: "auto",
                clientSupportsWebTransport: false,
                serverAvailable: true,
                webTransportConnectOk: null,
            })
        ).toBe("websocket");
        expect(
            chooseLiveTransport({
                mode: "auto",
                clientSupportsWebTransport: true,
                serverAvailable: true,
                webTransportConnectOk: false,
            })
        ).toBe("websocket");
        expect(
            chooseLiveTransport({
                mode: "webtransport",
                clientSupportsWebTransport: true,
                serverAvailable: true,
                webTransportConnectOk: null,
            })
        ).toBe("webtransport");
    });

    it("persists last seq in sessionStorage when available", () => {
        const key = "meshchatx_ws_last_seq:test";
        clearLastSeq(key);
        saveLastSeq(key, 9);
        expect(loadLastSeq(key)).toBe(9);
        clearLastSeq(key);
    });

    it("installWsLiveSync requests sync on ready and resyncs on gap", async () => {
        const handlers = {};
        const connection = {
            on(ev, fn) {
                handlers[ev] = fn;
            },
            off() {},
            sendQueued: vi.fn(),
        };
        const onNeedsResync = vi.fn(async () => {});
        const handle = installWsLiveSync({
            connection,
            onNeedsResync,
            getStorageKey: () => "meshchatx_ws_last_seq:vitest",
        });
        handle.clearCursor();
        handlers.ready();
        expect(connection.sendQueued).toHaveBeenCalled();
        const sent = JSON.parse(connection.sendQueued.mock.calls[0][0]);
        expect(sent.type).toBe("sync.subscribe");
        handlers.message({
            data: JSON.stringify({ type: "sync.subscribe", status: "gap", resync: true, current_seq: 12 }),
        });
        await vi.waitFor(() => expect(onNeedsResync).toHaveBeenCalledTimes(1));
        handle.dispose();
    });
});

describe("wtJsonFraming", () => {
    it("round-trips objects", () => {
        const line = encodeWtJsonLine({ type: "ping", n: 1 });
        const fed = feedWtJsonLines("", line);
        expect(fed.errors).toEqual([]);
        expect(fed.objects).toEqual([{ type: "ping", n: 1 }]);
    });

    it("rejects invalid json lines", () => {
        const fed = feedWtJsonLines("", "{not-json\n");
        expect(fed.errors).toContain("invalid_json");
    });
});
