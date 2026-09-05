// SPDX-License-Identifier: 0BSD

import { render, cleanup, screen, fireEvent } from "@testing-library/svelte";
import { describe, it, expect, afterEach, beforeEach, vi } from "vitest";
import NetworkVisualiserToolbar from "@/features/network-visualiser/components/NetworkVisualiserToolbar.svelte";
import { registerFallbackMessages, registerTranslator } from "@/js/i18n.js";
import en from "@/locales/en.json";

describe("NetworkVisualiserToolbar.svelte", () => {
    beforeEach(() => {
        registerTranslator(null);
        registerFallbackMessages(en);
    });

    afterEach(() => {
        cleanup();
    });

    const renderToolbar = (props = {}) => {
        return render(NetworkVisualiserToolbar, {
            props: {
                isShowingControls: true,
                nodeCount: 12,
                edgeCount: 8,
                onlineInterfaceCount: 2,
                offlineInterfaceCount: 1,
                preferredRenderer: "auto",
                engineMode: "wasm",
                fps: 58,
                isWideViewport: true,
                ...props,
            },
        });
    };

    it("keeps the control panel at a fixed sm width class", () => {
        const { container } = renderToolbar();
        const panel = container.querySelector(".pointer-events-auto.border");
        expect(panel?.className).toContain("sm:w-[280px]");
        expect(panel?.className).toContain("sm:max-w-[280px]");
    });

    it("shows themed engine trigger and FPS without a native select", () => {
        const { container } = renderToolbar();
        expect(container.querySelector("select")).toBeNull();
        const trigger = container.querySelector("#visualiser-engine-select");
        expect(trigger).toBeTruthy();
        expect(trigger?.tagName).toBe("BUTTON");
        expect(container.textContent).toContain("58");
    });

    it("opens custom engine menu and emits preferred renderer", async () => {
        const onUpdatePreferredRenderer = vi.fn();
        const { container } = render(NetworkVisualiserToolbar, {
            props: {
                isShowingControls: true,
                preferredRenderer: "auto",
                engineMode: "webgl",
                fps: 60,
                isWideViewport: true,
                onupdatepreferredrenderer: onUpdatePreferredRenderer,
            },
        });

        const trigger = container.querySelector("#visualiser-engine-select");
        expect(trigger).toBeTruthy();
        await fireEvent.click(trigger);

        const listbox = document.querySelector('[role="listbox"]');
        expect(listbox).toBeTruthy();

        const options = document.querySelectorAll('[role="option"]');
        expect(options.length).toBe(3);
        await fireEvent.click(options[1]);
        expect(onUpdatePreferredRenderer).toHaveBeenCalledWith("webgl");
    });

    it("hides planet view buttons unless the engine is WebGL", () => {
        const { container } = renderToolbar({ engineMode: "wasm" });
        expect(container.querySelector("#visualiser-view-planet")).toBeNull();
        expect(container.querySelector("#visualiser-view-flat")).toBeNull();
    });

    it("shows planet view buttons when engine is WebGL", () => {
        const { container } = renderToolbar({ engineMode: "webgl" });
        expect(container.querySelector("#visualiser-view-planet")).toBeTruthy();
    });
});
