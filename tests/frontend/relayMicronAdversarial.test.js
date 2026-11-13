// SPDX-License-Identifier: 0BSD

import { describe, expect, it } from "vitest";
import {
    hasRelayMicron,
    hasRelayMicronColour,
    renderRelayMicronHtml,
    stripRelayMicron,
} from "@/js/relay/relayMicron.js";

// The renderer only ever emits <span style="..."> and <a href="#" ...>.
// Anything else in the output means message text reached the DOM as markup.
const ALLOWED_ELEMENTS = new Set(["SPAN", "A"]);
const ALLOWED_ANCHOR_ATTRS = new Set([
    "href",
    "class",
    "rel",
    "data-http-url",
    "data-rrc-url",
    "data-lxmf-address",
    "data-nomadnet-url",
]);
// styleFor() only ever emits these declarations, with colours taken from
// validated hex digits.
const ALLOWED_STYLE_DECL =
    /^(?:(?:color|background-color):#[0-9a-f]{3}(?:[0-9a-f]{3})?|font-weight:bold|font-style:italic|text-decoration:underline)$/;
const DANGEROUS_URL = /^\s*(?:javascript|vbscript|data|file)\s*:/i;
// Every literal tag in the output must be markup the renderer generated;
// message text can never contribute tags because < > & " ' are escaped.
const GENERATED_TAG = /^<\/?(?:span|a)\b/;

// jsdom's parser throws RangeError on some lone-surrogate sequences where
// browsers emit U+FFFD. Normalise the same way so DOM assertions still run.
function replaceLoneSurrogates(s) {
    return s.replace(/[\uD800-\uDBFF][\uDC00-\uDFFF]|[\uD800-\uDFFF]/g, (m) => (m.length === 2 ? m : "�"));
}

// LinkUtils may absorb a trailing escaped entity into a standard http(s)
// link (shared with the Markdown path). Such inputs still get full safety
// checks; only the strict visible-text invariant is skipped.
function isLinkifiable(s) {
    return /https?:\/\//i.test(s) || /(?:nomadnet|lxmf|rrc|meshchatx|meshchat):/i.test(s) || /[0-9a-fA-F]{32}:/.test(s);
}

const GENERATED_TAG_RE = /<\/?(?:span|a)\b[^>]*>/g;
const ENTITY_RE = /&(?:amp|lt|gt|quot|#039);/g;
const ENTITY_MAP = { "&amp;": "&", "&lt;": "<", "&gt;": ">", "&quot;": '"', "&#039;": "'" };
const decodeEntities = (s) => s.replace(ENTITY_RE, (m) => ENTITY_MAP[m]);

// Strip the generated markup and decode entities: the exact code units the
// renderer meant to show, before any HTML parser touches them.
function htmlToText(html) {
    return decodeEntities(html.replace(GENERATED_TAG_RE, ""));
}

// Model the HTML parser for the generated markup: tags split the text into
// chunks, and inside each chunk CR/CRLF becomes LF, NUL is dropped and lone
// surrogates become U+FFFD. A surrogate pair split by a tag is two lone
// surrogates, matching what a browser produces.
function expectedDomText(html) {
    let out = "";
    for (const chunk of html.split(GENERATED_TAG_RE)) {
        out += replaceLoneSurrogates(decodeEntities(chunk)).replace(/\r\n?/g, "\n").replace(/\x00/g, "");
    }
    return out;
}

function assertSafeHtml(html) {
    for (const tag of html.match(/<\/?[a-zA-Z!][^>]*>/g) || []) {
        expect(GENERATED_TAG.test(tag), `unexpected markup in output: ${tag.slice(0, 80)}`).toBe(true);
    }
    const el = document.createElement("div");
    el.innerHTML = replaceLoneSurrogates(html);
    for (const node of el.querySelectorAll("*")) {
        expect(ALLOWED_ELEMENTS.has(node.tagName), `unexpected element <${node.tagName.toLowerCase()}>`).toBe(true);
        for (const attr of node.attributes) {
            if (node.tagName === "SPAN") {
                expect(attr.name, "span carries a non-style attribute").toBe("style");
            } else {
                expect(ALLOWED_ANCHOR_ATTRS.has(attr.name), `unexpected anchor attr ${attr.name}`).toBe(true);
            }
            expect(DANGEROUS_URL.test(attr.value), `dangerous URL in ${attr.name}`).toBe(false);
        }
        const style = node.getAttribute("style");
        if (style !== null) {
            for (const decl of style.split(";").filter((d) => d.trim() !== "")) {
                expect(ALLOWED_STYLE_DECL.test(decl.trim()), `unsafe style declaration: ${decl}`).toBe(true);
            }
        }
    }
    return el;
}

// Every character the user typed must survive as text: link labels echo the
// matched text, tags vanish, and nothing is re-interpreted.
function assertRoundTrip(input, html = renderRelayMicronHtml(input)) {
    const el = assertSafeHtml(html);
    if (!isLinkifiable(input)) {
        expect(htmlToText(html)).toBe(stripRelayMicron(input));
        expect(el.textContent).toBe(expectedDomText(html));
    }
    return el;
}

describe("relayMicron non-string and empty inputs", () => {
    it("handles nullish and non-string values without throwing", () => {
        expect(renderRelayMicronHtml(null)).toBe("");
        expect(renderRelayMicronHtml(undefined)).toBe("");
        for (const v of [0, 42, -1, false, true, {}, [], NaN, Symbol("s")]) {
            expect(renderRelayMicronHtml(v)).toBe(String(v));
            expect(hasRelayMicron(v)).toBe(false);
            expect(hasRelayMicronColour(v)).toBe(false);
        }
        expect(stripRelayMicron(null)).toBe("");
        expect(stripRelayMicron(undefined)).toBe("");
        expect(stripRelayMicron(123)).toBe("123");
    });

    it("renders tag-only and bar-only messages safely", () => {
        for (const s of ["¦Ff00", "¦B0f0¦f¦b", "¦!¦*¦_¦`", "¦<¦>¦{¦c¦l¦r¦a¦=", "¦¦¦", "¦"]) {
            assertRoundTrip(s);
        }
        expect(renderRelayMicronHtml("¦Ff00")).toBe("");
        expect(renderRelayMicronHtml("¦!")).toBe("");
    });
});

describe("relayMicron malformed tags", () => {
    const malformed = [
        "¦F",
        "¦F0",
        "¦F00",
        "¦Fggg",
        "¦F123g",
        "¦Ff00g",
        "¦FT",
        "¦FT0",
        "¦FT12345",
        "¦FTgggggg",
        "¦FT1234567",
        "¦B",
        "¦Bgg",
        "¦BT",
        "¦BT1234",
        "¦Xf00",
        "¦ f00",
        "¦FFf00 extra",
        "¦fF00 looks like a tag but is ¦f + text",
        "¦bB0f0",
        "¦`extra",
        "¦!",
        "¦*",
        "¦_",
        "a¦Ff00",
        "¦Ff00a",
        "¦Ff00¦",
        "¦¦Ff00",
        "¦Ff00¦Ff00",
        "¦Ff00 ¦Fgg ¦B0f0",
        "¦FTffffffx",
        "¦FTfffffg",
        "¦fT123456",
        "¦BT12345g",
    ];

    it("never throws and always preserves visible text", () => {
        for (const s of malformed) {
            assertRoundTrip(s);
        }
    });

    it("treats over-long hex runs as a valid tag plus trailing text", () => {
        // ¦F + exactly 3 hex digits; the rest is ordinary text.
        const html = renderRelayMicronHtml("¦Ff00000");
        expect(html).toBe('<span style="color:#f00">000</span>');
        const el = assertSafeHtml(html);
        expect(el.textContent).toBe("000");
    });

    it("accepts mixed-case hex digits", () => {
        const el = assertSafeHtml(renderRelayMicronHtml("¦FTfFfFfF a ¦BT00FfAa b"));
        const spans = el.querySelectorAll("span");
        expect(spans[0].getAttribute("style")).toBe("color:#ffffff");
        expect(spans[1].getAttribute("style")).toBe("color:#ffffff;background-color:#00ffaa");
    });
});

describe("relayMicron tag character confusion", () => {
    // Only U+00A6 BROKEN BAR is the Micron tag character in RRC. Bars that
    // merely look similar must stay literal text. Written as escapes so the
    // code points are unambiguous.
    const lookalikes = [
        "ǀ", // U+01C0 LATIN LETTER DENTAL CLICK
        "∣", // U+2223 DIVIDES
        "│", // U+2502 BOX DRAWINGS LIGHT VERTICAL
        "┃", // U+2503 BOX DRAWINGS HEAVY VERTICAL
        "┆", // U+2506 LIGHT TRIPLE DASH VERTICAL
        "┊", // U+250A HEAVY TRIPLE DASH VERTICAL
        "┇", // U+2507 QUADRUPLE DASH VERTICAL
        "┋", // U+250B HEAVY QUADRUPLE DASH VERTICAL
        "╎", // U+254E LIGHT DOUBLE DASH VERTICAL
        "╏", // U+254F HEAVY DOUBLE DASH VERTICAL
        "❘", // U+2758 HEAVY VERTICAL BAR
        "｜", // U+FF5C FULLWIDTH VERTICAL LINE
        "︱", // U+FE31 PRESENTATION FORM FOR VERTICAL EM DASH
        "§", // U+00A7 SECTION SIGN, near-identical glyph
    ];

    it("ignores every bar that is not U+00A6", () => {
        for (const bar of lookalikes) {
            const s = `${bar}Ff00red`;
            expect(hasRelayMicron(s), `U+${bar.codePointAt(0).toString(16)} must not tag`).toBe(false);
            assertRoundTrip(s);
        }
    });

    it("recognises only the exact U+00A6 code point", () => {
        // Explicit escapes: U+00A6 is the tag char, U+00A7 is not.
        expect("¦Ff00red".charCodeAt(0)).toBe(0x00a6);
        expect(hasRelayMicron("¦Ff00red")).toBe(true);
        expect(hasRelayMicron("§Ff00red")).toBe(false);
        expect(hasRelayMicron("x¦Ff00")).toBe(true);
    });
});

describe("relayMicron HTML and CSS injection", () => {
    const injections = [
        "¦Ff00<script>alert(1)</script>¦f",
        "¦Ff00</span><script>alert(1)</script>",
        "¦Ff00<img src=x onerror=alert(1)>",
        "¦Ff00<svg onload=alert(1)>",
        "¦Ff00<math><mtext><script>alert(1)</script></mtext></math>",
        "¦Ff00<style>body{display:none}</style>",
        '¦Ff00"><img src=x onerror=alert(1)>',
        "¦Ff00' onmouseover='alert(1)",
        "¦Ff00</style><script>alert(1)</script>",
        "¦Ff00<!--<script>alert(1)</script>-->",
        "¦Ff00<![CDATA[<script>alert(1)</script>]]>",
        '¦Ff00<?xml version="1.0"?><script>alert(1)</script>',
        "¦Ff00expression(alert(1))",
        "¦Ff00url(javascript:alert(1))",
        "¦Ff00behavior:url(evil.htc)",
        "¦Ff00@import 'https://evil.example/x.css'",
        "¦Ff00;position:fixed;inset:0;z-index:9999",
        "¦Ff00}body{background-image:url(https://evil.example/x)}",
        "¦Ff00--!><script>alert(1)</script>",
        "¦Ff00&#60;script&#62;alert(1)&#60;/script&#62;",
        "¦Ff00&lt;img src=x onerror=alert(1)&gt;",
        "¦Ff00&quot; onmouseover=&quot;alert(1)",
        "¦Ff00\u0000\u0001\u001Fbinary\u007F",
        "¦Ff00javascript:alert(1)",
        "¦Ff00vbscript:msgbox(1)",
        "¦Ff00data:text/html,<script>alert(1)</script>",
        "¦Ff00file:///etc/passwd",
        '¦Ff00https://good.example/" onclick="alert(1)',
        "¦Ff00https://good.example/'onmouseover='alert(1)",
    ];

    it("escapes every payload so only spans and safe anchors remain", () => {
        for (const s of injections) {
            assertRoundTrip(s);
        }
    });

    it("keeps javascript: and data: URLs as inert text", () => {
        for (const s of ["¦Ff00javascript:alert(1)¦f", "javascript:alert(1) ¦Ff00x"]) {
            const el = assertSafeHtml(renderRelayMicronHtml(s));
            expect(el.querySelector("a")).toBeNull();
        }
    });

    it("cannot break out of the style attribute with quotes or entities", () => {
        const el = assertSafeHtml(renderRelayMicronHtml('x ¦Ff00a";color:expression(alert(1))¦f "y'));
        for (const span of el.querySelectorAll("span[style]")) {
            // The attribute value must consist solely of whitelisted declarations.
            for (const decl of span.getAttribute("style").split(";")) {
                expect(ALLOWED_STYLE_DECL.test(decl.trim())).toBe(true);
            }
        }
        // The hostile text survives as a text node, not as markup.
        expect(el.textContent).toContain('";color:expression(alert(1))');
    });
});

describe("relayMicron linkification stays safe", () => {
    it("linkifies http(s) URLs but never emits a scriptable href", () => {
        const el = assertSafeHtml(renderRelayMicronHtml("¦Ff00see https://example.com/x?a=1&b=2¦f"));
        const a = el.querySelector("a");
        expect(a).not.toBeNull();
        expect(a.getAttribute("href")).toBe("#");
        expect(a.getAttribute("data-http-url")).toContain("https://example.com");
    });

    it("rejects URLs with embedded credentials", () => {
        const el = assertSafeHtml(renderRelayMicronHtml("¦Ff00https://user:pass@example.com/¦f"));
        expect(el.querySelector("a")).toBeNull();
    });

    it("does not let placeholder-shaped text forge anchors", () => {
        const s = "¦Ff00[[ANC_deadbeef_0]] and [[IC_1_2]] and <a href='https://evil.example'>x</a>¦f";
        assertRoundTrip(s);
    });
});

describe("relayMicron unicode and encoding edge cases", () => {
    const unicodeCases = [
        "lone high surrogate \uD800 end",
        "lone low surrogate \uDC00 start",
        "reversed pair \uDC00\uD800",
        "double high \uD800\uD800\uD800",
        "high then low then lone \uD83D\uDE00\uD800",
        "replacement char \uFFFD",
        "bidi override \u202Eevil\u202C",
        "bidi isolate \u2066x\u2069",
        "LRM/RLM \u200E\u200F",
        "zero width \u200B\u200C\u200D\uFEFF",
        "line/para separators \u2028\u2029",
        "controls \x00\x01\x1F\x7F",
        "combining marks e\u0301\u0300",
        "ZWJ emoji 👨‍👩‍👧‍👦",
        "musical symbols 𝄞𝄢",
        "CJK  and RTL العربية",
        "tag char next to surrogate ¦Ff00\uD800",
        "surrogate inside tag run ¦F\uD800f00",
        "fullwidth digits １２３ and fullwidth bar ｜Ff00",
        "tag char written twice ¦¦Ff00",
        "CRLF\r\nline\rbreaks\n",
        "tab\tseparated",
        "already-escaped &lt;tag&gt; &amp; entities",
        "double-escaped &amp;lt;script&amp;gt;",
        "numeric entities &#60;&#62;&#x3C;",
        "null byte inside colour ¦Ff0\x000",
        "very long word " + "x".repeat(5000),
    ];

    it("never throws and preserves text for every case", () => {
        for (const s of unicodeCases) {
            assertRoundTrip(`prefix ${s} ¦Ff00suffix`);
        }
    });
});

describe("relayMicron state machine adversarial", () => {
    it("resets fully on ¦`", () => {
        const el = assertSafeHtml(renderRelayMicronHtml("¦Ff00¦B0f0¦!¦*¦_bold all¦`reset ¦fonly-fg ¦bplain"));
        const spans = [...el.querySelectorAll("span")];
        expect(spans).toHaveLength(1);
        expect(spans[0].getAttribute("style")).toBe(
            "color:#f00;background-color:#0f0;font-weight:bold;font-style:italic;text-decoration:underline"
        );
        // After ¦` everything is default, so only-fg/plain are bare text.
        expect(el.textContent).toBe("bold allreset only-fg plain");
    });

    it("resets fg and bg independently", () => {
        const el = assertSafeHtml(renderRelayMicronHtml("¦Ff00¦B0f0x¦f y¦b z"));
        const spans = [...el.querySelectorAll("span")];
        expect(spans[0].textContent).toBe("x");
        expect(spans[0].getAttribute("style")).toBe("color:#f00;background-color:#0f0");
        expect(spans[1].textContent).toBe(" y");
        expect(spans[1].getAttribute("style")).toBe("background-color:#0f0");
        // After ¦b nothing is styled, so " z" is bare text.
        expect(el.textContent).toBe("x y z");
    });

    it("toggles bold, italic and underline independently", () => {
        const el = assertSafeHtml(renderRelayMicronHtml("¦!a¦!b¦*c¦*d¦_e¦_f"));
        const styles = [...el.querySelectorAll("span")].map((s) => s.getAttribute("style"));
        expect(styles).toEqual(["font-weight:bold", "font-style:italic", "text-decoration:underline"]);
        expect(el.textContent).toBe("abcdef");
    });

    it("drops layout and link tags without emitting elements", () => {
        const el = assertSafeHtml(renderRelayMicronHtml("x¦<y¦>z¦{w¦c¦l¦r¦a¦=v"));
        expect(el.querySelectorAll("a")).toHaveLength(0);
        expect(el.querySelectorAll("span")).toHaveLength(0);
        expect(el.textContent).toBe("xyzwv");
    });

    it("keeps unknown broken bars as literal text", () => {
        const el = assertSafeHtml(renderRelayMicronHtml("a¦zb¦Ff00ok¦yb"));
        expect(el.textContent).toBe("a¦zbok¦yb");
    });

    it("does not interpret raw backtick Micron", () => {
        const s = "`Ff00red`f `!bold`! `B0f0`B";
        expect(hasRelayMicron(s)).toBe(false);
        const el = assertSafeHtml(renderRelayMicronHtml(s));
        expect(el.querySelectorAll("span")).toHaveLength(0);
        expect(el.textContent).toBe(s);
    });
});

describe("relayMicron stripRelayMicron adversarial", () => {
    it("removes recognised tags and keeps everything else", () => {
        expect(stripRelayMicron("a¦Ff00b¦!c¦`d")).toBe("abcd");
        expect(stripRelayMicron("a¦zb")).toBe("a¦zb");
        expect(stripRelayMicron("no tags ¦ here")).toBe("no tags ¦ here");
        expect(stripRelayMicron("`Ff00`f backticks stay")).toBe("`Ff00`f backticks stay");
    });

    it("handles hostile input without throwing", () => {
        for (const s of ["<script>", "\uD800", "¦".repeat(1000), "&lt;&gt;&amp;"]) {
            expect(typeof stripRelayMicron(s)).toBe("string");
        }
    });
});

// Deterministic PRNG so failures reproduce.
function mulberry32(seed) {
    return function () {
        seed |= 0;
        seed = (seed + 0x6d2b79f5) | 0;
        let t = Math.imul(seed ^ (seed >>> 15), 1 | seed);
        t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t;
        return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
    };
}

function fuzzString(rand, alphabet, maxLen) {
    const len = Math.floor(rand() * maxLen);
    let s = "";
    for (let i = 0; i < len; i++) {
        s += alphabet[Math.floor(rand() * alphabet.length)];
    }
    return s;
}

describe("relayMicron fuzzing", () => {
    const alphabets = [
        // Tag-dense: valid and near-miss tag characters.
        "¦FfB!b*_`<>c{lra=}0123456789abcdefABCDEFxyz \n\t",
        // HTML-dense: injection-shaped fragments.
        "¦<>&\"'/=;()[]{}\\scriptmgonerrorjavascpt:hTp:/.-_FfB019",
        // Unicode-dense: bars, bidi, surrogate halves, wide chars.
        "¦│┃┆┊╎╏｜∣¦§\u202E\u200B\uFEFF\uFFFD\uD800\uDC00االعربية𝄞👨",
        // Link-dense.
        "¦http://a.bc/rrc://lxmf://nomadnet://0123456789abcdef0123456789abcdef:/x.mu?&=.#",
    ];
    const fragments = [
        "¦Ff00",
        "¦B0f0",
        "¦FTffffff",
        "¦BT000000",
        "¦f",
        "¦b",
        "¦!",
        "¦*",
        "¦_",
        "¦`",
        "¦<",
        ">",
        "{",
        "}",
        "c",
        "l",
        "r",
        "a",
        "=",
        "¦",
        "F",
        "B",
        "T",
        "0",
        "f",
        "g",
        "<script>",
        "</span>",
        "&",
        '"',
        "'",
        " ",
        "\n",
        "\r",
        "\t",
        "http://x.co",
        "https://a.b/c?d=e&f=g",
        "javascript:",
        "onerror=",
        "expression(",
        "\u202E",
        "\u200B",
        "\uD800",
        "\uDC00",
        "\uFFFD",
        "𝄞",
        "👨‍👩‍👧‍👦",
        "é",
        "",
        "\x00",
        "\x1F",
    ];

    it("random strings never throw and always round-trip", () => {
        const rand = mulberry32(0x5eed);
        for (const alphabet of alphabets) {
            for (let i = 0; i < 1500; i++) {
                const s = fuzzString(rand, alphabet, 200);
                // Must not throw.
                hasRelayMicron(s);
                hasRelayMicronColour(s);
                stripRelayMicron(s);
                assertRoundTrip(s);
            }
        }
    }, 30000);

    it("fragment soups never throw and always round-trip", () => {
        const rand = mulberry32(0xc0ffee);
        for (let i = 0; i < 3000; i++) {
            const count = 1 + Math.floor(rand() * 30);
            let s = "";
            for (let j = 0; j < count; j++) {
                s += fragments[Math.floor(rand() * fragments.length)];
            }
            hasRelayMicron(s);
            hasRelayMicronColour(s);
            stripRelayMicron(s);
            assertRoundTrip(s);
        }
    }, 30000);
});

describe("relayMicron pathological input", () => {
    it("handles bar floods and giant inputs without blowing up", () => {
        const cases = [
            "¦".repeat(200_000),
            "¦F".repeat(100_000),
            "¦!".repeat(100_000),
            "a¦Ff00".repeat(40_000),
            "¦Ff00".repeat(50_000),
            "x".repeat(1_000_000),
            ("http://a.co " + "y".repeat(50)).repeat(5_000),
            "¦F" + "f".repeat(200_000),
            "¦FT" + "a".repeat(200_000),
            "¦<".repeat(100_000),
        ];
        for (const s of cases) {
            const start = performance.now();
            const html = renderRelayMicronHtml(s);
            const elapsed = performance.now() - start;
            // Generous bound: catches exponential blowup, tolerates slow CI.
            expect(elapsed, `render took ${elapsed.toFixed(0)}ms for ${s.length} chars`).toBeLessThan(3000);
            assertSafeHtml(html);
        }
    }, 60000);
});
