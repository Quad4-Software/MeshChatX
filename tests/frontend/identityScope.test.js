// SPDX-License-Identifier: 0BSD

import { describe, expect, it } from "vitest";
import { useIdentityScope } from "../../meshchatx/src/frontend/js/identityScope.js";

describe("useIdentityScope", () => {
    it("captures the live identity at load time", () => {
        const scope = useIdentityScope({ getIdentityKey: () => "idA" });
        expect(scope.beginIdentity()).toBe("idA");
        expect(scope.identityKey.value).toBe("idA");
    });

    it("an explicit hash wins over live config at load time", () => {
        // The identity_switched payload is authoritative; the config store
        // can lag the event.
        const scope = useIdentityScope({ getIdentityKey: () => "stale" });
        expect(scope.beginIdentity("idB")).toBe("idB");
        expect(scope.identityKey.value).toBe("idB");
    });

    it("writes prefer the captured identity over a switched live one", () => {
        let live = "idA";
        const scope = useIdentityScope({ getIdentityKey: () => live });
        scope.beginIdentity();
        live = "idB";
        expect(scope.keyForWrite()).toBe("idA");
    });

    it("an explicit write key beats the captured one", () => {
        const scope = useIdentityScope({ getIdentityKey: () => "idA" });
        scope.beginIdentity();
        expect(scope.keyForWrite("idC")).toBe("idC");
    });

    it("falls back to live identity only when nothing was captured", () => {
        const scope = useIdentityScope({ getIdentityKey: () => "idA" });
        expect(scope.keyForWrite()).toBe("idA");
    });

    it("normalizes empty keys to the anonymous bucket", () => {
        const scope = useIdentityScope({ getIdentityKey: () => "" });
        expect(scope.beginIdentity()).toBe("_");
        expect(scope.keyForWrite("")).toBe("_");
    });
});
