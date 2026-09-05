// SPDX-License-Identifier: 0BSD

import { render, cleanup, fireEvent, waitFor, screen } from "@testing-library/svelte";
import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import FatalErrorPage from "../../meshchatx/src/frontend/features/fatal-error/FatalErrorPage.svelte";
import {
    copyFatalErrorReport,
    reportFatalErrorLocally,
    resolveFatalErrorSummary,
} from "../../meshchatx/src/frontend/features/fatal-error/lib/fatalErrorActions.ts";
import fatalErrorState, { clearFatalError, reportFatalError } from "../../meshchatx/src/frontend/js/fatalErrorState.js";
import { registerFallbackMessages, registerTranslator } from "../../meshchatx/src/frontend/js/i18n.js";
import ToastUtils from "../../meshchatx/src/frontend/js/ToastUtils.js";
import * as clipboardUtils from "../../meshchatx/src/frontend/js/clipboardUtils.js";
import * as fatalErrorStateModule from "../../meshchatx/src/frontend/js/fatalErrorState.js";

vi.mock("../../meshchatx/src/frontend/js/ToastUtils", () => ({
    default: {
        success: vi.fn(),
        error: vi.fn(),
    },
}));

const fatalErrorI18n = {
    app: {
        error_backend_title: "Backend unreachable",
        error_frontend_title: "Fatal error",
        error_details_heading: "Error details",
        error_reload_page: "Reload page",
        error_report_locally: "Report locally",
        error_report_saved: "Report saved",
        error_report_failed: "Failed to save report",
        error_copy_details: "Copy details",
    },
    common: {
        copied: "Copied",
        failed_to_copy: "Failed to copy",
    },
};

describe("fatalErrorActions", () => {
    it("resolves fatal error summaries correctly", () => {
        const summary = resolveFatalErrorSummary(
            {
                kind: "backend",
                title: "Custom Title",
                message: "Server crashed",
                details: "Error trace details",
                stack: "Stack line",
            },
            "Default Backend",
            "Default Frontend"
        );

        expect(summary.kind).toBe("backend");
        expect(summary.title).toBe("Custom Title");
        expect(summary.message).toBe("Server crashed");
        expect(summary.hasDetails).toBe(true);
        expect(summary.detailBody).toContain("Error trace details");
        expect(summary.detailBody).toContain("Stack line");
    });

    it("falls back to default title when error has no title", () => {
        const summary = resolveFatalErrorSummary(
            {
                kind: "frontend",
                message: "UI broke",
            },
            "Default Backend",
            "Default Frontend"
        );

        expect(summary.kind).toBe("frontend");
        expect(summary.title).toBe("Default Frontend");
        expect(summary.hasDetails).toBe(false);
    });

    it("copies error report to clipboard", async () => {
        const copySpy = vi.spyOn(clipboardUtils, "copyTextToClipboard").mockResolvedValue(true);
        const ok = await copyFatalErrorReport({
            kind: "backend",
            message: "fail",
            timestamp: Date.now(),
        });
        expect(ok).toBe(true);
        expect(copySpy).toHaveBeenCalled();
        copySpy.mockRestore();
    });

    it("reports error locally and routes", async () => {
        const recordSpy = vi.spyOn(fatalErrorStateModule, "recordFatalErrorLocally").mockResolvedValue({ ok: true });
        const router = { push: vi.fn() };
        const ok = await reportFatalErrorLocally(
            {
                kind: "backend",
                message: "fail",
                timestamp: Date.now(),
            },
            router
        );
        expect(ok).toBe(true);
        expect(router.push).toHaveBeenCalledWith({ name: "plugin-mcx-bugs" });
        recordSpy.mockRestore();
    });
});

describe("FatalErrorPage.svelte", () => {
    let routerMock;

    beforeEach(() => {
        clearFatalError();
        registerTranslator(null);
        registerFallbackMessages(fatalErrorI18n);

        routerMock = {
            push: vi.fn(),
        };

        Object.defineProperty(window, "location", {
            value: {
                reload: vi.fn(),
                hash: "",
            },
            writable: true,
        });
    });

    afterEach(() => {
        cleanup();
        clearFatalError();
        vi.clearAllMocks();
    });

    it("renders fatal error page with props", async () => {
        render(FatalErrorPage, {
            props: {
                error: {
                    kind: "backend",
                    title: "Custom Backend Crash",
                    message: "Database failed to open",
                    details: "disk full",
                    timestamp: Date.now(),
                },
                router: routerMock,
            },
        });

        expect(screen.getByText("Custom Backend Crash")).toBeTruthy();
        expect(screen.getByText("Database failed to open")).toBeTruthy();
        expect(screen.getByText("Error details")).toBeTruthy();
        expect(screen.getByText("Reload page")).toBeTruthy();
    });

    it("falls back to fatalErrorState.active when error prop is omitted", async () => {
        reportFatalError({
            kind: "frontend",
            message: "Active state error",
        });

        render(FatalErrorPage, {
            props: {
                router: routerMock,
            },
        });

        expect(screen.getByText("Fatal error")).toBeTruthy();
        expect(screen.getByText("Active state error")).toBeTruthy();
    });

    it("reloads page when reload button is clicked", async () => {
        render(FatalErrorPage, {
            props: {
                error: {
                    kind: "backend",
                    message: "reload test",
                    timestamp: Date.now(),
                },
            },
        });

        const reloadButton = screen.getByText("Reload page");
        await fireEvent.click(reloadButton);

        expect(window.location.reload).toHaveBeenCalled();
    });

    it("copies error report to clipboard when copy button is clicked", async () => {
        const copySpy = vi.spyOn(clipboardUtils, "copyTextToClipboard").mockResolvedValue(true);

        render(FatalErrorPage, {
            props: {
                error: {
                    kind: "backend",
                    message: "copy test",
                    timestamp: Date.now(),
                },
            },
        });

        const copyButton = screen.getByText("Copy details");
        await fireEvent.click(copyButton);

        await waitFor(() => {
            expect(ToastUtils.success).toHaveBeenCalledWith("Copied");
        });

        copySpy.mockRestore();
    });

    it("saves fatal error locally when report button is clicked", async () => {
        const recordSpy = vi.spyOn(fatalErrorStateModule, "recordFatalErrorLocally").mockResolvedValue({ ok: true });

        render(FatalErrorPage, {
            props: {
                error: {
                    kind: "backend",
                    message: "report test",
                    timestamp: Date.now(),
                },
                router: routerMock,
            },
        });

        const reportButton = screen.getByText("Report locally");
        await fireEvent.click(reportButton);

        await waitFor(() => {
            expect(ToastUtils.success).toHaveBeenCalledWith("Report saved");
            expect(routerMock.push).toHaveBeenCalledWith({ name: "plugin-mcx-bugs" });
        });

        recordSpy.mockRestore();
    });
});
