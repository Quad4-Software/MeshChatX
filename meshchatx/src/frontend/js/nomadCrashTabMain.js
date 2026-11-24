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
import { shouldOpenCustomContextMenu } from "./contextMenuUtils.js";
import { DESKTOP_ZOOM_MESSAGE_TYPE, desktopZoomKeyAction, desktopZoomWheelAction } from "./desktopZoom.js";

const root = document.getElementById("root");
let renderSeq = 0;
let displayMode = "fit";

// Legibility floor. Very wide art still fits because the guarantee is no
// horizontal overflow, so the floor stays permissive.
const FIT_MIN_SCALE = 0.05;

function resetDisplayModeStyles() {
    root.style.zoom = "";
    root.style.transform = "";
    root.style.transformOrigin = "";
    root.style.marginBottom = "";
    root.style.width = "";
    root.style.maxWidth = "";
    for (const el of root.querySelectorAll("[data-fit-zoom]")) {
        el.style.zoom = "";
        delete el.dataset.fitZoom;
    }
}

function applyDisplayMode() {
    const body = document.body;
    body.classList.remove("mcx-display-fit", "mcx-display-scroll");
    body.dataset.displayMode = displayMode;
    resetDisplayModeStyles();
    delete root.dataset.fitScale;
    if (displayMode === "off") {
        body.style.overflowX = "hidden";
        return;
    }
    if (displayMode === "scroll") {
        // Natural width, horizontal scroll inside this frame only.
        body.classList.add("mcx-display-scroll");
        body.style.overflowX = "auto";
        return;
    }
    // The fit class removes pre clipping so the widest line is measurable.
    body.classList.add("mcx-display-fit");
    body.style.overflowX = "hidden";
    const avail = document.documentElement.clientWidth;
    if (avail <= 0) {
        return;
    }
    // Wide ASCII/box art wraps instead of overflowing, so page-level scaling
    // never caught it and banners fell apart on narrow screens. Zoom each run
    // of art lines on its own so the block stays whole; text keeps its size.
    zoomArtRunsToFit(avail);
    const natural = widestContentWidth();
    if (natural <= 0 || natural <= avail) {
        return;
    }
    let scale = Math.max(FIT_MIN_SCALE, avail / natural);
    // transform does not trigger relayout, so rendered width is exactly
    // layout width times scale. zoom would relayout shrink-to-fit content
    // and overshoot. The transform leaves the layout box at natural size,
    // so pull the empty space back with a negative bottom margin.
    for (let i = 0; i < 4; i++) {
        root.dataset.fitScale = String(scale);
        root.style.transformOrigin = "0 0";
        root.style.transform = `scale(${scale})`;
        // .nodeContainer caps root at the screen width. Undo that for the
        // scaled page so prose wraps across the width the scale frees up
        // instead of shrinking into a strip on the left.
        root.style.maxWidth = "none";
        root.style.width = `${100 / scale}%`;
        // scrollWidth is transform-invariant, so multiplying it predicts the
        // scaled width even if a rect read misses the transform.
        const rendered = Math.max(widestRenderedWidth(), root.scrollWidth * scale);
        if (rendered <= avail + 1) {
            break;
        }
        const correction = Math.max(FIT_MIN_SCALE, scale * (avail / rendered));
        if (Math.abs(correction - scale) < 0.001) {
            break;
        }
        scale = correction;
    }
    root.style.marginBottom = `${-((1 - scale) * root.scrollHeight)}px`;
}

// A line is art when it carries 3+ box/block drawing characters, or when
// letters and digits are rare enough that it is figlet-style ASCII art.
const ART_BOX_RE = /[\u2500-\u259f]{3}/;
const ART_ALNUM_RE = /[\p{L}\p{N}]/gu;

function looksLikeArtLine(text) {
    if (ART_BOX_RE.test(text)) {
        return true;
    }
    const compact = text.replace(/\s/g, "");
    if (!compact.length) {
        return false;
    }
    const alnum = compact.match(ART_ALNUM_RE)?.length || 0;
    return alnum < compact.length * 0.25;
}

// Zoom consecutive runs of wide art lines so each banner fits on one row.
// Leaf divs only: a line that contains divs is a container, not a line.
function zoomArtRunsToFit(avail) {
    const lines = [];
    for (const el of root.querySelectorAll("div")) {
        if (el.querySelector("div") || el.getAttribute("role") === "separator") {
            continue;
        }
        if (looksLikeArtLine(el.textContent || "")) {
            lines.push(el);
        }
    }
    const runs = [];
    let prev = null;
    for (const el of lines) {
        if (prev && el.previousElementSibling === prev) {
            runs[runs.length - 1].push(el);
        } else {
            runs.push([el]);
        }
        prev = el;
    }
    for (const run of runs) {
        let widest = 0;
        for (const el of run) {
            const prevWidth = el.style.width;
            el.style.width = "max-content";
            const w = el.getBoundingClientRect().width;
            el.style.width = prevWidth;
            if (w > widest) {
                widest = w;
            }
        }
        if (widest <= avail + 1) {
            continue;
        }
        const zoom = Math.max(0.2, (avail - 2) / widest);
        for (const el of run) {
            el.dataset.fitZoom = String(zoom);
            el.style.zoom = String(zoom);
        }
    }
}

// Pre-scale measurement: scrollWidth still reflects content that inner
// clips hide, so take the max of both metrics across descendants.
function widestContentWidth() {
    const clippedX = /^(?:hidden|clip)$/;
    let w = root.scrollWidth;
    const els = root.querySelectorAll("*");
    for (let i = 0; i < els.length; i++) {
        const el = els[i];
        // Screen-reader copies and already-zoomed art lines must not drive
        // the page scale.
        if (el.closest(".Mu-sr, [data-fit-zoom]")) {
            continue;
        }
        const r = el.getBoundingClientRect().width;
        const s = el.scrollWidth;
        if (r <= w && s <= w) {
            continue;
        }
        const cs = getComputedStyle(el);
        // Wrapped inline boxes cannot show horizontal overflow of their own.
        if (cs.display === "inline") {
            continue;
        }
        const clipped = clippedX.test(cs.overflowX);
        // Clipped absolutely-positioned content (Mu-sr style) never paints.
        if (clipped && cs.position === "absolute") {
            continue;
        }
        if (r > w) w = r;
        // scrollWidth counts overflow that overflow:hidden/clip hides
        // (`-` dividers run 250 chars but only paint to the edge), so only
        // trust it where the overflow can actually show.
        if (!clipped && s > w) w = s;
    }
    return w;
}

// Post-scale check: scrollWidth inflates under zoom because it reports
// layout pixels, so only rendered rects are meaningful here.
function widestRenderedWidth() {
    let w = root.getBoundingClientRect().width;
    const els = root.querySelectorAll("*");
    for (let i = 0; i < els.length; i++) {
        const r = els[i].getBoundingClientRect().width;
        if (r > w) w = r;
    }
    return w;
}
let multilineCleanup = null;
let rendererPromise = null;

window.addEventListener("resize", () => {
    if (displayMode === "fit") {
        applyDisplayMode();
    }
});

// Webfonts change monospace metrics after load, so a fit computed early
// can drift wide. Re-measure whenever a font finishes loading.
if (document.fonts) {
    if (typeof document.fonts.addEventListener === "function") {
        document.fonts.addEventListener("loadingdone", () => {
            if (displayMode === "fit") {
                applyDisplayMode();
            }
        });
    }
    if (typeof document.fonts.ready === "object") {
        document.fonts.ready.then(() => {
            if (displayMode === "fit") {
                applyDisplayMode();
            }
        });
    }
}

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

function readImage(el) {
    return {
        url: el.getAttribute("data-mu-image-url") || "",
        path: el.getAttribute("data-mu-image-path") || el.getAttribute("data-mu-image-url") || "",
        alt: el.getAttribute("data-mu-image-alt") || "",
        w: el.getAttribute("data-mu-image-w") || null,
        h: el.getAttribute("data-mu-image-h") || null,
        size: el.getAttribute("data-mu-image-s") || null,
        key: el.getAttribute("data-mu-image-k") || "",
        align: el.getAttribute("data-mu-image-a") || "left",
        profile: el.getAttribute("data-mu-image-profile") || "",
    };
}

function listImages() {
    return [...root.querySelectorAll(".mu-image")].map((el, index) => {
        el.setAttribute("data-mu-image-index", String(index));
        return { index, ...readImage(el) };
    });
}

function isAllowedImageDataUrl(url) {
    if (typeof url !== "string" || !url) {
        return false;
    }
    // Only allow base64 data URLs for image types the browser can render.
    // TIFF is fetched but not renderable, so it stays outside the allowlist.
    return /^data:image\/(webp|png|jpeg|jpg|gif|bmp|svg\+xml);base64,/i.test(url);
}

function sanitizeImageErrorReason(reason) {
    return [...String(reason ?? "")]
        .filter((ch) => {
            const code = ch.charCodeAt(0);
            return code >= 32 && code !== 127;
        })
        .slice(0, 120)
        .join("");
}

function escapeSource(content) {
    return String(content ?? "")
        .replace(/&/g, "&amp;")
        .replace(/</g, "&lt;")
        .replace(/>/g, "&gt;")
        .replace(/"/g, "&quot;")
        .replace(/'/g, "&#039;");
}

function scrollToFragmentId(rawId, block = "nearest") {
    // Field/request variables ride along after a backtick on micron links.
    let id = String(rawId).split("`")[0];
    try {
        id = decodeURIComponent(id);
    } catch {
        return;
    }
    if (!id) {
        return;
    }
    let el = null;
    try {
        el = root.querySelector(`#${CSS.escape(id)}`);
    } catch {
        // Hostile ids can still fail selector parsing; getElementById covers them.
    }
    if (!el) {
        el = document.getElementById(id);
    }
    if (el) {
        el.scrollIntoView({ behavior: "smooth", block });
    }
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
        // Micron marks every link openNode, including same-page anchors like
        // `[Arts`#arts]. A "#" destination is never a node URL, so scroll to
        // the target inside this frame instead of navigating.
        const dest = (node.getAttribute("data-destination") || "").trim();
        if (dest.charAt(0) === "#") {
            scrollToFragmentId(dest.slice(1), "start");
            return;
        }
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
    const imageAction = t.closest(".mu-image-action");
    if (imageAction) {
        event.preventDefault();
        event.stopPropagation();
        const container = imageAction.closest(".mu-image");
        if (container) {
            const info = readImage(container);
            const index = container.getAttribute("data-mu-image-index");
            const action = imageAction.getAttribute("data-mu-image-action") || "load";
            post({
                type: "image-action",
                action,
                index: index != null ? Number(index) : null,
                ...info,
                // "view" opens the already-loaded bitmap; only then is the
                // data URL worth shipping to the parent.
                ...(action === "view"
                    ? { dataUrl: container.querySelector(".mu-image-output")?.getAttribute("src") || "" }
                    : {}),
            });
        }
        return;
    }
    const frag = t.closest("a[href]");
    if (frag) {
        const fh = (frag.getAttribute("href") || "").trim();
        if (fh.charAt(0) === "#" && fh.length > 1 && !frag.getAttribute("data-nomadnet-url")) {
            event.preventDefault();
            event.stopPropagation();
            scrollToFragmentId(fh.slice(1));
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
    root.setAttribute("role", "document");
    root.setAttribute("tabindex", "0");
    paintShell(msg.background || "#000000", msg.color || "#dddddd");
}

async function renderPage(msg, seq, api) {
    teardownMultiline();
    applyChrome(msg);
    const path = msg.path || "";
    const content = msg.content ?? "";
    const renderOptions = msg.renderOptions && typeof msg.renderOptions === "object" ? msg.renderOptions : {};
    document.title = path || "Nomad";
    document.documentElement.lang = renderOptions.locale || "en";
    if (msg.showSource) {
        root.innerHTML = escapeSource(content);
        if (seq === renderSeq) {
            post({ type: "render-done", partials: [] });
            requestAnimationFrame(applyDisplayMode);
        }
        return;
    }
    const [pagePathWithoutData] = String(path).split("`");
    const pagePartials = msg.pagePartials && typeof msg.pagePartials === "object" ? msg.pagePartials : {};
    if (renderOptions.nomad_micron_wasm_use === true) {
        await api.preloadNomadMicronWasm();
    }
    if (seq !== renderSeq) {
        return;
    }
    const opts = { ...renderOptions };
    let html;
    try {
        html = api.renderNomadPageByPath(pagePathWithoutData, content, pagePartials, api.MicronParser, opts);
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
    const pageShell = root.querySelector(".mu-page");
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
    post({ type: "render-done", partials: listPartials(), images: listImages() });
    // Content size is final here. Rescale before the next paint if needed.
    requestAnimationFrame(applyDisplayMode);
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
    if (d.type === "extract-text") {
        let text;
        try {
            text = root.innerText || "";
        } catch {
            text = root.textContent || "";
        }
        post({ type: "page-text", id: d.id, text });
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
    if (d.type === "display-mode") {
        const mode = ["fit", "scroll", "off"].includes(d.mode) ? d.mode : "fit";
        displayMode = mode;
        applyDisplayMode();
        return;
    }
    if (d.type === "paste-text") {
        applyPastedText(d.text);
        return;
    }
    if (d.type === "set-partial") {
        const id = d.id || "";
        if (!id) {
            return;
        }
        let target;
        try {
            target = root.querySelector(`[data-partial-id="${CSS.escape(id)}"]`);
        } catch {
            target = null;
        }
        if (target) {
            target.innerHTML = d.html || "";
            // Partials can introduce new .mu-image placeholders after
            // render-done already listed the page's images. Keep existing
            // indexes stable, assign fresh ones past the current max, and
            // tell the parent so load/view actions correlate. Images removed
            // by the overwrite leave stale parent entries that are simply
            // unreachable.
            const allImages = [...root.querySelectorAll(".mu-image")];
            let nextIndex = 0;
            for (const el of allImages) {
                const existing = Number(el.getAttribute("data-mu-image-index"));
                if (Number.isInteger(existing)) {
                    nextIndex = Math.max(nextIndex, existing + 1);
                }
            }
            const added = [];
            for (const el of allImages) {
                if (el.getAttribute("data-mu-image-index") == null) {
                    el.setAttribute("data-mu-image-index", String(nextIndex));
                    added.push({ index: nextIndex, ...readImage(el) });
                    nextIndex += 1;
                }
            }
            if (added.length > 0) {
                post({ type: "images-added", images: added });
            }
        }
        return;
    }
    if (d.type === "set-image") {
        const index = d.index;
        if (index == null) {
            return;
        }
        let el;
        try {
            el = root.querySelector(`.mu-image[data-mu-image-index="${CSS.escape(String(index))}"]`);
        } catch {
            el = null;
        }
        if (!el) {
            return;
        }
        const img = el.querySelector(".mu-image-output");
        const load = el.querySelector('.mu-image-action[data-mu-image-action="load"]');
        if (d.state === "loading") {
            if (load) {
                const progress = d.progress != null ? `${Math.round(Number(d.progress) * 100)}%` : "";
                load.textContent = progress ? `Loading... ${progress}` : "Loading...";
            }
        } else if (d.state === "loaded") {
            const dataUrl = d.dataUrl || "";
            const allowed = isAllowedImageDataUrl(dataUrl);
            if (img && allowed) {
                img.src = dataUrl;
                img.removeAttribute("hidden");
                // Move the micron size spec from the placeholder box onto the
                // image itself. A percentage width resolves against the page,
                // so it stays on the block container and the img fills it.
                // Other specs (ch columns, lh/vh height) size the img directly
                // so it honors the spec even when the natural size differs.
                const wSpec = el.getAttribute("data-mu-image-w");
                const hSpec = el.getAttribute("data-mu-image-h");
                if (wSpec && wSpec !== "auto" && wSpec.endsWith("%")) {
                    img.style.width = "100%";
                } else {
                    el.style.width = "fit-content";
                    if (wSpec && wSpec !== "auto") {
                        img.style.width = wSpec;
                    }
                }
                if (hSpec && hSpec !== "auto") {
                    img.style.height = hSpec;
                }
                // Release the reserved placeholder space so loaded pages do not
                // keep dead space below the image.
                el.style.minHeight = "";
                el.classList.add("mu-image-loaded");
            }
            if (load) {
                load.textContent = allowed ? "Loaded" : "Error: unsupported image type";
                if (allowed) {
                    load.setAttribute("data-mu-image-action", "view");
                }
            }
            const size = el.querySelector(".mu-image-size");
            if (size && d.actualSize != null) {
                size.textContent = d.actualSize;
            }
        } else if (d.state === "error") {
            if (load) {
                const reason = sanitizeImageErrorReason(d.reason);
                load.textContent = reason ? `Error: ${reason}` : "Error";
            }
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

function onImageKeyDown(event) {
    if (event.key !== "Enter" && event.key !== " ") {
        return;
    }
    const imageAction = event.target && event.target.closest ? event.target.closest(".mu-image-action") : null;
    if (!imageAction) {
        return;
    }
    event.preventDefault();
    event.stopPropagation();
    const container = imageAction.closest(".mu-image");
    if (container) {
        const info = readImage(container);
        const index = container.getAttribute("data-mu-image-index");
        const action = imageAction.getAttribute("data-mu-image-action") || "load";
        post({
            type: "image-action",
            action,
            index: index != null ? Number(index) : null,
            ...info,
            ...(action === "view"
                ? { dataUrl: container.querySelector(".mu-image-output")?.getAttribute("src") || "" }
                : {}),
        });
    }
}

/**
 * Android WebView cannot raise the insertion/paste ActionMode for fields
 * inside an iframe, so micron inputs on nomad pages get no long-press Paste.
 * When running in the Android shell, intercept contextmenu on text fields and
 * ask the parent to show an app-level Paste menu instead. Desktop browsers
 * keep the native context menu untouched.
 */
let pendingFieldPasteEl = null;

const NON_TEXT_INPUT_TYPES = new Set([
    "button",
    "checkbox",
    "file",
    "hidden",
    "image",
    "radio",
    "range",
    "reset",
    "submit",
]);

function isAndroidWebViewShell() {
    try {
        const bridge = window.MeshChatXAndroid;
        if (bridge && typeof bridge.getPlatform === "function" && bridge.getPlatform() === "android") {
            return true;
        }
    } catch {
        // Bridge object may be inaccessible. Fall through to UA detection.
    }
    try {
        const ua = navigator.userAgent || "";
        return /Android/i.test(ua) && /;\s*wv\)/.test(ua);
    } catch {
        return false;
    }
}

function fieldFromContextTarget(target) {
    const el = target && target.closest ? target.closest("input, textarea") : null;
    if (!el || el.disabled || el.readOnly) {
        return null;
    }
    if (el.tagName === "INPUT" && NON_TEXT_INPUT_TYPES.has((el.getAttribute("type") || "text").toLowerCase())) {
        return null;
    }
    return el;
}

function onFieldContextMenu(event) {
    pendingFieldPasteEl = null;
    if (!isAndroidWebViewShell()) {
        return;
    }
    const el = fieldFromContextTarget(event.target);
    if (!el) {
        // Non-field targets: a touch long-press must keep the native
        // selection/copy menu; caret hit-testing is unreliable in this frame.
        if (!shouldOpenCustomContextMenu(event, { touchPrefersNative: true })) {
            return;
        }
    }
    event.preventDefault();
    event.stopPropagation();
    if (el) {
        pendingFieldPasteEl = el;
        post({ type: "field-contextmenu", x: event.clientX, y: event.clientY });
        return;
    }
    post({ type: "page-contextmenu", x: event.clientX, y: event.clientY });
}

function applyPastedText(text) {
    const el = pendingFieldPasteEl;
    pendingFieldPasteEl = null;
    if (!el || !root.contains(el)) {
        return;
    }
    const value = String(text ?? "");
    try {
        el.focus();
    } catch {
        // Field may have been removed between the long-press and the tap.
    }
    let start = el.value.length;
    let end = start;
    try {
        // Input types without selection support (number, date, ...) throw
        // InvalidStateError when selectionStart is read.
        if (typeof el.selectionStart === "number") {
            start = el.selectionStart;
        }
        if (typeof el.selectionEnd === "number") {
            end = el.selectionEnd;
        }
    } catch {
        // keep defaults
    }
    if (typeof el.setRangeText === "function") {
        el.setRangeText(value, start, end, "end");
    } else {
        el.value = el.value.slice(0, start) + value + el.value.slice(end);
    }
    el.dispatchEvent(new Event("input", { bubbles: true }));
    el.dispatchEvent(new Event("change", { bubbles: true }));
}

root.addEventListener("click", onClick, true);
root.addEventListener("auxclick", onClick, true);
root.addEventListener("keydown", onImageKeyDown, true);
root.addEventListener("contextmenu", onFieldContextMenu, true);
window.addEventListener("keydown", (event) => {
    const action = desktopZoomKeyAction(event);
    if (action) {
        post({ type: DESKTOP_ZOOM_MESSAGE_TYPE, action });
    }
});
window.addEventListener("wheel", (event) => {
    const action = desktopZoomWheelAction(event);
    if (action) {
        post({ type: DESKTOP_ZOOM_MESSAGE_TYPE, action });
    }
});
paintShell("#000000", "#dddddd");
// Warm the parser chunk while the shell downloads the page.
void loadRenderer();
post({ type: "ready" });
