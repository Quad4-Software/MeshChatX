// SPDX-License-Identifier: 0BSD

import { describe, expect, it } from "vitest";
import { isSelfLxmfDestination } from "@/features/messages/lib/conversationPeer.ts";

describe("ConversationViewer self peer detection", () => {
    const myLxmf = "aa".repeat(16);
    const identityHash = "bb".repeat(16);

    it("accepts the local LXMF destination case-insensitively", () => {
        expect(isSelfLxmfDestination(myLxmf, myLxmf, identityHash)).toBe(true);
        expect(isSelfLxmfDestination(myLxmf.toUpperCase(), myLxmf, identityHash)).toBe(true);
    });

    it("accepts the local identity hash", () => {
        expect(isSelfLxmfDestination(identityHash, myLxmf, identityHash)).toBe(true);
    });

    it("rejects empty and unrelated destinations", () => {
        expect(isSelfLxmfDestination("", myLxmf, identityHash)).toBe(false);
        expect(isSelfLxmfDestination("cc".repeat(16), myLxmf, identityHash)).toBe(false);
    });
});
