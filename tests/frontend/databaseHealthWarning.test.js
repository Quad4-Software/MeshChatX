// SPDX-License-Identifier: 0BSD

import { beforeEach, describe, expect, it, vi } from "vitest";
import {
    DATABASE_HEALTH_FALLBACK_MESSAGE,
    DATABASE_HEALTH_TOAST_DURATION_MS,
    DATABASE_HEALTH_TOAST_KEY,
    fingerprintDatabaseHealthIssues,
    resetDatabaseHealthWarningStateForTests,
    showDatabaseHealthIssuesToastIfNeeded,
} from "@/js/databaseHealthWarning.js";

describe("databaseHealthWarning", () => {
    beforeEach(() => {
        resetDatabaseHealthWarningStateForTests();
    });

    describe("fingerprintDatabaseHealthIssues", () => {
        it("returns empty for missing or empty issues", () => {
            expect(fingerprintDatabaseHealthIssues(null)).toBe("");
            expect(fingerprintDatabaseHealthIssues(undefined)).toBe("");
            expect(fingerprintDatabaseHealthIssues([])).toBe("");
            expect(fingerprintDatabaseHealthIssues(["", "  "])).toBe("");
            expect(fingerprintDatabaseHealthIssues([1, null])).toBe("");
        });

        it("joins trimmed issue strings", () => {
            expect(fingerprintDatabaseHealthIssues([" a ", "b"])).toBe("a\nb");
        });
    });

    describe("showDatabaseHealthIssuesToastIfNeeded", () => {
        it("shows once per fingerprint then ignores repeats", () => {
            const toastUtils = { warning: vi.fn() };
            const issues = [
                "Database content anomaly: was 70 messages / 15420968 bytes, now 0 / 11292728. Restore from backup if needed.",
            ];
            expect(showDatabaseHealthIssuesToastIfNeeded(issues, toastUtils)).toBe(true);
            expect(toastUtils.warning).toHaveBeenCalledTimes(1);
            expect(toastUtils.warning).toHaveBeenCalledWith(
                issues[0],
                DATABASE_HEALTH_TOAST_DURATION_MS,
                DATABASE_HEALTH_TOAST_KEY
            );

            toastUtils.warning.mockClear();
            expect(showDatabaseHealthIssuesToastIfNeeded(issues, toastUtils)).toBe(false);
            expect(showDatabaseHealthIssuesToastIfNeeded([...issues], toastUtils)).toBe(false);
            expect(toastUtils.warning).not.toHaveBeenCalled();
        });

        it("does not toast when issues are empty", () => {
            const toastUtils = { warning: vi.fn() };
            expect(showDatabaseHealthIssuesToastIfNeeded([], toastUtils)).toBe(false);
            expect(showDatabaseHealthIssuesToastIfNeeded(null, toastUtils)).toBe(false);
            expect(toastUtils.warning).not.toHaveBeenCalled();
        });

        it("shows again after issues clear then a new fingerprint arrives", () => {
            const toastUtils = { warning: vi.fn() };
            expect(showDatabaseHealthIssuesToastIfNeeded(["first"], toastUtils)).toBe(true);
            expect(showDatabaseHealthIssuesToastIfNeeded([], toastUtils)).toBe(false);
            expect(showDatabaseHealthIssuesToastIfNeeded(["second"], toastUtils)).toBe(true);
            expect(toastUtils.warning).toHaveBeenCalledTimes(2);
            expect(toastUtils.warning.mock.calls[1][0]).toBe("second");
        });

        it("no-ops without toast utils", () => {
            expect(showDatabaseHealthIssuesToastIfNeeded(["issue"], null)).toBe(false);
            expect(showDatabaseHealthIssuesToastIfNeeded(["issue"], {})).toBe(false);
        });

        it("uses fallback when join would be empty after fingerprint", () => {
            const toastUtils = { warning: vi.fn() };
            expect(showDatabaseHealthIssuesToastIfNeeded(["ok"], toastUtils)).toBe(true);
            expect(toastUtils.warning.mock.calls[0][0]).not.toBe(DATABASE_HEALTH_FALLBACK_MESSAGE);
        });
    });
});
