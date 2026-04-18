import "fake-indexeddb/auto";
import { injectMeshchatThemeVariables } from "../../meshchatx/src/frontend/theme/designTokens.js";

injectMeshchatThemeVariables(typeof document !== "undefined" ? document : undefined);

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

import { readFileSync, existsSync } from "fs";
import { join } from "path";
import { vi } from "vitest";
import { config } from "@vue/test-utils";
import createDOMPurify from "dompurify";

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

// Stub all Vuetify components to avoid warnings and CSS issues
config.global.stubs = {
    MaterialDesignIcon: { template: '<div class="mdi-stub"><slot /></div>' },
    RouterLink: { template: "<a><slot /></a>" },
    RouterView: { template: "<div><slot /></div>" },
    // Common Vuetify components
    "v-app": true,
    "v-main": true,
    "v-container": true,
    "v-row": true,
    "v-col": true,
    "v-btn": true,
    "v-icon": true,
    "v-card": true,
    "v-card-title": true,
    "v-card-text": true,
    "v-card-actions": true,
    "v-dialog": true,
    "v-text-field": true,
    "v-textarea": true,
    "v-select": true,
    "v-switch": true,
    "v-checkbox": true,
    "v-list": true,
    "v-list-item": true,
    "v-list-item-title": true,
    "v-list-item-subtitle": true,
    "v-menu": true,
    "v-divider": true,
    "v-spacer": true,
    "v-progress-circular": true,
    "v-progress-linear": true,
    "v-tabs": true,
    "v-tab": true,
    "v-window": true,
    "v-window-item": true,
    "v-expansion-panels": true,
    "v-expansion-panel": true,
    "v-expansion-panel-title": true,
    "v-expansion-panel-text": true,
    "v-chip": true,
    "v-toolbar": true,
    "v-toolbar-title": true,
    "v-tooltip": true,
    "v-alert": true,
    "v-snackbar": true,
    "v-badge": true,
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
