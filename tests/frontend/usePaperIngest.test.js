// SPDX-License-Identifier: 0BSD

import { beforeEach, describe, expect, it, vi } from "vitest";
import { usePaperIngest } from "../../meshchatx/src/frontend/js/messages/usePaperIngest.js";

vi.mock("../../meshchatx/src/frontend/js/WebSocketConnection.js", () => ({
    default: { send: vi.fn() },
}));

import WebSocketConnection from "../../meshchatx/src/frontend/js/WebSocketConnection.js";

describe("usePaperIngest", () => {
    beforeEach(() => {
        vi.clearAllMocks();
        localStorage.clear();
    });

    it("ingest sends lxm.ingest_uri and tracks the pending hash", async () => {
        const p = usePaperIngest({ getIdentityKey: () => "idA" });
        await p.ingestPaperMessage("lxm://hash:payload", "aa".repeat(16));
        expect(WebSocketConnection.send).toHaveBeenCalled();
        const sent = JSON.parse(WebSocketConnection.send.mock.calls[0][0]);
        expect(sent.type).toBe("lxm.ingest_uri");
        expect(p.pendingPaperIngestMessageHash.value).toBe("aa".repeat(16));
    });

    it("successful ingest result marks the hash ingested", () => {
        const p = usePaperIngest({ getIdentityKey: () => "idA" });
        const hash = "bb".repeat(16);
        p.pendingPaperIngestMessageHash.value = hash;
        p.onLxmIngestUriResultEvent({ status: "success" });
        expect(p.pendingPaperIngestMessageHash.value).toBeNull();
        expect(p.isPaperMessageIngested({ lxmf_message: { hash } })).toBe(true);
    });

    it("warning/error ingest results do not mark the hash", () => {
        const p = usePaperIngest({ getIdentityKey: () => "idA" });
        const hash = "cc".repeat(16);
        p.pendingPaperIngestMessageHash.value = hash;
        p.onLxmIngestUriResultEvent({ status: "error" });
        expect(p.isPaperMessageIngested({ lxmf_message: { hash } })).toBe(false);
    });

    it("isPaperMessageIngested returns false for items without a hash", () => {
        const p = usePaperIngest();
        expect(p.isPaperMessageIngested({})).toBe(false);
        expect(p.isPaperMessageIngested(null)).toBe(false);
    });

    it("reload populates the ingested map from storage", () => {
        const p = usePaperIngest({ getIdentityKey: () => "idA" });
        const hash = "dd".repeat(16);
        p.pendingPaperIngestMessageHash.value = hash;
        p.onLxmIngestUriResultEvent({ status: "success" });
        // fresh composable sees the persisted hash after reload
        const p2 = usePaperIngest({ getIdentityKey: () => "idA" });
        p2.reloadIngestedPaperMessageHashes();
        expect(p2.isPaperMessageIngested({ lxmf_message: { hash } })).toBe(true);
    });
});
