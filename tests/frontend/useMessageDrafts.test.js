// SPDX-License-Identifier: 0BSD

import { beforeEach, describe, expect, it } from "vitest";
import { useMessageDrafts } from "../../meshchatx/src/frontend/js/messages/useMessageDrafts.js";
import { STORAGE_KEYS } from "../../meshchatx/src/frontend/js/constants.js";

const KEY = STORAGE_KEYS.MESSAGE_DRAFTS;

function stored() {
    return JSON.parse(localStorage.getItem(KEY) || "{}");
}

describe("useMessageDrafts", () => {
    beforeEach(() => {
        localStorage.clear();
    });

    it("saves and loads drafts under the identity bucket", () => {
        let text = "";
        const d = useMessageDrafts({
            getIdentityKey: () => "idA",
            getNewMessageText: () => text,
            setDraftText: (v) => (text = v),
        });
        text = "hello";
        d.saveDraft("peer1");
        expect(stored()).toEqual({ idA: { peer1: "hello" } });
        text = "";
        d.loadDraft("peer1");
        expect(text).toBe("hello");
    });

    it("isolates drafts across identities", () => {
        let text = "";
        let identity = "idA";
        const d = useMessageDrafts({
            getIdentityKey: () => identity,
            getNewMessageText: () => text,
            setDraftText: (v) => (text = v),
        });
        text = "for A";
        d.saveDraft("peer1");
        identity = "idB";
        d.loadDraft("peer1");
        expect(text).toBe("");
    });

    it("reads legacy flat keys when no nested buckets exist", () => {
        let text = "";
        const d = useMessageDrafts({ setDraftText: (v) => (text = v) });
        localStorage.setItem(KEY, JSON.stringify({ peer1: "legacy" }));
        d.loadDraft("peer1");
        expect(text).toBe("legacy");
    });

    it("clears the bucket entry when text is empty", () => {
        const d = useMessageDrafts({
            getIdentityKey: () => "idA",
            getNewMessageText: () => "",
        });
        localStorage.setItem(KEY, JSON.stringify({ idA: { peer1: "old" } }));
        d.saveDraft("peer1");
        expect(stored().idA).toEqual({});
        expect(d.lastDraftIdentityKey.value).toBe("idA");
    });

    it("load failure leaves the text alone", () => {
        let text = "keep";
        const d = useMessageDrafts({ setDraftText: (v) => (text = v) });
        localStorage.setItem(KEY, "{bad json");
        d.loadDraft("peer1");
        expect(text).toBe("keep");
    });
});
