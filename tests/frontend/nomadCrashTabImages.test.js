// SPDX-License-Identifier: 0BSD
import { beforeAll, beforeEach, describe, expect, it, vi } from "vitest";

// The crash-tab script warms the real parser chunk at boot. Stub the dynamic
// imports so the warmup resolves before the jsdom environment tears down.
vi.mock("../../meshchatx/src/frontend/js/MicronParser.js", () => ({ default: {} }));
vi.mock("../../meshchatx/src/frontend/js/NomadPageRenderer.js", () => ({
    renderNomadPageByPath: vi.fn(),
    resolveNomadPageShellBackground: vi.fn(),
}));
vi.mock("../../meshchatx/src/frontend/js/MicronWasmLoader.js", () => ({
    preloadNomadMicronWasm: vi.fn(),
}));
vi.mock("dompurify", () => ({ default: {} }));
vi.mock("../../meshchatx/src/frontend/fonts/RobotoMonoNerdFont/font.css", () => ({}));

/**
 * Exercises the crash-tab renderer script's set-image handling in jsdom:
 * after an image loads, the micron size spec moves onto the <img>, the
 * reserved placeholder space is released, and the placeholder chrome drops.
 */

const CHANNEL = "nomad-crash-tab";
const WEBP = "data:image/webp;base64,UklGRiIAAABXRUJQVlA4IBYAAAAwAQCdASoBAAEADsD+JaQAA3AAAAAA";

function mountImage(attrs = {}, style = "") {
    // The module caches the #root element at import time, so swap its
    // innerHTML instead of replacing the element itself.
    document.getElementById("root").innerHTML = `<div class="nodeContainer"><div
        class="mu-image"
        data-mu-image-index="0"
        data-mu-image-alt="alt"
        ${Object.entries(attrs)
            .map(([k, v]) => `${k}="${v}"`)
            .join(" ")}
        style="${style}"
    >
        <span class="mu-image-meta"><span class="mu-image-alt">alt</span></span>
        <span class="mu-image-actions"><a class="mu-image-action" data-mu-image-action="load" role="button">Load image</a></span>
        <img class="mu-image-output" alt="alt" hidden />
    </div></div>`;
    return document.querySelector(".mu-image");
}

function sendSetImage(payload) {
    window.dispatchEvent(
        new MessageEvent("message", {
            data: { channel: CHANNEL, type: "set-image", index: 0, ...payload },
            source: window,
        })
    );
}

function sendFrameMessage(payload) {
    window.dispatchEvent(
        new MessageEvent("message", {
            data: { channel: CHANNEL, ...payload },
            source: window,
        })
    );
}

let postSpy;

beforeEach(() => {
    postSpy = vi.spyOn(window, "postMessage").mockImplementation(() => {});
    postSpy.mockClear();
});

function postedMessages(type) {
    return postSpy.mock.calls.map(([msg]) => msg).filter((msg) => msg && msg.type === type);
}

beforeAll(async () => {
    document.body.innerHTML = '<div id="root"></div>';
    await import("../../meshchatx/src/frontend/js/nomadCrashTabMain.js");
});

describe("nomad crash-tab set-image", () => {
    it("applies a column width spec to the loaded image and releases the placeholder box", () => {
        const el = mountImage(
            { "data-mu-image-w": "50ch", "data-mu-image-h": "20lh" },
            "width: 50ch; min-height: 20lh;"
        );
        sendSetImage({ state: "loaded", dataUrl: WEBP });

        const img = el.querySelector(".mu-image-output");
        expect(img.getAttribute("hidden")).toBeNull();
        expect(img.src).toBe(WEBP);
        expect(img.style.width).toBe("50ch");
        expect(img.style.height).toBe("20lh");
        // The container no longer reserves the spec box, so no dead space
        // remains below the rendered image.
        expect(el.style.width).toBe("fit-content");
        expect(el.style.minHeight).toBe("");
        expect(el.classList.contains("mu-image-loaded")).toBe(true);
    });

    it("keeps a percentage width on the container so it resolves against the page", () => {
        const el = mountImage({ "data-mu-image-w": "50%" }, "width: 50%;");
        sendSetImage({ state: "loaded", dataUrl: WEBP });

        const img = el.querySelector(".mu-image-output");
        expect(el.style.width).toBe("50%");
        expect(img.style.width).toBe("100%");
        expect(el.classList.contains("mu-image-loaded")).toBe(true);
    });

    it("leaves native-size images unsized and shrink-wraps the container", () => {
        const el = mountImage({ "data-mu-image-w": "auto" }, "width: auto;");
        sendSetImage({ state: "loaded", dataUrl: WEBP });

        const img = el.querySelector(".mu-image-output");
        expect(img.style.width).toBe("");
        expect(img.style.height).toBe("");
        expect(el.style.width).toBe("fit-content");
        expect(el.classList.contains("mu-image-loaded")).toBe(true);
    });

    it("keeps the placeholder chrome when the image errors", () => {
        const el = mountImage({ "data-mu-image-w": "50ch" }, "width: 50ch; min-height: 10lh;");
        sendSetImage({ state: "error", reason: "denied" });

        const img = el.querySelector(".mu-image-output");
        expect(img.getAttribute("hidden")).not.toBeNull();
        expect(el.classList.contains("mu-image-loaded")).toBe(false);
        expect(el.style.minHeight).toBe("10lh");
        const action = el.querySelector(".mu-image-action");
        expect(action.textContent).toContain("Error");
    });
});

describe("nomad crash-tab set-partial images", () => {
    it("indexes images injected after render-done and reports them to the parent", () => {
        mountImage({}, "");
        const target = document.createElement("div");
        target.setAttribute("data-partial-id", "p1");
        document.getElementById("root").appendChild(target);

        sendFrameMessage({
            type: "set-partial",
            id: "p1",
            html: '<div class="mu-image" data-mu-image-url="/img/a.png"><img class="mu-image-output" hidden></div>',
        });

        const added = target.querySelector(".mu-image");
        expect(added.getAttribute("data-mu-image-index")).toBe("1");
        const posts = postedMessages("images-added");
        expect(posts).toHaveLength(1);
        expect(posts[0].images[0]).toMatchObject({ index: 1, url: "/img/a.png" });
    });

    it("does not renumber images that already have indexes", () => {
        mountImage({}, "");
        const target = document.createElement("div");
        target.setAttribute("data-partial-id", "p1");
        document.getElementById("root").appendChild(target);

        sendFrameMessage({
            type: "set-partial",
            id: "p1",
            html: '<div class="mu-image" data-mu-image-index="7" data-mu-image-url="/img/b.png"></div>',
        });

        const kept = target.querySelector(".mu-image");
        expect(kept.getAttribute("data-mu-image-index")).toBe("7");
        expect(postedMessages("images-added")).toHaveLength(0);
    });
});

describe("nomad crash-tab image view action", () => {
    it("ships the loaded data URL when the action becomes view", () => {
        const el = mountImage({}, "");
        sendSetImage({ state: "loaded", dataUrl: WEBP });

        const action = el.querySelector(".mu-image-action");
        expect(action.getAttribute("data-mu-image-action")).toBe("view");
        action.dispatchEvent(new MouseEvent("click", { bubbles: true }));

        const posts = postedMessages("image-action");
        expect(posts).toHaveLength(1);
        expect(posts[0]).toMatchObject({ action: "view", dataUrl: WEBP, index: 0 });
    });

    it("does not ship a data URL for load actions", () => {
        const el = mountImage({}, "");
        const action = el.querySelector(".mu-image-action");
        action.dispatchEvent(new MouseEvent("click", { bubbles: true }));

        const posts = postedMessages("image-action");
        expect(posts).toHaveLength(1);
        expect(posts[0].action).toBe("load");
        expect(posts[0].dataUrl).toBeUndefined();
    });
});
