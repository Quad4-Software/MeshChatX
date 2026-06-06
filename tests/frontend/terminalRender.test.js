import { describe, expect, it } from "vitest";

import { renderTerminalOutput } from "@/js/terminalRender";

describe("renderTerminalOutput", () => {
    it("returns empty string for non-string or empty input", () => {
        expect(renderTerminalOutput("")).toBe("");
        expect(renderTerminalOutput(null)).toBe("");
        expect(renderTerminalOutput(undefined)).toBe("");
    });

    it("strips ANSI colour sequences", () => {
        const raw = "\u001b[31mred\u001b[0m text";
        expect(renderTerminalOutput(raw)).toBe("red text");
    });

    it("strips OSC title sequences", () => {
        const raw = "\u001b]0;window title\u0007prompt$ ";
        expect(renderTerminalOutput(raw)).toBe("prompt$");
    });

    it("collapses carriage-return progress redraws to the final line", () => {
        const raw = "loading 10%\rloading 100%";
        expect(renderTerminalOutput(raw)).toBe("loading 100%");
    });

    it("applies backspace edits", () => {
        const raw = "abcd\b\bXY";
        expect(renderTerminalOutput(raw)).toBe("abXY");
    });

    it("preserves multiple lines", () => {
        const raw = "line1\nline2\nline3";
        expect(renderTerminalOutput(raw)).toBe("line1\nline2\nline3");
    });
});
