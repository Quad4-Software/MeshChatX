// SPDX-License-Identifier: 0BSD

import { render, cleanup, screen } from "@testing-library/svelte";
import { beforeEach, afterEach, describe, expect, it, vi } from "vitest";

import RNSHPage from "@/features/rnsh/RNSHPage.svelte";
import { registerFallbackMessages, registerTranslator } from "@/js/i18n.js";
import en from "@/locales/en.json";
import {
    buildRnshConnectPayload,
    buildRnshListenPayload,
    createRnshSession,
    sendRnshSessionInput,
} from "@/features/rnsh/lib/rnshApi.ts";
import { appendSessionOutput, ingestSessionOutput } from "@/features/remote-shell/lib/sessionOutput.ts";

vi.mock("@/js/ToastUtils", () => ({
    default: {
        success: vi.fn(),
        error: vi.fn(),
        warning: vi.fn(),
    },
}));

vi.mock("@/js/browserLayoutStore", () => ({
    loadRnshLayout: vi.fn(() => null),
    saveRnshLayout: vi.fn(),
}));

const SESSION_ID = "session-1";

function makeSession(overrides = {}) {
    return {
        id: SESSION_ID,
        name: "Ops",
        mode: "connect",
        destination: "00112233445566778899aabbccddeeff",
        status: "running",
        output_chunks: [{ seq: 1, text: "ready\n", ts: 1 }],
        output_text: "ready\n",
        ...overrides,
    };
}

describe("RNSHPage.svelte", () => {
    beforeEach(() => {
        registerTranslator(null);
        registerFallbackMessages(en);
        window.api = {
            get: vi.fn(async (url) => {
                if (url === "/api/v1/rnsh/sessions") {
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
        render(RNSHPage);
        await vi.waitFor(() => {
            expect(window.api.get).toHaveBeenCalledWith("/api/v1/rnsh/sessions");
        });
        expect((await screen.findAllByText("Ops")).length).toBeGreaterThan(0);
    });

    it("creates a new session in connect mode", async () => {
        window.api.post.mockResolvedValueOnce({
            data: { session: makeSession({ id: "session-2", name: "Created" }) },
        });

        const payload = buildRnshConnectPayload({
            name: "Created",
            destination: "aabbccddeeff00112233445566778899",
            command: "",
            config_path: "",
            mirror: false,
            no_id: false,
        });
        await createRnshSession(payload);

        expect(window.api.post).toHaveBeenCalledWith("/api/v1/rnsh/sessions", {
            name: "Created",
            mode: "connect",
            mirror: false,
            no_id: false,
            autostart: true,
            destination: "aabbccddeeff00112233445566778899",
            remote_command: undefined,
            config_path: undefined,
        });
    });

    it("sends command input to selected session", async () => {
        await sendRnshSessionInput(SESSION_ID, "ls -la");
        expect(window.api.post).toHaveBeenCalledWith(`/api/v1/rnsh/sessions/${SESSION_ID}/input`, {
            text: "ls -la",
            newline: true,
        });
    });

    it("appends websocket output chunks", () => {
        const outputs = {};
        appendSessionOutput(SESSION_ID, "line2\n", outputs);
        expect(outputs[SESSION_ID]).toContain("line2");
    });

    it("creates a listen session with no_auth disabled by default", async () => {
        window.api.post.mockResolvedValueOnce({
            data: { session: makeSession({ id: "listen-1", mode: "listen", name: "Listener" }) },
        });

        const payload = buildRnshListenPayload({
            name: "Listener",
            command: "",
            config_path: "",
            allowed_hashes_text: "",
            no_auth: false,
        });
        expect(payload.no_auth).toBe(false);
        await createRnshSession(payload);

        expect(window.api.post).toHaveBeenCalledWith("/api/v1/rnsh/sessions", {
            name: "Listener",
            mode: "listen",
            allowed_hashes: [],
            default_command: undefined,
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
