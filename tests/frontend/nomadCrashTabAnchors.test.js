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
 * Micron marks every link data-action="openNode", including same-page anchors
 * like `[Arts`#arts]. The frame must scroll those to the in-page target
 * instead of posting a navigation the parent cannot resolve
 * ("unsupported url: #arts").
 */

let postSpy;
let scrollSpy;

function navigatePosts() {
    return postSpy.mock.calls.filter(([msg]) => msg && msg.type === "navigate");
}

beforeAll(async () => {
    Element.prototype.scrollIntoView = vi.fn();
    // The module caches the #root element at import time.
    document.body.innerHTML = '<div id="root"></div>';
    document.getElementById("root").innerHTML = `
        <div class="nodeContainer">
            <a id="arts"></a>
            <a href="#arts" class="Mu-nl" data-action="openNode" data-destination="#arts">Arts</a>
            <a href="#arts" class="Mu-nl" data-action="openNode" data-destination="#arts\`key=val">Arts with vars</a>
            <a href="#arts">Plain href link</a>
            <a class="Mu-nl" data-action="openNode" data-destination="deadbeef:/page/other.mu">Other node</a>
        </div>`;
    await import("../../meshchatx/src/frontend/js/nomadCrashTabMain.js");
    scrollSpy = Element.prototype.scrollIntoView;
});

beforeEach(() => {
    scrollSpy.mockClear();
    postSpy = vi.spyOn(window, "postMessage").mockImplementation(() => {});
});

describe("nomad crash-tab in-page anchor links", () => {
    it("scrolls to the anchor instead of posting an openNode navigation", () => {
        const link = document.querySelector('a[data-destination="#arts"]');
        link.dispatchEvent(new MouseEvent("click", { bubbles: true }));

        expect(document.getElementById("arts").scrollIntoView).toHaveBeenCalledOnce();
        expect(navigatePosts()).toHaveLength(0);
    });

    it("strips request variables after the backtick before scrolling", () => {
        const link = document.querySelector('a[data-destination="#arts`key=val"]');
        link.dispatchEvent(new MouseEvent("click", { bubbles: true }));

        expect(document.getElementById("arts").scrollIntoView).toHaveBeenCalledOnce();
        expect(navigatePosts()).toHaveLength(0);
    });

    it("keeps scrolling plain a[href] fragment links", () => {
        const link = document.querySelector('a[href="#arts"]:not([data-action])');
        link.dispatchEvent(new MouseEvent("click", { bubbles: true }));

        expect(document.getElementById("arts").scrollIntoView).toHaveBeenCalledOnce();
        expect(navigatePosts()).toHaveLength(0);
    });

    it("still posts openNode navigation for node destinations", () => {
        const link = document.querySelector('a[data-destination="deadbeef:/page/other.mu"]');
        link.dispatchEvent(new MouseEvent("click", { bubbles: true }));

        expect(scrollSpy).not.toHaveBeenCalled();
        const posts = navigatePosts();
        expect(posts).toHaveLength(1);
        expect(posts[0][0]).toMatchObject({
            type: "navigate",
            kind: "openNode",
            url: "deadbeef:/page/other.mu",
        });
    });
});
