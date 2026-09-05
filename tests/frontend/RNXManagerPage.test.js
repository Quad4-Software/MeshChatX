// SPDX-License-Identifier: 0BSD

import { render, cleanup, screen } from "@testing-library/svelte";
import { beforeEach, afterEach, describe, expect, it, vi } from "vitest";

import RNXPage from "@/features/rnx/RNXPage.svelte";
import { registerFallbackMessages, registerTranslator } from "@/js/i18n.js";
import en from "@/locales/en.json";
import {
    buildRnxExecutePayload,
    buildRnxListenPayload,
    createRnxSession,
    sendRnxSessionInput,
} from "@/features/rnx/lib/rnxApi.ts";
import {
    appendSessionOutput,
    ingestSessionOutput,
} from "@/features/remote-shell/lib/sessionOutput.ts";

vi.mock("@/js/ToastUtils", () => ({
    default: {
        success: vi.fn(),
        error: vi.fn(),
        warning: vi.fn(),
    },
}));

vi.mock("@/js/browserLayoutStore", () => ({
    loadRnxLayout: vi.fn(() => null),
    saveRnxLayout: vi.fn(),
}));

const SESSION_ID = "session-1";

function makeSession(overrides = {}) {
    return {
        id: SESSION_ID,
        name: "Ops",
        mode: "execute",
        destination: "00112233445566778899aabbccddeeff",
        status: "running",
        output_chunks: [{ seq: 1, text: "ready\n", ts: 1 }],
        output_text: "ready\n",
        ...overrides,
    };
}

describe("RNXPage.svelte", () => {
    beforeEach(() => {
        registerTranslator(null);
        registerFallbackMessages(en);
        window.api = {
            get: vi.fn(async (url) => {
                if (url === "/api/v1/rnx/sessions") {
                    return { data: { sessions: [makeSession()] } };
                }
                return { data: {} };
            }),
            post: vi.fn(async () => ({ data: {} })),
            delete: vi.fn(async () => ({ data: {} })),
        };
    });

    afterEach(() => {
        cleanup();
        delete window.api;
        vi.clearAllMocks();
    });

    it("loads sessions and selects the first one", async () => {
        render(RNXPage);
        expect((await screen.findAllByText("Ops")).length).toBeGreaterThan(0);
    });

    it("creates a new session in execute mode", async () => {
        window.api.post.mockResolvedValueOnce({
            data: { session: makeSession({ id: "session-2", name: "Created" }) },
        });

        const payload = buildRnxExecutePayload({
            name: "Created",
            destination: "aabbccddeeff00112233445566778899",
            command: "uname -a",
            mirror: false,
            no_id: false,
            detailed: true,
            timeout: undefined,
            result_timeout: undefined,
            stdout_limit: undefined,
            stderr_limit: undefined,
            config_path: "",
        });
        await createRnxSession(payload);

        expect(window.api.post).toHaveBeenCalledWith("/api/v1/rnx/sessions", {
            name: "Created",
            mode: "execute",
            mirror: false,
            no_id: false,
            detailed: true,
            timeout: undefined,
            result_timeout: undefined,
            stdout_limit: undefined,
            stderr_limit: undefined,
            autostart: true,
            destination: "aabbccddeeff00112233445566778899",
            remote_command: "uname -a",
            config_path: undefined,
        });
    });

    it("creates an interactive session without a remote command", async () => {
        window.api.post.mockResolvedValueOnce({
            data: { session: makeSession({ id: "session-3", name: "Interactive", mode: "interactive" }) },
        });

        const payload = buildRnxExecutePayload({
            name: "",
            destination: "aabbccddeeff00112233445566778899",
            interactive: true,
            timeout: "20",
            stdout_limit: "4096",
            mirror: false,
            no_id: false,
            detailed: true,
            result_timeout: undefined,
            stderr_limit: undefined,
            config_path: "",
        });
        await createRnxSession(payload);

        expect(window.api.post).toHaveBeenCalledWith("/api/v1/rnx/sessions", {
            name: undefined,
            mode: "interactive",
            mirror: false,
            no_id: false,
            detailed: true,
            timeout: "20",
            result_timeout: undefined,
            stdout_limit: "4096",
            stderr_limit: undefined,
            autostart: true,
            destination: "aabbccddeeff00112233445566778899",
            remote_command: undefined,
            config_path: undefined,
        });
    });

    it("sends command input to selected session", async () => {
        await sendRnxSessionInput(SESSION_ID, "ls -la");
        expect(window.api.post).toHaveBeenCalledWith(`/api/v1/rnx/sessions/${SESSION_ID}/input`, {
            text: "ls -la",
            newline: true,
        });
    });

    it("appends websocket output chunks", () => {
        const outputs = {};
        appendSessionOutput(SESSION_ID, "line2\n", outputs);
        expect(outputs[SESSION_ID]).toContain("line2");
    });

    it("creates a listen session with auth enabled by default", async () => {
        window.api.post.mockResolvedValueOnce({
            data: { session: makeSession({ id: "listen-1", mode: "listen", name: "Listener" }) },
        });

        const payload = buildRnxListenPayload({
            name: "Listener",
            command: "",
            config_path: "",
            allowed_hashes_text: "",
            no_auth: false,
        });
        expect(payload.no_auth).toBe(false);
        await createRnxSession(payload);

        expect(window.api.post).toHaveBeenCalledWith("/api/v1/rnx/sessions", {
            name: "Listener",
            mode: "listen",
            allowed_hashes: [],
            config_path: undefined,
            no_auth: false,
            autostart: true,
        });
    });

    it("keeps longer live output when session reload returns a truncated chunk tail", () => {
        const live = "LINE_0000\n".repeat(50) + "LINE_TAIL\n";
        const outputs = { [SESSION_ID]: live };

        ingestSessionOutput(
            makeSession({
                output_chunks: [{ seq: 99, text: "LINE_TAIL\n", ts: 2 }],
                output_text: "LINE_0400\nLINE_TAIL\n",
            }),
            outputs
        );

        expect(outputs[SESSION_ID]).toBe(live);
    });

    it("prefers longer output_text over short output_chunks on ingest", () => {
        const longText = "full history\n".repeat(20);
        const outputs = {};
        ingestSessionOutput(
            makeSession({
                output_chunks: [{ seq: 1, text: "tail only\n", ts: 1 }],
                output_text: longText,
            }),
            outputs
        );

        expect(outputs[SESSION_ID]).toBe(longText);
    });
});
