import { beforeEach, describe, expect, it, vi } from "vitest";
import { isRetryableHttpError, withRetryableHttp } from "@/js/httpRetry.js";

describe("withRetryableHttp", () => {
    beforeEach(() => {
        vi.useRealTimers();
    });

    it("returns on first success without sleep", async () => {
        const sleep = vi.fn();
        const result = await withRetryableHttp(async () => ({ data: { ok: true } }), {
            sleep,
        });
        expect(result.data.ok).toBe(true);
        expect(sleep).not.toHaveBeenCalled();
    });

    it("retries 503 then succeeds", async () => {
        const sleep = vi.fn().mockResolvedValue(undefined);
        let calls = 0;
        const result = await withRetryableHttp(
            async () => {
                calls += 1;
                if (calls < 3) {
                    throw Object.assign(new Error("HTTP 503"), {
                        response: { status: 503, data: { error: "busy" } },
                    });
                }
                return { data: { contacts: [{ id: 1 }] } };
            },
            { sleep, baseDelayMs: 10 }
        );
        expect(calls).toBe(3);
        expect(sleep).toHaveBeenCalledTimes(2);
        expect(result.data.contacts).toHaveLength(1);
    });

    it("retries failed-to-fetch network errors", async () => {
        const sleep = vi.fn().mockResolvedValue(undefined);
        let calls = 0;
        const result = await withRetryableHttp(
            async () => {
                calls += 1;
                if (calls < 2) {
                    throw Object.assign(new TypeError("Failed to fetch"), { name: "TypeError" });
                }
                return { data: { ok: true } };
            },
            { sleep, baseDelayMs: 5 }
        );
        expect(calls).toBe(2);
        expect(result.data.ok).toBe(true);
    });

    it("does not retry non-503 errors", async () => {
        const sleep = vi.fn();
        await expect(
            withRetryableHttp(
                async () => {
                    throw Object.assign(new Error("HTTP 500"), {
                        response: { status: 500, data: { error: "boom" } },
                    });
                },
                { sleep }
            )
        ).rejects.toMatchObject({ response: { status: 500 } });
        expect(sleep).not.toHaveBeenCalled();
    });

    it("stops after maxAttempts on persistent 503", async () => {
        const sleep = vi.fn().mockResolvedValue(undefined);
        let calls = 0;
        await expect(
            withRetryableHttp(
                async () => {
                    calls += 1;
                    throw Object.assign(new Error("HTTP 503"), {
                        response: { status: 503 },
                    });
                },
                { sleep, maxAttempts: 3, baseDelayMs: 5 }
            )
        ).rejects.toMatchObject({ response: { status: 503 } });
        expect(calls).toBe(3);
        expect(sleep).toHaveBeenCalledTimes(2);
    });

    it("isRetryableHttpError oracle", () => {
        expect(isRetryableHttpError({ response: { status: 503 } })).toBe(true);
        expect(isRetryableHttpError({ response: { status: 500 } })).toBe(false);
        expect(isRetryableHttpError({ name: "AbortError" })).toBe(false);
        expect(isRetryableHttpError(Object.assign(new TypeError("Failed to fetch"), { name: "TypeError" }))).toBe(true);
    });
});
