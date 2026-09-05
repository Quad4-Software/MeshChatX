// SPDX-License-Identifier: 0BSD

import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { mount } from "@vue/test-utils";
import { readFileSync } from "node:fs";
import { resolve } from "node:path";
import Toast from "@/components/Toast.vue";
import CallOverlay from "@/components/call/CallOverlay.vue";
import GlobalEmitter from "@/js/GlobalEmitter";

const src = (rel) => readFileSync(resolve(__dirname, "../../meshchatx/src/frontend", rel), "utf8");

describe("layout UX oracle-light", () => {
    it("App shell drawer sits in middle pane without fake pt-16 header gap", () => {
        const app = src("components/App.vue");
        expect(app).toContain('class="relative flex flex-1 w-full overflow-hidden');
        expect(app).toContain("absolute inset-y-0 left-0 z-70");
        expect(app).toContain("absolute inset-0 z-65");
        expect(app).not.toContain("pt-16 sm:pt-0");
        expect(app).toContain("pt-[env(safe-area-inset-top,0px)]");
    });

    it("ConversationViewer message list uses overflow-y-auto and composer safe-area", () => {
        const cv = src("features/messages/components/ConversationViewer.svelte");
        const composer = src("features/messages/components/ConversationComposer.svelte");
        expect(cv).toContain('class="min-h-0 flex-1 overflow-y-auto bg-sem-canvas"');
        expect(cv).toContain('data-message-list-mode={useVirtualMessageList ? "virtual" : "flow"}');
        expect(cv).not.toContain("flex-col-reverse");
        expect(composer).toContain("env(safe-area-inset-bottom");
    });

    it("MessagesPage mobile compose FAB and sheet clear safe-area and use dvh", () => {
        const page = src("features/messages/MessagesPage.svelte");
        const compose = src("features/messages/components/MessagesMobileCompose.svelte");
        expect(page).toContain("bottom-[max(1.25rem,env(safe-area-inset-bottom,0px))]");
        expect(compose).toContain("max-h-[90dvh]");
        expect(compose).not.toContain("max-h-[90vh]");
    });

    it("MicronEditor shows tab close on touch and splits at tablet width", () => {
        const page = src("components/micron-editor/MicronEditorPage.vue");
        expect(page).toContain("opacity-100 lg:opacity-0 lg:group-hover:opacity-100");
        expect(page).toContain("window.innerWidth < 768");
    });

    it("Settings page scroll includes bottom safe-area", () => {
        const page = src("components/settings/SettingsPage.vue");
        expect(page).toContain("pb-[max(1.5rem,env(safe-area-inset-bottom))]");
    });

    describe("Toast + CallOverlay stacking", () => {
        let toastWrapper;
        let callWrapper;

        beforeEach(() => {
            toastWrapper = mount(Toast, {
                global: {
                    mocks: { $t: (msg) => msg },
                    stubs: {
                        TransitionGroup: { template: "<div><slot /></div>" },
                        MaterialDesignIcon: { template: '<div class="mdi-stub"></div>', props: ["iconName"] },
                    },
                },
            });
            callWrapper = mount(CallOverlay, {
                props: {
                    activeCall: {
                        remote_identity_hash: "abcdef0123456789abcdef0123456789",
                        remote_identity_name: "Peer",
                        status: 6,
                        is_incoming: false,
                        is_voicemail: false,
                        call_start_time: Date.now() / 1000,
                        tx_bytes: 0,
                        rx_bytes: 0,
                    },
                },
                global: {
                    mocks: {
                        $t: (msg) => msg,
                        $router: { push: vi.fn() },
                    },
                    stubs: {
                        MaterialDesignIcon: true,
                        LxmfUserIcon: true,
                        AudioWaveformPlayer: true,
                        Transition: { template: "<div><slot /></div>" },
                    },
                },
            });
        });

        afterEach(() => {
            toastWrapper?.unmount();
            callWrapper?.unmount();
        });

        it("mobile toast bottom clears compose FAB band", () => {
            const cls = toastWrapper.find("[class*='fixed']").classes().join(" ");
            expect(cls).toContain("max-sm:bottom-[calc(5.5rem+env(safe-area-inset-bottom,0px))]");
        });

        it("call overlay uses safe-area bottom and responsive width", () => {
            const root = callWrapper.find("[class*='fixed']");
            expect(root.exists()).toBe(true);
            const cls = root.classes().join(" ");
            expect(cls).toContain("w-[min(20rem,calc(100%-1.5rem))]");
            expect(cls).toContain("bottom-[max(1rem,env(safe-area-inset-bottom,0px))]");
            expect(cls).toContain("max-sm:bottom-[calc(5.5rem+env(safe-area-inset-bottom,0px))]");
        });
    });

    it("toast dismiss key still works after touch-target change", async () => {
        const wrapper = mount(Toast, {
            global: {
                mocks: { $t: (msg) => msg },
                stubs: {
                    TransitionGroup: { template: "<div><slot /></div>" },
                    MaterialDesignIcon: { template: '<div class="mdi-stub"></div>', props: ["iconName"] },
                },
            },
        });
        GlobalEmitter.emit("toast", { message: "X", duration: 0 });
        await wrapper.vm.$nextTick();
        await wrapper.find("button").trigger("click");
        await wrapper.vm.$nextTick();
        expect(wrapper.text()).not.toContain("X");
        wrapper.unmount();
    });
});
