import { mount } from "@vue/test-utils";
import { beforeEach, describe, expect, it, vi } from "vitest";

import RNXManagerPage from "@/components/tools/RNXManagerPage.vue";
import { mountToolsPageGlobals } from "./testI18n.js";

vi.mock("@/js/ToastUtils", () => ({
    default: {
        success: vi.fn(),
        error: vi.fn(),
        warning: vi.fn(),
    },
}));

vi.mock("@/js/WebSocketConnection", () => ({
    default: {
        on: vi.fn(),
        off: vi.fn(),
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

describe("RNXManagerPage.vue", () => {
    beforeEach(() => {
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

    it("loads sessions and selects the first one", async () => {
        const wrapper = mount(RNXManagerPage, { global: mountToolsPageGlobals() });
        await vi.waitFor(() => expect(wrapper.vm.sessions.length).toBe(1));
        expect(wrapper.vm.selectedSessionId).toBe(SESSION_ID);
        expect(wrapper.text()).toContain("Ops");
    });

    it("creates a new session in connect mode", async () => {
        window.api.post.mockResolvedValueOnce({
            data: { session: makeSession({ id: "session-2", name: "Created" }) },
        });

        const wrapper = mount(RNXManagerPage, { global: mountToolsPageGlobals() });
        await vi.waitFor(() => expect(wrapper.vm.sessions.length).toBe(1));

        wrapper.vm.executeForm.name = "Created";
        wrapper.vm.executeForm.destination = "aabbccddeeff00112233445566778899";
        wrapper.vm.executeForm.command = "uname -a";
        await wrapper.vm.createExecuteSession();

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
        });
    });

    it("creates an interactive session without a remote command", async () => {
        window.api.post.mockResolvedValueOnce({
            data: { session: makeSession({ id: "session-3", name: "Interactive", mode: "interactive" }) },
        });

        const wrapper = mount(RNXManagerPage, { global: mountToolsPageGlobals() });
        await vi.waitFor(() => expect(wrapper.vm.sessions.length).toBe(1));

        wrapper.vm.executeForm.destination = "aabbccddeeff00112233445566778899";
        wrapper.vm.executeForm.interactive = true;
        wrapper.vm.executeForm.timeout = "20";
        wrapper.vm.executeForm.stdout_limit = "4096";
        await wrapper.vm.createExecuteSession();

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
        const wrapper = mount(RNXManagerPage, { global: mountToolsPageGlobals() });
        await vi.waitFor(() => expect(wrapper.vm.sessions.length).toBe(1));
        wrapper.vm.commandInput = "ls -la";
        await wrapper.vm.sendCommand();
        expect(window.api.post).toHaveBeenCalledWith(`/api/v1/rnx/sessions/${SESSION_ID}/input`, {
            text: "ls -la",
            newline: true,
        });
    });

    it("appends websocket output chunks", async () => {
        const wrapper = mount(RNXManagerPage, { global: mountToolsPageGlobals() });
        await vi.waitFor(() => expect(wrapper.vm.sessions.length).toBe(1));

        wrapper.vm.onWebsocketMessage({
            data: JSON.stringify({
                type: "rnx.output",
                session_id: SESSION_ID,
                chunk: { text: "line2\n" },
            }),
        });

        expect(wrapper.vm.outputsBySession[SESSION_ID]).toContain("line2");
    });

    it("toggles session fullscreen and closes mobile sessions drawer on narrow screens", async () => {
        const wrapper = mount(RNXManagerPage, { global: mountToolsPageGlobals() });
        await vi.waitFor(() => expect(wrapper.vm.sessions.length).toBe(1));

        wrapper.vm.isNarrowScreen = true;
        wrapper.vm.mobileSessionsOpen = true;
        wrapper.vm.toggleSessionFullscreen();
        expect(wrapper.vm.sessionFullscreen).toBe(true);
        expect(wrapper.vm.mobileSessionsOpen).toBe(false);

        wrapper.vm.toggleSessionFullscreen();
        expect(wrapper.vm.sessionFullscreen).toBe(false);
    });

    it("selectSession closes mobile sessions list on narrow screens", async () => {
        const wrapper = mount(RNXManagerPage, { global: mountToolsPageGlobals() });
        await vi.waitFor(() => expect(wrapper.vm.sessions.length).toBe(1));

        wrapper.vm.isNarrowScreen = true;
        wrapper.vm.mobileSessionsOpen = true;
        wrapper.vm.selectSession(SESSION_ID);
        expect(wrapper.vm.mobileSessionsOpen).toBe(false);
    });

    it("creates a listen session with auth enabled by default", async () => {
        window.api.post.mockResolvedValueOnce({
            data: { session: makeSession({ id: "listen-1", mode: "listen", name: "Listener" }) },
        });

        const wrapper = mount(RNXManagerPage, { global: mountToolsPageGlobals() });
        await vi.waitFor(() => expect(wrapper.vm.sessions.length).toBe(1));

        expect(wrapper.vm.listenForm.no_auth).toBe(false);
        wrapper.vm.listenForm.name = "Listener";
        await wrapper.vm.createListenSession();

        expect(window.api.post).toHaveBeenCalledWith("/api/v1/rnx/sessions", {
            name: "Listener",
            mode: "listen",
            allowed_hashes: [],
            config_path: undefined,
            no_auth: false,
            autostart: true,
        });
    });

    it("keeps longer live output when session reload returns a truncated chunk tail", async () => {
        const wrapper = mount(RNXManagerPage, { global: mountToolsPageGlobals() });
        await vi.waitFor(() => expect(wrapper.vm.sessions.length).toBe(1));

        const live = "LINE_0000\n".repeat(50) + "LINE_TAIL\n";
        wrapper.vm.outputsBySession[SESSION_ID] = live;

        wrapper.vm.ingestSession(
            makeSession({
                output_chunks: [{ seq: 99, text: "LINE_TAIL\n", ts: 2 }],
                output_text: "LINE_0400\nLINE_TAIL\n",
            })
        );

        expect(wrapper.vm.outputsBySession[SESSION_ID]).toBe(live);
    });

    it("prefers longer output_text over short output_chunks on ingest", async () => {
        const wrapper = mount(RNXManagerPage, { global: mountToolsPageGlobals() });
        await vi.waitFor(() => expect(wrapper.vm.sessions.length).toBe(1));

        const longText = "full history\n".repeat(20);
        wrapper.vm.ingestSession(
            makeSession({
                output_chunks: [{ seq: 1, text: "tail only\n", ts: 1 }],
                output_text: longText,
            })
        );

        expect(wrapper.vm.outputsBySession[SESSION_ID]).toBe(longText);
    });
});
