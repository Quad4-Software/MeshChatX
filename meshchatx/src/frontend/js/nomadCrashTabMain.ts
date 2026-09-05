// SPDX-License-Identifier: 0BSD
/**
 * Isolated Nomad page renderer (runs inside NomadCrashTab iframe).
 *
 * Heavy Micron/Markdown/HTML work stays off the MeshChatX shell thread.
 * Parent cancels by reloading this frame.
 *
 * Boot is intentionally thin: paint dark chrome and post ready before loading
 * parsers so the shell can keep a warm frame during page download.
 */

import "../css/nomad-page-chrome.css";
import { NOMAD_CRASH_TAB_CHANNEL } from "./nomadCrashTabShell.js";

const root = document.getElementById("root");
let renderSeq = 0;
let multilineCleanup = null;
let rendererPromise = null;

function post(msg) {
    // Opaque sandbox frames must use "*". Parent accepts only event.origin "null"
    // from this frame's contentWindow (see NomadCrashTab.onWindowMessage).
    parent.postMessage({ channel: NOMAD_CRASH_TAB_CHANNEL, ...msg }, "*");
}

function paintShell(background, color) {
    const bg = background && background !== "transparent" ? background : "#000000";
    const fg = color || "#dddddd";
    root.style.background = bg;
    root.style.color = fg;
    document.body.style.background = bg;
    document.body.style.color = fg;
    document.documentElement.style.background = bg;
}

function loadRenderer() {
    if (rendererPromise) {
        return rendererPromise;
    }
    rendererPromise = Promise.all([
        import("./MicronParser.js"),
        import("./NomadPageRenderer.js"),
        import("./MicronWasmLoader.js"),
        import("dompurify"),
        import("../fonts/RobotoMonoNerdFont/font.css"),
    ]).then(([micronMod, pageMod, wasmMod, purifyMod]) => {
        const DOMPurify = purifyMod.default || purifyMod;
        globalThis.DOMPurify = DOMPurify;
        if (typeof window !== "undefined") {
            window.DOMPurify = DOMPurify;
        }
        return {
            MicronParser: micronMod.default || micronMod,
            renderNomadPageByPath: pageMod.renderNomadPageByPath,
            resolveNomadPageShellBackground: pageMod.resolveNomadPageShellBackground,
            preloadNomadMicronWasm: wasmMod.preloadNomadMicronWasm,
        };
    });
    return rendererPromise;
}

function teardownMultiline() {
    if (typeof multilineCleanup === "function") {
        try {
            multilineCleanup();
        } catch (e) {
            console.warn("nomad crash-tab: multiline cleanup failed", e);
        }
    }
    multilineCleanup = null;
}

function setupMultilineForMicron(MicronParser, pagePath, renderOptions) {
    teardownMultiline();
    const pl = String(pagePath || "").toLowerCase();
    if (!pl.endsWith(".mu")) {
        return;
    }
    if (renderOptions && renderOptions.nomad_micron_wasm_use === true) {
        return;
    }
    const onArmed = (e) => {
        e.detail?.element?.classList?.add("Mu-armed");
    };
    const onDisarmed = (e) => {
        e.detail?.element?.classList?.remove("Mu-armed");
    };
    const onExpanded = (e) => {
        e.detail?.element?.classList?.add("Mu-multiline");
    };
    root.addEventListener("micron-multiline-armed", onArmed);
    root.addEventListener("micron-multiline-disarmed", onDisarmed);
    root.addEventListener("micron-field-multiline-enabled", onExpanded);
    const detach = MicronParser.enableDoubleEnterMultiline(root, {
        windowMs: 500,
        rows: 4,
    });
    multilineCleanup = () => {
        root.removeEventListener("micron-multiline-armed", onArmed);
        root.removeEventListener("micron-multiline-disarmed", onDisarmed);
        root.removeEventListener("micron-field-multiline-enabled", onExpanded);
        if (typeof detach === "function") {
            detach();
        }
    };
}

function collectFields(filterNames) {
    const inputs = root.querySelectorAll<HTMLInputElement>("input,textarea");
    const out: any = {};
    let allow = null;
    if (filterNames && filterNames !== "*") {
        allow = {};
        String(filterNames)
            .split("|")
            .forEach((n) => {
                if (n) {
                    allow[n] = true;
                }
            });
    }
    for (const input of inputs) {
        const name = input.name || input.id || input.type;
        if (!name) {
            continue;
        }
        if (allow && !allow[name]) {
            continue;
        }
        if (input.type === "radio" || input.type === "checkbox") {
            if (input.checked) {
                out[name] = input.value;
            }
        } else {
            out[name] = input.value;
        }
    }
    return out;
}

function listPartials() {
    return [...root.querySelectorAll(".mu-partial")].map((el) => ({
        id: el.getAttribute("data-partial-id"),
        dest: el.getAttribute("data-dest"),
        path: el.getAttribute("data-path"),
        refresh: el.getAttribute("data-refresh"),
        fields: el.getAttribute("data-fields"),
    }));
}

function escapeSource(content) {
    return String(content ?? "")
        .replace(/&/g, "&amp;")
        .replace(/</g, "&lt;")
        .replace(/>/g, "&gt;")
        .replace(/"/g, "&quot;")
        .replace(/'/g, "&#039;");
}

function onClick(event) {
    const t = event.target;
    if (!t || !t.closest) {
        return;
    }
    const nomad = t.closest("a.nomadnet-link[data-nomadnet-url]");
    if (nomad) {
        event.preventDefault();
        event.stopPropagation();
        post({
            type: "navigate",
            kind: "nomad",
            url: nomad.getAttribute("data-nomadnet-url"),
            button: event.button,
            ctrlKey: !!event.ctrlKey,
            metaKey: !!event.metaKey,
            fields: null,
        });
        return;
    }
    const lxmf = t.closest("a.lxmf-link[data-lxmf-address]");
    if (lxmf) {
        event.preventDefault();
        event.stopPropagation();
        post({
            type: "navigate",
            kind: "lxmf",
            url: lxmf.getAttribute("data-lxmf-address"),
            button: event.button,
            ctrlKey: !!event.ctrlKey,
            metaKey: !!event.metaKey,
            fields: null,
        });
        return;
    }
    const node = t.closest('[data-action="openNode"]');
    if (node) {
        event.preventDefault();
        event.stopPropagation();
        const fieldSpec = node.getAttribute("data-fields");
        let fields = null;
        if (fieldSpec === "" || fieldSpec === "*") {
            fields = collectFields("*");
        } else if (fieldSpec) {
            fields = collectFields(fieldSpec);
        }
        post({
            type: "navigate",
            kind: "openNode",
            url: node.getAttribute("data-destination"),
            button: event.button,
            ctrlKey: !!event.ctrlKey,
            metaKey: !!event.metaKey,
            fields,
            fieldSpec,
        });
        return;
    }
    const httpA = t.closest("a[href],a[data-http-url]");
    if (httpA && !httpA.classList.contains("nomadnet-link")) {
        const dataHttp = httpA.getAttribute("data-http-url");
        const href = httpA.getAttribute("href") || "";
        const candidate = (dataHttp || href || "").trim();
        if (/^https?:\/\//i.test(candidate)) {
            event.preventDefault();
            event.stopPropagation();
            post({
                type: "navigate",
                kind: "http",
                url: candidate,
                button: event.button,
                ctrlKey: !!event.ctrlKey,
                metaKey: !!event.metaKey,
                fields: null,
            });
            return;
        }
    }
    const frag = t.closest("a[href]");
    if (frag) {
        const fh = (frag.getAttribute("href") || "").trim();
        if (fh.charAt(0) === "#" && fh.length > 1 && !frag.getAttribute("data-nomadnet-url")) {
            event.preventDefault();
            event.stopPropagation();
            let id = fh.slice(1);
            try {
                id = decodeURIComponent(id);
            } catch {
                return;
            }
            let el = null;
            try {
                el = root.querySelector(`#${CSS.escape(id)}`);
            } catch {
                el = document.getElementById(id);
            }
            if (el) {
                el.scrollIntoView({ behavior: "smooth", block: "nearest" });
            }
            return;
        }
        if (fh && fh !== "#" && fh.charAt(0) !== "#") {
            event.preventDefault();
            event.stopPropagation();
        }
    }
}

/**
 * Build iframe root classes. Always include nodeContainer so ForceMonospace
 * Mu-mnt / Mu-mws cells use the Nomad monospace grid.
 */
function applyChrome(msg) {
    const parts = ["nodeContainer"];
    const fromParent = String(msg.className || "")
        .split(/\s+/)
        .filter(Boolean);
    for (const c of fromParent) {
        if (!parts.includes(c)) {
            parts.push(c);
        }
    }
    if (msg.showSource === true && !parts.includes("source")) {
        parts.push("source");
    }
    if (msg.showSource === true && !parts.includes("bg-black")) {
        parts.push("bg-black");
    }
    root.className = parts.join(" ");
    paintShell(msg.background || "#000000", msg.color || "#dddddd");
}

async function renderPage(msg, seq, api) {
    teardownMultiline();
    applyChrome(msg);
    const path = msg.path || "";
    const content = msg.content ?? "";
    if (msg.showSource) {
        root.innerHTML = escapeSource(content);
        if (seq === renderSeq) {
            post({ type: "render-done", partials: [] });
        }
        return;
    }
    const [pagePathWithoutData] = String(path).split("`");
    const pagePartials = msg.pagePartials && typeof msg.pagePartials === "object" ? msg.pagePartials : {};
    const renderOptions = msg.renderOptions && typeof msg.renderOptions === "object" ? msg.renderOptions : {};
    if (renderOptions.nomad_micron_wasm_use === true) {
        await api.preloadNomadMicronWasm();
    }
    if (seq !== renderSeq) {
        return;
    }
    const opts: any = { ...renderOptions };
    let html = "";
    try {
        html = api.renderNomadPageByPath(pagePathWithoutData, content, pagePartials, api.MicronParser, opts);
    } catch (err) {
        if (seq === renderSeq) {
            const error = err as Error;
            post({
                type: "render-error",
                message: error.message ? String(error.message) : "render_failed",
            });
        }
        return;
    }
    if (seq !== renderSeq) {
        return;
    }
    root.innerHTML = html || "";
    const pageShell = root.querySelector<HTMLElement>(".mu-page");
    if (pageShell) {
        const pageBg = pageShell.style.backgroundColor;
        const pageFg = pageShell.style.color;
        if (pageBg) {
            paintShell(pageBg, pageFg || root.style.color || "#dddddd");
            post({ type: "shell-background", background: pageBg });
        } else if (pageFg) {
            root.style.color = pageFg;
            document.body.style.color = pageFg;
        }
    } else {
        const resolved = api.resolveNomadPageShellBackground(root);
        if (resolved) {
            paintShell(resolved, root.style.color || "#dddddd");
            post({ type: "shell-background", background: resolved });
        }
    }
    setupMultilineForMicron(api.MicronParser, pagePathWithoutData, opts);
    post({ type: "render-done", partials: listPartials() });
}

window.addEventListener("message", (ev) => {
    if (ev.source !== window.parent) {
        return;
    }
    const d = ev.data;
    if (!d || d.channel !== NOMAD_CRASH_TAB_CHANNEL) {
        return;
    }
    if (d.type === "ping") {
        post({ type: "pong", id: d.id });
        return;
    }
    if (d.type === "abort") {
        renderSeq += 1;
        teardownMultiline();
        root.innerHTML = "";
        paintShell("#000000", "#dddddd");
        post({ type: "aborted" });
        return;
    }
    if (d.type === "clear") {
        renderSeq += 1;
        teardownMultiline();
        root.innerHTML = "";
        root.className = "nodeContainer";
        paintShell("#000000", "#dddddd");
        return;
    }
    if (d.type === "chrome") {
        applyChrome(d);
        return;
    }
    if (d.type === "set-partial") {
        const id = d.id || "";
        if (!id) {
            return;
        }
        let target = null;
        try {
            target = root.querySelector(`[data-partial-id="${CSS.escape(id)}"]`);
        } catch {
            target = null;
        }
        if (target) {
            target.innerHTML = d.html || "";
        }
        return;
    }
    if (d.type === "render") {
        renderSeq += 1;
        const seq = renderSeq;
        // Paint expected chrome before loading parsers so the frame stays dark.
        applyChrome(d);
        post({ type: "render-started", seq });
        void loadRenderer()
            .then((api) => {
                if (seq !== renderSeq) {
                    return null;
                }
                return renderPage(d, seq, api);
            })
            .catch((err) => {
                if (seq !== renderSeq) {
                    return;
                }
                post({
                    type: "render-error",
                    message: err && err.message ? String(err.message) : "renderer_load_failed",
                });
            });
    }
});

root.addEventListener("click", onClick, true);
root.addEventListener("auxclick", onClick, true);
paintShell("#000000", "#dddddd");
// Warm the parser chunk while the shell downloads the page.
void loadRenderer();
post({ type: "ready" });
