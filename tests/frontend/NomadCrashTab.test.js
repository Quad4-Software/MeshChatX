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
        const { container } = render(NomadCrashTab, {
            path: "aabb:/page/index.mu",
            content: ">#!\n# Hi",
            active: true,
        });
        const frame = container.querySelector("iframe");
        expect(frame).toBeTruthy();
        expect(frame.getAttribute("sandbox")).toBe("allow-scripts");
        expect(frame.getAttribute("allow")).toBe("local-network-access");
    });

    it("posts render message to iframe when frame is ready", async () => {
        const { container } = render(NomadCrashTab, {
            path: "aabb:/page/index.mu",
            content: ">#!\n# Hi",
            active: true,
        });
        const frame = container.querySelector("iframe");
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
        const { container } = render(NomadCrashTab, {
            path: "aabb:/page/index.mu",
            content: ">#!\n# Hi",
            active: true,
            onnavigate,
        });
        const frame = container.querySelector("iframe");
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
        return readFileSync(
            join(process.cwd(), "meshchatx/src/frontend/js/nomadCrashTabMain.ts"),
            "utf8"
        );
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
