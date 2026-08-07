import { mount } from "@vue/test-utils";
import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import PageNodesPage from "@/components/page-nodes/PageNodesPage.vue";
import ToastUtils from "@/js/ToastUtils";
import { mountToolsPageGlobals } from "./testI18n.js";

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

const NODE_ID = "node-1";

function makeNode(overrides = {}) {
    return {
        node_id: NODE_ID,
        name: "My Server",
        running: true,
        destination_hash: "aabbccddeeff00112233445566778899",
        identity_hash: "1122334455667788",
        active_links: 0,
        unique_connections: 0,
        uptime_seconds: 60,
        pages: ["index.mu"],
        files: [],
        stats: { pages_served: 0, files_served: 0, links_established: 0 },
        announce_enabled: true,
        announce_interval_seconds: 900,
        last_announced_at: null,
        ...overrides,
    };
}

describe("PageNodesPage.vue", () => {
    let axiosMock;

    beforeEach(() => {
        axiosMock = {
            get: vi.fn().mockResolvedValue({ data: [makeNode()] }),
            post: vi.fn().mockResolvedValue({ data: {} }),
            patch: vi.fn().mockResolvedValue({ data: makeNode() }),
            delete: vi.fn().mockResolvedValue({ data: {} }),
        };
        window.api = axiosMock;
    });

    afterEach(() => {
        delete window.api;
    });

    const mountPage = () => mount(PageNodesPage, { global: mountToolsPageGlobals() });

    it("loads and renders mesh servers", async () => {
        const wrapper = mountPage();
        await vi.waitFor(() => expect(wrapper.vm.nodes.length).toBe(1));
        expect(wrapper.text()).toContain("My Server");
    });

    it("shows an auto-announce off badge when announce is disabled", async () => {
        axiosMock.get.mockResolvedValue({ data: [makeNode({ announce_enabled: false })] });
        const wrapper = mountPage();
        await vi.waitFor(() => expect(wrapper.vm.nodes.length).toBe(1));
        expect(wrapper.text()).toContain("Auto-announce off");
    });

    it("does not show the auto-announce off badge when announce is enabled", async () => {
        const wrapper = mountPage();
        await vi.waitFor(() => expect(wrapper.vm.nodes.length).toBe(1));
        expect(wrapper.text()).not.toContain("Auto-announce off");
    });

    it("shows never announced when a node has not announced yet", async () => {
        const wrapper = mountPage();
        await vi.waitFor(() => expect(wrapper.vm.nodes.length).toBe(1));
        expect(wrapper.text()).toContain("Never announced");
    });

    it("shows last announced time when a node has announced", async () => {
        const lastAnnouncedAt = Date.now() / 1000 - 120;
        axiosMock.get.mockResolvedValue({ data: [makeNode({ last_announced_at: lastAnnouncedAt })] });
        const wrapper = mountPage();
        await vi.waitFor(() => expect(wrapper.vm.nodes.length).toBe(1));
        expect(wrapper.text()).toContain("Last announced");
    });

    it("initializes the announce settings form when selecting a node", async () => {
        const wrapper = mountPage();
        await vi.waitFor(() => expect(wrapper.vm.nodes.length).toBe(1));
        wrapper.vm.selectNode(wrapper.vm.nodes[0]);
        expect(wrapper.vm.announceSettingsForm).toEqual({
            announce_enabled: true,
            announce_interval_seconds: 900,
        });
    });

    it("defaults the announce settings form for a disabled node", async () => {
        axiosMock.get.mockResolvedValue({
            data: [makeNode({ announce_enabled: false, announce_interval_seconds: 300 })],
        });
        const wrapper = mountPage();
        await vi.waitFor(() => expect(wrapper.vm.nodes.length).toBe(1));
        wrapper.vm.selectNode(wrapper.vm.nodes[0]);
        expect(wrapper.vm.announceSettingsForm).toEqual({
            announce_enabled: false,
            announce_interval_seconds: 300,
        });
    });

    it("converts the announce interval to and from minutes", async () => {
        const wrapper = mountPage();
        await vi.waitFor(() => expect(wrapper.vm.nodes.length).toBe(1));
        wrapper.vm.selectNode(wrapper.vm.nodes[0]);
        expect(wrapper.vm.announceIntervalMinutes).toBe(15);

        wrapper.vm.announceIntervalMinutes = 30;
        expect(wrapper.vm.announceSettingsForm.announce_interval_seconds).toBe(1800);
    });

    it("clamps the announce interval minutes to the supported range", async () => {
        const wrapper = mountPage();
        await vi.waitFor(() => expect(wrapper.vm.nodes.length).toBe(1));
        wrapper.vm.selectNode(wrapper.vm.nodes[0]);

        wrapper.vm.announceIntervalMinutes = 0;
        expect(wrapper.vm.announceSettingsForm.announce_interval_seconds).toBe(0);

        wrapper.vm.announceIntervalMinutes = -5;
        expect(wrapper.vm.announceSettingsForm.announce_interval_seconds).toBe(60);

        wrapper.vm.announceIntervalMinutes = 999999;
        expect(wrapper.vm.announceSettingsForm.announce_interval_seconds).toBe(1440 * 60);
    });

    it("saves announce settings via the PATCH API", async () => {
        const wrapper = mountPage();
        await vi.waitFor(() => expect(wrapper.vm.nodes.length).toBe(1));
        wrapper.vm.selectNode(wrapper.vm.nodes[0]);

        wrapper.vm.announceSettingsForm = {
            announce_enabled: false,
            announce_interval_seconds: 300,
        };
        await wrapper.vm.saveAnnounceSettings();

        expect(axiosMock.patch).toHaveBeenCalledWith(`/api/v1/page-nodes/${NODE_ID}/announce-settings`, {
            announce_enabled: false,
            announce_interval_seconds: 300,
        });
    });

    it("preserves a zero announce interval when selecting a node", async () => {
        axiosMock.get.mockResolvedValue({
            data: [makeNode({ announce_interval_seconds: 0 })],
        });
        const wrapper = mountPage();
        await vi.waitFor(() => expect(wrapper.vm.nodes.length).toBe(1));
        wrapper.vm.selectNode(wrapper.vm.nodes[0]);
        expect(wrapper.vm.announceSettingsForm.announce_interval_seconds).toBe(0);
        expect(wrapper.vm.announceIntervalMinutes).toBe(0);
    });

    it("shows an error toast when saving announce settings fails", async () => {
        axiosMock.patch.mockRejectedValueOnce(new Error("boom"));
        const wrapper = mountPage();
        await vi.waitFor(() => expect(wrapper.vm.nodes.length).toBe(1));
        wrapper.vm.selectNode(wrapper.vm.nodes[0]);

        await wrapper.vm.saveAnnounceSettings();
        expect(ToastUtils.error).toHaveBeenCalledWith("Failed to save announce settings");
    });

    it("creates a node without touching announce settings by default", async () => {
        axiosMock.post.mockResolvedValueOnce({ data: makeNode({ name: "Fresh Node" }) });
        const wrapper = mountPage();
        await vi.waitFor(() => expect(wrapper.vm.nodes.length).toBe(1));

        wrapper.vm.createNodeName = "Fresh Node";
        await wrapper.vm.createNode();

        expect(axiosMock.post).toHaveBeenCalledWith("/api/v1/page-nodes", { name: "Fresh Node" });
    });
});
