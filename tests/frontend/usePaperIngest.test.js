// SPDX-License-Identifier: 0BSD

import { beforeEach, describe, expect, it, vi } from "vitest";
import { usePaperIngest } from "../../meshchatx/src/frontend/js/messages/usePaperIngest.js";

vi.mock("../../meshchatx/src/frontend/js/WebSocketConnection", () => ({
    default: { send: vi.fn() },
}));

import WebSocketConnection from "../../meshchatx/src/frontend/js/WebSocketConnection";

function lastSentRequestId() {
    const sent = JSON.parse(WebSocketConnection.send.mock.calls.at(-1)[0]);
    return sent.request_id;
}

describe("usePaperIngest", () => {
    beforeEach(() => {
        vi.clearAllMocks();
        localStorage.clear();
    });

    it("ingest sends lxm.ingest_uri and tracks the pending hash", async () => {
        WebSocketConnection.send.mockReturnValue(true);
        const p = usePaperIngest({ getIdentityKey: () => "idA" });
        await p.ingestPaperMessage("lxm://hash:payload", "aa".repeat(16));
        expect(WebSocketConnection.send).toHaveBeenCalled();
        const sent = JSON.parse(WebSocketConnection.send.mock.calls[0][0]);
        expect(sent.type).toBe("lxm.ingest_uri");
        expect(typeof sent.request_id).toBe("string");
        expect(p.pendingPaperIngestMessageHash.value).toBe("aa".repeat(16));
    });

    it("ingest does not track the hash when the socket is not open", async () => {
        WebSocketConnection.send.mockReturnValue(false);
        const p = usePaperIngest({ getIdentityKey: () => "idA" });
        await p.ingestPaperMessage("lxm://hash:payload", "aa".repeat(16));
        // A dropped send must not mark the message pending, or an unrelated
        // ingest result could flash a false ingested badge.
        expect(p.pendingPaperIngestMessageHash.value).toBeNull();
    });

    it("successful ingest result marks the hash ingested", async () => {
        WebSocketConnection.send.mockReturnValue(true);
        const p = usePaperIngest({ getIdentityKey: () => "idA" });
        const hash = "bb".repeat(16);
        await p.ingestPaperMessage("lxm://hash:payload", hash);
        p.onLxmIngestUriResultEvent({ status: "success", request_id: lastSentRequestId() });
        expect(p.pendingPaperIngestMessageHash.value).toBeNull();
        expect(p.isPaperMessageIngested({ lxmf_message: { hash } })).toBe(true);
    });

    it("warning/error ingest results do not mark the hash", async () => {
        WebSocketConnection.send.mockReturnValue(true);
        const p = usePaperIngest({ getIdentityKey: () => "idA" });
        const hash = "cc".repeat(16);
        await p.ingestPaperMessage("lxm://hash:payload", hash);
        p.onLxmIngestUriResultEvent({ status: "error", request_id: lastSentRequestId() });
        expect(p.isPaperMessageIngested({ lxmf_message: { hash } })).toBe(false);
        expect(p.pendingPaperIngestMessageHash.value).toBeNull();
    });

    it("ignores results that do not match a pending request", async () => {
        WebSocketConnection.send.mockReturnValue(true);
        const p = usePaperIngest({ getIdentityKey: () => "idA" });
        const hash = "ee".repeat(16);
        await p.ingestPaperMessage("lxm://hash:payload", hash);
        // Results with no request id, or a different one, belong to other
        // ingests and must neither mark the hash nor consume the pending slot.
        p.onLxmIngestUriResultEvent({ status: "success" });
        p.onLxmIngestUriResultEvent({ status: "success", request_id: "unrelated" });
        expect(p.isPaperMessageIngested({ lxmf_message: { hash } })).toBe(false);
        expect(p.pendingPaperIngestMessageHash.value).toBe(hash);
        p.onLxmIngestUriResultEvent({ status: "success", request_id: lastSentRequestId() });
        expect(p.isPaperMessageIngested({ lxmf_message: { hash } })).toBe(true);
    });

    it("isPaperMessageIngested returns false for items without a hash", () => {
        const p = usePaperIngest();
        expect(p.isPaperMessageIngested({})).toBe(false);
        expect(p.isPaperMessageIngested(null)).toBe(false);
    });

    it("reload populates the ingested map from storage", async () => {
        WebSocketConnection.send.mockReturnValue(true);
        const p = usePaperIngest({ getIdentityKey: () => "idA" });
        const hash = "dd".repeat(16);
        await p.ingestPaperMessage("lxm://hash:payload", hash);
        p.onLxmIngestUriResultEvent({ status: "success", request_id: lastSentRequestId() });
        // fresh composable sees the persisted hash after reload
        const p2 = usePaperIngest({ getIdentityKey: () => "idA" });
        p2.reloadIngestedPaperMessageHashes();
        expect(p2.isPaperMessageIngested({ lxmf_message: { hash } })).toBe(true);
    });
});
