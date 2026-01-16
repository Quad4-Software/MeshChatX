import { mount } from "@vue/test-utils";
import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import BotsPage from "@/components/tools/BotsPage.vue";

describe("BotsPage.vue", () => {
    let axiosMock;

    beforeEach(() => {
        axiosMock = {
            get: vi.fn(),
            post: vi.fn(),
        };
        window.axios = axiosMock;

        axiosMock.get.mockImplementation((url) => {
            if (url === "/api/v1/bots/status") {
                return Promise.resolve({
                    data: {
                        status: {
                            bots: [{ id: "bot1", name: "Test Bot", address: "addr1", template_id: "echo" }],
                            running_bots: [{ id: "bot1", address: "addr1" }],
                        },
                        templates: [{ id: "echo", name: "Echo Bot", description: "Echos messages" }],
                    },
                });
            }
            return Promise.resolve({ data: {} });
        });
    });

    afterEach(() => {
        delete window.axios;
        vi.clearAllMocks();
    });

    const mountBotsPage = () => {
        return mount(BotsPage, {
            global: {
                mocks: {
                    $t: (key) => key,
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

        const templateCard = wrapper.find(".glass-card[class*='cursor-pointer']");
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

        const startButton = wrapper.findAll("button").find((b) => b.text().includes("bots.start_bot"));
        await startButton.trigger("click");

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
});
