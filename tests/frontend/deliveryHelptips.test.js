// SPDX-License-Identifier: 0BSD

import { describe, it, expect, beforeEach, vi } from "vitest";
import { buildDeliveryHelptips, mapSendFailureKind } from "@/js/deliveryHelptips.js";
import { shouldShowDeliveryHelptips, shouldShowHelptip, resetHelptipPolicyForTests } from "@/js/helptipPolicy.js";

describe("deliveryHelptips.test.js", () => {
    beforeEach(() => {
        resetHelptipPolicyForTests();
    });

    it("orders self announce tips before peer path tips", () => {
        const tips = buildDeliveryHelptips({
            diagnostics: {
                self: { auto_announce_enabled: false, seconds_since_last_announce: 100000 },
                peer_announce: { known: false },
                path: { has_path: false, path_stale: true, path_unresponsive: false },
                recall: { identity_known: false },
                delivery_prefs: { propagation_fallback: false },
            },
            failureKind: "recall",
        });
        const ids = tips.map((tip) => tip.id);
        expect(ids.indexOf("self_announce_disabled")).toBeLessThan(ids.indexOf("no_path"));
        expect(ids).toContain("recall_failed");
    });

    it("maps recall send failures", () => {
        expect(mapSendFailureKind(400, "Could not recall destination identity.")).toBe("recall");
        expect(mapSendFailureKind(503, "No path to destination.")).toBe("no_path");
    });

    it("respects delivery helptips config toggle", () => {
        expect(shouldShowDeliveryHelptips({ delivery_helptips_enabled: true })).toBe(true);
        expect(shouldShowDeliveryHelptips({ delivery_helptips_enabled: false })).toBe(false);
        expect(shouldShowDeliveryHelptips({})).toBe(true);
    });

    it("throttles duplicate helptips per peer and tip id", () => {
        expect(shouldShowHelptip("peer-a", "no_path")).toBe(true);
        expect(shouldShowHelptip("peer-a", "no_path")).toBe(false);
        expect(shouldShowHelptip("peer-a", "path_stale")).toBe(true);
    });
});

describe("HelptipUtils integration", () => {
    beforeEach(() => {
        resetHelptipPolicyForTests();
        vi.resetModules();
    });

    it("shows helptip toast when enabled", async () => {
        const ToastUtils = (await import("@/js/ToastUtils.js")).default;
        const helptipSpy = vi.spyOn(ToastUtils, "helptips").mockImplementation(() => {});
        const { showDeliveryHelptips } = await import("@/js/HelptipUtils.js");

        await showDeliveryHelptips({
            api: {
                get: vi.fn().mockResolvedValue({
                    data: {
                        self: { auto_announce_enabled: false, seconds_since_last_announce: 1000 },
                        peer_announce: { known: false, stamp_cost: 0 },
                        path: { has_path: false, path_stale: true, path_unresponsive: false },
                        recall: { identity_known: false },
                        delivery_prefs: { propagation_fallback: false },
                    },
                }),
            },
            peerHash: "abc123",
            failureKind: "send_failed",
            status: 400,
            message: "Could not recall destination identity.",
            config: { delivery_helptips_enabled: true },
            i18n: (key) => key,
        });

        expect(helptipSpy).toHaveBeenCalled();
        helptipSpy.mockRestore();
    });
});
