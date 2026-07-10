import { afterEach, describe, expect, it, vi } from "vitest";
import {
    STARTUP_STAGE_LABELS,
    interpretStartupStatus,
    waitForNetworkReady,
} from "../../meshchatx/src/frontend/js/networkStartupWait.js";

describe("networkStartupWait", () => {
    afterEach(() => {
        vi.useRealTimers();
    });

    it("interpretStartupStatus marks ready for ok", () => {
        expect(interpretStartupStatus({ status: "ok", network_ready: true })).toEqual({
            kind: "ready",
            stage: "ready",
        });
    });

    it("interpretStartupStatus marks ready when network_ready alone", () => {
        expect(interpretStartupStatus({ status: "starting", network_ready: true, stage: "identity" })).toEqual({
            kind: "ready",
            stage: "identity",
        });
    });

    it("interpretStartupStatus marks failed", () => {
        expect(interpretStartupStatus({ status: "failed", error: "boom", stage: "failed" })).toEqual({
            kind: "failed",
            stage: "failed",
            error: "boom",
        });
    });

    it("interpretStartupStatus marks degraded when ui_ready", () => {
        expect(
            interpretStartupStatus({
                status: "failed",
                error: "RNS died",
                stage: "failed",
                ui_ready: true,
                network_degraded: true,
            })
        ).toEqual({
            kind: "degraded",
            stage: "failed",
            error: "RNS died",
        });
    });

    it("interpretStartupStatus maps starting stages to labels", () => {
        for (const stage of Object.keys(STARTUP_STAGE_LABELS)) {
            if (stage === "ready" || stage === "failed") {
                continue;
            }
            const result = interpretStartupStatus({ status: "starting", stage });
            expect(result.kind).toBe("starting");
            expect(result.label).toBe(STARTUP_STAGE_LABELS[stage]);
        }
    });

    it("interpretStartupStatus rejects invalid payloads", () => {
        expect(interpretStartupStatus(null).kind).toBe("invalid");
        expect(interpretStartupStatus("x").kind).toBe("invalid");
        expect(interpretStartupStatus({ status: "nope" }).kind).toBe("invalid");
    });

    it("waitForNetworkReady resolves when status becomes ok", async () => {
        let calls = 0;
        const lines = [];
        const fetchImpl = vi.fn(async () => {
            calls += 1;
            if (calls < 3) {
                return {
                    ok: true,
                    json: async () => ({ status: "starting", stage: "rns", network_ready: false }),
                };
            }
            return {
                ok: true,
                json: async () => ({ status: "ok", stage: "ready", network_ready: true }),
            };
        });
        const ready = await waitForNetworkReady({
            fetchImpl,
            sleep: async () => {},
            timeoutMs: 5000,
            onLine: (text) => lines.push(text),
        });
        expect(ready).toBe("ready");
        expect(lines).toContain(STARTUP_STAGE_LABELS.rns);
        expect(fetchImpl).toHaveBeenCalled();
    });

    it("waitForNetworkReady returns false on failed status", async () => {
        const errors = [];
        const ready = await waitForNetworkReady({
            fetchImpl: async () => ({
                ok: true,
                json: async () => ({ status: "failed", error: "RNS died" }),
            }),
            sleep: async () => {},
            timeoutMs: 1000,
            onLine: () => {},
            onErrorState: () => errors.push("error"),
        });
        expect(ready).toBe(false);
        expect(errors).toEqual(["error"]);
    });

    it("waitForNetworkReady returns degraded when ui_ready", async () => {
        const degraded = [];
        const ready = await waitForNetworkReady({
            fetchImpl: async () => ({
                ok: true,
                json: async () => ({
                    status: "failed",
                    error: "I2P brick",
                    ui_ready: true,
                    network_degraded: true,
                }),
            }),
            sleep: async () => {},
            timeoutMs: 1000,
            onLine: () => {},
            onDegraded: (error) => degraded.push(error),
        });
        expect(ready).toBe("degraded");
        expect(degraded).toEqual(["I2P brick"]);
    });

    it("waitForNetworkReady keeps polling through fetch errors", async () => {
        let calls = 0;
        const lines = [];
        const ready = await waitForNetworkReady({
            fetchImpl: async () => {
                calls += 1;
                if (calls === 1) {
                    throw new Error("offline");
                }
                return {
                    ok: true,
                    json: async () => ({ status: "ok", network_ready: true }),
                };
            },
            sleep: async () => {},
            timeoutMs: 5000,
            onLine: (text) => lines.push(text),
        });
        expect(ready).toBe("ready");
        expect(lines).toContain("Still starting…");
    });

    it("waitForNetworkReady times out", async () => {
        let now = 0;
        const errors = [];
        const lines = [];
        const ready = await waitForNetworkReady({
            fetchImpl: async () => ({
                ok: true,
                json: async () => ({ status: "starting", stage: "identity", network_ready: false }),
            }),
            now: () => now,
            sleep: async () => {
                now += 500;
            },
            timeoutMs: 1000,
            onLine: (text) => lines.push(text),
            onErrorState: () => errors.push("error"),
        });
        expect(ready).toBe(false);
        expect(errors).toEqual(["error"]);
        expect(lines.at(-1)).toContain("timed out");
    });
});
