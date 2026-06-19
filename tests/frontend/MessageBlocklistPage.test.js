import { mount } from "@vue/test-utils";
import { describe, it, expect, vi, beforeEach } from "vitest";
import MessageBlocklistPage from "@/components/tools/MessageBlocklistPage.vue";
import { createRouter, createWebHistory } from "vue-router";
import ToastUtils from "../../meshchatx/src/frontend/js/ToastUtils";

vi.mock("../../meshchatx/src/frontend/js/ToastUtils", () => ({
    default: {
        success: vi.fn(),
        error: vi.fn(),
        warning: vi.fn(),
        info: vi.fn(),
    },
}));

vi.mock("../../meshchatx/src/frontend/js/DialogUtils", () => ({
    default: {
        confirm: vi.fn(() => Promise.resolve(false)),
    },
}));

vi.mock("../../meshchatx/src/frontend/js/DownloadUtils", () => ({
    default: {
        downloadFile: vi.fn(() => Promise.resolve()),
    },
}));

describe("MessageBlocklistPage.vue", () => {
    const router = createRouter({
        history: createWebHistory(),
        routes: [{ path: "/tools", name: "tools", component: { template: "<div/>" } }],
    });

    beforeEach(() => {
        vi.clearAllMocks();
        global.api.get = vi.fn((url) => {
            if (url.includes("message-blocklist/export")) {
                return Promise.resolve({
                    data: {
                        schema: "meshchatx.message_blocklist",
                        version: 1,
                        entries: [],
                    },
                });
            }
            if (url.includes("message-blocklist")) {
                return Promise.resolve({
                    data: {
                        enabled: false,
                        blocklist: {
                            scope: "non_contacts",
                            match_peer_fields: false,
                            match_message: true,
                            entries: [{ id: "e1", enabled: true, text: "spam", match_mode: "substring" }],
                        },
                    },
                });
            }
            return Promise.resolve({ data: {} });
        });
        global.api.put = vi.fn(() =>
            Promise.resolve({
                data: {
                    enabled: true,
                    blocklist: {
                        scope: "non_contacts",
                        match_message: true,
                        match_peer_fields: false,
                        entries: [{ id: "e1", enabled: true, text: "spam", match_mode: "substring" }],
                    },
                },
            })
        );
        global.api.post = vi.fn(() =>
            Promise.resolve({
                data: {
                    enabled: false,
                    blocklist: {
                        scope: "non_contacts",
                        match_message: true,
                        match_peer_fields: false,
                        entries: [],
                    },
                },
            })
        );
        window.api = global.api;
    });

    it("loads blocklist from the API", async () => {
        const wrapper = mount(MessageBlocklistPage, {
            global: {
                plugins: [router],
                mocks: { $t: (k) => k },
                stubs: {
                    MaterialDesignIcon: { template: "<span/>", props: ["iconName"] },
                    ToolsPageHeader: { template: "<div/>" },
                    RouterLink: { template: "<a><slot/></a>", props: ["to"] },
                },
            },
        });
        await Promise.resolve();
        await wrapper.vm.$nextTick();
        await Promise.resolve();
        expect(global.api.get).toHaveBeenCalledWith("/api/v1/lxmf/message-blocklist");
        expect(wrapper.vm.blocklist.entries.length).toBe(1);
        expect(wrapper.vm.enabled).toBe(false);
    });

    it("saves blocklist via PUT", async () => {
        const wrapper = mount(MessageBlocklistPage, {
            global: {
                plugins: [router],
                mocks: { $t: (k) => k },
                stubs: {
                    MaterialDesignIcon: { template: "<span/>", props: ["iconName"] },
                    ToolsPageHeader: { template: "<div/>" },
                    RouterLink: { template: "<a><slot/></a>", props: ["to"] },
                },
            },
        });
        await Promise.resolve();
        await wrapper.vm.$nextTick();
        await Promise.resolve();
        await wrapper.vm.save();
        expect(global.api.put).toHaveBeenCalledWith(
            "/api/v1/lxmf/message-blocklist",
            expect.objectContaining({
                enabled: false,
                blocklist: expect.objectContaining({
                    entries: expect.arrayContaining([
                        expect.objectContaining({ text: "spam", match_mode: "substring" }),
                    ]),
                }),
            })
        );
        expect(ToastUtils.success).toHaveBeenCalled();
    });
});
