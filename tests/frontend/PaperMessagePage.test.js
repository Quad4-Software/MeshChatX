import { mount } from "@vue/test-utils";
import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import PaperMessagePage from "@/components/tools/PaperMessagePage.vue";
import WebSocketConnection from "@/js/WebSocketConnection";

vi.mock("@/js/WebSocketConnection", () => ({
    default: {
        on: vi.fn(),
        off: vi.fn(),
        send: vi.fn(),
    },
}));

vi.mock("qrcode", () => ({
    default: {
        toCanvas: vi.fn().mockResolvedValue({}),
    },
}));

describe("PaperMessagePage.vue", () => {
    let axiosMock;

    beforeEach(() => {
        axiosMock = {
            get: vi.fn(),
            post: vi.fn(),
        };
        window.axios = axiosMock;
    });

    afterEach(() => {
        delete window.axios;
        vi.clearAllMocks();
    });

    const mountPaperMessagePage = () => {
        return mount(PaperMessagePage, {
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

    it("renders the paper message page", () => {
        const wrapper = mountPaperMessagePage();
        expect(wrapper.text()).toContain("Paper Message Generator");
        expect(wrapper.text()).toContain("Compose Message");
    });

    it("enables generate button only when inputs are valid", async () => {
        const wrapper = mountPaperMessagePage();
        const generateButton = wrapper.findAll("button").find((b) => b.text().includes("Generate Paper Message"));

        expect(generateButton.element.disabled).toBe(true);

        await wrapper.setData({
            destinationHash: "a".repeat(32),
            content: "Hello World",
        });

        expect(generateButton.element.disabled).toBe(false);
    });

    it("sends websocket request to generate paper message", async () => {
        const wrapper = mountPaperMessagePage();
        await wrapper.setData({
            destinationHash: "a".repeat(32),
            content: "Hello World",
            title: "Test Title",
        });

        const generateButton = wrapper.findAll("button").find((b) => b.text().includes("Generate Paper Message"));
        await generateButton.trigger("click");

        expect(WebSocketConnection.send).toHaveBeenCalledWith(
            JSON.stringify({
                type: "lxm.generate_paper_uri",
                destination_hash: "a".repeat(32),
                content: "Hello World",
                title: "Test Title",
            })
        );
    });

    it("handles websocket result and shows QR code", async () => {
        const wrapper = mountPaperMessagePage();

        // Find the callback passed to WebSocketConnection.on
        const onCall = WebSocketConnection.on.mock.calls.find((call) => call[0] === "message");
        const callback = onCall[1];

        await callback({
            data: JSON.stringify({
                type: "lxm.generate_paper_uri.result",
                status: "success",
                uri: "lxmf://testuri",
            }),
        });

        expect(wrapper.vm.generatedUri).toBe("lxmf://testuri");
        expect(wrapper.text()).toContain("Generated QR Code");
    });

    it("calls ingest API when ingest button is clicked", async () => {
        const wrapper = mountPaperMessagePage();
        await wrapper.setData({ ingestUri: "lxmf://ingestme" });

        const ingestButton = wrapper.findAll("button").find((b) => b.text().includes("Read LXM"));
        await ingestButton.trigger("click");

        expect(WebSocketConnection.send).toHaveBeenCalledWith(
            JSON.stringify({
                type: "lxm.ingest_uri",
                uri: "lxmf://ingestme",
            })
        );
    });
});
