import { mount } from "@vue/test-utils";
import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import NomadNetworkSidebar from "@/components/nomadnetwork/NomadNetworkSidebar.vue";
import DialogUtils from "@/js/DialogUtils";
import GlobalState from "@/js/GlobalState";
import GlobalEmitter from "@/js/GlobalEmitter";

vi.mock("@/js/DialogUtils", () => ({
    default: {
        confirm: vi.fn(() => Promise.resolve(true)),
        alert: vi.fn(),
        prompt: vi.fn((msg, def) => Promise.resolve(def || "renamed")),
    },
}));

describe("NomadNetworkSidebar.vue", () => {
    let axiosMock;

    const defaultFavourite = {
        destination_hash: "a".repeat(32),
        display_name: "Test Favourite",
    };
    const defaultNode = {
        destination_hash: "b".repeat(32),
        identity_hash: "c".repeat(32),
        display_name: "Test Node",
        updated_at: new Date().toISOString(),
    };

    beforeEach(() => {
        axiosMock = {
            get: vi.fn().mockResolvedValue({ data: {} }),
            post: vi.fn().mockResolvedValue({ data: {} }),
            delete: vi.fn().mockResolvedValue({ data: {} }),
        };
        window.api = axiosMock;

        GlobalState.blockedDestinations = [];
        GlobalState.config = { banished_effect_enabled: false };

        vi.stubGlobal("localStorage", {
            getItem: vi.fn(),
            setItem: vi.fn(),
            removeItem: vi.fn(),
        });
    });

    afterEach(() => {
        delete window.api;
        vi.unstubAllGlobals();
    });

    const mountSidebar = (overrides = {}) =>
        mount(NomadNetworkSidebar, {
            props: {
                nodes: overrides.nodes ?? { [defaultNode.destination_hash]: defaultNode },
                favourites: overrides.favourites ?? [defaultFavourite],
                selectedDestinationHash: overrides.selectedDestinationHash ?? "",
                nodesSearchTerm: overrides.nodesSearchTerm ?? "",
                totalNodesCount: overrides.totalNodesCount ?? 1,
                isLoadingMoreNodes: overrides.isLoadingMoreNodes ?? false,
                hasMoreNodes: overrides.hasMoreNodes ?? false,
            },
            global: {
                mocks: { $t: (key) => key },
                stubs: {
                    MaterialDesignIcon: {
                        template: '<div class="mdi-stub" :data-icon-name="iconName"></div>',
                        props: ["iconName"],
                    },
                },
            },
        });

    it("renders favourites tab with favourite cards", async () => {
        const wrapper = mountSidebar();
        await wrapper.vm.$nextTick();

        expect(wrapper.text()).toContain("nomadnet.favourites");
        expect(wrapper.text()).toContain("Test Favourite");
    });

    it("3-dots on favourite card opens context menu", async () => {
        const wrapper = mountSidebar();
        await wrapper.vm.$nextTick();

        const favouriteCard = wrapper.find(".favourite-card");
        expect(favouriteCard.exists()).toBe(true);
        const dotsBtn = favouriteCard.findComponent({ name: "IconButton" });
        expect(dotsBtn.exists()).toBe(true);

        await dotsBtn.trigger("click");
        await wrapper.vm.$nextTick();

        expect(wrapper.vm.favouriteContextMenu.show).toBe(true);
        expect(wrapper.vm.favouriteContextMenu.targetHash).toBe(defaultFavourite.destination_hash);
    });

    it("favourite context menu has rename, banish, remove options", async () => {
        const wrapper = mountSidebar();
        wrapper.vm.favouriteContextMenu = {
            show: true,
            targetHash: defaultFavourite.destination_hash,
            targetSectionId: "default",
            x: 100,
            y: 100,
        };
        wrapper.vm.sectionContextMenu.show = false;
        await wrapper.vm.$nextTick();

        const menuEls = document.body.querySelectorAll(".context-menu-panel");
        const menuEl = Array.from(menuEls).find((el) => el.textContent.includes("nomadnet.rename"));
        expect(menuEl).toBeTruthy();
        expect(menuEl.textContent).toContain("nomadnet.block_node");
        expect(menuEl.textContent).toContain("nomadnet.remove");
    });

    it("rename from favourite context menu emits rename-favourite", async () => {
        const wrapper = mountSidebar();
        wrapper.vm.favouriteContextMenu = {
            show: true,
            targetHash: defaultFavourite.destination_hash,
            targetSectionId: "default",
        };
        await wrapper.vm.renameFavouriteFromContext();

        expect(wrapper.emitted("rename-favourite")).toBeDefined();
        expect(wrapper.emitted("rename-favourite")).toHaveLength(1);
    });

    it("remove from favourite context menu emits remove-favourite", async () => {
        const wrapper = mountSidebar();
        wrapper.vm.favouriteContextMenu = {
            show: true,
            targetHash: defaultFavourite.destination_hash,
            targetSectionId: "default",
        };
        await wrapper.vm.removeFavouriteFromContext();

        expect(wrapper.emitted("remove-favourite")).toBeDefined();
        expect(wrapper.emitted("remove-favourite")).toHaveLength(1);
    });

    it("banish from favourite context menu calls API and emits block-status-changed", async () => {
        const emitSpy = vi.spyOn(GlobalEmitter, "emit");
        const wrapper = mountSidebar();
        wrapper.vm.favouriteContextMenu = {
            show: true,
            targetHash: defaultFavourite.destination_hash,
            targetSectionId: "default",
        };
        wrapper.vm.sectionContextMenu.show = false;
        await wrapper.vm.$nextTick();

        const menuEls = document.body.querySelectorAll(".context-menu-panel");
        const menuEl = Array.from(menuEls).find((el) => el.textContent.includes("nomadnet.rename"));
        expect(menuEl).toBeTruthy();
        const banishBtn = Array.from(menuEl.querySelectorAll("button")).find((b) =>
            b.textContent.includes("nomadnet.block_node")
        );
        expect(banishBtn).toBeTruthy();
        await banishBtn.click();
        await wrapper.vm.$nextTick();

        expect(DialogUtils.confirm).toHaveBeenCalled();
        expect(axiosMock.post).toHaveBeenCalledWith(
            "/api/v1/blocked-destinations",
            expect.objectContaining({ destination_hash: defaultFavourite.destination_hash })
        );
        expect(emitSpy).toHaveBeenCalledWith("block-status-changed");
        emitSpy.mockRestore();
    });

    it("announces tab shows announce cards with 3-dots dropdown", async () => {
        const wrapper = mountSidebar();
        const announceTab = wrapper.findAll("button").find((b) => b.text().includes("nomadnet.announces"));
        await announceTab.trigger("click");
        await wrapper.vm.$nextTick();

        expect(wrapper.text()).toContain("Test Node");
        const dropMenus = wrapper.findAllComponents({ name: "DropDownMenu" });
        expect(dropMenus.length).toBeGreaterThan(0);
    });

    it("right-click on announce card opens context menu", async () => {
        const wrapper = mountSidebar();
        const announceTab = wrapper.findAll("button").find((b) => b.text().includes("nomadnet.announces"));
        await announceTab.trigger("click");
        await wrapper.vm.$nextTick();

        const announceCard = wrapper.find(".announce-card");
        expect(announceCard.exists()).toBe(true);

        await announceCard.trigger("contextmenu");
        await wrapper.vm.$nextTick();

        expect(wrapper.vm.announceContextMenu.show).toBe(true);
        expect(wrapper.vm.announceContextMenu.node).toEqual(defaultNode);
    });

    it("add favourite from announce context menu emits add-favourite", async () => {
        const wrapper = mountSidebar({ favourites: [] });
        const announceTab = wrapper.findAll("button").find((b) => b.text().includes("nomadnet.announces"));
        await announceTab.trigger("click");
        await wrapper.vm.$nextTick();

        wrapper.vm.announceContextMenu = { show: true, node: defaultNode };
        await wrapper.vm.$nextTick();

        wrapper.vm.addFavouriteFromContext();
        await wrapper.vm.$nextTick();

        expect(wrapper.emitted("add-favourite")).toHaveLength(1);
        expect(wrapper.emitted("add-favourite")[0][0]).toEqual(defaultNode);
    });

    it("block from announce context menu calls API", async () => {
        const emitSpy = vi.spyOn(GlobalEmitter, "emit");
        const wrapper = mountSidebar();
        wrapper.vm.announceContextMenu = { show: true, node: defaultNode };
        await wrapper.vm.$nextTick();

        await wrapper.vm.blockAnnounceFromContext();
        await wrapper.vm.$nextTick();

        expect(DialogUtils.confirm).toHaveBeenCalled();
        expect(axiosMock.post).toHaveBeenCalledWith(
            "/api/v1/blocked-destinations",
            expect.objectContaining({ destination_hash: defaultNode.identity_hash })
        );
        expect(emitSpy).toHaveBeenCalledWith("block-status-changed");
        emitSpy.mockRestore();
    });
});
