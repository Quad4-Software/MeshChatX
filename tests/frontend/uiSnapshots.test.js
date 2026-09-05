import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import Toast from "@/components/Toast.vue";
import ConfirmDialog from "@/components/ConfirmDialog.vue";
import FormLabel from "@/components/forms/FormLabel.vue";
import FormSubLabel from "@/components/forms/FormSubLabel.vue";
import IconButton from "@/components/IconButton.vue";
import SidebarLink from "@/components/SidebarLink.vue";
import GlobalEmitter from "@/js/GlobalEmitter";
import { expectHtmlSnapshot, mountSnapshot } from "./snapshotTestUtils.js";

vi.mock("@/js/GlobalEmitter", () => ({
    default: { on: vi.fn(), off: vi.fn(), emit: vi.fn() },
}));

const RouterLinkStub = {
    name: "RouterLinkStub",
    props: ["to"],
    template: '<a class="router-link-stub" href="#"><slot :href="\'#\'" :navigate="() => {}" :isActive="false"/></a>',
};

describe("UI snapshot regression", () => {
    describe("Toast.vue", () => {
        let wrapper;

        beforeEach(() => {
            vi.useFakeTimers();
            wrapper = mountSnapshot(Toast);
        });

        afterEach(() => {
            wrapper?.unmount();
            vi.useRealTimers();
        });

        it("empty state", () => {
            expectHtmlSnapshot(wrapper);
        });

        it("success toast", async () => {
            GlobalEmitter.emit("toast", { message: "Saved", type: "success", duration: 0 });
            await wrapper.vm.$nextTick();
            expectHtmlSnapshot(wrapper);
        });

        it("error toast", async () => {
            GlobalEmitter.emit("toast", { message: "Failed", type: "error", duration: 0 });
            await wrapper.vm.$nextTick();
            expectHtmlSnapshot(wrapper);
        });

        it("loading toast", async () => {
            GlobalEmitter.emit("toast", {
                message: "Working",
                type: "loading",
                duration: 0,
                key: "job-1",
            });
            await wrapper.vm.$nextTick();
            expectHtmlSnapshot(wrapper);
        });
    });

    describe("ConfirmDialog.vue", () => {
        it("visible confirm dialog", async () => {
            const wrapper = mountSnapshot(ConfirmDialog);
            await Promise.resolve();
            await Promise.resolve();
            const showFn = vi.mocked(GlobalEmitter.on).mock.calls.find((c) => c[0] === "confirm")?.[1];
            showFn?.({ message: "Delete this item?", resolve: vi.fn() });
            await Promise.resolve();
            await Promise.resolve();
            expectHtmlSnapshot(wrapper);
            wrapper.unmount();
        });
    });

    describe("FormLabel.vue", () => {
        it("default label", () => {
            const wrapper = mountSnapshot(FormLabel, {
                slots: { default: "Display name" },
            });
            expectHtmlSnapshot(wrapper);
            wrapper.unmount();
        });
    });

    describe("FormSubLabel.vue", () => {
        it("default sub-label", () => {
            const wrapper = mountSnapshot(FormSubLabel, {
                slots: { default: "Optional helper text" },
            });
            expectHtmlSnapshot(wrapper);
            wrapper.unmount();
        });
    });

    describe("IconButton.vue", () => {
        it("icon button", () => {
            const wrapper = mountSnapshot(IconButton, {
                slots: { default: '<span class="icon">+</span>' },
            });
            expectHtmlSnapshot(wrapper);
            wrapper.unmount();
        });
    });

    describe("SidebarLink.vue", () => {
        it("sidebar link", () => {
            const wrapper = mountSnapshot(SidebarLink, {
                props: { to: { name: "messages" } },
                slots: {
                    icon: '<span class="icon-slot">M</span>',
                    text: "Messages",
                },
                global: { stubs: { RouterLink: RouterLinkStub } },
            });
            expectHtmlSnapshot(wrapper);
            wrapper.unmount();
        });
    });
});
