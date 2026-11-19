// SPDX-License-Identifier: 0BSD

import fs from "fs";
import path from "path";
import { describe, expect, it } from "vitest";

const stylePath = path.join(__dirname, "..", "..", "meshchatx", "src", "frontend", "style.css");
const css = fs.readFileSync(stylePath, "utf-8");

// Interactive elements must show the pointer cursor and disabled controls the
// not-allowed cursor. The global rules in style.css are what guarantee this
// for shared components; these assertions fail if they are removed.
describe("interactive cursor rules", () => {
    it("applies pointer cursor to buttons and interactive roles", () => {
        for (const selector of [
            "button:not(:disabled)",
            '[role="button"]:not([aria-disabled="true"])',
            "select",
            "summary",
            "label[for]",
            "a[href]",
        ]) {
            expect(css).toContain(selector);
        }
        expect(css).toMatch(/\{[^}]*cursor:\s*pointer/s);
    });

    it("applies not-allowed cursor to disabled controls", () => {
        expect(css).toContain("button:disabled");
        expect(css).toContain("select:disabled");
        expect(css).toMatch(/cursor:\s*not-allowed/);
    });
});
