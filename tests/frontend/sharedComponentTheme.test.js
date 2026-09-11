import { describe, it, expect } from "vitest";
import { mount } from "@vue/test-utils";
import { readFileSync, readdirSync } from "node:fs";
import { join } from "node:path";
import IconButton from "@/components/IconButton.vue";

// Reusable components must colour themselves with sem-* design tokens so
// they follow the active theme (dark/light/custom). Hardcoded palette
// utilities like bg-white, text-black or bg-zinc-* silently break theming.

const COMPONENTS_DIR = join(__dirname, "../../meshchatx/src/frontend/components");

// Components that intentionally carry no colours of their own (slot wrappers,
// positioners, icon renderers) — they are exempt from the "must use sem-
// tokens" check but still may not hardcode palette colours.
const STYLE_FREE = new Set([
    "DropDownMenu.vue",
    "DropDownMenuItem.vue",
    "MaterialDesignIcon.vue",
    "ContextMenuDivider.vue",
    "ContextMenuItem.vue",
    "ContextMenuPanel.vue",
    "ContextMenuSectionLabel.vue",
]);

// Files covered by this contract.
const SHARED_FILES = [
    "IconButton.vue",
    "SearchInput.vue",
    "EmptyState.vue",
    "LoadingState.vue",
    "Skeleton.vue",
    "Toast.vue",
    "ConfirmDialog.vue",
    "PromptDialog.vue",
    "DropDownMenu.vue",
    "DropDownMenuItem.vue",
    "MaterialDesignIcon.vue",
    ...readdirSync(join(COMPONENTS_DIR, "contextmenu"))
        .filter((f) => f.endsWith(".vue"))
        .map((f) => join("contextmenu", f)),
    ...readdirSync(join(COMPONENTS_DIR, "forms"))
        .filter((f) => f.endsWith(".vue"))
        .map((f) => join("forms", f)),
];

// Utilities that pin a literal palette colour for a theme surface and
// therefore ignore the active theme. Allowed exceptions:
// - bg-black/<opacity>: modal scrims are intentionally dark in both themes
// - after:/before: pseudo-element colours: decorative details (toggle knob)
// - text-gray-400 on icons/placeholders: intentionally muted in both themes
const BANNED = [
    /(?<!after:)(?<!before:)\bbg-white\b/,
    /\btext-black\b/,
    /\bbg-black\b(?!\/)/,
    /\bbg-gray-\d/,
    /\bbg-zinc-\d/,
    /\btext-zinc-\d/,
];

describe("shared component theming contract", () => {
    for (const file of SHARED_FILES) {
        it(`${file} uses semantic tokens and no hardcoded palette surfaces`, () => {
            const src = readFileSync(join(COMPONENTS_DIR, file), "utf8");

            for (const pattern of BANNED) {
                const match = src.match(pattern);
                expect(match, `${file} contains hardcoded colour ${match}`).toBeNull();
            }

            if (!STYLE_FREE.has(file.replace(/\\/g, "/").split("/").pop())) {
                expect(src, `${file} should use sem-* tokens`).toMatch(/sem-/);
            }
        });
    }

    it("search-input classes in style.css use semantic tokens", () => {
        const css = readFileSync(join(COMPONENTS_DIR, "../style.css"), "utf8");
        const block = css.match(/\.search-input\s*\{[^}]+\}/s);
        expect(block, ".search-input rule missing").toBeTruthy();
        expect(block[0]).toContain("sem-");
        expect(block[0]).toContain("pl-10");
    });

    it("IconButton renders a slotted 44px touch target with focus ring", () => {
        const wrapper = mount(IconButton, { slots: { default: "<i class='x' />" } });
        const btn = wrapper.find("button");
        expect(btn.exists()).toBe(true);
        expect(btn.classes()).toContain("min-w-11");
        expect(btn.classes()).toContain("min-h-11");
        expect(btn.classes()).toContain("focus-ring-sem");
        expect(btn.html()).toContain('<i class="x"');
    });
});
