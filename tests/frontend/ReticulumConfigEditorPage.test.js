// SPDX-License-Identifier: 0BSD

import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { render, cleanup, fireEvent, waitFor, screen } from "@testing-library/svelte";
import ReticulumConfigEditorPage from "@/features/reticulum-config-editor/ReticulumConfigEditorPage.svelte";
import DialogUtils from "@/js/DialogUtils.js";
import GlobalState from "@/js/GlobalState.js";
import { registerFallbackMessages, registerTranslator } from "@/js/i18n.js";
import {
    extractErrorMessage,
    insertTabAtSelection,
    isConfigDirty,
    shouldShowRestartReminder,
} from "@/features/reticulum-config-editor/lib/configFormat.ts";
import {
    RETICULUM_CONFIG_RAW_ENDPOINT,
    RETICULUM_CONFIG_RESET_ENDPOINT,
    RETICULUM_RELOAD_ENDPOINT,
} from "@/features/reticulum-config-editor/lib/constants.ts";
import { registerReticulumConfigEditorFeature } from "@/features/reticulum-config-editor/index.ts";
import { clearRoutes, listRoutes } from "@/js/registries/routeRegistry.js";
import { clearFeatureIds, listFeatureIds } from "@/js/registries/featureRegistry.js";

vi.mock("@/js/DialogUtils", () => ({
    default: {
        confirm: vi.fn(),
        alert: vi.fn(),
        prompt: vi.fn(),
    },
}));

vi.mock("@/js/ToastUtils", () => ({
    default: {
        success: vi.fn(),
        error: vi.fn(),
        warning: vi.fn(),
        info: vi.fn(),
        loading: vi.fn(),
        dismiss: vi.fn(),
    },
}));

const SAMPLE_CONFIG =
    "[reticulum]\n  enable_transport = False\n\n[interfaces]\n  [[Default Interface]]\n    type = AutoInterface\n";
const DEFAULT_CONFIG =
    "[reticulum]\n  enable_transport = False\n\n[interfaces]\n  [[Default Interface]]\n    type = AutoInterface\n    enabled = true\n";
const CONFIG_PATH = "/tmp/.reticulum/config";

describe("reticulum-config-editor lib helpers", () => {
    it("inserts tab at selection position", () => {
        const text = "helloworld";
        const result = insertTabAtSelection(text, 5, 5, "  ");
        expect(result.content).toBe("hello  world");
        expect(result.newCursor).toBe(7);
    });

    it("checks dirty state accurately", () => {
        expect(isConfigDirty("abc", "abc")).toBe(false);
        expect(isConfigDirty("abc", "abd")).toBe(true);
    });

    it("evaluates restart reminder condition", () => {
        expect(shouldShowRestartReminder(false, false)).toBe(false);
        expect(shouldShowRestartReminder(true, false)).toBe(true);
        expect(shouldShowRestartReminder(false, true)).toBe(true);
        expect(shouldShowRestartReminder(true, true)).toBe(true);
    });

    it("extracts error message from various error formats", () => {
        expect(extractErrorMessage({ response: { data: { error: "Custom err" } } }, "fallback")).toBe("Custom err");
        expect(extractErrorMessage({ message: "Network fail" }, "fallback")).toBe("Network fail");
        expect(extractErrorMessage("String error", "fallback")).toBe("String error");
        expect(extractErrorMessage(null, "fallback")).toBe("fallback");
    });
});

describe("registerReticulumConfigEditorFeature", () => {
    beforeEach(() => {
        clearRoutes();
        clearFeatureIds();
    });

    afterEach(() => {
        clearRoutes();
        clearFeatureIds();
    });

    it("registers reticulum-config-editor route correctly", () => {
        registerReticulumConfigEditorFeature();
        expect(listFeatureIds()).toContain("reticulum-config-editor");
        const route = listRoutes().find((r) => r.name === "reticulum-config-editor");
        expect(route).toBeTruthy();
        expect(route?.path).toBe("/tools/reticulum-config-editor");
        expect(route?.mount).toBe("svelte");
    });
});

describe("ReticulumConfigEditorPage.svelte", () => {
    let axiosMock;

    beforeEach(() => {
        vi.clearAllMocks();
        axiosMock = {
            get: vi.fn(),
            put: vi.fn(),
            post: vi.fn(),
        };
        window.api = axiosMock;

        registerTranslator(null);
        registerFallbackMessages({
            app: {
                tools: "Tools",
                reloading_rns: "Reloading RNS...",
            },
            tools: {
                back_to_tools: "Back",
                reticulum_config_editor: {
                    title: "Reticulum Config Editor",
                    description: "Edit raw reticulum configuration file",
                    reload: "Reload",
                    restore_defaults: "Restore Defaults",
                    discard: "Discard Changes",
                    save: "Save",
                    saving: "Saving...",
                    saved: "Configuration saved",
                    restart_required: "Restart Required",
                    restart_description: "Restart RNS to apply interface changes",
                    restart_now: "Restart Now",
                    restart_done: "Restart completed",
                    versions: "Versions",
                    versions_empty: "No saved versions yet.",
                    preview: "Preview",
                    restore_version: "Restore",
                    confirm_restore_version: "Restore this version?",
                    failed_versions: "Failed to load versions",
                    info: "Direct file editing",
                    unsaved: "Unsaved Changes",
                    loading: "Loading config...",
                    failed_load: "Failed to load config",
                    failed_save: "Failed to save config",
                    failed_restore: "Failed to restore defaults",
                    failed_restart: "Failed to restart RNS",
                    confirm_restore: "Are you sure you want to restore defaults?",
                    restoring: "Restoring...",
                    restored: "Restored to defaults",
                },
            },
        });

        axiosMock.get.mockResolvedValue({
            data: { content: SAMPLE_CONFIG, path: CONFIG_PATH },
        });
        axiosMock.put.mockResolvedValue({
            data: { message: "Reticulum config saved", path: CONFIG_PATH },
        });
        axiosMock.post.mockImplementation((url) => {
            if (url === RETICULUM_CONFIG_RESET_ENDPOINT) {
                return Promise.resolve({
                    data: {
                        message: "Reticulum config restored to defaults",
                        content: DEFAULT_CONFIG,
                        path: CONFIG_PATH,
                    },
                });
            }
            if (url === RETICULUM_RELOAD_ENDPOINT) {
                return Promise.resolve({
                    data: { message: "Reticulum reloaded successfully" },
                });
            }
            return Promise.resolve({ data: {} });
        });

        GlobalState.hasPendingInterfaceChanges = false;
        if (!GlobalState.modifiedInterfaceNames) {
            GlobalState.modifiedInterfaceNames = new Set();
        }
        GlobalState.modifiedInterfaceNames.clear();
    });

    afterEach(() => {
        cleanup();
        delete window.api;
    });

    it("loads current config on mount and displays path", async () => {
        render(ReticulumConfigEditorPage);
        expect(screen.getByText("Reticulum Config Editor")).toBeTruthy();

        await waitFor(() => {
            expect(axiosMock.get).toHaveBeenCalledWith(RETICULUM_CONFIG_RAW_ENDPOINT);
        });

        expect(await screen.findByText(CONFIG_PATH)).toBeTruthy();
        const textarea = screen.getByRole("textbox");
        expect(textarea.value).toBe(SAMPLE_CONFIG);
    });

    it("marks the editor as dirty and saves config", async () => {
        render(ReticulumConfigEditorPage);
        await waitFor(() => {
            expect(axiosMock.get).toHaveBeenCalledWith(RETICULUM_CONFIG_RAW_ENDPOINT);
        });

        const textarea = screen.getByRole("textbox");
        const newContent = SAMPLE_CONFIG + "\n# my edit\n";
        await fireEvent.input(textarea, { target: { value: newContent } });

        expect(screen.getByText("Unsaved Changes")).toBeTruthy();

        const saveButton = screen.getByText("Save");
        await fireEvent.click(saveButton);

        await waitFor(() => {
            expect(axiosMock.put).toHaveBeenCalledWith(RETICULUM_CONFIG_RAW_ENDPOINT, {
                content: newContent,
            });
        });

        expect(GlobalState.hasPendingInterfaceChanges).toBe(true);
        expect(await screen.findByText("Restart Required")).toBeTruthy();
    });

    it("restores defaults after confirmation", async () => {
        DialogUtils.confirm.mockResolvedValue(true);
        render(ReticulumConfigEditorPage);
        await waitFor(() => {
            expect(axiosMock.get).toHaveBeenCalledWith(RETICULUM_CONFIG_RAW_ENDPOINT);
        });

        const restoreBtn = screen.getByText("Restore Defaults");
        await fireEvent.click(restoreBtn);

        await waitFor(() => {
            expect(DialogUtils.confirm).toHaveBeenCalled();
            expect(axiosMock.post).toHaveBeenCalledWith(RETICULUM_CONFIG_RESET_ENDPOINT);
        });

        const textarea = screen.getByRole("textbox");
        expect(textarea.value).toBe(DEFAULT_CONFIG);
        expect(GlobalState.hasPendingInterfaceChanges).toBe(true);
    });

    it("does not restore defaults if canceled", async () => {
        DialogUtils.confirm.mockResolvedValue(false);
        render(ReticulumConfigEditorPage);
        await waitFor(() => {
            expect(axiosMock.get).toHaveBeenCalledWith(RETICULUM_CONFIG_RAW_ENDPOINT);
        });

        const restoreBtn = screen.getByText("Restore Defaults");
        await fireEvent.click(restoreBtn);

        expect(DialogUtils.confirm).toHaveBeenCalled();
        expect(axiosMock.post).not.toHaveBeenCalledWith(RETICULUM_CONFIG_RESET_ENDPOINT);
    });

    it("reloads RNS and clears restart banner", async () => {
        render(ReticulumConfigEditorPage);
        await waitFor(() => {
            expect(axiosMock.get).toHaveBeenCalledWith(RETICULUM_CONFIG_RAW_ENDPOINT);
        });

        const textarea = screen.getByRole("textbox");
        await fireEvent.input(textarea, { target: { value: SAMPLE_CONFIG + "\n# edit" } });
        const saveButton = screen.getByText("Save");
        await fireEvent.click(saveButton);

        await waitFor(() => {
            expect(screen.getByText("Restart Now")).toBeTruthy();
        });

        const restartBtn = screen.getByText("Restart Now");
        await fireEvent.click(restartBtn);

        await waitFor(() => {
            expect(axiosMock.post).toHaveBeenCalledWith(RETICULUM_RELOAD_ENDPOINT);
        });
        expect(GlobalState.hasPendingInterfaceChanges).toBe(false);
    });

    it("discards unsaved changes back to original content", async () => {
        render(ReticulumConfigEditorPage);
        await waitFor(() => {
            expect(axiosMock.get).toHaveBeenCalledWith(RETICULUM_CONFIG_RAW_ENDPOINT);
        });

        const textarea = screen.getByRole("textbox");
        await fireEvent.input(textarea, { target: { value: "# altered" } });
        expect(screen.getByText("Unsaved Changes")).toBeTruthy();

        const discardBtn = screen.getByText("Discard Changes");
        await fireEvent.click(discardBtn);

        expect(textarea.value).toBe(SAMPLE_CONFIG);
        expect(screen.queryByText("Unsaved Changes")).toBeNull();
    });

    it("loads versions when the versions panel is toggled", async () => {
        axiosMock.get.mockImplementation((url) => {
            if (url === "/api/v1/reticulum/config/versions") {
                return Promise.resolve({
                    data: {
                        versions: [
                            {
                                id: "20250101T000000-abcdef12",
                                created_at: "2025-01-01T00:00:00Z",
                                label: "before save",
                                size: 120,
                            },
                        ],
                    },
                });
            }
            return Promise.resolve({ data: { content: SAMPLE_CONFIG, path: CONFIG_PATH } });
        });
        render(ReticulumConfigEditorPage);
        await waitFor(() => {
            expect(axiosMock.get).toHaveBeenCalledWith(RETICULUM_CONFIG_RAW_ENDPOINT);
        });

        expect(screen.queryByText("before save")).toBeNull();
        await fireEvent.click(screen.getByText("Versions"));

        await waitFor(() => {
            expect(axiosMock.get).toHaveBeenCalledWith("/api/v1/reticulum/config/versions");
        });
        expect(await screen.findByText("before save")).toBeTruthy();
    });

    it("previews a version into the editor without saving", async () => {
        axiosMock.get.mockImplementation((url) => {
            if (url === "/api/v1/reticulum/config/versions") {
                return Promise.resolve({
                    data: { versions: [{ id: "v1", created_at: "", label: "x", size: 1 }] },
                });
            }
            if (url === "/api/v1/reticulum/config/versions/v1") {
                return Promise.resolve({ data: { version: { content: DEFAULT_CONFIG } } });
            }
            return Promise.resolve({ data: { content: SAMPLE_CONFIG, path: CONFIG_PATH } });
        });
        render(ReticulumConfigEditorPage);
        await waitFor(() => {
            expect(axiosMock.get).toHaveBeenCalledWith(RETICULUM_CONFIG_RAW_ENDPOINT);
        });

        await fireEvent.click(screen.getByText("Versions"));
        await screen.findByText("x");
        await fireEvent.click(screen.getByText("Preview"));

        await waitFor(() => {
            expect(axiosMock.get).toHaveBeenCalledWith("/api/v1/reticulum/config/versions/v1");
        });
        const textarea = screen.getByRole("textbox");
        expect(textarea.value).toBe(DEFAULT_CONFIG);
        expect(screen.getByText("Unsaved Changes")).toBeTruthy();
        expect(axiosMock.put).not.toHaveBeenCalled();
    });

    it("restores a version after confirmation and marks restart pending", async () => {
        DialogUtils.confirm.mockResolvedValue(true);
        axiosMock.get.mockImplementation((url) => {
            if (url === "/api/v1/reticulum/config/versions") {
                return Promise.resolve({
                    data: { versions: [{ id: "v1", created_at: "", label: "x", size: 1 }] },
                });
            }
            return Promise.resolve({ data: { content: SAMPLE_CONFIG, path: CONFIG_PATH } });
        });
        axiosMock.post.mockImplementation((url) => {
            if (url === "/api/v1/reticulum/config/versions/v1/restore") {
                return Promise.resolve({
                    data: { message: "Reticulum config restored", content: DEFAULT_CONFIG, path: CONFIG_PATH },
                });
            }
            return Promise.resolve({ data: {} });
        });
        render(ReticulumConfigEditorPage);
        await waitFor(() => {
            expect(axiosMock.get).toHaveBeenCalledWith(RETICULUM_CONFIG_RAW_ENDPOINT);
        });

        await fireEvent.click(screen.getByText("Versions"));
        await screen.findByText("x");
        await fireEvent.click(screen.getByText("Restore"));

        await waitFor(() => {
            expect(axiosMock.post).toHaveBeenCalledWith("/api/v1/reticulum/config/versions/v1/restore");
        });
        expect(DialogUtils.confirm).toHaveBeenCalled();
        const textarea = screen.getByRole("textbox");
        expect(textarea.value).toBe(DEFAULT_CONFIG);
        expect(screen.queryByText("Unsaved Changes")).toBeNull();
        expect(await screen.findByText("Restart Required")).toBeTruthy();
        expect(GlobalState.hasPendingInterfaceChanges).toBe(true);
    });

    it("does not restore a version when the user cancels", async () => {
        DialogUtils.confirm.mockResolvedValue(false);
        axiosMock.get.mockImplementation((url) => {
            if (url === "/api/v1/reticulum/config/versions") {
                return Promise.resolve({
                    data: { versions: [{ id: "v1", created_at: "", label: "x", size: 1 }] },
                });
            }
            return Promise.resolve({ data: { content: SAMPLE_CONFIG, path: CONFIG_PATH } });
        });
        render(ReticulumConfigEditorPage);
        await waitFor(() => {
            expect(axiosMock.get).toHaveBeenCalledWith(RETICULUM_CONFIG_RAW_ENDPOINT);
        });

        await fireEvent.click(screen.getByText("Versions"));
        await screen.findByText("x");
        await fireEvent.click(screen.getByText("Restore"));

        await waitFor(() => {
            expect(DialogUtils.confirm).toHaveBeenCalled();
        });
        expect(axiosMock.post).not.toHaveBeenCalledWith("/api/v1/reticulum/config/versions/v1/restore");
        const textarea = screen.getByRole("textbox");
        expect(textarea.value).toBe(SAMPLE_CONFIG);
    });
});
