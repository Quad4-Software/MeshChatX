// SPDX-License-Identifier: 0BSD

import { describe, it, expect } from "vitest";
import { hydrateContactVisuals } from "@/features/call/lib/callHistory.ts";

describe("CallPage custom contact images", () => {
    it("hydrateContactVisuals applies contact custom_image onto active call", () => {
        const contacts = [
            {
                id: 1,
                name: "Alice",
                remote_identity_hash: "abcdef0123456789abcdef0123456789",
                custom_image: "data:image/webp;base64,abc",
            },
        ];
        const activeCall = {
            hash: "c1",
            status: 6,
            remote_identity_hash: "abcdef0123456789abcdef0123456789",
        };
        const result = hydrateContactVisuals({
            contacts,
            activeCall,
            callHistory: [],
        });
        expect(result.activeCall?.custom_image).toBe("data:image/webp;base64,abc");
    });

    it("hydrateContactVisuals applies images onto history rows", () => {
        const contacts = [
            {
                id: 1,
                name: "Bob",
                remote_identity_hash: "11112222333344445555666677778888",
                custom_image: "data:image/webp;base64,bob",
            },
        ];
        const result = hydrateContactVisuals({
            contacts,
            callHistory: [
                {
                    id: 9,
                    remote_identity_hash: "11112222333344445555666677778888",
                    timestamp: 1,
                },
            ],
        });
        expect(result.callHistory[0].custom_image || result.callHistory[0].contact_image).toBeTruthy();
    });
});
