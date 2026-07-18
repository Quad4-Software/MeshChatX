// SPDX-License-Identifier: 0BSD

import { beforeEach, describe, expect, it, vi } from "vitest";
import {
    CLIENT_HEAP_CONSECUTIVE_NEEDED,
    CLIENT_HEAP_RATIO_THRESHOLD,
    MEMORY_WARNING_MESSAGE_KEY,
    MEMORY_WARNING_TOAST_KEY,
    evaluateClientHeapSample,
    handleHealthWarningPayload,
    isMemoryHealthWarningPayload,
    isMemoryRecoveredPayload,
    markMemoryWarningDismissed,
    markMemoryWarningRecovered,
    markMemoryWarningShown,
    resetMemoryWarningStateForTests,
    shouldShowMemoryWarningToast,
    showMemoryWarningToastIfNeeded,
} from "@/js/healthMemoryWarning.js";

describe("healthMemoryWarning", () => {
    beforeEach(() => {
        resetMemoryWarningStateForTests();
    });

    describe("payload classification (false positives)", () => {
        it("rejects null and non-objects", () => {
            expect(isMemoryHealthWarningPayload(null)).toBe(false);
            expect(isMemoryHealthWarningPayload(undefined)).toBe(false);
            expect(isMemoryHealthWarningPayload("memory_low")).toBe(false);
        });

        it("rejects entropy and error_rate warnings", () => {
            expect(isMemoryHealthWarningPayload({ kind: "entropy_climbing" })).toBe(false);
            expect(isMemoryHealthWarningPayload({ kind: "error_rate_high" })).toBe(false);
            expect(
                isMemoryHealthWarningPayload({
                    type: "health_warning",
                    data: { kind: "entropy_climbing" },
                })
            ).toBe(false);
        });

        it("accepts memory_low nested under data or flat", () => {
            expect(isMemoryHealthWarningPayload({ kind: "memory_low" })).toBe(true);
            expect(
                isMemoryHealthWarningPayload({
                    type: "health_warning",
                    data: { kind: "memory_low", value: 42 },
                })
            ).toBe(true);
        });

        it("detects memory_recovered", () => {
            expect(isMemoryRecoveredPayload({ kind: "memory_recovered" })).toBe(true);
            expect(
                isMemoryRecoveredPayload({
                    type: "health_warning",
                    data: { kind: "memory_recovered" },
                })
            ).toBe(true);
            expect(isMemoryRecoveredPayload({ kind: "memory_low" })).toBe(false);
        });
    });

    describe("one-time sticky toast gating", () => {
        it("shows once for host memory_low then ignores until recovered", () => {
            const toastUtils = { warning: vi.fn() };
            expect(handleHealthWarningPayload({ data: { kind: "memory_low" } }, toastUtils)).toBe("shown");
            expect(toastUtils.warning).toHaveBeenCalledWith(MEMORY_WARNING_MESSAGE_KEY, 0, MEMORY_WARNING_TOAST_KEY);

            toastUtils.warning.mockClear();
            expect(handleHealthWarningPayload({ data: { kind: "memory_low" } }, toastUtils)).toBe("ignored");
            expect(toastUtils.warning).not.toHaveBeenCalled();

            markMemoryWarningDismissed();
            expect(handleHealthWarningPayload({ data: { kind: "memory_low" } }, toastUtils)).toBe("ignored");

            expect(handleHealthWarningPayload({ data: { kind: "memory_recovered" } }, toastUtils)).toBe("recovered");
            expect(handleHealthWarningPayload({ data: { kind: "memory_low" } }, toastUtils)).toBe("shown");
            expect(toastUtils.warning).toHaveBeenCalledTimes(1);
        });

        it("ignores non-memory health kinds without toasting", () => {
            const toastUtils = { warning: vi.fn() };
            expect(handleHealthWarningPayload({ data: { kind: "entropy_climbing" } }, toastUtils)).toBe("ignored");
            expect(handleHealthWarningPayload({ data: { kind: "error_rate_high" } }, toastUtils)).toBe("ignored");
            expect(toastUtils.warning).not.toHaveBeenCalled();
        });

        it("shouldShowMemoryWarningToast blocks when visible or dismissed", () => {
            expect(shouldShowMemoryWarningToast({ fromHealthWs: true })).toBe(true);
            markMemoryWarningShown();
            expect(shouldShowMemoryWarningToast({ fromHealthWs: true })).toBe(false);
            markMemoryWarningDismissed();
            expect(shouldShowMemoryWarningToast({ fromClientHeap: true })).toBe(false);
            markMemoryWarningRecovered();
            expect(shouldShowMemoryWarningToast({ fromClientHeap: true })).toBe(true);
        });

        it("showMemoryWarningToastIfNeeded no-ops without toast utils", () => {
            expect(showMemoryWarningToastIfNeeded(null, { fromHealthWs: true })).toBe(false);
            expect(showMemoryWarningToastIfNeeded({}, { fromHealthWs: true })).toBe(false);
        });
    });

    describe("client heap false positives", () => {
        it("does not warn when performance.memory is missing", () => {
            expect(evaluateClientHeapSample(null)).toEqual({ shouldWarn: false, reason: "unavailable" });
            expect(evaluateClientHeapSample({})).toEqual({ shouldWarn: false, reason: "unavailable" });
            expect(evaluateClientHeapSample({ jsHeapSizeLimit: 0, usedJSHeapSize: 1 })).toEqual({
                shouldWarn: false,
                reason: "unavailable",
            });
        });

        it("does not warn on invalid used heap", () => {
            expect(
                evaluateClientHeapSample({
                    jsHeapSizeLimit: 100,
                    usedJSHeapSize: Number.NaN,
                })
            ).toEqual({ shouldWarn: false, reason: "invalid" });
        });

        it("does not warn below ratio threshold", () => {
            const limit = 1000;
            const used = Math.floor(limit * (CLIENT_HEAP_RATIO_THRESHOLD - 0.05));
            const result = evaluateClientHeapSample({ jsHeapSizeLimit: limit, usedJSHeapSize: used });
            expect(result.shouldWarn).toBe(false);
            expect(result.reason).toBe("below_threshold");
        });

        it("requires consecutive high samples (single spike is false positive)", () => {
            const limit = 1000;
            const used = Math.ceil(limit * CLIENT_HEAP_RATIO_THRESHOLD);
            const first = evaluateClientHeapSample({ jsHeapSizeLimit: limit, usedJSHeapSize: used });
            expect(first.shouldWarn).toBe(false);
            expect(first.reason).toBe("need_consecutive");
            expect(first.consecutive).toBe(1);

            if (CLIENT_HEAP_CONSECUTIVE_NEEDED > 1) {
                const second = evaluateClientHeapSample({ jsHeapSizeLimit: limit, usedJSHeapSize: used });
                expect(second.shouldWarn).toBe(true);
                expect(second.reason).toBe("high_heap");
            }
        });

        it("resets consecutive counter after a low sample", () => {
            const limit = 1000;
            const high = Math.ceil(limit * CLIENT_HEAP_RATIO_THRESHOLD);
            const low = Math.floor(limit * 0.2);
            evaluateClientHeapSample({ jsHeapSizeLimit: limit, usedJSHeapSize: high });
            const afterLow = evaluateClientHeapSample({ jsHeapSizeLimit: limit, usedJSHeapSize: low });
            expect(afterLow.shouldWarn).toBe(false);
            expect(afterLow.reason).toBe("below_threshold");
            const afterHighAgain = evaluateClientHeapSample({ jsHeapSizeLimit: limit, usedJSHeapSize: high });
            expect(afterHighAgain.shouldWarn).toBe(false);
            expect(afterHighAgain.reason).toBe("need_consecutive");
        });
    });
});
