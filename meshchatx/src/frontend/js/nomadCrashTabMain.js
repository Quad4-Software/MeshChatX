// SPDX-License-Identifier: 0BSD
/**
 * Isolated Nomad page renderer (runs inside NomadCrashTab iframe).
 *
 * Heavy Micron/Markdown/HTML work stays off the MeshChatX shell thread.
 * Parent cancels by reloading this frame.
 */

import MicronParser from "./MicronParser.js";
import { renderNomadPageByPath } from "./NomadPageRenderer.js";
import { NOMAD_CRASH_TAB_CHANNEL } from "./nomadCrashTabShell.js";

const root = document.getElementById("root");
let renderSeq = 0;

function post(msg) {
    parent.postMessage({ channel: NOMAD_CRASH_TAB_CHANNEL, ...msg }, "*");
}

function collectFields(filterNames) {
    const inputs = root.querySelectorAll("input,textarea");
    const out = {};
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
            const id = decodeURIComponent(fh.slice(1));
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

function applyChrome(msg) {
    root.className = msg.className || "";
    root.style.color = msg.color || "";
    root.style.background = msg.background || "transparent";
}

async function renderPage(msg, seq) {
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
    // Keep WASM out of the crash tab. JS Micron is enough and avoids cross-frame wasm bootstrap.
    const opts = { ...renderOptions, nomad_micron_wasm_use: false };
    let html = "";
    try {
        html = renderNomadPageByPath(pagePathWithoutData, content, pagePartials, MicronParser, opts);
    } catch (err) {
        if (seq === renderSeq) {
            post({
                type: "render-error",
                message: err && err.message ? String(err.message) : "render_failed",
            });
        }
        return;
    }
    if (seq !== renderSeq) {
        return;
    }
    root.innerHTML = html || "";
    post({ type: "render-done", partials: listPartials() });
}

window.addEventListener("message", (ev) => {
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
        root.innerHTML = "";
        post({ type: "aborted" });
        return;
    }
    if (d.type === "clear") {
        renderSeq += 1;
        root.innerHTML = "";
        root.className = "";
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
            target = root.querySelector(`[data-partial-id="${String(id).replace(/"/g, "")}"]`);
        }
        if (target) {
            target.innerHTML = d.html || "";
        }
        return;
    }
    if (d.type === "render") {
        renderSeq += 1;
        const seq = renderSeq;
        post({ type: "render-started", seq });
        // Yield so the shell can paint Cancel / stay responsive before heavy work.
        setTimeout(() => {
            if (seq !== renderSeq) {
                return;
            }
            void renderPage(d, seq);
        }, 0);
    }
});

root.addEventListener("click", onClick, true);
root.addEventListener("auxclick", onClick, true);
post({ type: "ready" });
