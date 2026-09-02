// SPDX-License-Identifier: 0BSD
import { mount } from "@vue/test-utils";
import { describe, expect, it, vi, beforeEach, afterEach } from "vitest";
import NomadCrashTab from "@/components/nomadnetwork/NomadCrashTab.vue";
import { NOMAD_CRASH_TAB_CHANNEL } from "@/js/nomadCrashTabShell.js";

function setDocumentVisibility(state) {
    Object.defineProperty(document, "visibilityState", {
        configurable: true,
        get: () => state,
    });
    Object.defineProperty(document, "hidden", {
        configurable: true,
        get: () => state === "hidden",
    });
}

describe("NomadCrashTab.vue", () => {
    let postMessageSpy;
    let previousVisibilityState;
    let previousHidden;

    beforeEach(() => {
        postMessageSpy = vi.fn();
        previousVisibilityState = Object.getOwnPropertyDescriptor(document, "visibilityState");
        previousHidden = Object.getOwnPropertyDescriptor(document, "hidden");
        setDocumentVisibility("visible");
    });

    afterEach(() => {
        vi.restoreAllMocks();
        if (previousVisibilityState) {
            Object.defineProperty(document, "visibilityState", previousVisibilityState);
        }
        if (previousHidden) {
            Object.defineProperty(document, "hidden", previousHidden);
        }
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

    const attachFrame = (wrapper) => {
        const frameEl = wrapper.find("iframe").element;
        Object.defineProperty(frameEl, "contentWindow", {
            configurable: true,
            get: () => ({ postMessage: postMessageSpy }),
        });
        return frameEl;
    };

    const mountReadyCrashTab = (props = {}) => {
        const wrapper = mountCrashTab(props);
        attachFrame(wrapper);
        wrapper.vm.frameReady = true;
        wrapper.vm.status = "ready";
        wrapper.vm.lastPongAt = Date.now();
        return wrapper;
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
        await wrapper.vm.$nextTick();
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
            origin: "null",
            data: { channel: NOMAD_CRASH_TAB_CHANNEL, type: "aborted" },
        });
        expect(wrapper.emitted("aborted")?.length).toBe(1);
    });

    it("ignores frame messages that are not opaque-null origin", () => {
        const wrapper = mountCrashTab();
        const frame = wrapper.find("iframe").element;
        const fakeWindow = { postMessage: postMessageSpy };
        Object.defineProperty(frame, "contentWindow", {
            configurable: true,
            get: () => fakeWindow,
        });

        wrapper.vm.onWindowMessage({
            source: fakeWindow,
            origin: "https://evil.example",
            data: { channel: NOMAD_CRASH_TAB_CHANNEL, type: "ready" },
        });
        expect(wrapper.vm.frameReady).toBe(false);
        expect(wrapper.emitted("ready")).toBeUndefined();
    });

    it("postToFrame uses * targetOrigin for opaque-origin frame", () => {
        const wrapper = mountCrashTab();
        const frame = wrapper.find("iframe").element;
        Object.defineProperty(frame, "contentWindow", {
            configurable: true,
            get: () => ({ postMessage: postMessageSpy }),
        });
        wrapper.vm.postToFrame({ type: "ping", id: 1 });
        expect(postMessageSpy).toHaveBeenCalledOnce();
        // HTML forbids targetOrigin "null" when the target browsing context is opaque.
        expect(postMessageSpy.mock.calls[0][1]).toBe("*");
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

    it("unstable renderOptions object identity does not retrigger render after done", async () => {
        const wrapper = mountCrashTab({
            renderOptions: { renderMarkdown: true },
        });
        const frame = wrapper.find("iframe").element;
        Object.defineProperty(frame, "contentWindow", {
            configurable: true,
            get: () => ({ postMessage: postMessageSpy }),
        });
        wrapper.vm.frameReady = true;
        wrapper.vm.pushRender();
        await wrapper.vm.$nextTick();
        postMessageSpy.mockClear();

        // Simulate parent re-creating the options object with the same values.
        await wrapper.setProps({ renderOptions: { renderMarkdown: true } });
        await wrapper.vm.$nextTick();
        await Promise.resolve();
        const renderCalls = postMessageSpy.mock.calls.filter((c) => c[0]?.type === "render");
        expect(renderCalls.length).toBe(0);
    });

    it("background and contentClass chrome updates do not emit render-started", async () => {
        const wrapper = mountCrashTab({
            background: "#000000",
            contentClass: "nomad-page-rich bg-black",
        });
        const frame = wrapper.find("iframe").element;
        Object.defineProperty(frame, "contentWindow", {
            configurable: true,
            get: () => ({ postMessage: postMessageSpy }),
        });
        wrapper.vm.frameReady = true;
        wrapper.vm.status = "ready";
        wrapper.vm.framePainted = true;
        wrapper.vm.lastPostedRenderKey = wrapper.vm.contentRenderKey;

        await wrapper.setProps({ background: "rgb(0, 0, 0)", contentClass: "nomad-page-rich bg-black pad" });
        await wrapper.vm.$nextTick();
        await Promise.resolve();

        expect(wrapper.emitted("render-started")).toBeUndefined();
        const chromeCalls = postMessageSpy.mock.calls.filter((c) => c[0]?.type === "chrome");
        expect(chromeCalls.length).toBeGreaterThanOrEqual(1);
        const renderCalls = postMessageSpy.mock.calls.filter((c) => c[0]?.type === "render");
        expect(renderCalls.length).toBe(0);
    });

    it("render deadline emits hung when paint never completes", async () => {
        vi.useFakeTimers();
        let wrapper;
        try {
            wrapper = mountCrashTab();
            attachFrame(wrapper);
            wrapper.vm.frameReady = true;
            wrapper.vm.pushRender();
            await wrapper.vm.$nextTick();
            expect(wrapper.emitted("render-started")?.length).toBe(1);

            vi.advanceTimersByTime(20000);
            expect(wrapper.vm.status).toBe("hung");
            expect(wrapper.emitted("hung")?.length).toBe(1);
        } finally {
            wrapper?.unmount();
            vi.useRealTimers();
        }
    });

    it("does not mark hung after ping silence while the document is hidden", () => {
        vi.useFakeTimers();
        let wrapper;
        try {
            wrapper = mountReadyCrashTab();
            setDocumentVisibility("hidden");
            wrapper.vm.onVisibilityChange();
            vi.advanceTimersByTime(30000);
            expect(wrapper.vm.status).toBe("ready");
            expect(wrapper.emitted("hung")).toBeUndefined();

            setDocumentVisibility("visible");
            wrapper.vm.onVisibilityChange();
            vi.advanceTimersByTime(2000);
            expect(wrapper.vm.status).toBe("ready");
            expect(wrapper.emitted("hung")).toBeUndefined();
        } finally {
            wrapper?.unmount();
            vi.useRealTimers();
        }
    });

    it("does not mark hung across freeze and resume", () => {
        vi.useFakeTimers();
        let wrapper;
        try {
            wrapper = mountReadyCrashTab();
            wrapper.vm.onPageFreeze();
            vi.advanceTimersByTime(30000);
            expect(wrapper.vm.status).toBe("ready");
            expect(wrapper.emitted("hung")).toBeUndefined();

            wrapper.vm.onPageResume();
            vi.advanceTimersByTime(2000);
            expect(wrapper.vm.status).toBe("ready");
            expect(wrapper.emitted("hung")).toBeUndefined();
        } finally {
            wrapper?.unmount();
            vi.useRealTimers();
        }
    });

    it("marks hung after ping silence while the document stays visible", () => {
        vi.useFakeTimers();
        let wrapper;
        try {
            wrapper = mountReadyCrashTab();
            vi.advanceTimersByTime(13000);
            expect(wrapper.vm.status).toBe("hung");
            expect(wrapper.emitted("hung")?.length).toBe(1);
        } finally {
            wrapper?.unmount();
            vi.useRealTimers();
        }
    });

    it("treats a coalesced wake gap as a stall instead of a hang", () => {
        vi.useFakeTimers();
        let wrapper;
        try {
            wrapper = mountReadyCrashTab();
            wrapper.vm.lastPongAt = Date.now() - 30000;
            wrapper.vm.checkWatchdog();
            expect(wrapper.vm.status).toBe("ready");
            expect(wrapper.emitted("hung")).toBeUndefined();
            expect(postMessageSpy.mock.calls.some((c) => c[0]?.type === "ping")).toBe(true);

            vi.advanceTimersByTime(13000);
            expect(wrapper.vm.status).toBe("hung");
            expect(wrapper.emitted("hung")?.length).toBe(1);
        } finally {
            wrapper?.unmount();
            vi.useRealTimers();
        }
    });

    it("does not fire the render deadline while the document is hidden", async () => {
        vi.useFakeTimers();
        let wrapper;
        try {
            wrapper = mountCrashTab();
            attachFrame(wrapper);
            wrapper.vm.frameReady = true;
            wrapper.vm.pushRender();
            await wrapper.vm.$nextTick();
            expect(wrapper.emitted("render-started")?.length).toBe(1);

            setDocumentVisibility("hidden");
            wrapper.vm.onVisibilityChange();
            vi.advanceTimersByTime(25000);
            expect(wrapper.vm.status).toBe("rendering");
            expect(wrapper.emitted("hung")).toBeUndefined();

            setDocumentVisibility("visible");
            wrapper.vm.onVisibilityChange();
            vi.advanceTimersByTime(20000);
            expect(wrapper.vm.status).toBe("hung");
            expect(wrapper.emitted("hung")?.length).toBe(1);
        } finally {
            wrapper?.unmount();
            vi.useRealTimers();
        }
    });

    it("does not start the ping watchdog while the document is hidden", () => {
        const wrapper = mountReadyCrashTab();
        try {
            setDocumentVisibility("hidden");
            wrapper.vm.onVisibilityChange();
            wrapper.vm.startWatchdog();
            expect(wrapper.vm.watchdogTimer).toBeNull();
            expect(wrapper.vm.pingTimer).toBeNull();
        } finally {
            wrapper.unmount();
        }
    });

    it("does not deep-watch renderOptions object identity", () => {
        const wrapper = mountCrashTab();
        const src = wrapper.vm.$options.watch || {};
        // Watchers are on stable JSON keys, not deep object identity.
        expect(wrapper.vm.renderOptionsKey).toEqual(expect.any(String));
        expect(wrapper.vm.pagePartialsKey).toEqual(expect.any(String));
        expect(src.renderOptions).toBeUndefined();
        expect(src.pagePartials).toBeUndefined();
        expect(src.renderOptionsKey).toBeTruthy();
        expect(src.pagePartialsKey).toBeTruthy();
    });

    it("crash-tab entry boots dark and lazy-loads the Micron renderer", async () => {
        const fs = await import("node:fs");
        const path = await import("node:path");
        const src = fs.readFileSync(
            path.resolve(__dirname, "../../meshchatx/src/frontend/js/nomadCrashTabMain.js"),
            "utf8"
        );
        expect(src).toContain('import "../css/nomad-page-chrome.css"');
        expect(src).toContain('parts = ["nodeContainer"]');
        expect(src).toContain("paintShell");
        expect(src).toContain("loadRenderer");
        expect(src).toContain('import("./MicronParser.js")');
        expect(src).toContain('import("dompurify")');
        expect(src).toContain("globalThis.DOMPurify = DOMPurify");
        expect(src).toContain('import("../fonts/RobotoMonoNerdFont/font.css")');
        expect(src).toContain('parent.postMessage({ channel: NOMAD_CRASH_TAB_CHANNEL, ...msg }, "*")');
        expect(src).not.toContain("parentTargetOrigin");
        expect(src).toContain('d.type === "chrome"');
        expect(src).not.toMatch(/^import MicronParser from/m);
    });
});
