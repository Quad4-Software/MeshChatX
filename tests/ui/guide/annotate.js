/**
 * In-page annotation overlay for docs/guide screenshots.
 *
 * applyGuideAnnotations(page, annotations) injects a single overlay layer
 * (#mcx-guide-layer) containing positioned guide elements:
 *
 *   { selector, kind: "box",       note?, badge?, notePos? } accent ring + optional note card
 *   { selector, kind: "spotlight", note?, badge? }           dim everything except the target
 *   { selector, kind: "blur" }                               backdrop blur for privacy redaction
 *   { selector, kind: "arrow", from, note? }                 arrow into target (from: top|bottom|left|right)
 *   { kind: "caption", text, sub?, pos: "top"|"bottom" }     floating caption strip
 *
 * selector values are full playwright selectors ("text=Foo", "#id", css,
 * "role=tab[name=..]"); geometry is resolved via locator.boundingBox() so the
 * page never sees selector syntax. Colors follow the active theme via CSS
 * vars so guides match the theme they are captured in. pointer-events:none.
 */

const LAYER_ID = "mcx-guide-layer";

const OVERLAY_CSS = `
#${LAYER_ID} {
    position: fixed; inset: 0; z-index: 99999; pointer-events: none;
    --guide-accent: var(--mc-accent, #2563eb);
    --guide-accent-text: var(--mc-action-primary-text, #ffffff);
    --guide-surface: var(--mc-surface, #ffffff);
    --guide-text: var(--mc-text, #111111);
    --guide-dim: rgb(0 0 0 / 0.55);
    font-family: inherit;
}
#${LAYER_ID} .guide-box {
    position: fixed; border: 3px solid var(--guide-accent); border-radius: 10px;
    box-shadow: 0 0 0 4px rgb(255 255 255 / 0.18), 0 4px 24px rgb(0 0 0 / 0.35);
}
#${LAYER_ID} .guide-blur {
    position: fixed; backdrop-filter: blur(10px) saturate(0.6);
    border-radius: 8px;
}
#${LAYER_ID} .guide-dim { position: fixed; background: var(--guide-dim); }
#${LAYER_ID} .guide-badge {
    position: fixed; width: 26px; height: 26px; border-radius: 999px;
    background: var(--guide-accent); color: var(--guide-accent-text);
    display: flex; align-items: center; justify-content: center;
    font-size: 13px; font-weight: 700; box-shadow: 0 2px 10px rgb(0 0 0 / 0.4);
}
#${LAYER_ID} .guide-note {
    position: fixed; max-width: 280px; padding: 8px 12px; border-radius: 10px;
    background: var(--guide-surface); color: var(--guide-text);
    font-size: 13px; font-weight: 500; line-height: 1.4;
    border: 1px solid var(--mc-border, rgb(0 0 0 / 0.15));
    box-shadow: 0 4px 20px rgb(0 0 0 / 0.35);
}
#${LAYER_ID} .guide-caption {
    position: fixed; left: 50%; transform: translateX(-50%);
    padding: 10px 18px; border-radius: 12px;
    background: var(--guide-surface); color: var(--guide-text);
    font-size: 15px; font-weight: 600; text-align: center; max-width: 70%;
    border: 1px solid var(--mc-border, rgb(0 0 0 / 0.15));
    box-shadow: 0 6px 28px rgb(0 0 0 / 0.4);
}
#${LAYER_ID} .guide-caption small {
    display: block; font-size: 12px; font-weight: 400; opacity: 0.75; margin-top: 2px;
}
#${LAYER_ID} .guide-arrow-line {
    position: fixed; height: 3px; background: var(--guide-accent);
    transform-origin: left center; box-shadow: 0 1px 6px rgb(0 0 0 / 0.4);
}
#${LAYER_ID} .guide-arrow-head {
    position: fixed; width: 0; height: 0;
    border-left: 9px solid transparent; border-right: 9px solid transparent;
    border-bottom: 14px solid var(--guide-accent);
    filter: drop-shadow(0 2px 4px rgb(0 0 0 / 0.4));
}
`;

const PAD = 6;

// injected fn receives annotation objects with rect already resolved
const INJECT_FN = `
(annotations) => {
    const LAYER_ID = ${JSON.stringify(LAYER_ID)};
    document.getElementById(LAYER_ID)?.remove();
    const layer = document.createElement("div");
    layer.id = LAYER_ID;
    document.body.appendChild(layer);
    const pad = ${PAD};
    const vh = window.innerHeight, vw = window.innerWidth;
    const add = (cls, style) => {
        const el = document.createElement("div");
        el.className = cls;
        Object.assign(el.style, style);
        layer.appendChild(el);
        return el;
    };
    for (const a of annotations) {
        const rect = a.rect || null;
        if ((a.kind === "box" || a.kind === "spotlight") && rect) {
            const bx = rect.x - pad, by = rect.y - pad, bw = rect.w + pad * 2, bh = rect.h + pad * 2;
            if (a.kind === "spotlight") {
                add("guide-dim", { left: "0px", top: "0px", width: vw + "px", height: Math.max(0, by) + "px" });
                add("guide-dim", { left: "0px", top: by + bh + "px", width: vw + "px", height: Math.max(0, vh - by - bh) + "px" });
                add("guide-dim", { left: "0px", top: by + "px", width: Math.max(0, bx) + "px", height: bh + "px" });
                add("guide-dim", { left: bx + bw + "px", top: by + "px", width: Math.max(0, vw - bx - bw) + "px", height: bh + "px" });
            }
            add("guide-box", { left: bx + "px", top: by + "px", width: bw + "px", height: bh + "px" });
            if (a.badge !== undefined) {
                add("guide-badge", { left: bx - 10 + "px", top: by - 10 + "px" }).textContent = String(a.badge);
            }
            if (a.note) {
                const pos = a.notePos || "bottom";
                const style = {};
                if (pos === "bottom") { style.left = bx + "px"; style.top = by + bh + 12 + "px"; }
                else if (pos === "top") { style.left = bx + "px"; style.top = Math.max(8, by - 78) + "px"; }
                else if (pos === "right") { style.left = bx + bw + 12 + "px"; style.top = by + "px"; }
                else { style.left = Math.max(8, bx - 292) + "px"; style.top = by + "px"; }
                add("guide-note", style).textContent = a.note;
            }
        } else if (a.kind === "blur" && rect) {
            add("guide-blur", { left: rect.x + "px", top: rect.y + "px", width: rect.w + "px", height: rect.h + "px" });
        } else if (a.kind === "arrow" && rect) {
            const side = a.from || "bottom";
            const len = 46;
            const cx = rect.x + rect.w / 2, cy = rect.y + rect.h / 2;
            let x1, y1, x2, y2, rot;
            if (side === "bottom") { x2 = cx; y2 = rect.y + rect.h + pad; x1 = x2; y1 = y2 + len; rot = 0; }
            else if (side === "top") { x2 = cx; y2 = rect.y - pad; x1 = x2; y1 = y2 - len; rot = 180; }
            else if (side === "left") { x2 = rect.x - pad; y2 = cy; x1 = x2 - len; y1 = y2; rot = 90; }
            else { x2 = rect.x + rect.w + pad; y2 = cy; x1 = x2 + len; y1 = y2; rot = -90; }
            add("guide-arrow-line", {
                left: x1 + "px", top: y1 + "px",
                width: Math.hypot(x2 - x1, y2 - y1) + "px",
                transform: "rotate(" + (Math.atan2(y2 - y1, x2 - x1) * 180 / Math.PI) + "deg)",
            });
            add("guide-arrow-head", {
                left: x2 - 9 + "px", top: y2 - 7 + "px",
                transform: "rotate(" + rot + "deg) translateY(" + (rot === 0 ? -5 : 5) + "px)",
            });
        } else if (a.kind === "caption") {
            const cap = add("guide-caption", a.pos === "top" ? { top: "24px" } : { bottom: "24px" });
            cap.textContent = a.text || "";
            if (a.sub) {
                const s = document.createElement("small");
                s.textContent = a.sub;
                cap.appendChild(s);
            }
        }
    }
    return true;
}
`;

/**
 * Resolve playwright selectors to bounding boxes, then paint the overlay.
 * @param {import('@playwright/test').Page} page
 * @param {object[]} annotations
 * @returns {Promise<string[]>} selectors that resolved to no element
 */
async function applyGuideAnnotations(page, annotations) {
    const resolved = [];
    const missing = [];
    for (const a of annotations) {
        let rect = null;
        if (a.selector) {
            const loc = page.locator(a.selector).first();
            const box = await loc.boundingBox().catch(() => null);
            if (!box) {
                missing.push(a.selector);
                continue;
            }
            rect = { x: box.x, y: box.y, w: box.width, h: box.height };
        }
        resolved.push({ ...a, rect });
    }
    await page.addStyleTag({ content: OVERLAY_CSS });
    await page.evaluate(`(${INJECT_FN})(${JSON.stringify(resolved)})`);
    return missing;
}

async function clearGuideAnnotations(page) {
    await page.evaluate(`document.getElementById(${JSON.stringify(LAYER_ID)})?.remove()`);
}

module.exports = { applyGuideAnnotations, clearGuideAnnotations, LAYER_ID };
