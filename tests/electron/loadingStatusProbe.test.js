import { describe, expect, it } from "vitest";
import { createRequire } from "module";

const require = createRequire(import.meta.url);
const probe = require("../../electron/loadingStatusProbe.js");

describe("electron/loadingStatusProbe", () => {
    it("parseStatusJson returns null for invalid JSON", () => {
        expect(probe.parseStatusJson("{")).toBeNull();
        expect(probe.parseStatusJson(null)).toBeNull();
    });

    it("evaluateStatusResponse accepts starting before network ready", () => {
        const result = probe.evaluateStatusResponse(
            200,
            JSON.stringify({
                status: "starting",
                stage: "rns",
                network_ready: false,
            })
        );
        expect(result.ok).toBe(true);
        expect(result.networkReady).toBe(false);
        expect(result.stage).toBe("rns");
    });

    it("evaluateStatusResponse accepts ok when network ready", () => {
        const result = probe.evaluateStatusResponse(
            200,
            JSON.stringify({
                status: "ok",
                stage: "ready",
                network_ready: true,
            })
        );
        expect(result.ok).toBe(true);
        expect(result.networkReady).toBe(true);
    });

    it("evaluateStatusResponse rejects failed startup", () => {
        const result = probe.evaluateStatusResponse(
            200,
            JSON.stringify({
                status: "failed",
                stage: "failed",
                error: "boom",
                network_ready: false,
            })
        );
        expect(result.ok).toBe(false);
        expect(result.failure.kind).toBe("startup-failed");
        expect(result.failure.error).toBe("boom");
    });

    it("evaluateStatusResponse rejects non-200", () => {
        const result = probe.evaluateStatusResponse(503, '{"status":"starting"}');
        expect(result.ok).toBe(false);
        expect(result.failure.kind).toBe("http-error");
        expect(result.failure.status).toBe(503);
    });

    it("evaluateStatusResponse rejects invalid payload", () => {
        expect(probe.evaluateStatusResponse(200, "not-json").ok).toBe(false);
        expect(probe.evaluateStatusResponse(200, '{"status":"nope"}').ok).toBe(false);
    });

    it("evaluateStatusResponse fuzzes common stage transitions", () => {
        const stages = ["http", "starting", "rns", "identity"];
        for (const stage of stages) {
            const result = probe.evaluateStatusResponse(
                200,
                JSON.stringify({ status: "starting", stage, network_ready: false })
            );
            expect(result.ok).toBe(true);
            expect(result.stage).toBe(stage);
            expect(result.networkReady).toBe(false);
        }
    });
});
