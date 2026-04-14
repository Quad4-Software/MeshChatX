import DOMPurify from "dompurify";
import { marked } from "marked";

marked.setOptions({
    gfm: true,
    breaks: true,
});

const FORBID_TAGS = [
    "script",
    "iframe",
    "object",
    "embed",
    "link",
    "base",
    "meta",
    "form",
    "input",
    "button",
    "textarea",
    "select",
    "option",
    "video",
    "audio",
    "source",
    "track",
    "picture",
];

function escapeHtmlText(text) {
    return String(text)
        .replace(/&/g, "&amp;")
        .replace(/</g, "&lt;")
        .replace(/>/g, "&gt;")
        .replace(/"/g, "&quot;")
        .replace(/'/g, "&#039;");
}

export function escapeNomadPlainText(content) {
    return `<div class="whitespace-pre-wrap text-gray-900 dark:text-gray-100">${escapeHtmlText(content)}</div>`;
}

const NOMAD_HTML_ROOT_CLASS = "nomad-html-root";

function normalizeMarkdownInput(md) {
    if (md == null || md === "") {
        return "";
    }
    let s = String(md);
    s = s.replace(/\r\n/g, "\n");
    // CommonMark requires a space after # for ATX headings; "#Title" is not a heading
    s = s.replace(/^(\s{0,3})(#{1,6})([^\s#])/gm, "$1$2 $3");
    return s;
}

export function rewriteCssBodyHtmlSelectors(css) {
    if (!css) {
        return "";
    }
    let s = stripExternalFromCss(css);
    s = s.replace(/\bhtml\s*\{/g, `.${NOMAD_HTML_ROOT_CLASS} {`);
    s = s.replace(/\bbody\s*\{/g, `.${NOMAD_HTML_ROOT_CLASS} {`);
    s = s.replace(/\bhtml\s*,/g, `.${NOMAD_HTML_ROOT_CLASS},`);
    s = s.replace(/\bbody\s*,/g, `.${NOMAD_HTML_ROOT_CLASS},`);
    s = s.replace(/\bhtml\s+body\b/g, `.${NOMAD_HTML_ROOT_CLASS}`);
    return s;
}

export function stripExternalFromCss(css) {
    if (!css) {
        return "";
    }
    let s = css;
    s = s.replace(/@import\s+[^;]+;/gi, "");
    s = s.replace(/@import\s+url\s*\([^)]+\)\s*;?/gi, "");
    s = s.replace(/expression\s*\(/gi, "blocked(");
    s = s.replace(/javascript\s*:/gi, "blocked:");
    s = s.replace(/-moz-binding/gi, "blocked-binding");
    s = s.replace(/url\s*\(\s*["']?(?:https?:|\/\/)/gi, "url(blocked:");
    return s;
}

function isAllowedNomadHref(href) {
    if (href == null || href === "") {
        return false;
    }
    const h = href.trim();
    const lower = h.toLowerCase();
    if (
        lower.startsWith("http:") ||
        lower.startsWith("https:") ||
        lower.startsWith("//") ||
        lower.startsWith("javascript:") ||
        lower.startsWith("vbscript:") ||
        lower.startsWith("data:") ||
        lower.startsWith("mailto:") ||
        lower.startsWith("ftp:") ||
        lower.startsWith("file:")
    ) {
        return false;
    }
    if (h.startsWith("#")) {
        return true;
    }
    if (h.startsWith(":") && !h.startsWith("://")) {
        return true;
    }
    if (/^[a-f0-9]{32}:/i.test(h)) {
        return true;
    }
    if (h.startsWith("/page/") || h.startsWith("/file/")) {
        return true;
    }
    return false;
}

/**
 * Rewrites in-renderer links so the browser does not follow relative or mesh paths as normal navigation.
 * Produces `href="#"` plus `data-nomadnet-url` for use with NomadNetworkPage `onElementClick`.
 */
export function isolateNomadLinksInHtml(html, destinationHash) {
    if (!html || !destinationHash || typeof destinationHash !== "string") {
        return html;
    }
    const dh = destinationHash.trim();
    if (!/^[a-f0-9]{32}$/i.test(dh)) {
        return html;
    }
    try {
        const parser = new DOMParser();
        const doc = parser.parseFromString(`<div class="nomad-link-root">${html}</div>`, "text/html");
        const root = doc.body.firstElementChild;
        if (!root) {
            return html;
        }
        const anchors = root.querySelectorAll("a[href]");
        anchors.forEach((a) => {
            const href = a.getAttribute("href");
            if (href == null) {
                return;
            }
            const h = href.trim();
            if (h.startsWith("#")) {
                if (h === "" || h === "#") {
                    a.setAttribute("href", "#");
                }
                return;
            }
            let full = null;
            if (/^[a-f0-9]{32}:/i.test(h)) {
                full = h;
            } else if (h.startsWith("/page/") || h.startsWith("/file/")) {
                full = `${dh}:${h}`;
            } else if (h.startsWith(":") && !h.startsWith("://")) {
                full = `${dh}:${h.slice(1)}`;
            }
            if (full) {
                a.setAttribute("href", "#");
                a.setAttribute("data-nomadnet-url", full);
                a.classList.add("nomadnet-link", "text-blue-600", "dark:text-blue-400", "hover:underline");
            } else {
                a.setAttribute("href", "#");
            }
            a.removeAttribute("target");
            a.removeAttribute("rel");
        });
        return root.innerHTML;
    } catch {
        return html;
    }
}

function isAllowedImgSrc(src) {
    if (src == null || src === "") {
        return false;
    }
    const s = src.trim();
    return /^data:image\/(png|gif|jpeg|jpg|webp|svg\+xml)/i.test(s);
}

let nomadPurifyHooksInstalled = false;

function ensureNomadPurifyHooks() {
    if (nomadPurifyHooksInstalled) {
        return;
    }
    nomadPurifyHooksInstalled = true;
    DOMPurify.addHook("uponSanitizeElement", (node) => {
        if (node.nodeName === "STYLE" && node.textContent) {
            node.textContent = stripExternalFromCss(node.textContent);
        }
    });
    DOMPurify.addHook("afterSanitizeAttributes", (node) => {
        if (node.nodeName === "A" && node.hasAttribute("href")) {
            const h = node.getAttribute("href");
            if (!isAllowedNomadHref(h)) {
                node.removeAttribute("href");
            }
        }
        if (node.nodeName === "IMG" && node.hasAttribute("src")) {
            const s = node.getAttribute("src");
            if (!isAllowedImgSrc(s)) {
                node.removeAttribute("src");
            }
        }
        if (node.hasAttributes) {
            const attrs = node.attributes;
            for (let i = attrs.length - 1; i >= 0; i--) {
                const a = attrs[i].name;
                if (a && a.toLowerCase().startsWith("on")) {
                    node.removeAttribute(a);
                }
            }
        }
    });
}

function basePurifyConfig() {
    return {
        FORBID_TAGS,
        ADD_TAGS: ["style"],
        ADD_ATTR: ["class", "id", "title", "colspan", "rowspan", "align", "start"],
    };
}

export function sanitizeNomadHtmlFragment(html) {
    ensureNomadPurifyHooks();
    return DOMPurify.sanitize(html, {
        ...basePurifyConfig(),
        WHOLE_DOCUMENT: false,
    });
}

export function sanitizeNomadHtmlDocument(html) {
    ensureNomadPurifyHooks();
    let bodyMarkup = html;
    try {
        const parser = new DOMParser();
        const doc = parser.parseFromString(html, "text/html");
        const styles = [...doc.querySelectorAll("style")]
            .map((el) => rewriteCssBodyHtmlSelectors(el.textContent || ""))
            .filter(Boolean)
            .join("\n");
        const body = doc.body;
        if (body) {
            bodyMarkup = (styles ? `<style>${styles}</style>` : "") + body.innerHTML;
        }
    } catch {
        bodyMarkup = html;
    }
    const wrapped = `<div class="${NOMAD_HTML_ROOT_CLASS}">${bodyMarkup}</div>`;
    return DOMPurify.sanitize(wrapped, {
        ...basePurifyConfig(),
        WHOLE_DOCUMENT: false,
    });
}

export function renderNomadMarkdown(markdown, options = {}) {
    const { destinationHash } = options;
    const raw = marked.parse(normalizeMarkdownInput(markdown ?? ""));
    let inner = sanitizeNomadHtmlFragment(raw);
    if (destinationHash) {
        inner = isolateNomadLinksInHtml(inner, destinationHash);
    }
    return `<div class="nomad-markdown">${inner}</div>`;
}

export function renderNomadHtmlPage(html, options = {}) {
    const { destinationHash } = options;
    let out = sanitizeNomadHtmlDocument(html);
    if (destinationHash) {
        out = isolateNomadLinksInHtml(out, destinationHash);
    }
    return out;
}

export function renderNomadPageByPath(
    pagePathWithoutData,
    content,
    pagePartials,
    MicronParserClass,
    renderOptions = {}
) {
    const renderMarkdown = renderOptions.renderMarkdown !== false;
    const renderHtml = renderOptions.renderHtml !== false;
    const renderPlaintext = renderOptions.renderPlaintext !== false;
    const nomadDestinationHash = renderOptions.nomadDestinationHash || null;
    const linkOpts = { destinationHash: nomadDestinationHash };
    const p = (pagePathWithoutData || "").toLowerCase();
    if (p.endsWith(".mu")) {
        const muParser = new MicronParserClass();
        let out = muParser.convertMicronToHtml(content, pagePartials);
        if (nomadDestinationHash) {
            out = isolateNomadLinksInHtml(out, nomadDestinationHash);
        }
        return out;
    }
    if (p.endsWith(".md")) {
        if (renderMarkdown) {
            return renderNomadMarkdown(content, linkOpts);
        }
        return escapeNomadPlainText(content);
    }
    if (p.endsWith(".html")) {
        if (renderHtml) {
            return renderNomadHtmlPage(content, linkOpts);
        }
        return escapeNomadPlainText(content);
    }
    if (p.endsWith(".txt")) {
        if (renderPlaintext) {
            return escapeNomadPlainText(content);
        }
        return `<pre class="whitespace-pre-wrap text-gray-900 dark:text-gray-100">${escapeHtmlText(content)}</pre>`;
    }
    return escapeHtmlText(content);
}
