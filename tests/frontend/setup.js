import "fake-indexeddb/auto";
import { readFileSync, existsSync } from "fs";
import { join } from "path";
import { beforeEach, vi } from "vitest";
import { config } from "@vue/test-utils";
import createDOMPurify from "dompurify";
import { injectMeshchatThemeVariables } from "../../meshchatx/src/frontend/theme/designTokens.js";
import GlobalState from "../../meshchatx/src/frontend/js/GlobalState.js";
import en from "../../meshchatx/src/frontend/locales/en.json";
import { registerFallbackMessages } from "../../meshchatx/src/frontend/js/i18n.ts";

injectMeshchatThemeVariables(typeof document !== "undefined" ? document : undefined);
registerFallbackMessages(en);

// App shell tests assume auth is settled with auth disabled unless a case overrides.
beforeEach(() => {
    GlobalState.authSessionResolved = true;
    GlobalState.authEnabled = false;
    GlobalState.authenticated = false;
    GlobalState.demoMode = false;
});

if (typeof window !== "undefined" && typeof window.PointerEvent === "undefined") {
    window.PointerEvent = class PointerEvent extends MouseEvent {
        constructor(type, params = {}) {
            super(type, { bubbles: true, cancelable: true, composed: true, ...params });
            this.pointerType = params.pointerType || "mouse";
            Object.defineProperty(this, "clientX", { value: params.clientX || 0, configurable: true });
            Object.defineProperty(this, "clientY", { value: params.clientY || 0, configurable: true });
            Object.defineProperty(this, "button", { value: params.button || 0, configurable: true });
        }
    };
    global.PointerEvent = window.PointerEvent;
}

if (typeof Element !== "undefined" && !Element.prototype.animate) {
    Element.prototype.animate = function () {
        const anim = {
            finished: Promise.resolve(),
            cancel: () => {},
            onfinish: null,
            play: () => {},
            pause: () => {},
            reverse: () => {},
            finish: () => {},
        };
        if (typeof setTimeout !== "undefined") {
            setTimeout(() => {
                if (typeof anim.onfinish === "function") {
                    anim.onfinish();
                }
            }, 0);
        }
        return anim;
    };
}

if (typeof Blob !== "undefined" && typeof Blob.prototype.stream !== "function") {
    Blob.prototype.stream = function streamPolyfill() {
        const blob = this;
        return new ReadableStream({
            async start(controller) {
                const u8 = new Uint8Array(await blob.arrayBuffer());
                controller.enqueue(u8);
                controller.close();
            },
        });
    };
}

const EMOJI_PICKER_DATA_PATH = join(
    process.cwd(),
    "node_modules",
    "emoji-picker-element-data",
    "en",
    "emojibase",
    "data.json"
);

const origFetch = globalThis.fetch;
globalThis.fetch = async (input, init) => {
    const reqUrl = typeof input === "string" ? input : (input?.url ?? "");
    if (
        reqUrl.includes("emoji-picker-element-data") &&
        reqUrl.includes("data.json") &&
        existsSync(EMOJI_PICKER_DATA_PATH)
    ) {
        const data = readFileSync(EMOJI_PICKER_DATA_PATH, "utf8");
        return new Response(data, { status: 200, headers: { "Content-Type": "application/json" } });
    }
    if (typeof origFetch === "function") {
        return origFetch(input, init);
    }
    throw new Error(`fetch not available for ${reqUrl}`);
};

// Initialize DOMPurify with the jsdom window
let DOMPurify;
try {
    if (typeof createDOMPurify === "function") {
        DOMPurify = createDOMPurify(window);
    } else if (createDOMPurify && typeof createDOMPurify.default === "function") {
        DOMPurify = createDOMPurify.default(window);
    } else {
        DOMPurify = createDOMPurify;
    }
} catch (e) {
    console.error("Failed to initialize DOMPurify:", e);
}

// Global mocks
if (DOMPurify) {
    global.DOMPurify = DOMPurify;
    window.DOMPurify = DOMPurify;
}
global.performance.mark = vi.fn();
global.performance.measure = vi.fn();
global.performance.getEntriesByName = vi.fn(() => []);
global.performance.clearMarks = vi.fn();
global.performance.clearMeasures = vi.fn();

// Mock window.api by default to prevent TypeErrors
global.api = {
    get: vi.fn().mockResolvedValue({ data: {} }),
    post: vi.fn().mockResolvedValue({ data: {} }),
    put: vi.fn().mockResolvedValue({ data: {} }),
    patch: vi.fn().mockResolvedValue({ data: {} }),
    delete: vi.fn().mockResolvedValue({ data: {} }),
    isCancel: vi.fn().mockReturnValue(false),
};
window.api = global.api;

config.global.stubs = {
    MaterialDesignIcon: { template: '<div class="mdi-stub"><slot /></div>' },
    RouterLink: { template: "<a><slot /></a>" },
    RouterView: { template: "<div><slot /></div>" },
    AppModal: {
        template: '<div class="app-modal-stub"><slot /><slot name="header" /><slot name="actions" /></div>',
        props: ["modelValue"],
    },
    ClickPopover: {
        template: '<div class="click-popover-stub"><slot name="activator" /><slot /></div>',
    },
};

// Mock window.matchMedia
Object.defineProperty(window, "matchMedia", {
    writable: true,
    value: vi.fn().mockImplementation((query) => ({
        matches: false,
        media: query,
        onchange: null,
        addListener: vi.fn(), // deprecated
        removeListener: vi.fn(), // deprecated
        addEventListener: vi.fn(),
        removeEventListener: vi.fn(),
        dispatchEvent: vi.fn(),
    })),
});
