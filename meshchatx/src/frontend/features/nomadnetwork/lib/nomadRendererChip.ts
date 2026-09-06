// SPDX-License-Identifier: 0BSD

import type { NomadPageRendererChip } from "./types.js";

export type NomadRendererChipTranslate = (key: string, params?: Record<string, unknown>) => string;

export interface NomadBrowserRendererChipInput {
    selectedNode: unknown | null | undefined;
    /** Relative Nomad page path (may include a backtick query suffix). */
    relativePagePath: string | null | undefined;
    isShowingNodePageSource: boolean;
    nomadMicronWasmActive: boolean;
    nomadMicronWasmFeatureEffective: boolean;
    nomadMicronWasmReady: boolean;
    defaultEngine?: string | null;
    micronGoRelease?: string | null;
    t: NomadRendererChipTranslate;
}

export interface NomadMicronRendererMenuInput {
    wasmBundled: boolean;
    selectedNode: unknown | null | undefined;
    relativePagePath: string | null | undefined;
    isShowingNodePageSource: boolean;
}

/**
 * Toolbar chip for the active Nomad page renderer.
 * Matches Vue NomadNetworkPage.nomadBrowserRendererChip: path-gated, null when
 * no page or viewing source. WASM preferred but not ready uses wasm_pending
 * (covers both still-loading and load-failed / unavailable).
 */
export function buildNomadBrowserRendererChip(input: NomadBrowserRendererChipInput): NomadPageRendererChip | null {
    if (!input.selectedNode || !input.relativePagePath) {
        return null;
    }
    if (input.isShowingNodePageSource) {
        return null;
    }

    const [p] = String(input.relativePagePath).split("`");
    const pathLower = (p || "").toLowerCase();
    const micronGoRelease = input.micronGoRelease || "\u2014";
    const t = input.t;

    const plainChip = (labelKey: string, detailKey: string): NomadPageRendererChip => ({
        label: t(labelKey),
        popoverVariant: undefined,
        tooltipBody: t(detailKey),
    });

    if (pathLower.endsWith(".mu")) {
        if (input.nomadMicronWasmActive) {
            return {
                label: t("nomadnet.renderer_chip_micron_wasm"),
                popoverVariant: "wasm_active",
                micronGoRelease,
            };
        }
        const engineWasm = (input.defaultEngine || "js") === "wasm";
        const wasmPreferred = input.nomadMicronWasmFeatureEffective && engineWasm;
        if (wasmPreferred && !input.nomadMicronWasmReady) {
            return {
                label: t("nomadnet.renderer_chip_micron_js"),
                popoverVariant: "wasm_pending",
                micronGoRelease,
            };
        }
        return plainChip("nomadnet.renderer_chip_micron_js", "nomadnet.renderer_hint_micron_js");
    }
    if (pathLower.endsWith(".md")) {
        return plainChip("nomadnet.renderer_chip_markdown", "nomadnet.renderer_hint_markdown");
    }
    if (pathLower.endsWith(".html")) {
        return plainChip("nomadnet.renderer_chip_html", "nomadnet.renderer_hint_html");
    }
    if (pathLower.endsWith(".txt")) {
        return plainChip("nomadnet.renderer_chip_plaintext", "nomadnet.renderer_hint_plaintext");
    }
    return null;
}

/** True when the Micron JS/WASM switch belongs in the mobile overflow menu. */
export function shouldShowMicronRendererInMobileMenu(input: NomadMicronRendererMenuInput): boolean {
    if (!input.wasmBundled || !input.selectedNode || !input.relativePagePath || input.isShowingNodePageSource) {
        return false;
    }
    const [p] = String(input.relativePagePath).split("`");
    return (p || "").toLowerCase().endsWith(".mu");
}
