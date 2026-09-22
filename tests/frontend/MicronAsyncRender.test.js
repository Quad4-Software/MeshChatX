import { describe, it, expect, beforeEach } from "vitest";
import MicronParser from "@/js/MicronParser";
import {
    renderNomadPageByPath,
    renderNomadPageByPathAsync,
} from "@/js/NomadPageRenderer";

const FIXTURE = [
    "#!bg=444",
    "#!fg=ddd",
    ">Heading One",
    "plain body line with text",
    "`b`cBold section`c",
    "- list item one",
    "- list item two",
    "`[link`:/page/index.mu]",
    ...Array.from({ length: 300 }, (_, i) => `filler line ${i} of content`),
].join("\n");

describe("MicronParser async render", () => {
    let parser;

    beforeEach(() => {
        parser = new MicronParser(true, false);
    });

    it("chunked JS path matches the synchronous render byte-for-byte", async () => {
        const sync = parser.convertMicronToHtml(FIXTURE, {}, {});
        const asyncOut = await parser.convertMicronToHtmlAsync(FIXTURE, {}, {});
        expect(asyncOut).toBe(sync);
    });

    it("async path handles empty and null markup", async () => {
        expect(await parser.convertMicronToHtmlAsync(null)).toBe("");
        expect(await parser.convertMicronToHtmlAsync("")).toBe(
            parser.convertMicronToHtml("")
        );
    });

    it("async path returns the same fallback for pathological input", async () => {
        const bad = { toString: () => "\ud800\ud800" };
        const sync = parser.convertMicronToHtml(bad, {}, {});
        const asyncOut = await parser.convertMicronToHtmlAsync(bad, {}, {});
        expect(asyncOut).toBe(sync);
    });

    it("falls back to chunked JS when the worker is unavailable", async () => {
        // jsdom has no Worker; the wasm-worker path must degrade cleanly.
        const asyncOut = await parser.convertMicronToHtmlAsync(FIXTURE, {}, {
            useWasm: true,
        });
        expect(asyncOut).toBe(parser.convertMicronToHtml(FIXTURE, {}, {}));
    });
});

describe("renderNomadPageByPathAsync", () => {
    it("matches sync output for .mu pages", async () => {
        const sync = renderNomadPageByPath("/page.mu", FIXTURE, {}, MicronParser, {});
        const asyncOut = await renderNomadPageByPathAsync(
            "/page.mu",
            FIXTURE,
            {},
            MicronParser,
            {},
        );
        expect(asyncOut).toBe(sync);
    });

    it("matches sync output for .md pages when the worker is unavailable", async () => {
        const md = "# Title\n\nsome **bold** text and a [link](https://example.com)";
        const sync = renderNomadPageByPath("/page.md", md, {}, MicronParser, {});
        const asyncOut = await renderNomadPageByPathAsync(
            "/page.md",
            md,
            {},
            MicronParser,
            {},
        );
        expect(asyncOut).toBe(sync);
    });

    it("passes through .txt pages identically", async () => {
        const sync = renderNomadPageByPath("/a.txt", "hi <b>", {}, MicronParser, {});
        const asyncOut = await renderNomadPageByPathAsync(
            "/a.txt",
            "hi <b>",
            {},
            MicronParser,
            {},
        );
        expect(asyncOut).toBe(sync);
    });

    it("still sanitizes worker-supplied markdown HTML", async () => {
        const md = 'text <img src=x onerror="alert(1)">';
        const out = await renderNomadPageByPathAsync(
            "/p.md",
            md,
            {},
            MicronParser,
            {},
        );
        expect(out).not.toContain("onerror");
    });
});
