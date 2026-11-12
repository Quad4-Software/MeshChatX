// SPDX-License-Identifier: 0BSD

import { readFileSync } from "node:fs";
import { resolve } from "node:path";
import { describe, expect, it } from "vitest";
import {
    hasRelayMicron,
    hasRelayMicronColour,
    renderRelayMicronHtml,
    stripRelayMicron,
} from "@/js/relay/relayMicron.js";

// 17 consecutive messages from one art sender: plasma block art drawn with
// coloured spaces and half blocks, then a framed text banner.
const ART_LINES = readFileSync(resolve(import.meta.dirname, "fixtures/relay-micron-art.txt"), "utf8")
    .split("\n")
    .filter((line) => line.length > 0);

function toDom(html) {
    const el = document.createElement("div");
    el.innerHTML = html;
    return el;
}

describe("hasRelayMicron", () => {
    it("is false for plain and Markdown text", () => {
        expect(hasRelayMicron("hello there")).toBe(false);
        expect(hasRelayMicron("**bold** and `code`")).toBe(false);
        expect(hasRelayMicron("")).toBe(false);
        expect(hasRelayMicron(null)).toBe(false);
        expect(hasRelayMicron(42)).toBe(false);
    });

    it("ignores raw backtick Micron, which is Markdown inline code here", () => {
        expect(hasRelayMicron("`Ff00red`f")).toBe(false);
        expect(hasRelayMicron("`!bold`!")).toBe(false);
    });

    it("ignores a broken bar that does not start a tag", () => {
        expect(hasRelayMicron("a ¦ b")).toBe(false);
        expect(hasRelayMicron("¦Fzzz")).toBe(false);
        expect(hasRelayMicron("¦x")).toBe(false);
        expect(hasRelayMicron("¦")).toBe(false);
        expect(hasRelayMicron("ends with a bar ¦")).toBe(false);
        expect(hasRelayMicron("¦¦")).toBe(false);
    });

    it("detects every supported tag", () => {
        for (const tag of ["¦Ff00", "¦B0a0", "¦FTff8800", "¦BT001122", "¦f", "¦b", "¦!", "¦*", "¦_", "¦`"]) {
            expect(hasRelayMicron(`x${tag}y`), tag).toBe(true);
        }
        for (const tag of ["¦<", "¦>", "¦{", "¦c", "¦l", "¦r", "¦a", "¦="]) {
            expect(hasRelayMicron(`x${tag}y`), tag).toBe(true);
        }
    });
});

describe("hasRelayMicronColour", () => {
    it("is true only when a colour is set", () => {
        expect(hasRelayMicronColour("¦Ff00red")).toBe(true);
        expect(hasRelayMicronColour("¦BTabcdefx")).toBe(true);
        expect(hasRelayMicronColour("¦!bold¦!")).toBe(false);
        expect(hasRelayMicronColour("¦f¦b")).toBe(false);
        expect(hasRelayMicronColour("`Ff00")).toBe(false);
        expect(hasRelayMicronColour(undefined)).toBe(false);
    });
});

describe("renderRelayMicronHtml", () => {
    it("colours text from 12-bit and 24-bit tags", () => {
        expect(renderRelayMicronHtml("¦Ff00red")).toBe('<span style="color:#f00">red</span>');
        expect(renderRelayMicronHtml("¦FTFF8800orange")).toBe('<span style="color:#ff8800">orange</span>');
        expect(renderRelayMicronHtml("¦B00fx¦BT112233y")).toBe(
            '<span style="background-color:#00f">x</span><span style="background-color:#112233">y</span>'
        );
    });

    it("returns to the default colours on ¦f and ¦b", () => {
        expect(renderRelayMicronHtml("¦Ff00¦B00fa¦fb¦bc")).toBe(
            '<span style="color:#f00;background-color:#00f">a</span>' + '<span style="background-color:#00f">b</span>c'
        );
    });

    it("toggles bold, italic and underline", () => {
        expect(renderRelayMicronHtml("¦!b¦!n")).toBe('<span style="font-weight:bold">b</span>n');
        expect(renderRelayMicronHtml("¦*i¦*n")).toBe('<span style="font-style:italic">i</span>n');
        expect(renderRelayMicronHtml("¦_u¦_n")).toBe('<span style="text-decoration:underline">u</span>n');
    });

    it("resets everything on ¦`", () => {
        expect(renderRelayMicronHtml("¦!¦*¦_¦Ff00¦B00fa¦`b")).toBe(
            '<span style="color:#f00;background-color:#00f;font-weight:bold;font-style:italic;text-decoration:underline">a</span>b'
        );
    });

    it("drops layout and link tags instead of showing them", () => {
        expect(renderRelayMicronHtml("¦c¦l¦r¦a¦=¦<¦>¦{¦Ff00x")).toBe('<span style="color:#f00">x</span>');
    });

    it("keeps an unrecognised broken bar as text", () => {
        expect(renderRelayMicronHtml("¦Ff00a ¦ b ¦Fzzz ¦x ¦¦")).toBe(
            '<span style="color:#f00">a ¦ b ¦Fzzz ¦x ¦¦</span>'
        );
        expect(renderRelayMicronHtml("¦Ff00a¦")).toBe('<span style="color:#f00">a¦</span>');
    });

    it("keeps whitespace exactly, including leading, repeated and trailing spaces", () => {
        const html = renderRelayMicronHtml("   ¦Ff00a    b   ¦f  ");
        expect(html).toBe('   <span style="color:#f00">a    b   </span>  ');
        expect(toDom(html).textContent).toBe("   a    b     ");
    });

    it("paints a background over exactly the characters it applies to", () => {
        const dom = toDom(renderRelayMicronHtml("x¦B0f0  ¦by"));
        const spans = dom.querySelectorAll("span");
        expect(spans).toHaveLength(1);
        expect(spans[0].textContent).toBe("  ");
        expect(spans[0].getAttribute("style")).toBe("background-color:#0f0");
        expect(spans[0].getAttribute("style")).not.toMatch(/padding|margin|display/);
    });

    it("carries formatting across lines of one message", () => {
        expect(renderRelayMicronHtml("¦Ff00a\nb")).toBe('<span style="color:#f00">a\nb</span>');
    });

    it("escapes markup in the message text", () => {
        const html = renderRelayMicronHtml('¦Ff00<img src=x onerror="alert(1)"><script>alert(2)</script>');
        expect(html).not.toContain("<img");
        expect(html).not.toContain("<script");
        const dom = toDom(html);
        expect(dom.querySelector("img, script")).toBeNull();
        expect(dom.textContent).toBe('<img src=x onerror="alert(1)"><script>alert(2)</script>');
    });

    it("never lets message text into a style attribute", () => {
        const attempts = [
            '¦FT00ff00;background:url(x)"><b>x',
            "¦F0f0;position:fixed¦B00f\"' onmouseover=alert(1) x",
            "¦FTgg0000x¦F12x",
        ];
        for (const text of attempts) {
            const dom = toDom(renderRelayMicronHtml(text));
            expect(dom.querySelector("b")).toBeNull();
            for (const el of dom.querySelectorAll("*")) {
                expect([...el.attributes].map((a) => a.name)).toEqual(["style"]);
                expect(el.getAttribute("style")).toMatch(
                    /^(?:(?:color|background-color):#[0-9a-f]{3}(?:[0-9a-f]{3})?|font-weight:bold|font-style:italic|text-decoration:underline)(?:;(?:(?:color|background-color):#[0-9a-f]{3}(?:[0-9a-f]{3})?|font-weight:bold|font-style:italic|text-decoration:underline))*$/
                );
            }
        }
    });

    it("does not apply Markdown inside Micron messages", () => {
        expect(renderRelayMicronHtml("¦Ff00__a__ *b* `c`")).toBe('<span style="color:#f00">__a__ *b* `c`</span>');
    });

    it("still links URLs in the text", () => {
        const html = renderRelayMicronHtml("¦!see¦! https://example.com/page");
        expect(html).toContain('data-http-url="https://example.com/page"');
    });

    it("renders empty input as empty output", () => {
        expect(renderRelayMicronHtml(null)).toBe("");
        expect(renderRelayMicronHtml("")).toBe("");
    });
});

describe("stripRelayMicron", () => {
    it("removes tags and keeps text", () => {
        expect(stripRelayMicron("¦!¦Ff00waves¦f¦! at ¦cyou")).toBe("waves at you");
    });

    it("leaves text without tags alone", () => {
        expect(stripRelayMicron("a ¦ b `Ff00")).toBe("a ¦ b `Ff00");
        expect(stripRelayMicron(null)).toBe("");
    });
});

describe("sample art", () => {
    it("has 17 lines, every one drawn as art", () => {
        expect(ART_LINES).toHaveLength(17);
        for (const line of ART_LINES) {
            expect(hasRelayMicron(line)).toBe(true);
            expect(hasRelayMicronColour(line)).toBe(true);
        }
    });

    it("renders each line to exactly its text, with every tag consumed", () => {
        for (const line of ART_LINES) {
            const dom = toDom(renderRelayMicronHtml(line));
            expect(dom.textContent).toBe(stripRelayMicron(line));
            expect(dom.textContent).not.toContain("¦");
        }
    });

    it("keeps the block art rows the same width so they line up", () => {
        const widths = ART_LINES.slice(0, 14).map((line) => [...stripRelayMicron(line)].length);
        expect(new Set(widths).size).toBe(1);
        expect(widths[0]).toBe(64);
    });

    it("keeps the banner's spacing", () => {
        const banner = ART_LINES.slice(14).map((line) => toDom(renderRelayMicronHtml(line)).textContent);
        expect(banner[0]).toBe(` .${"-".repeat(55)}. `);
        expect(banner[1]).toBe(" | RRC art over Reticulum, drawn by ascii.py          | ");
    });
});
