// SPDX-License-Identifier: 0BSD

import { render, cleanup, screen, waitFor, fireEvent } from "@testing-library/svelte";
import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import RepositoryServerPage from "@/features/repository-server/RepositoryServerPage.svelte";
import ToastUtils from "@/js/ToastUtils";
import { registerFallbackMessages, registerTranslator } from "@/js/i18n.js";
import {
    API_REPOSITORY_SERVER_HTTP_START,
    API_REPOSITORY_SERVER_LIST,
    API_REPOSITORY_SERVER_STATUS,
} from "@/features/repository-server/lib/constants.ts";

vi.mock("@/js/ToastUtils", () => ({
    default: {
        success: vi.fn(),
        error: vi.fn(),
        info: vi.fn(),
        warning: vi.fn(),
    },
}));

vi.mock("@/js/DialogUtils", () => ({
    default: {
        confirm: vi.fn().mockResolvedValue(true),
        alert: vi.fn(),
    },
}));

describe("RepositoryServerPage.svelte", () => {
    let apiMock;

    beforeEach(() => {
        registerTranslator(null);
        registerFallbackMessages({
            common: { loading: "Loading" },
            app: { tools: "Tools" },
            tools: {
                back_to_tools: "Back",
                repository_server: {
                    title: "Repository Server",
                    description: "Local wheel shelf",
                    http_heading: "HTTP",
                    host_label: "Host",
                    port_label: "Port",
                    start_http: "Start",
                    stop_http: "Stop",
                    restart_http: "Restart",
                    stop_before_edit: "Stop first",
                    already_running: "Already running",
                    not_running: "Not running",
                    http_listen_label: "Listening:",
                    open_http: "Open",
                    http_started: "HTTP started",
                    http_stopped: "HTTP stopped",
                    http_restarted: "HTTP restarted",
                    http_err_generic: "HTTP error",
                    http_err_invalid_port: "invalid port",
                    upload_heading: "Upload",
                    choose_file: "Choose file",
                    files_heading: "Files",
                    col_name: "Name",
                    col_source: "Source",
                    col_size: "Size",
                    empty: "No files",
                    delete: "Delete",
                    load_failed: "load failed",
                },
            },
        });
        apiMock = {
            get: vi.fn(async (url) => {
                if (url === API_REPOSITORY_SERVER_STATUS) {
                    return {
                        data: {
                            http: {
                                running: false,
                                host: "127.0.0.1",
                                port: 8787,
                                url: null,
                            },
                        },
                    };
                }
                if (url === API_REPOSITORY_SERVER_LIST) {
                    return {
                        data: [{ name: "demo.whl", source: "upload", bytes: 1024 }],
                    };
                }
                return { data: {} };
            }),
            post: vi.fn().mockResolvedValue({ data: { ok: true } }),
            delete: vi.fn().mockResolvedValue({ data: { ok: true } }),
        };
        window.api = apiMock;
    });

    afterEach(() => {
        cleanup();
        delete window.api;
        vi.clearAllMocks();
    });

    it("loads status and package list on mount", async () => {
        render(RepositoryServerPage);
        await waitFor(() => {
            expect(apiMock.get).toHaveBeenCalledWith(API_REPOSITORY_SERVER_STATUS);
            expect(apiMock.get).toHaveBeenCalledWith(API_REPOSITORY_SERVER_LIST);
            expect(screen.getByText("Repository Server")).toBeTruthy();
            expect(screen.getByText("demo.whl")).toBeTruthy();
        });
    });

    it("starts HTTP server via API and toasts success", async () => {
        render(RepositoryServerPage);
        await waitFor(() => expect(screen.getByText("Start")).toBeTruthy());
        await fireEvent.click(screen.getByText("Start"));
        await waitFor(() => {
            expect(apiMock.post).toHaveBeenCalledWith(
                API_REPOSITORY_SERVER_HTTP_START,
                expect.objectContaining({ host: "127.0.0.1" })
            );
            expect(ToastUtils.success).toHaveBeenCalledWith("HTTP started");
        });
    });
});
