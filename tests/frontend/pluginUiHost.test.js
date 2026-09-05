// SPDX-License-Identifier: 0BSD

import { describe, expect, it, afterEach } from "vitest";
import { render, cleanup } from "@testing-library/svelte";
import PluginSlotNode from "../../meshchatx/src/frontend/features/plugins/components/PluginSlotNode.svelte";
import {
    validateUiDescriptor,
    KNOWN_NODE_TYPES,
    sanitizePluginAssetSrc,
} from "../../meshchatx/src/frontend/js/plugins/pluginUiDescriptor.js";
import { isKnownHostWidget } from "../../meshchatx/src/frontend/js/plugins/pluginHostWidgets.js";
import { getThemeSnapshot } from "../../meshchatx/src/frontend/theme/themeEngine.js";

describe("pluginUiDescriptor", () => {
    it("accepts known vocabulary and rejects unknown types", () => {
        expect(KNOWN_NODE_TYPES).toContain("tabs");
        expect(KNOWN_NODE_TYPES).toContain("table");
        expect(KNOWN_NODE_TYPES).toContain("code");
        const ok = validateUiDescriptor({
            type: "column",
            children: [{ type: "text", value: "hi" }],
        });
        expect(ok.ok).toBe(true);
        const bad = validateUiDescriptor({ type: "script" });
        expect(bad.ok).toBe(false);
        expect(String(bad.error)).toMatch(/Unknown UI node type/);
    });

    it("requires sandboxed-html permission for html-frame", () => {
        const denied = validateUiDescriptor({ type: "html-frame", srcdoc: "<p>x</p>" });
        expect(denied.ok).toBe(false);
        const allowed = validateUiDescriptor({ type: "html-frame", srcdoc: "<p>x</p>" }, { allowHtmlFrame: true });
        expect(allowed.ok).toBe(true);
    });

    it("restricts image src to plugin asset URLs", () => {
        const pluginId = "com.meshchatx.mcx-bugs";
        expect(sanitizePluginAssetSrc(pluginId, `/api/v1/plugins/${pluginId}/asset/icon.png`)).toBeTruthy();
        expect(sanitizePluginAssetSrc(pluginId, "https://evil.example/x.png")).toBeNull();
        expect(sanitizePluginAssetSrc(pluginId, `/api/v1/plugins/${pluginId}/asset/../secret`)).toBeNull();
    });

    it("restricts html-frame src to plugin asset URLs", () => {
        const pluginId = "com.meshchatx.mcx-bugs";
        const evil = validateUiDescriptor(
            { type: "html-frame", src: "https://evil.example/exfil" },
            { allowHtmlFrame: true, pluginId }
        );
        expect(evil.ok).toBe(false);
        expect(String(evil.error)).toMatch(/html-frame src must be a plugin asset URL/);

        const asset = `/api/v1/plugins/${pluginId}/asset/frame.html`;
        const ok = validateUiDescriptor({ type: "html-frame", src: asset }, { allowHtmlFrame: true, pluginId });
        expect(ok.ok).toBe(true);
        expect(ok.descriptor.src).toBe(asset);

        const srcdocOnly = validateUiDescriptor(
            { type: "html-frame", srcdoc: "<p>ok</p>" },
            { allowHtmlFrame: true, pluginId }
        );
        expect(srcdocOnly.ok).toBe(true);
        expect(srcdocOnly.descriptor.src || "").toBe("");
    });

    it("does not fall back to unsanitized html-frame src", async () => {
        const { container } = render(PluginSlotNode, {
            props: {
                node: { type: "html-frame", src: "https://evil.example/x", srcdoc: "" },
                pluginId: "com.example.test",
                allowHtmlFrame: true,
            },
        });
        const frame = container.querySelector("iframe");
        expect(frame).toBeTruthy();
        expect(frame?.getAttribute("src") || "").toBe("");
    });

    it("knows reviewed host widgets", () => {
        expect(isKnownHostWidget("IssueStackView")).toBe(true);
        expect(isKnownHostWidget("EvilWidget")).toBe(false);
    });
});

describe("PluginSlotNode theming", () => {
    afterEach(() => {
        cleanup();
    });

    it("uses semantic action classes instead of blue-600", () => {
        const { container } = render(PluginSlotNode, {
            props: {
                node: { type: "button", id: "go", label: "Go" },
                pluginId: "com.example.test",
            },
        });
        const btn = container.querySelector("button");
        expect(btn).toBeTruthy();
        expect(btn?.className).toContain("bg-sem-action-primary");
        expect(btn?.className).not.toContain("bg-blue-600");
    });

    it("renders code blocks with surface-muted styling", () => {
        const { container } = render(PluginSlotNode, {
            props: {
                node: { type: "code", value: "stack\nframe" },
                pluginId: "com.example.test",
            },
        });
        const pre = container.querySelector("pre");
        expect(pre).toBeTruthy();
        expect(pre?.className).toContain("bg-sem-surface-muted");
        expect(pre?.textContent).toContain("stack");
    });
});

describe("getThemeSnapshot", () => {
    it("returns preference effective preset and accent", () => {
        const snap = getThemeSnapshot(
            { theme: "dark", theme_preset: "nord", accent_color: "#88c0d0" },
            { prefersDark: true }
        );
        expect(snap.preference).toBe("dark");
        expect(snap.effective).toBe("dark");
        expect(snap.preset).toBe("nord");
        expect(snap.accent).toBe("#88c0d0");
    });
});
