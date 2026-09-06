import { mount } from "@vue/test-utils";
import { describe, it, expect } from "vitest";
import PublishSiteModal from "@/components/micron-editor/PublishSiteModal.vue";

const mountModal = (props = {}) =>
    mount(PublishSiteModal, {
        props: {
            show: true,
            tabs: [
                { id: 1, name: "Home", content: "h" },
                { id: 2, name: "About Us", content: "a" },
                { id: 3, name: "", content: "e" },
            ],
            pageNodes: [{ node_id: "n1", name: "Srv", running: true }],
            ...props,
        },
        global: {
            mocks: {
                $t: (key, params = {}) => {
                    let out = key;
                    for (const [k, v] of Object.entries(params)) {
                        out = out.replace(`{${k}}`, String(v));
                    }
                    return out;
                },
            },
            stubs: {
                MaterialDesignIcon: {
                    template: "<span />",
                    props: ["iconName"],
                },
            },
        },
    });

describe("PublishSiteModal.vue", () => {
    it("builds page entries from tabs with .mu filenames", () => {
        const wrapper = mountModal();
        expect(wrapper.vm.entries.map((e) => e.filename)).toEqual(["Home.mu", "About_Us.mu", "page_3.mu"]);
        expect(wrapper.vm.entries.every((e) => e.include)).toBe(true);
        expect(wrapper.vm.selectedNodeId).toBe("n1");
    });

    it("sanitizes filenames on input", () => {
        const wrapper = mountModal();
        expect(wrapper.vm.sanitizeFilename("My Page!.mu")).toBe("My_Page.mu");
        expect(wrapper.vm.sanitizeFilename("../evil")).toBe("evil");
        expect(wrapper.vm.sanitizeFilename("a/b")).toBe("ab");
    });

    it("reorders entries with moveEntry and drag drop", () => {
        const wrapper = mountModal();
        wrapper.vm.moveEntry(1, -1);
        expect(wrapper.vm.entries.map((e) => e.tabName)).toEqual(["About Us", "Home", ""]);
        wrapper.vm.onDragStart(2);
        wrapper.vm.onDrop(0);
        expect(wrapper.vm.entries.map((e) => e.tabName)).toEqual(["", "About Us", "Home"]);
    });

    it("emits publish with included pages only", async () => {
        const wrapper = mountModal();
        wrapper.vm.entries[1].include = false;
        await wrapper.vm.$nextTick();
        wrapper.vm.submit();
        const events = wrapper.emitted("publish");
        expect(events).toHaveLength(1);
        expect(events[0][0].pages.map((p) => p.name)).toEqual(["Home.mu", "page_3.mu"]);
        expect(events[0][0].nodeId).toBe("n1");
        expect(events[0][0].generateIndex).toBe(true);
    });

    it("requires a server name when creating a new server", () => {
        const wrapper = mountModal();
        wrapper.vm.selectedNodeId = "__new";
        expect(wrapper.vm.canSubmit).toBe(false);
        wrapper.vm.newServerName = "Fresh";
        expect(wrapper.vm.canSubmit).toBe(true);
    });
});
