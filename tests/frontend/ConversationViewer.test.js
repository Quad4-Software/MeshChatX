import { mount } from "@vue/test-utils";
import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import ConversationViewer from "@/components/messages/ConversationViewer.vue";
import WebSocketConnection from "@/js/WebSocketConnection";

describe("ConversationViewer.vue", () => {
    let axiosMock;

    beforeEach(() => {
        WebSocketConnection.connect();
        axiosMock = {
            get: vi.fn().mockImplementation((url) => {
                if (url.includes("/path")) return Promise.resolve({ data: { path: [] } });
                if (url.includes("/stamp-info")) return Promise.resolve({ data: { stamp_info: {} } });
                if (url.includes("/signal-metrics")) return Promise.resolve({ data: { signal_metrics: {} } });
                return Promise.resolve({ data: {} });
            }),
            post: vi.fn().mockResolvedValue({ data: {} }),
        };
        window.axios = axiosMock;

        // Mock localStorage
        const localStorageMock = {
            getItem: vi.fn(),
            setItem: vi.fn(),
            removeItem: vi.fn(),
        };
        vi.stubGlobal("localStorage", localStorageMock);

        // Mock URL.createObjectURL
        window.URL.createObjectURL = vi.fn(() => "mock-url");

        // Mock FileReader
        const mockFileReader = {
            readAsDataURL: vi.fn(function (blob) {
                this.result = "data:image/png;base64,mock";
                this.onload({ target: { result: this.result } });
            }),
        };
        vi.stubGlobal(
            "FileReader",
            vi.fn(() => mockFileReader)
        );
    });

    afterEach(() => {
        delete window.axios;
        vi.unstubAllGlobals();
        WebSocketConnection.destroy();
    });

    const mountConversationViewer = (props = {}) => {
        return mount(ConversationViewer, {
            props: {
                selectedPeer: { destination_hash: "test-hash", display_name: "Test Peer" },
                myLxmfAddressHash: "my-hash",
                conversations: [],
                ...props,
            },
            global: {
                mocks: {
                    $t: (key) => key,
                },
                stubs: {
                    MaterialDesignIcon: true,
                    AddImageButton: true,
                    AddAudioButton: true,
                    SendMessageButton: true,
                    ConversationDropDownMenu: true,
                    PaperMessageModal: true,
                    AudioWaveformPlayer: true,
                    LxmfUserIcon: true,
                },
            },
        });
    };

    it("adds multiple images and renders previews", async () => {
        const wrapper = mountConversationViewer();

        const image1 = new File([""], "image1.png", { type: "image/png" });
        const image2 = new File([""], "image2.png", { type: "image/png" });

        await wrapper.vm.onImageSelected(image1);
        await wrapper.vm.onImageSelected(image2);

        expect(wrapper.vm.newMessageImages).toHaveLength(2);
        expect(wrapper.vm.newMessageImageUrls).toHaveLength(2);

        // Check if previews are rendered
        const previews = wrapper.findAll("img");
        expect(previews).toHaveLength(2);
    });

    it("removes an image attachment", async () => {
        const wrapper = mountConversationViewer();

        const image1 = new File([""], "image1.png", { type: "image/png" });
        await wrapper.vm.onImageSelected(image1);

        expect(wrapper.vm.newMessageImages).toHaveLength(1);

        // Mock confirm dialog
        vi.mock("@/js/DialogUtils", () => ({
            default: {
                confirm: vi.fn(() => Promise.resolve(true)),
            },
        }));

        await wrapper.vm.removeImageAttachment(0);
        expect(wrapper.vm.newMessageImages).toHaveLength(0);
    });

    it("sends multiple images as separate messages", async () => {
        const wrapper = mountConversationViewer();
        wrapper.vm.newMessageText = "Hello";

        const image1 = new File([""], "image1.png", { type: "image/png" });
        const image2 = new File([""], "image2.png", { type: "image/png" });

        // Mock arrayBuffer for files
        image1.arrayBuffer = vi.fn(() => Promise.resolve(new ArrayBuffer(8)));
        image2.arrayBuffer = vi.fn(() => Promise.resolve(new ArrayBuffer(8)));

        await wrapper.vm.onImageSelected(image1);
        await wrapper.vm.onImageSelected(image2);

        axiosMock.post.mockResolvedValue({ data: { lxmf_message: { hash: "mock-hash" } } });

        await wrapper.vm.sendMessage();

        // Should call post twice
        expect(axiosMock.post).toHaveBeenCalledTimes(2);

        // First call should have the message text
        expect(axiosMock.post).toHaveBeenNthCalledWith(
            1,
            "/api/v1/lxmf-messages/send",
            expect.objectContaining({
                lxmf_message: expect.objectContaining({
                    content: "Hello",
                }),
            })
        );

        // Second call should have the image name as content
        expect(axiosMock.post).toHaveBeenNthCalledWith(
            2,
            "/api/v1/lxmf-messages/send",
            expect.objectContaining({
                lxmf_message: expect.objectContaining({
                    content: "image2.png",
                }),
            })
        );
    });

    it("auto-loads audio attachments on mount", async () => {
        const chatItems = [
            {
                lxmf_message: {
                    hash: "audio-hash",
                    fields: {
                        audio: { audio_mode: 0x10, audio_bytes: "base64-data" },
                    },
                },
            },
        ];

        axiosMock.get.mockResolvedValue({
            data: { lxmf_messages: chatItems.map((i) => i.lxmf_message) },
        });

        const wrapper = mountConversationViewer({
            conversations: [],
        });

        // initialLoad is called on mount
        await vi.waitFor(() => expect(axiosMock.get).toHaveBeenCalled());

        // downloadAndDecodeAudio should be triggered by autoLoadAudioAttachments
        await vi.waitFor(() =>
            expect(axiosMock.get).toHaveBeenCalledWith(expect.stringContaining("/audio"), expect.any(Object))
        );
    });
});
