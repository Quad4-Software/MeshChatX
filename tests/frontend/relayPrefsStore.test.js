// SPDX-License-Identifier: 0BSD

import { beforeEach, describe, expect, it } from "vitest";
import {
    isIgnoredRelayMessage,
    loadRelayPrefs,
    relayPrefsEqualIgnored,
    saveRelayPrefs,
} from "@/js/relay/relayPrefsStore.js";
import { STORAGE_KEYS } from "@/js/constants.js";

const OWN = "aa".repeat(16);
const PEER = "bb".repeat(16);

describe("relayPrefsStore", () => {
    beforeEach(() => {
        localStorage.clear();
    });

    it("round-trips ignored peers and highlight words per identity", () => {
        saveRelayPrefs("id1", {
            ignored: [{ hash: PEER, name: "burger" }],
            highlightWords: ["uucp", "m0oue"],
        });
        const prefs = loadRelayPrefs("id1");
        expect(prefs.ignored).toEqual([{ hash: PEER, name: "burger" }]);
        expect(prefs.highlightWords).toEqual(["uucp", "m0oue"]);
    });

    it("scopes prefs by identity bucket", () => {
        saveRelayPrefs("id1", { ignored: [{ hash: PEER, name: "a" }], highlightWords: ["x"] });
        saveRelayPrefs("id2", { ignored: [], highlightWords: ["y"] });
        expect(loadRelayPrefs("id1").ignored).toHaveLength(1);
        expect(loadRelayPrefs("id1").highlightWords).toEqual(["x"]);
        expect(loadRelayPrefs("id2").highlightWords).toEqual(["y"]);
        expect(loadRelayPrefs("missing")).toEqual({ ignored: [], highlightWords: [] });
    });

    it("drops malformed entries on read and write", () => {
        localStorage.setItem(
            STORAGE_KEYS.RRC_PREFS,
            JSON.stringify({
                id1: { ignored: [null, { hash: PEER }, "junk", { name: "ok" }], highlightWords: [1, "keep", null] },
            })
        );
        const prefs = loadRelayPrefs("id1");
        expect(prefs.ignored).toEqual([
            { hash: PEER, name: "" },
            { hash: "", name: "ok" },
        ]);
        expect(prefs.highlightWords).toEqual(["keep"]);

        const saved = saveRelayPrefs("id1", {
            ignored: [{ hash: "  " + PEER.toUpperCase(), name: " B " }],
            highlightWords: [" w "],
        });
        expect(saved.ignored[0].hash).toBe(PEER);
        expect(saved.highlightWords).toEqual(["w"]);
    });

    it("survives corrupt storage", () => {
        localStorage.setItem(STORAGE_KEYS.RRC_PREFS, "not json{");
        expect(loadRelayPrefs("id1")).toEqual({ ignored: [], highlightWords: [] });
        localStorage.setItem(STORAGE_KEYS.RRC_PREFS, JSON.stringify(["array"]));
        expect(loadRelayPrefs("id1")).toEqual({ ignored: [], highlightWords: [] });
    });

    describe("isIgnoredRelayMessage", () => {
        const ignored = [
            { hash: PEER, name: "burger" },
            { hash: "", name: "nickonly" },
        ];

        it("matches by identity hash", () => {
            expect(isIgnoredRelayMessage({ kind: "msg", src: PEER, nick: "renamed", text: "hi" }, ignored, OWN)).toBe(
                true
            );
        });

        it("matches by nick when src is absent", () => {
            expect(isIgnoredRelayMessage({ kind: "msg", src: "", nick: "nickonly", text: "hi" }, ignored, OWN)).toBe(
                true
            );
        });

        it("matches by nick even when src is present", () => {
            expect(
                isIgnoredRelayMessage({ kind: "msg", src: "cc".repeat(16), nick: "Burger", text: "hi" }, ignored, OWN)
            ).toBe(true);
        });

        it("keeps system, notice, and presence kinds visible", () => {
            for (const kind of ["system", "notice", "error", "presence"]) {
                expect(isIgnoredRelayMessage({ kind, src: PEER, nick: "burger", text: "x" }, ignored, OWN)).toBe(false);
            }
        });

        it("hides ignored action messages too", () => {
            expect(isIgnoredRelayMessage({ kind: "action", src: PEER, nick: "burger", text: "x" }, ignored, OWN)).toBe(
                true
            );
        });

        it("never hides the user's own messages", () => {
            const ownIgnored = [{ hash: OWN, name: "me" }];
            expect(isIgnoredRelayMessage({ kind: "msg", src: OWN, nick: "me", text: "hi" }, ownIgnored, OWN)).toBe(
                false
            );
        });

        it("leaves unrelated peers visible", () => {
            expect(
                isIgnoredRelayMessage({ kind: "msg", src: "cc".repeat(16), nick: "other", text: "hi" }, ignored, OWN)
            ).toBe(false);
            expect(isIgnoredRelayMessage(null, ignored, OWN)).toBe(false);
        });
    });

    describe("relayPrefsEqualIgnored", () => {
        it("matches entries to messages by hash or nick", () => {
            const entry = { hash: PEER, name: "burger" };
            expect(relayPrefsEqualIgnored(entry, { src: PEER, nick: "other" })).toBe(true);
            expect(relayPrefsEqualIgnored(entry, { src: "cc".repeat(16), nick: "Burger" })).toBe(true);
            expect(relayPrefsEqualIgnored(entry, { src: "cc".repeat(16), nick: "someone" })).toBe(false);
        });
    });
});
