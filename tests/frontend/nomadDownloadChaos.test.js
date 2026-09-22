// SPDX-License-Identifier: 0BSD
//
// Chaos tests for the nomad download event pipeline and the typed ws event
// registry: stale ids, duplicate and malformed events, resend races, and
// teardown ordering. These exercise the lib layer directly with a fake
// access object, no DOM mount needed.

import { describe, it, expect, vi, beforeEach } from "vitest";
import {
    onNomadPageDownloadEvent,
    onNomadFileDownloadEvent,
    onNomadDownloadCancelledEvent,
    resendInFlightNomadDownloads,
    cancelNomadActiveDownload,
} from "../../meshchatx/src/frontend/features/nomadnetwork/lib/nomadPageDownloadEvents.ts";
import WebSocketConnection from "../../meshchatx/src/frontend/js/WebSocketConnection.ts";
import { dispatchWsEvent, onWsEvent, offWsEvent } from "../../meshchatx/src/frontend/js/registries/wsEventRegistry.ts";

vi.mock("../../meshchatx/src/frontend/js/WebSocketConnection.ts", () => ({
    default: {
        send: vi.fn(() => true),
        isOpen: vi.fn(() => true),
        on: vi.fn(),
        off: vi.fn(),
    },
}));

vi.mock("../../meshchatx/src/frontend/js/ToastUtils.ts", () => ({
    default: { success: vi.fn(), error: vi.fn(), warning: vi.fn(), info: vi.fn(), dismiss: vi.fn() },
}));
vi.mock("../../meshchatx/src/frontend/js/ToastUtils.js", () => ({
    default: { success: vi.fn(), error: vi.fn(), warning: vi.fn(), info: vi.fn(), dismiss: vi.fn() },
}));
vi.mock("../../meshchatx/src/frontend/js/DialogUtils.ts", () => ({
    default: { confirm: vi.fn(async () => true), prompt: vi.fn(async () => null), alert: vi.fn() },
}));
vi.mock("../../meshchatx/src/frontend/js/DialogUtils.js", () => ({
    default: { confirm: vi.fn(async () => true), prompt: vi.fn(async () => null), alert: vi.fn() },
}));
vi.mock("../../meshchatx/src/frontend/js/DownloadUtils.ts", () => ({
    default: { downloadFromBase64: vi.fn() },
}));
vi.mock("../../meshchatx/src/frontend/js/DownloadUtils.js", () => ({
    default: { downloadFromBase64: vi.fn() },
}));

const DEST = "aabbccddeeff00112233445566778899";

function makeSnapshot(overrides = {}) {
    return {
        active: true,
        isPrivate: false,
        isLoadingNodePage: true,
        isDownloadingNodeFile: false,
        isCrashTabRendering: false,
        currentPageDownloadId: 5,
        pendingPageCancelWithoutId: false,
        currentFileDownloadId: null,
        nodeFilePath: null,
        nodePageContent: null,
        selectedNode: { destination_hash: DEST, display_name: "node" },
        relativePagePath: "/page/index.mu",
        nodePagePath: `${DEST}:/page/index.mu`,
        nodePageCache: {},
        nomadPageDownloadChunkBuffers: {},
        nomadFileDownloadChunkBuffers: {},
        ...overrides,
    };
}

function makeAccess(snapshot) {
    return {
        get: () => snapshot,
        apply: (patch) => Object.assign(snapshot, patch),
        clearPageLoadTimeout: vi.fn(),
        ontabtitlechange: vi.fn(),
    };
}

function pageEvent(body, downloadId = 5) {
    return { type: "nomadnet.page.download", nomadnet_page_download: body, download_id: downloadId };
}

beforeEach(() => {
    vi.clearAllMocks();
    WebSocketConnection.send.mockReturnValue(true);
});

describe("nomad download chaos", () => {
    it("ignores a stale cancel for the old download id after resend", () => {
        const s = makeSnapshot();
        const access = makeAccess(s);
        resendInFlightNomadDownloads(access, { pagePayload: { type: "nomadnet.page.download" } });
        // Old id was cancelled; simulate the backend's stale cancelled event
        // arriving after the resend, then the new download starting.
        onNomadDownloadCancelledEvent(access, { download_id: 5 });
        expect(s.isLoadingNodePage).toBe(true);
        onNomadPageDownloadEvent(
            access,
            pageEvent({ status: "started", destination_hash: DEST, page_path: "/page/index.mu" }, 9)
        );
        expect(s.currentPageDownloadId).toBe(9);
        onNomadDownloadCancelledEvent(access, { download_id: 5 });
        expect(s.currentPageDownloadId).toBe(9);
        expect(s.isLoadingNodePage).toBe(true);
    });

    it("settles failure when the resend socket write fails", () => {
        WebSocketConnection.send.mockReturnValue(false);
        const s = makeSnapshot();
        const access = makeAccess(s);
        const onPageResendFailed = vi.fn();
        resendInFlightNomadDownloads(access, {
            pagePayload: { type: "nomadnet.page.download" },
            onPageResendFailed,
        });
        expect(onPageResendFailed).toHaveBeenCalled();
        expect(s.isLoadingNodePage).toBe(false);
        expect(s.currentPageDownloadId).toBeNull();
    });

    it("ignores events for a different destination", () => {
        const s = makeSnapshot({ currentPageDownloadId: null });
        const access = makeAccess(s);
        onNomadPageDownloadEvent(
            access,
            pageEvent({ status: "success", page_content: "evil", destination_hash: "deadbeef" }, 42)
        );
        expect(s.nodePageContent).toBeNull();
    });

    it("tolerates malformed events without throwing", () => {
        const s = makeSnapshot();
        const access = makeAccess(s);
        const junk = [
            {},
            { nomadnet_page_download: null },
            { nomadnet_page_download: "string" },
            { nomadnet_page_download: { status: 42 } },
            { nomadnet_page_download: { status: "chunk" }, download_id: null },
            { nomadnet_page_download: { status: "chunk", chunk_b64: "%%%notbase64%%%" }, download_id: 5 },
            { nomadnet_page_download: { status: "progress", progress: "fast" }, download_id: 5 },
            { nomadnet_page_download: { status: "success" }, download_id: "non-numeric" },
            null,
            undefined,
        ];
        for (const event of junk) {
            expect(() => onNomadPageDownloadEvent(access, event || {})).not.toThrow();
        }
        for (const event of junk) {
            expect(() => onNomadFileDownloadEvent(access, event || {})).not.toThrow();
        }
        for (const event of junk) {
            expect(() => onNomadDownloadCancelledEvent(access, event || {})).not.toThrow();
        }
    });

    it("assembles chunked success after a chunk storm", () => {
        const s = makeSnapshot();
        const access = makeAccess(s);
        for (let i = 0; i < 50; i++) {
            onNomadPageDownloadEvent(
                access,
                pageEvent({ status: "chunk", chunk_b64: btoa(`chunk${i}`), total: 100, offset: i * 2 })
            );
        }
        onNomadPageDownloadEvent(
            access,
            pageEvent({ status: "success", chunked: true, destination_hash: DEST, page_path: "/page/index.mu" })
        );
        expect(s.isLoadingNodePage).toBe(false);
        expect(s.currentPageDownloadId).toBeNull();
        expect(s.nodePageContent).toContain("chunk0");
        expect(s.nodePageContent).toContain("chunk49");
        expect(s.nomadPageDownloadChunkBuffers[5]).toBeUndefined();
    });

    it("cancel clears both transfers and ignores a second cancel", () => {
        const s = makeSnapshot({ currentFileDownloadId: 7, isDownloadingNodeFile: true });
        const access = makeAccess(s);
        cancelNomadActiveDownload(access);
        expect(s.currentPageDownloadId).toBeNull();
        expect(s.currentFileDownloadId).toBeNull();
        expect(s.isLoadingNodePage).toBe(false);
        expect(s.isDownloadingNodeFile).toBe(false);
        // A second cancel with nothing in flight must be a no-op.
        cancelNomadActiveDownload(access);
        expect(s.currentPageDownloadId).toBeNull();
    });

    it("cancel-before-id then started cancels the fresh download", () => {
        const s = makeSnapshot({ currentPageDownloadId: null });
        const access = makeAccess(s);
        cancelNomadActiveDownload(access);
        expect(s.pendingPageCancelWithoutId).toBe(true);
        onNomadPageDownloadEvent(
            access,
            pageEvent({ status: "started", destination_hash: DEST, page_path: "/page/index.mu" }, 11)
        );
        expect(s.pendingPageCancelWithoutId).toBe(false);
        const sentCancel = WebSocketConnection.send.mock.calls
            .map((c) => c[0])
            .find((m) => typeof m === "string" && m.includes("nomadnet.download.cancel"));
        expect(sentCancel).toBeTruthy();
        expect(JSON.parse(sentCancel)).toEqual({ type: "nomadnet.download.cancel", download_id: 11 });
    });
});

describe("wsEventRegistry chaos", () => {
    it("handler registered mid-dispatch does not run for the in-flight event", async () => {
        const late = vi.fn();
        const first = vi.fn(() => {
            onWsEvent("chaos.late", late);
        });
        onWsEvent("chaos.late", first);
        await dispatchWsEvent("chaos.late", { type: "chaos.late" });
        expect(first).toHaveBeenCalled();
        expect(late).not.toHaveBeenCalled();
        offWsEvent("chaos.late", first);
        offWsEvent("chaos.late", late);
    });

    it("an async-rejecting handler does not starve later handlers", async () => {
        const bad = vi.fn(async () => {
            throw new Error("async boom");
        });
        const good = vi.fn();
        onWsEvent("chaos.reject", bad);
        onWsEvent("chaos.reject", good);
        await dispatchWsEvent("chaos.reject", { type: "chaos.reject" });
        expect(good).toHaveBeenCalled();
        offWsEvent("chaos.reject", bad);
        offWsEvent("chaos.reject", good);
    });

    it("a slow handler no longer blocks later handlers for the same event", async () => {
        const order = [];
        const slow = async () => {
            await new Promise((r) => setTimeout(r, 50));
            order.push("slow");
        };
        const fast = async () => {
            order.push("fast");
        };
        onWsEvent("chaos.slow", slow);
        onWsEvent("chaos.slow", fast);
        await dispatchWsEvent("chaos.slow", { type: "chaos.slow" });
        expect(order).toEqual(["fast", "slow"]);
        offWsEvent("chaos.slow", slow);
        offWsEvent("chaos.slow", fast);
    });

    it("event storm delivers every event to every handler", async () => {
        const seen = [];
        const handler = vi.fn((p) => seen.push(p.n));
        onWsEvent("chaos.storm", handler);
        const dispatches = [];
        for (let i = 0; i < 200; i++) {
            dispatches.push(dispatchWsEvent("chaos.storm", { type: "chaos.storm", n: i }));
        }
        await Promise.all(dispatches);
        expect(seen.length).toBe(200);
        expect(new Set(seen).size).toBe(200);
        offWsEvent("chaos.storm", handler);
    });
});
