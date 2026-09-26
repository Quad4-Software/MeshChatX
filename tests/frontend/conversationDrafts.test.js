// SPDX-License-Identifier: 0BSD

import { beforeEach, describe, expect, it } from "vitest";
import { draftStorageKey, loadDraft, saveDraft } from "@/features/messages/lib/conversationDrafts.ts";

describe("conversationDrafts", () => {
    beforeEach(() => {
        localStorage.clear();
    });

    it("saves and loads drafts under the identity-scoped key", () => {
        saveDraft("peer1", "idA", "hello");
        expect(loadDraft("peer1", "idA")).toBe("hello");
        expect(loadDraft("peer1", "idB")).toBe("");
    });

    it("loadDraft folds the _ fallback keys into the real identity bucket", () => {
        // Drafts saved before the identity hash resolved live under "_".
        saveDraft("peer1", "_", "early");
        saveDraft("peer2", "_", "also early");
        expect(loadDraft("peer1", "idA")).toBe("early");
        expect(localStorage.getItem(draftStorageKey("idA", "peer1"))).toBe("early");
        expect(localStorage.getItem(draftStorageKey("idA", "peer2"))).toBe("also early");
        expect(localStorage.getItem(draftStorageKey("_", "peer1"))).toBeNull();
        expect(localStorage.getItem(draftStorageKey("_", "peer2"))).toBeNull();
    });

    it("loadDraft keeps real bucket entries over _ fallback duplicates", () => {
        saveDraft("peer1", "_", "orphan");
        saveDraft("peer1", "idA", "real");
        expect(loadDraft("peer1", "idA")).toBe("real");
        expect(localStorage.getItem(draftStorageKey("idA", "peer1"))).toBe("real");
        expect(localStorage.getItem(draftStorageKey("_", "peer1"))).toBeNull();
    });

    it("loadDraft under _ leaves fallback drafts in place", () => {
        saveDraft("peer1", "_", "early");
        expect(loadDraft("peer1", "_")).toBe("early");
        expect(localStorage.getItem(draftStorageKey("_", "peer1"))).toBe("early");
    });
});
