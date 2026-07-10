import { mount } from "@vue/test-utils";
import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";

vi.mock("vuetify/components/VTooltip", () => ({
    VTooltip: {
        name: "VTooltip",
        template: '<div class="v-tooltip-stub"><slot /></div>',
    },
}));

vi.mock("@/js/WebSocketConnection", () => ({
    default: {
        send: vi.fn(),
        on: vi.fn(),
        off: vi.fn(),
    },
}));

import RelayChatPage from "@/components/relay/RelayChatPage.vue";
import NomadNetworkPage from "@/components/nomadnetwork/NomadNetworkPage.vue";
import { mountToolsPageGlobals } from "./testI18n.js";

const HUB_HASH = "00112233445566778899aabbccddeeff";

function makeHub(overrides = {}) {
    return {
        hub_hash: HUB_HASH,
        name: "Test Hub",
        display_name: "Test Hub",
        rooms: ["lobby"],
        available_rooms: [],
        motd: null,
        max_msg_body_bytes: 350,
        ...overrides,
    };
}

describe("mobile popout visibility", () => {
    beforeEach(() => {
        vi.stubGlobal(
            "matchMedia",
            vi.fn().mockImplementation((query) => ({
                matches: false,
                media: query,
                addEventListener: vi.fn(),
                removeEventListener: vi.fn(),
                addListener: vi.fn(),
                removeListener: vi.fn(),
            }))
        );

        window.api = {
            get: vi.fn().mockImplementation((url) => {
                if (url === "/api/v1/rrc/hubs") {
                    return Promise.resolve({ data: { hubs: [makeHub()] } });
                }
                if (url.includes("/messages")) {
                    return Promise.resolve({ data: { messages: [], has_more: false } });
                }
                if (url.includes("/members")) {
                    return Promise.resolve({ data: { members: [] } });
                }
                if (url === "/api/v1/favourites") {
                    return Promise.resolve({ data: { favourites: [] } });
                }
                if (url === "/api/v1/announces") {
                    return Promise.resolve({ data: { announces: [] } });
                }
                return Promise.resolve({ data: {} });
            }),
            post: vi.fn().mockResolvedValue({ data: {} }),
            delete: vi.fn().mockResolvedValue({ data: {} }),
        };
    });

    afterEach(() => {
        delete window.api;
        vi.unstubAllGlobals();
    });

    it("hides relay channel popout on mobile viewport", async () => {
        const wrapper = mount(RelayChatPage, { global: mountToolsPageGlobals() });
        wrapper.vm.hubs = [makeHub()];
        wrapper.vm.smUp = false;
        await wrapper.vm.selectRoom(HUB_HASH, "lobby");
        await wrapper.vm.$nextTick();

        expect(wrapper.find('[data-testid="relay-popout"]').exists()).toBe(false);

        wrapper.vm.smUp = true;
        await wrapper.vm.$nextTick();
        expect(wrapper.find('[data-testid="relay-popout"]').exists()).toBe(true);

        wrapper.unmount();
    });

    it("omits nomad popout from mobile overflow menu", async () => {
        const wrapper = mount(NomadNetworkPage, {
            props: { destinationHash: "" },
            global: {
                mocks: {
                    $t: (key) => key,
                    $route: { query: {}, name: "nomadnetwork", meta: {}, params: {} },
                    $router: { replace: vi.fn(), push: vi.fn() },
                },
                stubs: {
                    MaterialDesignIcon: {
                        template: '<div class="mdi-stub" :data-icon-name="iconName"></div>',
                        props: ["iconName"],
                    },
                    IconButton: {
                        template: '<button type="button" v-bind="$attrs"><slot /></button>',
                    },
                    DropDownMenu: {
                        template:
                            '<div class="dd-stub"><slot name="button" /><div class="dd-items"><slot name="items" /></div></div>',
                    },
                    DropDownMenuItem: {
                        template: '<div class="dd-item"><slot /></div>',
                    },
                    NomadNetworkSidebar: true,
                    LoadingSpinner: true,
                    NomadBrowserContextMenu: true,
                    VTooltip: true,
                    LxmfUserIcon: true,
                },
                directives: {
                    "click-outside": { mounted() {}, unmounted() {} },
                },
            },
        });

        wrapper.vm.selectedNode = {
            destination_hash: "b".repeat(32),
            display_name: "Node",
        };
        await wrapper.vm.$nextTick();

        const mobileMenu = wrapper.findAll(".dd-stub").find((node) => {
            let el = node.element;
            while (el) {
                if (el.classList?.contains("lg:hidden")) {
                    return true;
                }
                el = el.parentElement;
            }
            return false;
        });

        expect(mobileMenu).toBeTruthy();
        const items = mobileMenu.find(".dd-items");
        expect(items.text()).not.toContain("nomadnet.pop_out_browser");
        expect(items.find('[data-icon-name="open-in-new"]').exists()).toBe(false);

        wrapper.unmount();
    });
});
