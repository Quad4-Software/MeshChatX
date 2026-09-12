import { mount } from "@vue/test-utils";
import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import BotSetupPage from "@/components/tools/BotSetupPage.vue";
import ToastUtils from "@/js/ToastUtils";

vi.mock("@/js/ToastUtils", () => ({
    default: {
        success: vi.fn(),
        error: vi.fn(),
        info: vi.fn(),
    },
}));

const TEMPLATES = [
    { id: "echo", name: "Echo Bot", description: "Echos messages", default_icon: "forum" },
    { id: "custom", name: "Custom Bot", description: "Your commands", default_icon: "robot" },
    { id: "rrc", name: "RRC Bot", description: "Relay rooms", default_icon: "chat" },
];

function stubbed(name, props = []) {
    return {
        name,
        template: "<div />",
        props,
    };
}

describe("BotSetupPage.vue", () => {
    let axiosMock;
    let routerPush;

    beforeEach(() => {
        routerPush = vi.fn();
        axiosMock = {
            get: vi.fn(),
            post: vi.fn().mockResolvedValue({ data: { bot_id: "b1", success: true } }),
            patch: vi.fn(),
        };
        window.api = axiosMock;

        axiosMock.get.mockImplementation((url) => {
            if (url === "/api/v1/bots/status") {
                return Promise.resolve({
                    data: { status: { bots: [] }, templates: TEMPLATES },
                });
            }
            return Promise.resolve({ data: {} });
        });
    });

    afterEach(() => {
        delete window.api;
        vi.clearAllMocks();
    });

    const mountPage = (query = {}) => {
        return mount(BotSetupPage, {
            global: {
                mocks: {
                    $t: (key) => key,
                    $router: { push: routerPush },
                    $route: { query },
                },
                stubs: {
                    MaterialDesignIcon: stubbed("MaterialDesignIcon", ["iconName"]),
                    ToolsPageHeader: stubbed("ToolsPageHeader", ["icon", "title"]),
                    LxmfUserIcon: stubbed("LxmfUserIcon", ["iconName"]),
                    LxmfIconEditor: stubbed("LxmfIconEditor", ["modelValue"]),
                    LxmfConfigFields: stubbed("LxmfConfigFields", ["modelValue"]),
                    BotCustomCommandsEditor: stubbed("BotCustomCommandsEditor", ["modelValue"]),
                    BotRrcFields: stubbed("BotRrcFields", ["modelValue"]),
                },
            },
        });
    };

    it("preselects the template from the route query", async () => {
        const wrapper = mountPage({ template: "custom" });
        await vi.waitFor(() => expect(wrapper.vm.loading).toBe(false));
        expect(wrapper.vm.selectedTemplateId).toBe("custom");
        expect(wrapper.vm.name).toBe("Custom Bot");
    });

    it("creates a custom bot with commands and icon", async () => {
        const wrapper = mountPage({ template: "custom" });
        await vi.waitFor(() => expect(wrapper.vm.loading).toBe(false));

        await wrapper.setData({
            name: "My Bot",
            customDraft: {
                welcome: "hi",
                commands: [{ name: "joke", response: "ha", description: "" }],
            },
            iconDraft: { icon_name: "robot", fg_color: "#aabbcc", bg_color: "#112233" },
        });
        await wrapper.vm.createBot();

        expect(axiosMock.post).toHaveBeenCalledWith("/api/v1/bots/start", {
            template_id: "custom",
            name: "My Bot",
            icon: { icon_name: "robot", fg_color: "#aabbcc", bg_color: "#112233" },
            custom: {
                welcome: "hi",
                commands: [{ name: "joke", response: "ha" }],
            },
        });
        expect(routerPush).toHaveBeenCalledWith("/bots");
        expect(ToastUtils.success).toHaveBeenCalledWith("bots.bot_started");
    });

    it("blocks rrc creation without a valid hub hash", async () => {
        const wrapper = mountPage({ template: "rrc" });
        await vi.waitFor(() => expect(wrapper.vm.loading).toBe(false));
        expect(wrapper.vm.canCreate).toBe(false);

        await wrapper.setData({ rrcDraft: { ...wrapper.vm.rrcDraft, hub: "nothex" } });
        await wrapper.vm.createBot();
        expect(axiosMock.post).not.toHaveBeenCalled();
        expect(ToastUtils.error).toHaveBeenCalledWith("bots.rrc_hub_required");
    });

    it("creates an rrc bot with a normalized payload", async () => {
        const wrapper = mountPage({ template: "rrc" });
        await vi.waitFor(() => expect(wrapper.vm.loading).toBe(false));

        await wrapper.setData({
            name: "Room Bot",
            rrcDraft: {
                hub: "A".repeat(32).toLowerCase(),
                rooms: "#Lobby, general",
                nick: "helper",
                mention_only: false,
                prefix: "?",
                rate_seconds: "5",
            },
        });
        await wrapper.vm.createBot();

        expect(axiosMock.post).toHaveBeenCalledWith("/api/v1/bots/start", {
            template_id: "rrc",
            name: "Room Bot",
            icon: { icon_name: "chat", fg_color: "#6b7280", bg_color: "#e5e7eb" },
            rrc: {
                hub: "a".repeat(32),
                rooms: ["Lobby", "general"],
                nick: "helper",
                mention_only: false,
                prefix: "?",
                rate_seconds: 5,
            },
        });
    });

    it("blocks custom creation with no commands", async () => {
        const wrapper = mountPage({ template: "custom" });
        await vi.waitFor(() => expect(wrapper.vm.loading).toBe(false));
        await wrapper.vm.createBot();
        expect(axiosMock.post).not.toHaveBeenCalled();
        expect(ToastUtils.error).toHaveBeenCalledWith("bots.custom_requires_command");
    });
});
