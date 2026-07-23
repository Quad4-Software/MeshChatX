// SPDX-License-Identifier: 0BSD

import { describe, expect, it } from "vitest";

import {
    isLikelyInterfaceRecoveryError,
    recoveryRouteForNetworkError,
} from "../../meshchatx/src/frontend/js/networkRecovery.js";

describe("networkRecovery", () => {
    it("does not treat telephony or generic errors as interface recovery", () => {
        expect(isLikelyInterfaceRecoveryError("type object 'Profiles' has no attribute 'available_modes'")).toBe(false);
        expect(recoveryRouteForNetworkError("Telephone init failed")).toBeNull();
        expect(recoveryRouteForNetworkError("")).toBeNull();
    });

    it("routes interface-shaped errors to the interfaces page", () => {
        expect(isLikelyInterfaceRecoveryError("RNode interface failed to open")).toBe(true);
        expect(recoveryRouteForNetworkError("AutoInterface bind error")).toBe("interfaces");
        expect(recoveryRouteForNetworkError("I2P interface unavailable")).toBe("interfaces");
    });
});
