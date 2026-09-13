// SPDX-License-Identifier: 0BSD

import { describe, it, expect, beforeEach, vi } from "vitest";
import { buildDeliveryHelptips, mapSendFailureKind } from "@/js/deliveryHelptips.js";
import {
    shouldShowDeliveryHelptips,
    shouldShowHelptip,
    shouldShowHelptipForPeer,
    recordHelptipShownForPeer,
    resetHelptipPolicyForTests,
} from "@/js/helptipPolicy.js";

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
        expect(mapSendFailureKind(503, "No path to preferred propagation node. Open Propagation Nodes.")).toBe(
            "no_path_propagation_node"
        );
        expect(mapSendFailureKind(400, "No preferred propagation node configured. Set one in Settings.")).toBe(
            "no_propagation_node"
        );
    });

    it("surfaces propagation-node path tips without peer no_path when hinted", () => {
        const tips = buildDeliveryHelptips({
            diagnostics: {
                self: { auto_announce_enabled: true, seconds_since_last_announce: 10 },
                peer_announce: { known: true, age_seconds: 60 },
                path: { has_path: false, path_stale: true, path_unresponsive: false },
                recall: { identity_known: true },
                delivery_prefs: { propagation_fallback: true },
                failure_hint: "no_path_propagation_node",
            },
            failureKind: "no_path_propagation_node",
        });
        const ids = tips.map((tip) => tip.id);
        expect(ids).toContain("no_path_propagation_node");
        expect(ids).not.toContain("no_path");
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

    it("throttles helptips per peer with a short cooldown", () => {
        const now = Date.now();
        expect(shouldShowHelptipForPeer("peer-a", now)).toBe(true);
        recordHelptipShownForPeer("peer-a", now);
        expect(shouldShowHelptipForPeer("peer-a", now)).toBe(false);
        expect(shouldShowHelptipForPeer("peer-a", now + 30001)).toBe(true);
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

    it("caps helptip details at three and prefers warnings", async () => {
        const ToastUtils = (await import("@/js/ToastUtils.js")).default;
        const helptipSpy = vi.spyOn(ToastUtils, "helptips").mockImplementation(() => {});
        const { showDeliveryHelptips } = await import("@/js/HelptipUtils.js");

        const diagnostics = {
            self: { auto_announce_enabled: false, seconds_since_last_announce: 1000 },
            peer_announce: { known: false, stamp_cost: 0, age_seconds: 100000 },
            path: { has_path: false, path_stale: true, path_unresponsive: true },
            recall: { identity_known: false },
            delivery_prefs: { propagation_fallback: false },
        };

        await showDeliveryHelptips({
            api: { get: vi.fn() },
            peerHash: "abc123",
            failureKind: "send_failed",
            status: 400,
            message: "Could not recall destination identity.",
            diagnostics,
            config: { delivery_helptips_enabled: true },
            i18n: (key) => key,
        });

        expect(helptipSpy).toHaveBeenCalledOnce();
        const args = helptipSpy.mock.calls[0][0];
        expect(args.details.length).toBeLessThanOrEqual(3);
        expect(args.details).toContain("helptips.self_announce_disabled");
        expect(args.details).toContain("helptips.recall_failed");
        expect(args.details).toContain("helptips.peer_announce_missing");
        helptipSpy.mockRestore();
    });

    it("deduplicates in-flight diagnostics fetches per peer", async () => {
        const get = vi.fn().mockResolvedValue({
            data: {
                self: { auto_announce_enabled: false, seconds_since_last_announce: 1000 },
                peer_announce: { known: false, stamp_cost: 0 },
                path: { has_path: false, path_stale: true, path_unresponsive: false },
                recall: { identity_known: false },
                delivery_prefs: { propagation_fallback: false },
            },
        });

        const [{ showDeliveryHelptips }] = await Promise.all([
            import("@/js/HelptipUtils.js"),
            import("@/js/HelptipUtils.js"),
        ]);

        const ToastUtils = (await import("@/js/ToastUtils.js")).default;
        const helptipSpy = vi.spyOn(ToastUtils, "helptips").mockImplementation(() => {});

        await Promise.all([
            showDeliveryHelptips({
                api: { get },
                peerHash: "abc123",
                failureKind: "send_failed",
                status: 400,
                message: "Could not recall destination identity.",
                config: { delivery_helptips_enabled: true },
                i18n: (key) => key,
            }),
            showDeliveryHelptips({
                api: { get },
                peerHash: "abc123",
                failureKind: "send_failed",
                status: 400,
                message: "Could not recall destination identity.",
                config: { delivery_helptips_enabled: true },
                i18n: (key) => key,
            }),
        ]);

        expect(get).toHaveBeenCalledOnce();
        expect(helptipSpy).toHaveBeenCalledOnce();
        helptipSpy.mockRestore();
    });

    it("throttles helptip toasts per peer", async () => {
        vi.useFakeTimers();
        try {
            const ToastUtils = (await import("@/js/ToastUtils.js")).default;
            const helptipSpy = vi.spyOn(ToastUtils, "helptips").mockImplementation(() => {});
            const { showDeliveryHelptips } = await import("@/js/HelptipUtils.js");

            const diagnostics = {
                self: { auto_announce_enabled: false, seconds_since_last_announce: 1000 },
                peer_announce: { known: false, stamp_cost: 0 },
                path: { has_path: false, path_stale: true, path_unresponsive: false },
                recall: { identity_known: false },
                delivery_prefs: { propagation_fallback: false },
            };

            await showDeliveryHelptips({
                api: { get: vi.fn() },
                peerHash: "abc123",
                failureKind: "send_failed",
                status: 400,
                message: "Could not recall destination identity.",
                diagnostics,
                config: { delivery_helptips_enabled: true },
                i18n: (key) => key,
            });

            await showDeliveryHelptips({
                api: { get: vi.fn() },
                peerHash: "abc123",
                failureKind: "send_failed",
                status: 503,
                message: "No path to destination.",
                diagnostics,
                config: { delivery_helptips_enabled: true },
                i18n: (key) => key,
            });

            expect(helptipSpy).toHaveBeenCalledOnce();
            helptipSpy.mockRestore();
        } finally {
            vi.useRealTimers();
        }
    });
});
