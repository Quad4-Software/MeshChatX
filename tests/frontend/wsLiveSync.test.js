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

describe("wsLiveSync references", () => {
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

    it("drops a stale cursor when the server epoch regressed", async () => {
        const handlers = {};
        const connection = {
            on(ev, fn) {
                handlers[ev] = fn;
            },
            off() {},
            sendQueued: vi.fn(),
        };
        const onNeedsResync = vi.fn(async () => {});
        const key = "meshchatx_ws_last_seq:vitest-epoch";
        saveLastSeq(key, 5000);
        const handle = installWsLiveSync({
            connection,
            onNeedsResync,
            getStorageKey: () => key,
        });
        expect(handle.getLastSeq()).toBe(5000);
        handlers.message({
            data: JSON.stringify({
                type: "sync.subscribe",
                status: "gap",
                resync: true,
                current_seq: 3,
            }),
        });
        await vi.waitFor(() => expect(onNeedsResync).toHaveBeenCalledTimes(1));
        expect(handle.getLastSeq()).toBe(3);
        handle.dispose();
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

    it("ignores replies whose request_id does not match the pending subscribe", async () => {
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
            getStorageKey: () => "meshchatx_ws_last_seq:vitest-stale",
        });
        handle.clearCursor();
        handlers.ready();
        const sent = JSON.parse(connection.sendQueued.mock.calls[0][0]);
        expect(sent.request_id).toBeTruthy();

        // A reply for a different (older epoch) request_id must be dropped.
        handlers.message({
            data: JSON.stringify({
                type: "sync.subscribe",
                request_id: "sync-old-epoch",
                status: "gap",
                resync: true,
                current_seq: 99,
            }),
        });
        await new Promise((r) => setTimeout(r, 20));
        expect(onNeedsResync).not.toHaveBeenCalled();

        // The matching reply releases the in-flight flag and resyncs.
        handlers.message({
            data: JSON.stringify({
                type: "sync.subscribe",
                request_id: sent.request_id,
                status: "gap",
                resync: true,
                current_seq: 99,
            }),
        });
        await vi.waitFor(() => expect(onNeedsResync).toHaveBeenCalledTimes(1));
        handle.dispose();
    });

    it("dedupes overlapping subscribes until the reply or watchdog", async () => {
        vi.useFakeTimers();
        try {
            const handlers = {};
            const connection = {
                on(ev, fn) {
                    handlers[ev] = fn;
                },
                off() {},
                sendQueued: vi.fn(),
            };
            const handle = installWsLiveSync({
                connection,
                onNeedsResync: vi.fn(async () => {}),
                getStorageKey: () => "meshchatx_ws_last_seq:vitest-dedupe",
            });
            handle.clearCursor();
            handlers.ready();
            handlers.ready();
            expect(connection.sendQueued).toHaveBeenCalledTimes(1);

            // Watchdog frees the flag when the reply never arrives.
            await vi.advanceTimersByTimeAsync(16000);
            handlers.ready();
            expect(connection.sendQueued).toHaveBeenCalledTimes(2);
            handle.dispose();
        } finally {
            vi.useRealTimers();
        }
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
