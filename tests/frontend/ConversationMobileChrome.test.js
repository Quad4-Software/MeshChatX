// SPDX-License-Identifier: 0BSD

import { readFileSync } from "node:fs";
import { resolve } from "node:path";
import { describe, expect, it } from "vitest";

function source(relativePath) {
    return readFileSync(resolve(process.cwd(), "meshchatx/src/frontend/features/messages", relativePath), "utf8");
}

describe("conversation mobile chrome", () => {
    it("keeps peer header actions compact on narrow layouts", () => {
        const header = source("components/ConversationPeerHeader.svelte");
        expect(header).toContain("compactPeerActions");
        expect(header).toContain("sm:max-w-sm");
        expect(header).toContain("messages.more_actions");
    });

    it("keeps the mobile composer above the safe-area inset", () => {
        const composer = source("components/ConversationComposer.svelte");
        expect(composer).toContain("env(safe-area-inset-bottom)");
        expect(composer).toContain("min-h-[44px]");
    });

    it("uses a dynamic viewport-height compose sheet", () => {
        const compose = source("components/MessagesMobileCompose.svelte");
        expect(compose).toContain("max-h-[90dvh]");
        expect(compose).not.toContain("max-h-[90vh]");
    });
});
