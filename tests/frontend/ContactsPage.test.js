import { mount } from "@vue/test-utils";
import { beforeEach, describe, expect, it, vi } from "vitest";
import ContactsPage from "@/components/contacts/ContactsPage.vue";
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
        toDataURL: vi.fn().mockResolvedValue("data:image/png;base64,test"),
    },
}));

describe("ContactsPage.vue", () => {
    let axiosMock;

    beforeEach(() => {
        vi.clearAllMocks();
        axiosMock = {
            get: vi.fn(),
            post: vi.fn(),
            delete: vi.fn(),
        };
        window.axios = axiosMock;

        axiosMock.get.mockImplementation((url) => {
            if (url === "/api/v1/config") {
                return Promise.resolve({
                    data: {
                        config: {
                            lxmf_address_hash: "a".repeat(32),
                            identity_public_key: "b".repeat(128),
                        },
                    },
                });
            }
            if (url === "/api/v1/telephone/contacts") {
                return Promise.resolve({ data: { contacts: [] } });
            }
            if (url.startsWith("/api/v1/telephone/contacts/check/")) {
                return Promise.resolve({ data: {} });
            }
            return Promise.resolve({ data: {} });
        });
    });

    const mountPage = () =>
        mount(ContactsPage, {
            global: {
                mocks: {
                    $t: (key) => key,
                },
                stubs: {
                    MaterialDesignIcon: true,
                },
            },
        });

    it("parses lxma URI correctly", () => {
        const wrapper = mountPage();
        const result = wrapper.vm.parseLxmaUri(`lxma://${"c".repeat(32)}:${"d".repeat(128)}`);
        expect(result.destinationHash).toBe("c".repeat(32));
        expect(result.publicKeyHex).toBe("d".repeat(128));
    });

    it("adds contact using manual destination hash", async () => {
        const wrapper = mountPage();
        await wrapper.vm.$nextTick();
        wrapper.vm.newContactInput = "e".repeat(32);
        wrapper.vm.newContactName = "Test Contact";

        await wrapper.vm.submitAddContact();

        expect(axiosMock.post).toHaveBeenCalledWith("/api/v1/telephone/contacts", {
            name: "Test Contact",
            remote_identity_hash: "e".repeat(32),
            lxmf_address: "e".repeat(32),
        });
    });

    it("uses websocket ingest for lxma URI input", async () => {
        const wrapper = mountPage();
        await wrapper.vm.$nextTick();
        wrapper.vm.newContactInput = `lxma://${"f".repeat(32)}:${"1".repeat(128)}`;

        await wrapper.vm.submitAddContact();

        expect(WebSocketConnection.send).toHaveBeenCalledWith(
            JSON.stringify({
                type: "lxm.ingest_uri",
                uri: `lxma://${"f".repeat(32)}:${"1".repeat(128)}`,
            })
        );
        expect(axiosMock.post).not.toHaveBeenCalled();
    });
});
