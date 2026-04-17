import { mount } from "@vue/test-utils";
import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import BotsPage from "@/components/tools/BotsPage.vue";

describe("BotsPage.vue", () => {
    let axiosMock;
    let routerPush;

    beforeEach(() => {
        routerPush = vi.fn();
        axiosMock = {
            get: vi.fn(),
            post: vi.fn(),
            patch: vi.fn(),
        };
        window.api = axiosMock;

        axiosMock.get.mockImplementation((url) => {
            if (url === "/api/v1/bots/status") {
                return Promise.resolve({
                    data: {
                        status: {
                            bots: [
                                {
                                    id: "bot1",
                                    name: "Test Bot",
                                    address: "<addr1>",
                                    lxmf_address: "a".repeat(32),
                                    running: true,
                                    template_id: "echo",
                                },
                            ],
                        },
                        templates: [{ id: "echo", name: "Echo Bot", description: "Echos messages" }],
                    },
                });
            }
            return Promise.resolve({ data: {} });
        });
    });

    afterEach(() => {
        delete window.api;
        vi.clearAllMocks();
    });

    const mountBotsPage = () => {
        return mount(BotsPage, {
            global: {
                mocks: {
                    $t: (key) => key,
                    $router: { push: routerPush },
                    $route: { meta: {} },
                },
                stubs: {
                    MaterialDesignIcon: {
                        template: '<div class="mdi-stub" :data-icon-name="iconName"></div>',
                        props: ["iconName"],
                    },
                },
            },
        });
    };

    it("renders and loads bots and templates", async () => {
        const wrapper = mountBotsPage();
        await vi.waitFor(() => expect(wrapper.vm.loading).toBe(false));

        expect(wrapper.text()).toContain("bots.title");
        expect(wrapper.text()).toContain("Echo Bot");
        expect(wrapper.text()).toContain("Test Bot");
    });

    it("opens start bot modal when a template is selected", async () => {
        const wrapper = mountBotsPage();
        await vi.waitFor(() => expect(wrapper.vm.loading).toBe(false));

        const cards = wrapper.findAll("div.cursor-pointer");
        const templateCard = cards.filter(
            (d) => d.text().includes("Echo Bot") && d.text().includes("Echos messages")
        )[0];
        await templateCard.trigger("click");

        expect(wrapper.vm.selectedTemplate).not.toBeNull();
        expect(wrapper.text()).toContain("bots.start_bot: Echo Bot");
    });

    it("calls start bot API when form is submitted", async () => {
        const wrapper = mountBotsPage();
        await vi.waitFor(() => expect(wrapper.vm.loading).toBe(false));

        await wrapper.setData({
            selectedTemplate: { id: "echo", name: "Echo Bot" },
            newBotName: "My New Bot",
        });

        await wrapper.vm.startBot();

        expect(axiosMock.post).toHaveBeenCalledWith("/api/v1/bots/start", {
            template_id: "echo",
            name: "My New Bot",
        });
    });

    it("calls stop bot API when stop button is clicked", async () => {
        const wrapper = mountBotsPage();
        await vi.waitFor(() => expect(wrapper.vm.loading).toBe(false));

        const stopButton = wrapper.find("button[title='bots.stop_bot']");
        await stopButton.trigger("click");

        expect(axiosMock.post).toHaveBeenCalledWith("/api/v1/bots/stop", {
            bot_id: "bot1",
        });
    });

    it("navigates to messages when chat is clicked", async () => {
        const wrapper = mountBotsPage();
        await vi.waitFor(() => expect(wrapper.vm.loading).toBe(false));

        const chatButton = wrapper.find("button[title='bots.chat_with_bot']");
        await chatButton.trigger("click");

        expect(routerPush).toHaveBeenCalledWith({
            name: "messages",
            params: { destinationHash: "a".repeat(32) },
        });
    });
});
