// SPDX-License-Identifier: 0BSD
import { describe, it, expect } from "vitest";
import { readFileSync } from "fs";
import { join } from "path";

function src(rel) {
    return readFileSync(join(process.cwd(), rel), "utf8");
}

describe("CommandPalette.svelte wiring", () => {
    it("opens from GlobalEmitter and Ctrl/Cmd+K and syncs propagation", () => {
        const palette = src("meshchatx/src/frontend/features/app-shell/components/CommandPalette.svelte");
        expect(palette).toContain("keydown");
        expect(palette).toContain("ctrlKey");
        expect(palette).toContain("metaKey");
        expect(palette).toContain("sync-propagation-node");
        expect(palette).toContain("listCommands");
        expect(palette).toContain("export function close");
        expect(palette).toContain("open-command-palette");
        expect(palette).toContain("isOpen = true");
    });
});
