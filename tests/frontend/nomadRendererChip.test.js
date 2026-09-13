// SPDX-License-Identifier: 0BSD

/**
 * Oracles for Nomad toolbar renderer chip (Vue NomadNetworkPage parity).
 */

import { describe, expect, it } from "vitest";
import {
    buildNomadBrowserRendererChip,
    shouldShowMicronRendererInMobileMenu,
} from "../../meshchatx/src/frontend/features/nomadnetwork/lib/nomadRendererChip.ts";

const t = (key, params) => {
    if (params && Object.keys(params).length) {
        return `${key}:${JSON.stringify(params)}`;
    }
    return key;
};

const baseMu = {
    selectedNode: { destination_hash: "abcd" },
    relativePagePath: "/page/index.mu",
    isShowingNodePageSource: false,
    nomadMicronWasmActive: false,
    nomadMicronWasmFeatureEffective: true,
    nomadMicronWasmReady: true,
    defaultEngine: "js",
    micronGoRelease: "v1.2.3",
    t,
};

describe("buildNomadBrowserRendererChip", () => {
    it("returns null with no selected node or page path", () => {
        expect(
            buildNomadBrowserRendererChip({
                ...baseMu,
                selectedNode: null,
            })
        ).toBeNull();
        expect(
            buildNomadBrowserRendererChip({
                ...baseMu,
                relativePagePath: null,
            })
        ).toBeNull();
        expect(
            buildNomadBrowserRendererChip({
                ...baseMu,
                relativePagePath: "",
            })
        ).toBeNull();
    });

    it("returns null while showing page source", () => {
        expect(
            buildNomadBrowserRendererChip({
                ...baseMu,
                isShowingNodePageSource: true,
            })
        ).toBeNull();
    });

    it("returns null for unknown page extensions", () => {
        expect(
            buildNomadBrowserRendererChip({
                ...baseMu,
                relativePagePath: "/page/file.bin",
            })
        ).toBeNull();
    });

    it("uses wasm_active when Micron WASM is active on .mu", () => {
        const chip = buildNomadBrowserRendererChip({
            ...baseMu,
            nomadMicronWasmActive: true,
        });
        expect(chip).toEqual({
            label: "nomadnet.renderer_chip_micron_wasm",
            popoverVariant: "wasm_active",
            micronGoRelease: "v1.2.3",
        });
    });

    it("uses wasm_pending when WASM preferred but not ready (loading or failed)", () => {
        const chip = buildNomadBrowserRendererChip({
            ...baseMu,
            nomadMicronWasmReady: false,
            defaultEngine: "wasm",
            nomadMicronWasmFeatureEffective: true,
        });
        expect(chip).toEqual({
            label: "nomadnet.renderer_chip_micron_js",
            popoverVariant: "wasm_pending",
            micronGoRelease: "v1.2.3",
        });
    });

    it("falls back to JS hint chip when WASM not preferred", () => {
        const chip = buildNomadBrowserRendererChip({
            ...baseMu,
            nomadMicronWasmReady: false,
            defaultEngine: "js",
        });
        expect(chip).toEqual({
            label: "nomadnet.renderer_chip_micron_js",
            popoverVariant: undefined,
            tooltipBody: "nomadnet.renderer_hint_micron_js",
        });
    });

    it("strips Nomad backtick query before extension checks", () => {
        const chip = buildNomadBrowserRendererChip({
            ...baseMu,
            relativePagePath: "/page/index.mu`g=reticulum|x",
            nomadMicronWasmActive: true,
        });
        expect(chip?.popoverVariant).toBe("wasm_active");
    });

    it("labels markdown html and plaintext paths", () => {
        expect(
            buildNomadBrowserRendererChip({
                ...baseMu,
                relativePagePath: "/page/readme.md",
            })
        ).toMatchObject({
            label: "nomadnet.renderer_chip_markdown",
            tooltipBody: "nomadnet.renderer_hint_markdown",
        });
        expect(
            buildNomadBrowserRendererChip({
                ...baseMu,
                relativePagePath: "/page/index.html",
            })
        ).toMatchObject({
            label: "nomadnet.renderer_chip_html",
            tooltipBody: "nomadnet.renderer_hint_html",
        });
        expect(
            buildNomadBrowserRendererChip({
                ...baseMu,
                relativePagePath: "/page/notes.txt",
            })
        ).toMatchObject({
            label: "nomadnet.renderer_chip_plaintext",
            tooltipBody: "nomadnet.renderer_hint_plaintext",
        });
    });

    it("uses em dash release fallback when label missing", () => {
        const chip = buildNomadBrowserRendererChip({
            ...baseMu,
            nomadMicronWasmActive: true,
            micronGoRelease: "",
        });
        expect(chip?.micronGoRelease).toBe("\u2014");
    });
});

describe("shouldShowMicronRendererInMobileMenu", () => {
    it("requires bundled WASM a .mu page and not source view", () => {
        expect(
            shouldShowMicronRendererInMobileMenu({
                wasmBundled: true,
                selectedNode: { destination_hash: "a" },
                relativePagePath: "/page/index.mu",
                isShowingNodePageSource: false,
            })
        ).toBe(true);
        expect(
            shouldShowMicronRendererInMobileMenu({
                wasmBundled: false,
                selectedNode: { destination_hash: "a" },
                relativePagePath: "/page/index.mu",
                isShowingNodePageSource: false,
            })
        ).toBe(false);
        expect(
            shouldShowMicronRendererInMobileMenu({
                wasmBundled: true,
                selectedNode: null,
                relativePagePath: "/page/index.mu",
                isShowingNodePageSource: false,
            })
        ).toBe(false);
        expect(
            shouldShowMicronRendererInMobileMenu({
                wasmBundled: true,
                selectedNode: { destination_hash: "a" },
                relativePagePath: "/page/readme.md",
                isShowingNodePageSource: false,
            })
        ).toBe(false);
        expect(
            shouldShowMicronRendererInMobileMenu({
                wasmBundled: true,
                selectedNode: { destination_hash: "a" },
                relativePagePath: "/page/index.mu",
                isShowingNodePageSource: true,
            })
        ).toBe(false);
    });
});
