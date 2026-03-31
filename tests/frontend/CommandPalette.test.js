import { mount } from "@vue/test-utils";
import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import CommandPalette from "../../meshchatx/src/frontend/components/CommandPalette.vue";
import GlobalEmitter from "../../meshchatx/src/frontend/js/GlobalEmitter";

describe("CommandPalette.vue", () => {
    let axiosMock;
    let routerMock;

    beforeEach(() => {
        axiosMock = {
            get: vi.fn().mockResolvedValue({
                data: {
                    announces: [],
                    contacts: [],
                },
            }),
        };
        window.api = axiosMock;

        routerMock = {
            push: vi.fn(),
        };

        GlobalEmitter.off("sync-propagation-node");
        GlobalEmitter.off("toggle-orbit");
    });

    afterEach(() => {
        delete window.api;
        GlobalEmitter.off("sync-propagation-node");
        GlobalEmitter.off("toggle-orbit");
        vi.clearAllMocks();
    });

    const mountCommandPalette = () => {
        return mount(CommandPalette, {
            global: {
                mocks: {
                    $t: (key) => key,
                    $router: routerMock,
                },
                stubs: {
                    MaterialDesignIcon: { template: '<div class="mdi"></div>' },
                    LxmfUserIcon: { template: '<div class="lxmf-icon"></div>' },
                },
                directives: {
                    "click-outside": {},
                },
            },
        });
    };

    it("renders nothing when closed", () => {
        const wrapper = mountCommandPalette();
        expect(wrapper.find(".fixed").exists()).toBe(false);
    });

    it("opens when Ctrl+K or Cmd+K is pressed", async () => {
        const wrapper = mountCommandPalette();

        const event = new KeyboardEvent("keydown", {
            key: "k",
            ctrlKey: true,
        });
        window.dispatchEvent(event);

        await wrapper.vm.$nextTick();
        expect(wrapper.vm.isOpen).toBe(true);
    });

    it("opens and closes when toggle is called", async () => {
        const wrapper = mountCommandPalette();

        await wrapper.vm.toggle();
        expect(wrapper.vm.isOpen).toBe(true);

        await wrapper.vm.toggle();
        expect(wrapper.vm.isOpen).toBe(false);
    });

    it("loads peers and contacts when opened", async () => {
        axiosMock.get
            .mockResolvedValueOnce({
                data: {
                    announces: [
                        {
                            destination_hash: "peer1",
                            display_name: "Peer 1",
                            lxmf_user_icon: { icon_name: "account" },
                        },
                    ],
                },
            })
            .mockResolvedValueOnce({
                data: [
                    {
                        id: 1,
                        name: "Contact 1",
                        remote_identity_hash: "contact1",
                    },
                ],
            });

        const wrapper = mountCommandPalette();
        await wrapper.vm.open();
        await wrapper.vm.$nextTick();

        expect(axiosMock.get).toHaveBeenCalledWith("/api/v1/announces", {
            params: { aspect: "lxmf.delivery", limit: 20 },
        });
        expect(axiosMock.get).toHaveBeenCalledWith("/api/v1/telephone/contacts");
    });

    it("filters results based on query", async () => {
        const wrapper = mountCommandPalette();
        wrapper.vm.isOpen = true;
        await wrapper.vm.$nextTick();

        wrapper.vm.query = "messages";
        await wrapper.vm.$nextTick();

        const results = wrapper.vm.filteredResults;
        expect(results.length).toBeGreaterThan(0);
        expect(results.some((r) => r.title.toLowerCase().includes("messages"))).toBe(true);
    });

    it("shows navigation and action items when query is empty", async () => {
        const wrapper = mountCommandPalette();
        wrapper.vm.isOpen = true;
        wrapper.vm.query = "";
        await wrapper.vm.$nextTick();

        const results = wrapper.vm.filteredResults;
        const hasNavigation = results.some((r) => r.type === "navigation");
        const hasAction = results.some((r) => r.type === "action");
        expect(hasNavigation || hasAction).toBe(true);
    });

    it("highlights first result when filtered results change", async () => {
        const wrapper = mountCommandPalette();
        wrapper.vm.isOpen = true;
        await wrapper.vm.$nextTick();

        const results = wrapper.vm.filteredResults;
        if (results.length > 0) {
            expect(wrapper.vm.highlightedId).toBe(results[0].id);
        }
    });

    it("moves highlight up and down with arrow keys", async () => {
        const wrapper = mountCommandPalette();
        wrapper.vm.isOpen = true;
        await wrapper.vm.$nextTick();

        const initialHighlight = wrapper.vm.highlightedId;
        wrapper.vm.moveHighlight(1);
        expect(wrapper.vm.highlightedId).not.toBe(initialHighlight);

        wrapper.vm.moveHighlight(-1);
        expect(wrapper.vm.highlightedId).toBe(initialHighlight);
    });

    it("wraps highlight when moving past boundaries", async () => {
        const wrapper = mountCommandPalette();
        wrapper.vm.isOpen = true;
        await wrapper.vm.$nextTick();

        const results = wrapper.vm.filteredResults;
        if (results.length > 0) {
            wrapper.vm.highlightedId = results[results.length - 1].id;
            wrapper.vm.moveHighlight(1);
            expect(wrapper.vm.highlightedId).toBe(results[0].id);

            wrapper.vm.highlightedId = results[0].id;
            wrapper.vm.moveHighlight(-1);
            expect(wrapper.vm.highlightedId).toBe(results[results.length - 1].id);
        }
    });

    it("navigates to route when navigation result is executed", async () => {
        const wrapper = mountCommandPalette();
        wrapper.vm.isOpen = true;
        await wrapper.vm.$nextTick();

        const navResult = wrapper.vm.filteredResults.find((r) => r.type === "navigation");
        if (navResult) {
            wrapper.vm.executeResult(navResult);
            expect(routerMock.push).toHaveBeenCalledWith(navResult.route);
            expect(wrapper.vm.isOpen).toBe(false);
        }
    });

    it("navigates to messages when peer result is executed", async () => {
        const wrapper = mountCommandPalette();
        wrapper.vm.isOpen = true;
        wrapper.vm.peers = [
            {
                destination_hash: "peer123",
                display_name: "Test Peer",
            },
        ];
        await wrapper.vm.$nextTick();

        const peerResult = wrapper.vm.filteredResults.find((r) => r.type === "peer");
        if (peerResult) {
            wrapper.vm.executeResult(peerResult);
            expect(routerMock.push).toHaveBeenCalledWith({
                name: "messages",
                params: { destinationHash: "peer123" },
            });
        }
    });

    it("navigates to call when contact result is executed", async () => {
        const wrapper = mountCommandPalette();
        wrapper.vm.isOpen = true;
        wrapper.vm.contacts = [
            {
                id: 1,
                name: "Test Contact",
                remote_identity_hash: "contact123",
            },
        ];
        await wrapper.vm.$nextTick();

        const contactResult = wrapper.vm.filteredResults.find((r) => r.type === "contact");
        if (contactResult) {
            wrapper.vm.executeResult(contactResult);
            expect(routerMock.push).toHaveBeenCalledWith({
                name: "call",
                query: { destination_hash: "contact123" },
            });
        }
    });

    it("emits sync event when sync action is executed", async () => {
        const wrapper = mountCommandPalette();
        const emitSpy = vi.spyOn(GlobalEmitter, "emit");
        wrapper.vm.isOpen = true;
        await wrapper.vm.$nextTick();

        const syncResult = wrapper.vm.filteredResults.find((r) => r.action === "sync");
        if (syncResult) {
            wrapper.vm.executeResult(syncResult);
            expect(emitSpy).toHaveBeenCalledWith("sync-propagation-node");
        }
    });

    it("emits toggle-orbit event when orbit action is executed", async () => {
        const wrapper = mountCommandPalette();
        const emitSpy = vi.spyOn(GlobalEmitter, "emit");
        wrapper.vm.isOpen = true;
        await wrapper.vm.$nextTick();

        const orbitResult = wrapper.vm.filteredResults.find((r) => r.action === "toggle-orbit");
        if (orbitResult) {
            wrapper.vm.executeResult(orbitResult);
            expect(emitSpy).toHaveBeenCalledWith("toggle-orbit");
        }
    });

    it("closes when ESC key is pressed", async () => {
        const wrapper = mountCommandPalette();
        wrapper.vm.isOpen = true;
        await wrapper.vm.$nextTick();

        const input = wrapper.find("input");
        await input.trigger("keydown.esc");

        expect(wrapper.vm.isOpen).toBe(false);
    });

    it("executes highlighted action when Enter is pressed", async () => {
        const wrapper = mountCommandPalette();
        wrapper.vm.isOpen = true;
        await wrapper.vm.$nextTick();

        const executeSpy = vi.spyOn(wrapper.vm, "executeAction");
        const input = wrapper.find("input");
        await input.trigger("keydown.enter");

        expect(executeSpy).toHaveBeenCalled();
    });

    it("groups results by type", async () => {
        const wrapper = mountCommandPalette();
        wrapper.vm.isOpen = true;
        wrapper.vm.peers = [
            {
                destination_hash: "peer1",
                display_name: "Peer 1",
            },
        ];
        await wrapper.vm.$nextTick();

        const grouped = wrapper.vm.groupedResults;
        expect(Object.keys(grouped).length).toBeGreaterThan(0);
    });

    it("shows no results message when query has no matches", async () => {
        const wrapper = mountCommandPalette();
        wrapper.vm.isOpen = true;
        wrapper.vm.query = "nonexistentquery12345";
        await wrapper.vm.$nextTick();

        const results = wrapper.vm.filteredResults;
        expect(results.length).toBe(0);
    });
});
