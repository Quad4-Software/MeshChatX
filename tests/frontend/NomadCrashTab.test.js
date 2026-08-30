// SPDX-License-Identifier: 0BSD
import { mount } from "@vue/test-utils";
import { describe, expect, it, vi, beforeEach, afterEach } from "vitest";
import NomadCrashTab from "@/components/nomadnetwork/NomadCrashTab.vue";
import { NOMAD_CRASH_TAB_CHANNEL } from "@/js/nomadCrashTabShell.js";

describe("NomadCrashTab.vue", () => {
    let postMessageSpy;

    beforeEach(() => {
        postMessageSpy = vi.fn();
    });

    afterEach(() => {
        vi.restoreAllMocks();
    });

    const mountCrashTab = (props = {}) => {
        return mount(NomadCrashTab, {
            props: {
                path: "aabb:/page/index.mu",
                content: ">#!\n# Hi",
                active: true,
                ...props,
            },
            global: {
                mocks: {
                    $t: (key) => key,
                },
            },
        });
    };

    it("abortRender skips re-push after iframe reload ready", async () => {
        const wrapper = mountCrashTab();
        const frame = wrapper.find("iframe");
        expect(frame.attributes("sandbox")).toBe("allow-scripts");
        expect(frame.attributes("allow")).toBe("local-network-access");
        expect(frame.classes()).toContain("absolute");
        expect(frame.classes()).toContain("inset-0");
        const frameEl = frame.element;
        Object.defineProperty(frameEl, "contentWindow", {
            configurable: true,
            get: () => ({ postMessage: postMessageSpy }),
        });

        wrapper.vm.frameReady = true;
        wrapper.vm.pushRender();
        expect(postMessageSpy).toHaveBeenCalled();
        const renderCalls = postMessageSpy.mock.calls.filter((c) => c[0]?.type === "render");
        expect(renderCalls.length).toBe(1);

        postMessageSpy.mockClear();
        wrapper.vm.abortRender();
        expect(wrapper.vm.skipRenderUntilPropChange).toBe(true);
        expect(wrapper.emitted("aborted")?.length).toBe(1);
        expect(wrapper.emitted("render-done")?.length).toBe(1);

        wrapper.vm.frameReady = true;
        wrapper.vm.pushRender();
        expect(postMessageSpy.mock.calls.filter((c) => c[0]?.type === "render").length).toBe(0);

        await wrapper.setProps({ content: ">#!\n# New" });
        expect(wrapper.vm.skipRenderUntilPropChange).toBe(false);
    });

    it("ignores aborted echo from frame after hard cancel", () => {
        const wrapper = mountCrashTab();
        const frame = wrapper.find("iframe").element;
        const fakeWindow = { postMessage: postMessageSpy };
        Object.defineProperty(frame, "contentWindow", {
            configurable: true,
            get: () => fakeWindow,
        });

        wrapper.vm.abortRender();
        expect(wrapper.emitted("aborted")?.length).toBe(1);

        wrapper.vm.onWindowMessage({
            source: fakeWindow,
            data: { channel: NOMAD_CRASH_TAB_CHANNEL, type: "aborted" },
        });
        expect(wrapper.emitted("aborted")?.length).toBe(1);
    });

    it("postToFrame JSON-clones Vue-like proxies so structured clone succeeds", () => {
        const wrapper = mountCrashTab({
            pagePartials: { p1: "<b>x</b>" },
            renderOptions: { nomad_micron_wasm_use: true, renderMarkdown: true },
        });
        const frame = wrapper.find("iframe").element;
        Object.defineProperty(frame, "contentWindow", {
            configurable: true,
            get: () => ({ postMessage: postMessageSpy }),
        });

        // Simulate a reactive-looking nested object (Proxy) that DataClone rejects.
        const reactivePartials = new Proxy(
            { p1: "<b>x</b>" },
            {
                get(target, prop, receiver) {
                    return Reflect.get(target, prop, receiver);
                },
            }
        );
        wrapper.vm.frameReady = true;
        const ok = wrapper.vm.postToFrame({
            type: "render",
            path: "aabb:/page/index.mu",
            content: "# Hi",
            pagePartials: reactivePartials,
            renderOptions: { nomad_micron_wasm_use: true },
        });
        expect(ok).toBe(true);
        expect(postMessageSpy).toHaveBeenCalledOnce();
        const payload = postMessageSpy.mock.calls[0][0];
        expect(payload.channel).toBe(NOMAD_CRASH_TAB_CHANNEL);
        expect(payload.pagePartials).toEqual({ p1: "<b>x</b>" });
        expect(payload.renderOptions.nomad_micron_wasm_use).toBe(true);
        expect(Object.getPrototypeOf(payload.pagePartials)).toBe(Object.prototype);
    });

    it("crash-tab entry installs DOMPurify for the JS micron-parser path", async () => {
        const fs = await import("node:fs");
        const path = await import("node:path");
        const src = fs.readFileSync(
            path.resolve(__dirname, "../../meshchatx/src/frontend/js/nomadCrashTabMain.js"),
            "utf8"
        );
        expect(src).toMatch(/import DOMPurify from ["']dompurify["']/);
        expect(src).toContain("globalThis.DOMPurify = DOMPurify");
        expect(src).toContain("window.DOMPurify = DOMPurify");
        expect(src).toContain('import "../css/nomad-page-chrome.css"');
        expect(src).toContain('import "../fonts/RobotoMonoNerdFont/font.css"');
        expect(src).toContain('parts = ["nodeContainer"]');
    });
});
