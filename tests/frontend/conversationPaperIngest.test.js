/* SPDX-License-Identifier: 0BSD */

import { describe, it, expect, beforeEach, afterEach } from "vitest";
import {
    isPaperMessageIngested,
    listIngestedPaperMessageHashes,
    markPaperMessageIngested,
    normalizePaperIngestMessageHash,
    shouldMarkPaperIngestFromResultStatus,
} from "@/features/messages/lib/conversationPaperIngest.ts";

describe("conversationPaperIngest", () => {
    beforeEach(() => {
        localStorage.clear();
    });

    afterEach(() => {
        localStorage.clear();
    });

    it("normalizes message hashes", () => {
        expect(normalizePaperIngestMessageHash(" AABB ")).toBe("aabb");
        expect(normalizePaperIngestMessageHash(null)).toBe("");
    });

    it("marks and reads ingested hashes per identity", () => {
        expect(isPaperMessageIngested("id-a", "aa".repeat(16))).toBe(false);
        markPaperMessageIngested("id-a", "AA".repeat(16));
        expect(isPaperMessageIngested("id-a", "aa".repeat(16))).toBe(true);
        expect(isPaperMessageIngested("id-b", "aa".repeat(16))).toBe(false);
        expect(listIngestedPaperMessageHashes("id-a")).toEqual(["aa".repeat(16)]);
    });

    it("does not duplicate hashes", () => {
        const hash = "bb".repeat(16);
        markPaperMessageIngested("id-a", hash);
        markPaperMessageIngested("id-a", hash);
        expect(listIngestedPaperMessageHashes("id-a")).toEqual([hash]);
    });

    it("marks success and info ingest results only", () => {
        expect(shouldMarkPaperIngestFromResultStatus("success")).toBe(true);
        expect(shouldMarkPaperIngestFromResultStatus("info")).toBe(true);
        expect(shouldMarkPaperIngestFromResultStatus("warning")).toBe(false);
        expect(shouldMarkPaperIngestFromResultStatus("error")).toBe(false);
    });
});
