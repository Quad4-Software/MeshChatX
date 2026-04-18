import { flushPromises, mount } from "@vue/test-utils";
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
        window.api = axiosMock;

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
            if (url === "/api/v1/telephone/contacts/export") {
                return Promise.resolve({ data: { contacts: [] } });
            }
            if (url.startsWith("/api/v1/telephone/contacts/check/")) {
                return Promise.resolve({ data: { is_contact: false, contact: null } });
            }
            if (
                url === "/api/v1/telephone/contacts" ||
                (typeof url === "string" && url.startsWith("/api/v1/telephone/contacts?"))
            ) {
                return Promise.resolve({ data: { contacts: [], total_count: 0 } });
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

    it("exports contacts via GET /api/v1/telephone/contacts/export", async () => {
        const wrapper = mountPage();
        await wrapper.vm.$nextTick();

        await wrapper.vm.exportContacts();

        expect(axiosMock.get).toHaveBeenCalledWith("/api/v1/telephone/contacts/export");
    });

    it("imports contacts via POST /api/v1/telephone/contacts/import", async () => {
        const wrapper = mountPage();
        await wrapper.vm.$nextTick();
        axiosMock.post.mockResolvedValue({ data: { added: 2, skipped: 0 } });

        await wrapper.vm.importContacts([
            { name: "A", remote_identity_hash: "a".repeat(32) },
            { name: "B", remote_identity_hash: "b".repeat(32) },
        ]);

        expect(axiosMock.post).toHaveBeenCalledWith("/api/v1/telephone/contacts/import", {
            contacts: [
                { name: "A", remote_identity_hash: "a".repeat(32) },
                { name: "B", remote_identity_hash: "b".repeat(32) },
            ],
        });
    });

    it("mounts within 500ms", () => {
        const start = performance.now();
        const wrapper = mountPage();
        const elapsed = performance.now() - start;
        expect(wrapper.find("h1").exists()).toBe(true);
        expect(elapsed).toBeLessThan(500);
    });

    it("export and import buttons are present", async () => {
        const wrapper = mountPage();
        await wrapper.vm.$nextTick();
        const html = wrapper.html();
        expect(html).toContain("contacts.export_contacts");
        expect(html).toContain("contacts.import_contacts");
    });

    it("renders floating add-contact action for mobile layout", async () => {
        const wrapper = mountPage();
        await wrapper.vm.$nextTick();
        const mobileFab = wrapper.find('button[title="contacts.add_contact"]');
        expect(mobileFab.exists()).toBe(true);
    });

    it("getContacts maps total_count from telephone contacts API", async () => {
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
            if (
                url === "/api/v1/telephone/contacts" ||
                (typeof url === "string" && url.startsWith("/api/v1/telephone/contacts?"))
            ) {
                return Promise.resolve({
                    data: {
                        contacts: [{ id: 1, name: "One", remote_identity_hash: "c".repeat(32) }],
                        total_count: 42,
                    },
                });
            }
            if (url === "/api/v1/telephone/contacts/export") {
                return Promise.resolve({ data: { contacts: [] } });
            }
            if (url.startsWith("/api/v1/telephone/contacts/check/")) {
                return Promise.resolve({ data: { is_contact: false, contact: null } });
            }
            return Promise.resolve({ data: {} });
        });
        const wrapper = mountPage();
        await flushPromises();
        expect(wrapper.vm.totalContactsCount).toBe(42);
        expect(wrapper.vm.contacts).toHaveLength(1);
        expect(wrapper.vm.contacts[0].name).toBe("One");
    });
});
