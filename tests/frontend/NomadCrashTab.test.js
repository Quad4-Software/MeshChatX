// SPDX-License-Identifier: 0BSD
import { readFileSync } from "fs";
import { join } from "path";
import { render, cleanup, waitFor } from "@testing-library/svelte";
import { describe, expect, it, vi, beforeEach, afterEach } from "vitest";
import NomadCrashTab from "@/features/nomadnetwork/components/NomadCrashTab.svelte";
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

function dispatchFrameMessage(frameWindow, data) {
    const event = new MessageEvent("message", {
        data,
    });
    Object.defineProperty(event, "source", { value: frameWindow, configurable: true });
    Object.defineProperty(event, "origin", { value: "null", configurable: true });
    window.dispatchEvent(event);
}

describe("NomadCrashTab.svelte", () => {
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
        cleanup();
        vi.restoreAllMocks();
        if (previousVisibilityState) {
            Object.defineProperty(document, "visibilityState", previousVisibilityState);
        }
        if (previousHidden) {
            Object.defineProperty(document, "hidden", previousHidden);
        }
    });

    it("renders iframe with sandbox attributes", () => {
        const { baseElement } = render(NomadCrashTab, {
            path: "aabb:/page/index.mu",
            content: ">#!\n# Hi",
            active: true,
        });
        const frame = baseElement.querySelector("iframe");
        expect(frame).toBeTruthy();
        expect(frame.getAttribute("sandbox")).toBe("allow-scripts");
        expect(frame.getAttribute("allow")).toBe("local-network-access");
    });

    it("parks the frame on document.body so host detach keeps it alive", () => {
        const { baseElement, container } = render(NomadCrashTab, {
            path: "aabb:/page/index.mu",
            content: ">#!\n# Hi",
            active: true,
        });
        const frame = baseElement.querySelector("iframe");
        expect(frame.parentElement).toBe(document.body);
        expect(container.contains(frame)).toBe(false);
        expect(frame.style.position).toBe("fixed");
    });

    it("parks the frame over the host rect and hides it while inactive", async () => {
        const { baseElement, container, rerender } = render(NomadCrashTab, {
            path: "aabb:/page/index.mu",
            content: ">#!\n# Hi",
            active: true,
        });
        const host = container.querySelector(".nomad-crash-tab");
        const frame = baseElement.querySelector("iframe");
        // jsdom reports a zero rect, so the frame starts hidden.
        expect(frame.style.visibility).toBe("hidden");

        host.getBoundingClientRect = () => ({ left: 10, top: 20, width: 300, height: 200 });
        window.dispatchEvent(new Event("resize"));

        await waitFor(() => {
            expect(frame.style.visibility).toBe("visible");
        });
        expect(frame.style.left).toBe("10px");
        expect(frame.style.top).toBe("20px");
        expect(frame.style.width).toBe("300px");
        expect(frame.style.height).toBe("200px");

        await rerender({ path: "aabb:/page/index.mu", content: ">#!\n# Hi", active: false });
        expect(frame.style.visibility).toBe("hidden");
        expect(frame.style.pointerEvents).toBe("none");
    });

    it("polls the host rect during geometry transitions", async () => {
        const { baseElement, container } = render(NomadCrashTab, {
            path: "aabb:/page/index.mu",
            content: ">#!\n# Hi",
            active: true,
        });
        const host = container.querySelector(".nomad-crash-tab");
        const frame = baseElement.querySelector("iframe");
        host.getBoundingClientRect = () => ({ left: 50, top: 5, width: 100, height: 50 });

        const event = new Event("transitionrun");
        Object.defineProperty(event, "propertyName", { value: "transform", configurable: true });
        document.dispatchEvent(event);

        await waitFor(() => {
            expect(frame.style.visibility).toBe("visible");
        });
        expect(frame.style.left).toBe("50px");
    });

    it("ignores paint-only transitions", async () => {
        render(NomadCrashTab, {
            path: "aabb:/page/index.mu",
            content: ">#!\n# Hi",
            active: true,
        });
        const rafSpy = vi.spyOn(window, "requestAnimationFrame");
        const event = new Event("transitionrun");
        Object.defineProperty(event, "propertyName", { value: "background-color", configurable: true });
        document.dispatchEvent(event);
        await new Promise((resolve) => setTimeout(resolve, 30));
        expect(rafSpy).not.toHaveBeenCalled();
    });

    it("posts render message to iframe when frame is ready", async () => {
        const { baseElement } = render(NomadCrashTab, {
            path: "aabb:/page/index.mu",
            content: ">#!\n# Hi",
            active: true,
        });
        const frame = baseElement.querySelector("iframe");
        const fakeWindow = { postMessage: postMessageSpy };
        Object.defineProperty(frame, "contentWindow", {
            configurable: true,
            get: () => fakeWindow,
        });

        dispatchFrameMessage(fakeWindow, {
            channel: NOMAD_CRASH_TAB_CHANNEL,
            type: "ready",
        });

        await waitFor(() => {
            expect(postMessageSpy).toHaveBeenCalled();
            const renderCalls = postMessageSpy.mock.calls.filter((c) => c[0]?.type === "render");
            expect(renderCalls.length).toBeGreaterThanOrEqual(1);
        });
    });

    it("handles frame navigation messages", async () => {
        const onnavigate = vi.fn();
        const { baseElement } = render(NomadCrashTab, {
            path: "aabb:/page/index.mu",
            content: ">#!\n# Hi",
            active: true,
            onnavigate,
        });
        const frame = baseElement.querySelector("iframe");
        const fakeWindow = { postMessage: postMessageSpy };
        Object.defineProperty(frame, "contentWindow", {
            configurable: true,
            get: () => fakeWindow,
        });

        dispatchFrameMessage(fakeWindow, {
            channel: NOMAD_CRASH_TAB_CHANNEL,
            type: "navigate",
            url: "aabb:/page/other.mu",
        });

        await waitFor(() => {
            expect(onnavigate).toHaveBeenCalledWith(expect.objectContaining({ url: "aabb:/page/other.mu" }));
        });
    });
});

describe("nomadCrashTabMain entry contract", () => {
    function readEntrySource() {
        return readFileSync(join(process.cwd(), "meshchatx/src/frontend/js/nomadCrashTabMain.ts"), "utf8");
    }

    it("crash-tab entry boots dark and lazy-loads the Micron renderer", () => {
        const src = readEntrySource();
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
        expect(src).toMatch(/try \{\s*id = decodeURIComponent\(id\)/);
        expect(src).not.toContain('replace(/"/g, "")');
    });

    it("crash-tab entry routes field long-press to the parent paste flow", () => {
        const src = readEntrySource();
        expect(src).toContain('post({ type: "field-contextmenu"');
        expect(src).toContain('d.type === "paste-text"');
        expect(src).toContain('root.addEventListener("contextmenu", onFieldContextMenu, true)');
        expect(src).toContain('el.setRangeText(value, start, end, "end")');
    });
});
