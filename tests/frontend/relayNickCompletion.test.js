// SPDX-License-Identifier: 0BSD

import { describe, expect, it } from "vitest";
import { relayNickCompletionStep, squashRelayNick } from "@/js/relay/relayNickCompletion.js";

const NAMES = ["burger", "Dayle M0OUE Desktop", "jlamothe", "vclv"];

function step(text, names = NAMES, cycle = null, backwards = false, caret = null) {
    return relayNickCompletionStep({
        text,
        caret: caret ?? (typeof text === "string" ? text.length : 0),
        names,
        cycle,
        backwards,
    });
}

describe("squashRelayNick", () => {
    it("strips whitespace for mention-safe nicks", () => {
        expect(squashRelayNick("Dayle M0OUE Desktop")).toBe("DayleM0OUEDesktop");
        expect(squashRelayNick("burger")).toBe("burger");
        expect(squashRelayNick("")).toBe("");
    });
});

describe("relayNickCompletionStep", () => {
    it("completes a prefix at line start as @nick:", () => {
        const r = step("bur");
        expect(r.text).toBe("@burger: ");
        expect(r.caret).toBe(r.text.length);
    });

    it("completes an @-prefix mid-line as @nick", () => {
        const r = step("hi @vcl", NAMES, null, false, 7);
        expect(r.text).toBe("hi @vclv ");
    });

    it("completes a bare mid-line token with an @ mention", () => {
        const r = step("hi jam", NAMES, null, false, 6);
        // no member matches "jam"
        expect(r).toBeNull();
        const r2 = step("hi jla", NAMES, null, false, 6);
        expect(r2.text).toBe("hi @jlamothe ");
    });

    it("matches squashed member names with spaces", () => {
        const r = step("@daylem0ou");
        expect(r.text).toBe("@DayleM0OUEDesktop: ");
    });

    it("is case-insensitive on the prefix", () => {
        const r = step("BUR");
        expect(r.text).toBe("@burger: ");
    });

    it("an empty token at start cycles all members", () => {
        const r = step("");
        expect(r.text).toBe("@burger: ");
    });

    it("an @ alone lists every member", () => {
        const r = step("@");
        expect(r.text).toBe("@burger: ");
    });

    it("repeated steps cycle through matches", () => {
        const r1 = step("");
        expect(r1.text).toBe("@burger: ");
        const r2 = step(r1.text, NAMES, r1.cycle);
        expect(r2.text).toBe("@DayleM0OUEDesktop: ");
        const r3 = step(r2.text, NAMES, r2.cycle);
        expect(r3.text).toBe("@jlamothe: ");
        // wraps around
        let c = r3.cycle;
        let cur = r3.text;
        for (const expected of ["@vclv: ", "@burger: "]) {
            const next = step(cur, NAMES, c);
            expect(next.text).toBe(expected);
            cur = next.text;
            c = next.cycle;
        }
    });

    it("shift-tab cycles backwards", () => {
        const r1 = step("");
        const r2 = step(r1.text, NAMES, r1.cycle, true);
        expect(r2.text).toBe("@vclv: ");
    });

    it("edited text breaks the cycle and recomputes", () => {
        const r1 = step("");
        // user edits: caret moved / text changed
        const r2 = step("@j", NAMES, r1.cycle);
        expect(r2.text).toBe("@jlamothe: ");
    });

    it("mid-line completion keeps the colon only at line start", () => {
        const r = step("hey bur", NAMES, null, false, 7);
        expect(r.text).toBe("hey @burger ");
    });

    it("returns null when nothing matches", () => {
        expect(step("zzz")).toBeNull();
        expect(step("", [])).toBeNull();
        expect(step(null)).toBeNull();
    });

    it("completes mid-token with text after the caret", () => {
        const r = step("@v tail", NAMES, null, false, 2);
        expect(r.text).toBe("@vclv:  tail");
        expect(r.caret).toBe("@vclv: ".length);
    });

    it("consumes the whole word when the caret sits mid-word", () => {
        const r = step("vclv", NAMES, null, false, 3);
        // vc|lv must not become "@vclv lv"
        expect(r.text).toBe("@vclv: ");
        expect(r.caret).toBe(r.text.length);
    });

    it("does not force a match when the full word under the caret fits nobody", () => {
        // caret inside "vclvx" should not complete against the "vcl" prefix
        const r = step("vclvx", NAMES, null, false, 3);
        expect(r).toBeNull();
    });
});
