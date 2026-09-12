// SPDX-License-Identifier: 0BSD

import { beforeEach, describe, expect, it, vi } from "vitest";
import { useSelfTest } from "../../meshchatx/src/frontend/js/settings/useSelfTest.js";

describe("useSelfTest", () => {
    beforeEach(() => {
        vi.restoreAllMocks();
        window.api = {
            get: vi.fn(async () => ({
                data: {
                    stack_up: { status: "ok" },
                    db_good: { status: "failed", reason: "locked" },
                },
            })),
        };
    });

    it("maps results to checks with labels", async () => {
        const t = (key) => key;
        const st = useSelfTest({ t });
        await st.runSelfTest();
        expect(window.api.get).toHaveBeenCalledWith(expect.stringContaining("/self-test"));
        const byKey = Object.fromEntries(st.selfTestChecks.value.map((c) => [c.key, c]));
        expect(byKey.stack_up.passed).toBe(true);
        expect(byKey.db_good.passed).toBe(false);
        expect(byKey.db_good.reason).toBe("locked");
        expect(byKey.db_good.label).toBe("selftest.db_good");
        expect(st.allSelfTestChecksPassed.value).toBe(false);
    });

    it("flags all-passed when every check is ok", async () => {
        const st = useSelfTest();
        const ok = {};
        for (const c of ["stack_up"]) ok[c] = { status: "ok" };
        window.api.get = vi.fn(async () => ({ data: { stack_up: { status: "ok" } } }));
        await st.runSelfTest();
        // unknown keys are not in the check list; listed keys missing -> failed
        expect(st.selfTestChecks.value.length).toBeGreaterThan(0);
        st.selfTestResults.value = Object.fromEntries(
            st.selfTestChecks.value.map((c) => [c.key, { status: "ok" }])
        );
        expect(st.allSelfTestChecksPassed.value).toBe(true);
    });

    it("failure fills every check with the error reason", async () => {
        window.api.get = vi.fn(async () => Promise.reject(new Error("nope")));
        const st = useSelfTest();
        await st.runSelfTest();
        expect(st.selfTestRunning.value).toBe(false);
        expect(st.selfTestChecks.value.length).toBeGreaterThan(40);
        expect(st.selfTestChecks.value.every((c) => !c.passed && c.reason === "nope")).toBe(true);
    });

    it("ignores a second run while running", async () => {
        let resolve;
        window.api.get = vi.fn(() => new Promise((r) => (resolve = r)));
        const st = useSelfTest();
        const first = st.runSelfTest();
        expect(st.selfTestRunning.value).toBe(true);
        await st.runSelfTest();
        expect(window.api.get).toHaveBeenCalledTimes(1);
        resolve({ data: {} });
        await first;
        expect(st.selfTestRunning.value).toBe(false);
    });

    it("toggles expanded reasons", () => {
        const st = useSelfTest();
        expect(st.isSelfTestReasonExpanded("db_good")).toBe(false);
        st.toggleSelfTestReason("db_good");
        expect(st.isSelfTestReasonExpanded("db_good")).toBe(true);
        st.toggleSelfTestReason("db_good");
        expect(st.isSelfTestReasonExpanded("db_good")).toBe(false);
    });
});
