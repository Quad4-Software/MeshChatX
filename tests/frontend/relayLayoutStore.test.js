// SPDX-License-Identifier: 0BSD

import { beforeEach, describe, expect, it } from "vitest";
import { loadRelayLayout, saveRelayLayout } from "@/js/relayLayoutStore.js";

const KEY = "meshchatx.relay.layout";

function stored() {
    return JSON.parse(localStorage.getItem(KEY) || "{}");
}

describe("relayLayoutStore", () => {
    beforeEach(() => {
        localStorage.clear();
    });

    it("scopes layout state under the identity key", () => {
        saveRelayLayout("idA", { view: "chat", selectedHubHash: "hubA" });
        saveRelayLayout("idB", { view: "chat", selectedHubHash: "hubB" });
        expect(stored()).toEqual({
            idA: { view: "chat", selectedHubHash: "hubA" },
            idB: { view: "chat", selectedHubHash: "hubB" },
        });
        expect(loadRelayLayout("idA").selectedHubHash).toBe("hubA");
        expect(loadRelayLayout("idB").selectedHubHash).toBe("hubB");
    });

    it("does not leak one identity's layout into another", () => {
        saveRelayLayout("idA", { view: "chat", selectedHubHash: "hubA" });
        expect(loadRelayLayout("idB")).toBeNull();
        expect(loadRelayLayout("_")).toBeNull();
    });

    it("treats a missing identity key as the _ bucket", () => {
        saveRelayLayout(null, { view: "chat" });
        expect(loadRelayLayout(undefined)).toEqual({ view: "chat" });
        expect(stored()._).toEqual({ view: "chat" });
    });

    it("reads a legacy flat layout stored before identity scoping", () => {
        localStorage.setItem(KEY, JSON.stringify({ view: "chat", selectedHubHash: "hubOld" }));
        expect(loadRelayLayout("idA").selectedHubHash).toBe("hubOld");
        // Saving under an identity strips the flat fields so the legacy
        // blob does not keep shadowing real buckets.
        saveRelayLayout("idA", { view: "chat" });
        expect(stored().view).toBeUndefined();
        expect(stored().selectedHubHash).toBeUndefined();
    });
});
