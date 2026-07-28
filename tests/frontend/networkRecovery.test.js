// SPDX-License-Identifier: 0BSD

import { describe, expect, it } from "vitest";

import {
    isDatabaseRecoveryError,
    isLikelyInterfaceRecoveryError,
    recoveryLocationForNetworkError,
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

    it("detects database recovery errors and routes to About backups", () => {
        const msg =
            "Database version 55 is newer than this MeshChatX build supports (54). Restore a backup or upgrade the application.";
        expect(isDatabaseRecoveryError(msg)).toBe(true);
        expect(isLikelyInterfaceRecoveryError(msg)).toBe(false);
        expect(recoveryLocationForNetworkError(msg)).toEqual({
            name: "about",
            hash: "#about-database-backups",
        });
    });
});
