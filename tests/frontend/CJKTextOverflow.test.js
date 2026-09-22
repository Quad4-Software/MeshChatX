import { describe, it, expect } from "vitest";
import { readFileSync } from "fs";
import { join } from "path";

describe("CJK Text Overflow UI CSS Tests", () => {
    it("ConversationMessageEntry uses wrap-break-word classes for long CJK text", () => {
        const src = readFileSync(
            join(process.cwd(), "meshchatx/src/frontend/features/messages/components/ConversationMessageEntry.svelte"),
            "utf8"
        );
        expect(src).toContain("wrap-break-word");
        expect(src).toContain("min-w-0");
        expect(src).toContain("markdown-content");
    });
});
