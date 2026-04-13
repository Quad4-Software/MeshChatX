import { mount } from "@vue/test-utils";
import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import MessagesPage from "@/components/messages/MessagesPage.vue";
import ContactsPage from "@/components/contacts/ContactsPage.vue";
import DialogUtils from "@/js/DialogUtils";

vi.mock("@/js/DialogUtils", () => ({
    default: {
        prompt: vi.fn(),
        alert: vi.fn(),
        confirm: vi.fn(() => Promise.resolve(true)),
    },
}));

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

describe("MessagesPage display name protection", () => {
    let axiosMock;

    beforeEach(() => {
        vi.clearAllMocks();
        axiosMock = {
            get: vi.fn(),
            post: vi.fn(),
        };
        window.api = axiosMock;

        axiosMock.get.mockImplementation((url) => {
            if (url === "/api/v1/config")
                return Promise.resolve({ data: { config: { lxmf_address_hash: "my-hash" } } });
            if (url === "/api/v1/lxmf/conversations") return Promise.resolve({ data: { conversations: [] } });
            if (url === "/api/v1/announces") return Promise.resolve({ data: { announces: [] } });
            if (url === "/api/v1/lxmf/conversation-pins") return Promise.resolve({ data: { peer_hashes: [] } });
            return Promise.resolve({ data: {} });
        });
    });

    afterEach(() => {
        delete window.api;
    });

    const mountMessagesPage = (props = { destinationHash: "" }) => {
        return mount(MessagesPage, {
            props,
            global: {
                mocks: {
                    $t: (key) => key,
                    $route: { query: {} },
                    $router: { replace: vi.fn() },
                },
                stubs: {
                    MaterialDesignIcon: true,
                    LoadingSpinner: true,
                    MessagesSidebar: {
                        template: '<div class="sidebar-stub"></div>',
                        props: ["conversations", "selectedDestinationHash"],
                    },
                    ConversationViewer: {
                        template: '<div class="viewer-stub"></div>',
                        props: ["selectedPeer", "myLxmfAddressHash"],
                    },
                    Modal: true,
                },
            },
        });
    };

    it("does not overwrite a known display name with Anonymous Peer from announce", async () => {
        const destHash = "a".repeat(32);
        const wrapper = mountMessagesPage();
        await wrapper.vm.$nextTick();

        wrapper.vm.peers[destHash] = {
            destination_hash: destHash,
            display_name: "Real Name",
            custom_display_name: null,
        };

        wrapper.vm.updatePeerFromAnnounce({
            destination_hash: destHash,
            display_name: "Anonymous Peer",
        });

        expect(wrapper.vm.peers[destHash].display_name).toBe("Real Name");
    });

    it("allows overwriting Anonymous Peer with a real name from announce", async () => {
        const destHash = "b".repeat(32);
        const wrapper = mountMessagesPage();
        await wrapper.vm.$nextTick();

        wrapper.vm.peers[destHash] = {
            destination_hash: destHash,
            display_name: "Anonymous Peer",
        };

        wrapper.vm.updatePeerFromAnnounce({
            destination_hash: destHash,
            display_name: "Newly Announced",
        });

        expect(wrapper.vm.peers[destHash].display_name).toBe("Newly Announced");
    });

    it("allows updating from one real name to another real name via announce", async () => {
        const destHash = "c".repeat(32);
        const wrapper = mountMessagesPage();
        await wrapper.vm.$nextTick();

        wrapper.vm.peers[destHash] = {
            destination_hash: destHash,
            display_name: "Old Name",
        };

        wrapper.vm.updatePeerFromAnnounce({
            destination_hash: destHash,
            display_name: "New Name",
        });

        expect(wrapper.vm.peers[destHash].display_name).toBe("New Name");
    });

    it("preserves known name when conversation list returns Anonymous Peer", async () => {
        const destHash = "d".repeat(32);
        const wrapper = mountMessagesPage();
        await wrapper.vm.$nextTick();

        wrapper.vm.peers[destHash] = {
            destination_hash: destHash,
            display_name: "Known Peer",
            custom_display_name: null,
        };

        axiosMock.get.mockImplementation((url) => {
            if (url === "/api/v1/lxmf/conversations")
                return Promise.resolve({
                    data: {
                        conversations: [
                            {
                                destination_hash: destHash,
                                display_name: "Anonymous Peer",
                                custom_display_name: null,
                            },
                        ],
                    },
                });
            if (url === "/api/v1/config")
                return Promise.resolve({ data: { config: { lxmf_address_hash: "my-hash" } } });
            if (url === "/api/v1/lxmf/conversation-pins") return Promise.resolve({ data: { peer_hashes: [] } });
            return Promise.resolve({ data: {} });
        });

        await wrapper.vm.getConversations();
        await wrapper.vm.$nextTick();

        expect(wrapper.vm.peers[destHash].display_name).toBe("Known Peer");
    });

    it("accepts new display name from conversation list when peer was Anonymous", async () => {
        const destHash = "e".repeat(32);
        const wrapper = mountMessagesPage();
        await wrapper.vm.$nextTick();

        wrapper.vm.peers[destHash] = {
            destination_hash: destHash,
            display_name: "Anonymous Peer",
        };

        axiosMock.get.mockImplementation((url) => {
            if (url === "/api/v1/lxmf/conversations")
                return Promise.resolve({
                    data: {
                        conversations: [
                            {
                                destination_hash: destHash,
                                display_name: "Resolved Name",
                                custom_display_name: null,
                            },
                        ],
                    },
                });
            if (url === "/api/v1/config")
                return Promise.resolve({ data: { config: { lxmf_address_hash: "my-hash" } } });
            if (url === "/api/v1/lxmf/conversation-pins") return Promise.resolve({ data: { peer_hashes: [] } });
            return Promise.resolve({ data: {} });
        });

        await wrapper.vm.getConversations();
        await wrapper.vm.$nextTick();

        expect(wrapper.vm.peers[destHash].display_name).toBe("Resolved Name");
    });

    it("does not overwrite name via resolvePeerDisplayName when server returns Anonymous", async () => {
        const destHash = "f".repeat(32);
        const wrapper = mountMessagesPage();
        await wrapper.vm.$nextTick();

        wrapper.vm.conversations = [
            { destination_hash: destHash, display_name: "Original Name", custom_display_name: null },
        ];
        wrapper.vm.selectedPeer = { destination_hash: destHash, display_name: "Original Name" };

        axiosMock.get.mockImplementation((url) => {
            if (url === "/api/v1/lxmf/conversations")
                return Promise.resolve({
                    data: {
                        conversations: [
                            {
                                destination_hash: destHash,
                                display_name: "Anonymous Peer",
                                custom_display_name: null,
                            },
                        ],
                    },
                });
            return Promise.resolve({ data: {} });
        });

        await wrapper.vm.resolvePeerDisplayName(destHash);
        await wrapper.vm.$nextTick();

        expect(wrapper.vm.conversations[0].display_name).toBe("Original Name");
        expect(wrapper.vm.selectedPeer.display_name).toBe("Original Name");
    });

    it("handles new peer with no prior entry gracefully", async () => {
        const destHash = "1".repeat(32);
        const wrapper = mountMessagesPage();
        await wrapper.vm.$nextTick();

        wrapper.vm.updatePeerFromAnnounce({
            destination_hash: destHash,
            display_name: "Anonymous Peer",
        });

        expect(wrapper.vm.peers[destHash].display_name).toBe("Anonymous Peer");
    });

    it("preserves custom_display_name when announce does not carry it", async () => {
        const destHash = "2".repeat(32);
        const wrapper = mountMessagesPage();
        await wrapper.vm.$nextTick();

        wrapper.vm.peers[destHash] = {
            destination_hash: destHash,
            display_name: "Announced Name",
            custom_display_name: "My Custom Name",
        };

        wrapper.vm.updatePeerFromAnnounce({
            destination_hash: destHash,
            display_name: "Anonymous Peer",
        });

        expect(wrapper.vm.peers[destHash].custom_display_name).toBe("My Custom Name");
        expect(wrapper.vm.peers[destHash].display_name).toBe("Announced Name");
    });

    it("server-provided custom_display_name in announce is authoritative", async () => {
        const destHash = "3".repeat(32);
        const wrapper = mountMessagesPage();
        await wrapper.vm.$nextTick();

        wrapper.vm.peers[destHash] = {
            destination_hash: destHash,
            display_name: "Old",
            custom_display_name: "Stale Custom",
        };

        wrapper.vm.updatePeerFromAnnounce({
            destination_hash: destHash,
            display_name: "Anonymous Peer",
            custom_display_name: "Server Custom",
        });

        expect(wrapper.vm.peers[destHash].custom_display_name).toBe("Server Custom");
        expect(wrapper.vm.peers[destHash].display_name).toBe("Old");
    });
});

describe("ContactsPage edit contact name", () => {
    let axiosMock;

    beforeEach(() => {
        vi.clearAllMocks();
        axiosMock = {
            get: vi.fn(),
            post: vi.fn(),
            patch: vi.fn(),
            delete: vi.fn(),
        };
        window.api = axiosMock;

        axiosMock.get.mockImplementation((url) => {
            if (url === "/api/v1/config")
                return Promise.resolve({
                    data: {
                        config: {
                            lxmf_address_hash: "a".repeat(32),
                            identity_public_key: "b".repeat(128),
                        },
                    },
                });
            if (url === "/api/v1/telephone/contacts")
                return Promise.resolve({ data: { contacts: [], total_count: 0 } });
            return Promise.resolve({ data: {} });
        });

        axiosMock.patch.mockResolvedValue({ data: { message: "Contact updated" } });
        axiosMock.post.mockResolvedValue({ data: { message: "OK" } });
    });

    afterEach(() => {
        delete window.api;
    });

    const mountPage = () =>
        mount(ContactsPage, {
            global: {
                mocks: {
                    $t: (key) => key,
                    $router: { push: vi.fn() },
                },
                stubs: {
                    MaterialDesignIcon: true,
                    LxmfUserIcon: true,
                },
            },
        });

    it("editContactName updates both contact and custom display name", async () => {
        DialogUtils.prompt.mockResolvedValue("Renamed Alice");

        const wrapper = mountPage();
        await wrapper.vm.$nextTick();

        const contact = {
            id: 42,
            name: "Alice",
            remote_identity_hash: "a".repeat(32),
            lxmf_address: "a".repeat(32),
            remote_destination_hash: "a".repeat(32),
        };

        await wrapper.vm.editContactName(contact);

        expect(axiosMock.patch).toHaveBeenCalledWith("/api/v1/telephone/contacts/42", {
            name: "Renamed Alice",
        });
        expect(axiosMock.post).toHaveBeenCalledWith(
            `/api/v1/destination/${"a".repeat(32)}/custom-display-name/update`,
            { display_name: "Renamed Alice" }
        );
    });

    it("editContactName does nothing when user cancels prompt", async () => {
        DialogUtils.prompt.mockResolvedValue(null);

        const wrapper = mountPage();
        await wrapper.vm.$nextTick();

        await wrapper.vm.editContactName({ id: 1, name: "Alice" });

        expect(axiosMock.patch).not.toHaveBeenCalled();
        expect(axiosMock.post).not.toHaveBeenCalled();
    });

    it("editContactName does nothing when name unchanged", async () => {
        DialogUtils.prompt.mockResolvedValue("Alice");

        const wrapper = mountPage();
        await wrapper.vm.$nextTick();

        await wrapper.vm.editContactName({ id: 1, name: "Alice" });

        expect(axiosMock.patch).not.toHaveBeenCalled();
    });

    it("editContactName skips custom display name when no dest hash", async () => {
        DialogUtils.prompt.mockResolvedValue("New Name");

        const wrapper = mountPage();
        await wrapper.vm.$nextTick();

        const contact = {
            id: 99,
            name: "Old Name",
            remote_identity_hash: null,
            lxmf_address: null,
        };

        await wrapper.vm.editContactName(contact);

        expect(axiosMock.patch).toHaveBeenCalledWith("/api/v1/telephone/contacts/99", {
            name: "New Name",
        });
        expect(axiosMock.post).not.toHaveBeenCalled();
    });

    it("editContactName uses lxmf_address when remote_destination_hash absent", async () => {
        DialogUtils.prompt.mockResolvedValue("Updated");

        const wrapper = mountPage();
        await wrapper.vm.$nextTick();

        const contact = {
            id: 10,
            name: "Old",
            remote_identity_hash: "i".repeat(32),
            lxmf_address: "l".repeat(32),
        };

        await wrapper.vm.editContactName(contact);

        expect(axiosMock.post).toHaveBeenCalledWith(
            `/api/v1/destination/${"l".repeat(32)}/custom-display-name/update`,
            { display_name: "Updated" }
        );
    });

    it("editContactName handles API error gracefully", async () => {
        DialogUtils.prompt.mockResolvedValue("Fail Name");
        axiosMock.patch.mockRejectedValue(new Error("Network error"));

        const wrapper = mountPage();
        await wrapper.vm.$nextTick();

        const contact = { id: 5, name: "Before", remote_identity_hash: "x".repeat(32) };

        await wrapper.vm.editContactName(contact);

        expect(axiosMock.patch).toHaveBeenCalled();
    });

    it("editContactName with empty string still calls patch but not custom display name", async () => {
        DialogUtils.prompt.mockResolvedValue("");

        const wrapper = mountPage();
        await wrapper.vm.$nextTick();

        const contact = {
            id: 7,
            name: "Was Something",
            remote_identity_hash: "r".repeat(32),
            lxmf_address: "r".repeat(32),
        };

        await wrapper.vm.editContactName(contact);

        expect(axiosMock.patch).toHaveBeenCalledWith("/api/v1/telephone/contacts/7", {
            name: "",
        });
        expect(axiosMock.post).not.toHaveBeenCalled();
    });

    it("editContactName with no contact id does nothing", async () => {
        const wrapper = mountPage();
        await wrapper.vm.$nextTick();

        await wrapper.vm.editContactName({});

        expect(DialogUtils.prompt).not.toHaveBeenCalled();
        expect(axiosMock.patch).not.toHaveBeenCalled();
    });
});
