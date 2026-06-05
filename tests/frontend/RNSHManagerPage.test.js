import { mount } from "@vue/test-utils";
import { beforeEach, describe, expect, it, vi } from "vitest";

import RNSHManagerPage from "@/components/tools/RNSHManagerPage.vue";
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

describe("RNSHManagerPage.vue", () => {
    beforeEach(() => {
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

    it("loads sessions and selects the first one", async () => {
        const wrapper = mount(RNSHManagerPage, { global: mountToolsPageGlobals() });
        await vi.waitFor(() => expect(wrapper.vm.sessions.length).toBe(1));
        expect(wrapper.vm.selectedSessionId).toBe(SESSION_ID);
        expect(wrapper.text()).toContain("Ops");
    });

    it("creates a new session in connect mode", async () => {
        window.api.post.mockResolvedValueOnce({
            data: { session: makeSession({ id: "session-2", name: "Created" }) },
        });

        const wrapper = mount(RNSHManagerPage, { global: mountToolsPageGlobals() });
        await vi.waitFor(() => expect(wrapper.vm.sessions.length).toBe(1));

        wrapper.vm.connectForm.name = "Created";
        wrapper.vm.connectForm.destination = "aabbccddeeff00112233445566778899";
        await wrapper.vm.createConnectSession();

        expect(window.api.post).toHaveBeenCalledWith("/api/v1/rnsh/sessions", {
            name: "Created",
            mode: "connect",
            mirror: false,
            no_id: false,
            autostart: true,
            destination: "aabbccddeeff00112233445566778899",
            remote_command: undefined,
        });
    });

    it("sends command input to selected session", async () => {
        const wrapper = mount(RNSHManagerPage, { global: mountToolsPageGlobals() });
        await vi.waitFor(() => expect(wrapper.vm.sessions.length).toBe(1));
        wrapper.vm.commandInput = "ls -la";
        await wrapper.vm.sendCommand();
        expect(window.api.post).toHaveBeenCalledWith(`/api/v1/rnsh/sessions/${SESSION_ID}/input`, {
            text: "ls -la",
            newline: true,
        });
    });

    it("appends websocket output chunks", async () => {
        const wrapper = mount(RNSHManagerPage, { global: mountToolsPageGlobals() });
        await vi.waitFor(() => expect(wrapper.vm.sessions.length).toBe(1));

        wrapper.vm.onWebsocketMessage({
            data: JSON.stringify({
                type: "rnsh.output",
                session_id: SESSION_ID,
                chunk: { text: "line2\n" },
            }),
        });

        expect(wrapper.vm.outputsBySession[SESSION_ID]).toContain("line2");
    });

    it("toggles session fullscreen and closes mobile sessions drawer on narrow screens", async () => {
        const wrapper = mount(RNSHManagerPage, { global: mountToolsPageGlobals() });
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
        const wrapper = mount(RNSHManagerPage, { global: mountToolsPageGlobals() });
        await vi.waitFor(() => expect(wrapper.vm.sessions.length).toBe(1));

        wrapper.vm.isNarrowScreen = true;
        wrapper.vm.mobileSessionsOpen = true;
        wrapper.vm.selectSession(SESSION_ID);
        expect(wrapper.vm.mobileSessionsOpen).toBe(false);
    });
});
