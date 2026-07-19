// SPDX-License-Identifier: 0BSD

/**
 * Adversarial fuzzing and oracles for early-UI / mesh-ready boot gating.
 */

import { afterEach, describe, expect, it, vi } from "vitest";
import {
    STARTUP_STAGE_LABELS,
    interpretStartupStatus,
    waitForMeshReady,
    waitForNetworkReady,
} from "../../meshchatx/src/frontend/js/networkStartupWait.js";

function assertInterpretOracle(result, data) {
    expect(result).toBeTruthy();
    expect(typeof result.kind).toBe("string");
    expect(["ready", "ui", "degraded", "failed", "starting", "invalid"]).toContain(result.kind);

    const own = (key) => Object.prototype.hasOwnProperty.call(data, key);
    const networkReady = own("network_ready") && data.network_ready === true;
    const uiReady = own("ui_ready") && data.ui_ready === true;
    const networkDegraded = own("network_degraded") && data.network_degraded === true;
    const status = own("status") ? data.status : undefined;

    if (result.kind === "ready") {
        expect(status === "ok" || networkReady).toBe(true);
    }
    if (result.kind === "ui") {
        expect(uiReady).toBe(true);
        expect(status === "starting" || status === undefined).toBe(true);
        expect(networkReady).toBe(false);
    }
    if (result.kind === "degraded") {
        expect(status).toBe("failed");
        expect(uiReady || networkDegraded).toBe(true);
    }
    if (result.kind === "failed") {
        expect(status).toBe("failed");
        expect(uiReady).toBe(false);
        expect(networkDegraded).toBe(false);
    }
    if (result.kind === "starting") {
        expect(uiReady).toBe(false);
    }
}

function mulberry32(seed) {
    let t = seed >>> 0;
    return () => {
        t += 0x6d2b79f5;
        let r = Math.imul(t ^ (t >>> 15), 1 | t);
        r ^= r + Math.imul(r ^ (r >>> 7), 61 | r);
        return ((r ^ (r >>> 14)) >>> 0) / 4294967296;
    };
}

describe("networkStartupWait adversarial / oracle", () => {
    afterEach(() => {
        vi.useRealTimers();
    });

    it("oracle: ready beats starting labels when network_ready is true", () => {
        const data = { status: "starting", stage: "identity", network_ready: true, ui_ready: true };
        const result = interpretStartupStatus(data);
        expect(result.kind).toBe("ready");
        assertInterpretOracle(result, data);
    });

    it("oracle: failed is checked before network_ready spoof", () => {
        const data = {
            status: "failed",
            network_ready: true,
            ui_ready: false,
            network_degraded: false,
            error: "spoof",
        };
        const result = interpretStartupStatus(data);
        expect(result.kind).toBe("failed");
        assertInterpretOracle(result, data);
    });

    it("oracle: only strict boolean true mounts UI early", () => {
        for (const fake of [1, "true", "yes", {}, [], "1"]) {
            const data = { status: "starting", stage: "rns", ui_ready: fake, network_ready: false };
            const result = interpretStartupStatus(data);
            expect(result.kind).toBe("starting");
            assertInterpretOracle(result, data);
        }
        const ok = interpretStartupStatus({
            status: "starting",
            stage: "rns",
            ui_ready: true,
            network_ready: false,
        });
        expect(ok.kind).toBe("ui");
    });

    it("oracle: degraded requires failed + recovery flag", () => {
        expect(
            interpretStartupStatus({
                status: "failed",
                ui_ready: true,
                error: "x",
            }).kind
        ).toBe("degraded");
        expect(
            interpretStartupStatus({
                status: "failed",
                network_degraded: true,
                error: "y",
            }).kind
        ).toBe("degraded");
        expect(interpretStartupStatus({ status: "failed", error: "z" }).kind).toBe("failed");
    });

    it("fuzz: random status payloads never throw and obey oracle", () => {
        const rand = mulberry32(0x51a7);
        const statuses = ["ok", "starting", "failed", undefined, null, "nope", 0, "", "OK"];
        const stages = [...Object.keys(STARTUP_STAGE_LABELS), undefined, null, "???", 12];
        for (let i = 0; i < 400; i++) {
            const data = {
                status: statuses[Math.floor(rand() * statuses.length)],
                stage: stages[Math.floor(rand() * stages.length)],
                network_ready: rand() < 0.3 ? true : rand() < 0.5 ? false : rand() < 0.5 ? 1 : "true",
                ui_ready: rand() < 0.3 ? true : rand() < 0.5 ? false : rand() < 0.5 ? 1 : "yes",
                network_degraded: rand() < 0.2,
                error: rand() < 0.2 ? "err" : rand() < 0.1 ? 123 : undefined,
            };
            let result;
            expect(() => {
                result = interpretStartupStatus(data);
            }).not.toThrow();
            if (data && typeof data === "object" && !Array.isArray(data)) {
                assertInterpretOracle(result, data);
            } else {
                expect(result.kind).toBe("invalid");
            }
        }
    });

    it("fuzz: interpretStartupStatus rejects non-objects without throwing", () => {
        for (const junk of [null, undefined, 0, 1, "", "starting", true, false, [], () => {}, Symbol("x")]) {
            expect(() => interpretStartupStatus(junk)).not.toThrow();
            expect(interpretStartupStatus(junk).kind).toBe("invalid");
        }
    });

    it("waitForMeshReady never returns ui even when ui_ready is set", async () => {
        let calls = 0;
        const result = await waitForMeshReady({
            fetchImpl: async () => {
                calls += 1;
                if (calls < 3) {
                    return {
                        ok: true,
                        json: async () => ({
                            status: "starting",
                            stage: "identity",
                            ui_ready: true,
                            network_ready: false,
                        }),
                    };
                }
                return {
                    ok: true,
                    json: async () => ({ status: "ok", network_ready: true, ui_ready: true }),
                };
            },
            sleep: async () => {},
            timeoutMs: 5000,
        });
        expect(result).toBe("ready");
        expect(calls).toBeGreaterThanOrEqual(3);
    });

    it("waitForNetworkReady prefers ready over ui on the same payload", async () => {
        const result = await waitForNetworkReady({
            fetchImpl: async () => ({
                ok: true,
                json: async () => ({
                    status: "ok",
                    network_ready: true,
                    ui_ready: true,
                    stage: "ready",
                }),
            }),
            sleep: async () => {},
            timeoutMs: 1000,
        });
        expect(result).toBe("ready");
    });

    it("waitForNetworkReady ignores non-ok HTTP and keeps polling", async () => {
        let calls = 0;
        const result = await waitForNetworkReady({
            fetchImpl: async () => {
                calls += 1;
                if (calls === 1) {
                    return { ok: false, status: 503, json: async () => ({}) };
                }
                if (calls === 2) {
                    return {
                        ok: true,
                        json: async () => ({
                            status: "starting",
                            ui_ready: true,
                            stage: "http",
                        }),
                    };
                }
                return { ok: true, json: async () => ({ status: "ok", network_ready: true }) };
            },
            sleep: async () => {},
            timeoutMs: 5000,
            mountOnUiReady: true,
        });
        expect(result).toBe("ui");
    });

    it("waitForNetworkReady: malformed JSON is treated as still starting", async () => {
        let calls = 0;
        const lines = [];
        const result = await waitForNetworkReady({
            fetchImpl: async () => {
                calls += 1;
                if (calls < 2) {
                    return {
                        ok: true,
                        json: async () => {
                            throw new Error("bad json");
                        },
                    };
                }
                return {
                    ok: true,
                    json: async () => ({ status: "ok", network_ready: true }),
                };
            },
            sleep: async () => {},
            timeoutMs: 5000,
            onLine: (text) => lines.push(text),
            mountOnUiReady: false,
        });
        expect(result).toBe("ready");
        expect(lines).toContain("Still starting…");
    });

    it("adversarial: prototype pollution cannot spoof network_ready or ui_ready", () => {
        const polluted = { status: "starting", stage: "rns" };
        Object.setPrototypeOf(polluted, {
            network_ready: true,
            ui_ready: true,
            network_degraded: true,
        });
        const result = interpretStartupStatus(polluted);
        expect(result.kind).toBe("starting");
        assertInterpretOracle(result, polluted);

        const ownUi = { status: "starting", stage: "rns", ui_ready: true };
        Object.setPrototypeOf(ownUi, { network_ready: true });
        expect(interpretStartupStatus(ownUi).kind).toBe("ui");
    });

    it("adversarial: arrays are invalid even with status-like indexes", () => {
        const arr = ["starting"];
        arr.status = "starting";
        arr.ui_ready = true;
        expect(interpretStartupStatus(arr).kind).toBe("invalid");
    });

    it("priority matrix: status/network_ready/ui_ready combinations", () => {
        const matrix = [
            [{ status: "ok", network_ready: false, ui_ready: false }, "ready"],
            [{ status: "starting", network_ready: true, ui_ready: false }, "ready"],
            [{ status: "starting", network_ready: false, ui_ready: true }, "ui"],
            [{ status: "starting", network_ready: false, ui_ready: false }, "starting"],
            [{ status: "failed", ui_ready: true }, "degraded"],
            [{ status: "failed", network_degraded: true }, "degraded"],
            [{ status: "failed" }, "failed"],
            [{ status: "wat" }, "invalid"],
        ];
        for (const [data, kind] of matrix) {
            const result = interpretStartupStatus(data);
            expect(result.kind).toBe(kind);
            assertInterpretOracle(result, data);
        }
    });
});
