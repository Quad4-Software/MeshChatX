// SPDX-License-Identifier: 0BSD

import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { mount } from "@vue/test-utils";
import { readFileSync } from "node:fs";
import { resolve } from "node:path";
import ToastSvelte from "@/ui/svelte/Toast.svelte";
import { render, fireEvent, waitFor } from "@testing-library/svelte";
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
        const cv = src("features/messages/components/ConversationViewerListPane.svelte");
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
        const page = src("features/micron-editor/MicronEditorPage.svelte");
        const tab = src("features/micron-editor/components/MicronEditorTabBar.svelte");
        expect(tab).toContain("opacity-100 lg:opacity-0 lg:group-hover:opacity-100");
        expect(page).toContain("window.innerWidth < 768");
    });

    it("Settings page scroll includes bottom safe-area", () => {
        const page = src("features/settings/components/SettingsPage.svelte");
        expect(page).toContain("pb-[max(1.5rem,env(safe-area-inset-bottom))]");
    });

    describe("Toast + CallOverlay stacking", () => {
        it("mobile toast bottom clears compose FAB band", () => {
            const toastSrc = src("ui/svelte/Toast.svelte");
            expect(toastSrc).toContain("max-sm:bottom-[calc(5.5rem+env(safe-area-inset-bottom,0px))]");
        });

        it("call overlay uses safe-area bottom and responsive width", () => {
            const overlay = src("features/call/components/CallOverlay.svelte");
            expect(overlay).toContain("w-[min(20rem,calc(100%-1.5rem))]");
            expect(overlay).toContain("bottom-[max(1rem,env(safe-area-inset-bottom,0px))]");
            expect(overlay).toContain("max-sm:bottom-[calc(5.5rem+env(safe-area-inset-bottom,0px))]");
        });
    });

    it("toast dismiss key still works after touch-target change", async () => {
        const { container, findByText } = render(ToastSvelte);
        GlobalEmitter.emit("toast", { message: "X", duration: 0 });
        await findByText("X");
        const btn = container.querySelector("button");
        await fireEvent.click(btn);
        await waitFor(() => {
            expect(container.textContent).not.toContain("X");
        });
    });
});
