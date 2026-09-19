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

    it("loadDraft records the loading identity so later saves stay in its bucket", () => {
        let identity = "idA";
        let text = "";
        const d = useMessageDrafts({
            getIdentityKey: () => identity,
            getNewMessageText: () => text,
            setDraftText: (v) => (text = v),
        });
        d.loadDraft("peer1");
        expect(d.lastDraftIdentityKey.value).toBe("idA");
        // Identity switches after the load: a save keyed off
        // lastDraftIdentityKey must write the old identity's bucket, not
        // silently leak the draft into the new identity's bucket.
        text = "typed under idA";
        identity = "idB";
        d.saveDraft("peer1", d.lastDraftIdentityKey.value);
        expect(stored().idA.peer1).toBe("typed under idA");
        expect(stored().idB).toBeUndefined();
    });

    it("a bare saveDraft after identity switch stays in the captured bucket", () => {
        let identity = "idA";
        let text = "";
        const d = useMessageDrafts({
            getIdentityKey: () => identity,
            getNewMessageText: () => text,
            setDraftText: (v) => (text = v),
        });
        d.loadDraft("peer1");
        text = "typed under idA";
        identity = "idB";
        // No explicit key: the scope's captured identity must win over the
        // live one so a deferred save cannot leak into idB.
        d.saveDraft("peer1");
        expect(stored().idA.peer1).toBe("typed under idA");
        expect(stored().idB).toBeUndefined();
    });
});
