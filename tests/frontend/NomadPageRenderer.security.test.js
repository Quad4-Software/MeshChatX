import { describe, expect, it } from "vitest";
import {
    isolateNomadLinksInHtml,
    renderNomadHtmlPage,
    renderNomadMarkdown,
    rewriteCssBodyHtmlSelectors,
    sanitizeNomadHtmlFragment,
    stripExternalFromCss,
} from "../../meshchatx/src/frontend/js/NomadPageRenderer";

function assertNoDangerousHtmlPatterns(html) {
    const lower = html.toLowerCase();
    expect(lower).not.toContain("<script");
    expect(lower).not.toContain("<iframe");
    expect(lower).not.toContain("javascript:");
    expect(lower).not.toContain("vbscript:");
    expect(lower).not.toContain("<object");
    expect(lower).not.toContain("<embed");
}

describe("NomadPageRenderer stripExternalFromCss", () => {
    it("removes @import rules", () => {
        const s = stripExternalFromCss(`@import url("http://evil.com/a.css"); p { color: red }`);
        expect(s).not.toContain("@import");
        expect(s).not.toContain("evil.com");
        expect(s).toMatch(/color:\s*red/i);
    });

    it("blocks url() pointing at http, https, or protocol-relative", () => {
        expect(stripExternalFromCss(`a { background: url(http://x/y) }`)).toContain("url(blocked:");
        expect(stripExternalFromCss(`a { background: url(https://x/y) }`)).toContain("url(blocked:");
        expect(stripExternalFromCss(`a { background: url(//x/y) }`)).toContain("url(blocked:");
    });

    it("allows local-looking and relative css without network url()", () => {
        const s = stripExternalFromCss(`p { color: #333; border: 1px solid currentColor }`);
        expect(s).toContain("#333");
        expect(s).toContain("currentColor");
    });

    it("neutralises expression() and IE-style javascript in css", () => {
        expect(stripExternalFromCss(`x{width:expression(alert(1))}`)).toContain("blocked(");
        expect(stripExternalFromCss(`x{foo:javascript:alert(1)}`)).toContain("blocked:");
    });

    it("fuzzing: stripExternalFromCss never throws", () => {
        for (let i = 0; i < 300; i++) {
            let s = "";
            const len = Math.floor(Math.random() * 2000);
            for (let j = 0; j < len; j++) {
                s += String.fromCharCode(Math.floor(Math.random() * 65536));
            }
            expect(() => stripExternalFromCss(s)).not.toThrow();
            expect(typeof stripExternalFromCss(s)).toBe("string");
        }
    });
});

describe("NomadPageRenderer rewriteCssBodyHtmlSelectors", () => {
    it("rewrites body and html block openers to nomad-html-root", () => {
        const out = rewriteCssBodyHtmlSelectors(`body { color: red } html { margin: 0 }`);
        expect(out).toContain(".nomad-html-root");
        expect(out).not.toMatch(/\bbody\s*\{/);
        expect(out).not.toMatch(/\bhtml\s*\{/);
    });

    it("rewrites html, body in selector lists", () => {
        const out = rewriteCssBodyHtmlSelectors(`html, body, p { margin: 0 }`);
        expect(out).toContain(".nomad-html-root");
    });

    it("rewrites html body descendant selector", () => {
        const out = rewriteCssBodyHtmlSelectors(`html body p { margin: 0 }`);
        expect(out).toContain(".nomad-html-root");
    });

    it("applies stripExternalFromCss inside rewrite", () => {
        const out = rewriteCssBodyHtmlSelectors(`body { background: url(https://cdn.example/bg.png) }`);
        expect(out).toContain("url(blocked:");
        expect(out).not.toMatch(/url\s*\(\s*["']?https?:\/\//i);
    });

    it("fuzzing: rewriteCssBodyHtmlSelectors never throws", () => {
        for (let i = 0; i < 200; i++) {
            let s = "";
            const len = Math.floor(Math.random() * 1500);
            for (let j = 0; j < len; j++) {
                s += String.fromCharCode(Math.floor(Math.random() * 65536));
            }
            expect(() => rewriteCssBodyHtmlSelectors(s)).not.toThrow();
            expect(typeof rewriteCssBodyHtmlSelectors(s)).toBe("string");
        }
    });
});

describe("NomadPageRenderer HTML document sanitization", () => {
    it("strips inline event handlers", () => {
        const html = renderNomadHtmlPage(
            '<body><p onclick="alert(1)" onmouseover="evil()">x</p><img onerror="bad()" src="x"></body>'
        );
        expect(html.toLowerCase()).not.toContain("onclick");
        expect(html.toLowerCase()).not.toContain("onmouseover");
        expect(html.toLowerCase()).not.toContain("onerror");
    });

    it("removes javascript and data-exfil hrefs from anchors", () => {
        const html = renderNomadHtmlPage(
            '<body><a href="javascript:alert(1)">a</a><a href="data:text/html,<script>x</script>">b</a><a href="https://evil.com">c</a></body>'
        );
        expect(html).not.toContain("javascript:");
        expect(html).not.toContain("evil.com");
    });

    it("strips external img src except safe data:image", () => {
        const html = renderNomadHtmlPage(
            '<body><img src="https://evil.com/i.png"><img src="data:image/png;base64,iVBORw0KGgo="></body>'
        );
        expect(html).not.toContain("evil.com");
        expect(html).toContain("data:image/png");
    });

    it("sanitises style text with network url in document", () => {
        const html = renderNomadHtmlPage("<body><style>p { background: url(http://x/y) }</style><p>ok</p></body>");
        expect(html).not.toContain("http://x");
        expect(html).toContain("ok");
    });

    it("handles nested style in body and head-less fragment", () => {
        const html = renderNomadHtmlPage("<p>x</p><style>body{color:blue}</style>");
        expect(html).toContain("nomad-html-root");
        expect(html).toContain(".nomad-html-root");
    });

    it("adversarial templates do not throw and omit script-like vectors", () => {
        const templates = [
            "<svg onload=alert(1)></svg>",
            '<math><mi//xlink:href="javascript:alert(1)">',
            "<body><style>@import 'http://a.com/b.css';</style></body>",
            "<template><script>alert(1)</script></template>",
            "<marquee onstart=alert(1)>x</marquee>",
            String.raw`<body><a href="jav&#x09;ascript:alert(1)">x</a></body>`,
        ];
        for (const t of templates) {
            expect(() => renderNomadHtmlPage(t)).not.toThrow();
            assertNoDangerousHtmlPatterns(renderNomadHtmlPage(t));
        }
    });

    it("fuzzing: renderNomadHtmlPage high-volume random and mixed payloads", () => {
        const snippets = [
            "<script>x</script>",
            "<style>body{background:url(https://a.b/c)}</style>",
            "<iframe src=x></iframe>",
            "<a href=http://x>y</a>",
            "<svg><script>.</script></svg>",
        ];
        for (let i = 0; i < 400; i++) {
            let s = snippets[i % snippets.length];
            const extra = Math.floor(Math.random() * 1200);
            for (let j = 0; j < extra; j++) {
                s += String.fromCharCode(Math.floor(Math.random() * 65536));
            }
            let out;
            expect(() => {
                out = renderNomadHtmlPage(s);
            }).not.toThrow();
            assertNoDangerousHtmlPatterns(out);
        }
    });
});

describe("NomadPageRenderer in-renderer link isolation", () => {
    const hash = "a".repeat(32);

    it("isolateNomadLinksInHtml rewrites /page links to data-nomadnet-url and href #", () => {
        const out = isolateNomadLinksInHtml('<p><a href="/page/x.mu">t</a></p>', hash);
        expect(out).toContain(`data-nomadnet-url="${hash}:/page/x.mu"`);
        expect(out).toContain('href="#"');
        expect(out).not.toContain('href="/page/');
    });

    it("renderNomadHtmlPage with destinationHash isolates relative links", () => {
        const html = renderNomadHtmlPage('<body><a href="/page/a.html">x</a></body>', { destinationHash: hash });
        expect(html).toContain(`data-nomadnet-url="${hash}:/page/a.html"`);
        expect(html).not.toMatch(/href="\/page\//);
    });

    it("renderNomadMarkdown with destinationHash isolates relative links", () => {
        const html = renderNomadMarkdown("[l](/page/b.md)", { destinationHash: hash });
        expect(html).toContain(`data-nomadnet-url="${hash}:/page/b.md"`);
        expect(html).not.toMatch(/href="\/page\//);
    });
});

describe("NomadPageRenderer fragment and markdown sanitization", () => {
    it("sanitizeNomadHtmlFragment removes script and keeps safe markup", () => {
        const out = sanitizeNomadHtmlFragment("<div>ok</div><script>bad</script>");
        expect(out.toLowerCase()).not.toContain("<script");
        expect(out).toContain("ok");
    });

    it("markdown pipeline does not emit executable URLs", () => {
        const md = "[l](javascript:void(0))\n\n[ext](https://bad.example)\n\n`code`";
        const html = renderNomadMarkdown(md);
        assertNoDangerousHtmlPatterns(html);
        expect(html).not.toContain("bad.example");
    });

    it("fuzzing: sanitizeNomadHtmlFragment and renderNomadMarkdown combined stress", () => {
        for (let i = 0; i < 250; i++) {
            let s = "";
            const len = Math.floor(Math.random() * 600);
            for (let j = 0; j < len; j++) {
                s += String.fromCharCode(Math.floor(Math.random() * 65536));
            }
            expect(() => sanitizeNomadHtmlFragment(s)).not.toThrow();
            expect(() => renderNomadMarkdown(s)).not.toThrow();
            assertNoDangerousHtmlPatterns(renderNomadMarkdown(s));
        }
    });
});
