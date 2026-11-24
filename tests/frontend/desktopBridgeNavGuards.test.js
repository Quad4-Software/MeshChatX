import { describe, it, expect } from "vitest";
import { readFileSync } from "node:fs";
import { resolve } from "node:path";
import vm from "node:vm";

const bridgeSrc = readFileSync(resolve(__dirname, "../../desktop/shell/desktop-bridge.js"), "utf8");

const STUBS = ["HTMLAnchorElement","HTMLInputElement","HTMLElement","HTMLButtonElement","Node","Element","Event","CustomEvent","KeyboardEvent","MouseEvent","FocusEvent","InputEvent","DragEvent","ClipboardEvent","FileReader","Image","Option","DocumentFragment","MutationObserver","ResizeObserver","IntersectionObserver","XMLHttpRequest","Headers","Request","Response","FormData","URLSearchParams","DOMParser","XMLSerializer","CSS","matchMedia","getComputedStyle","requestAnimationFrame","cancelAnimationFrame","queueMicrotask","structuredClone","performance","screen","history","location","alert","confirm","prompt","open","close","focus","blur","print","postMessage","addEventListener","removeEventListener","dispatchEvent","btoa","atob"];

function loadBridge({ href = "http://127.0.0.1:9338/", metas = [] } = {}) {
    const posted = [];
    const listeners = {};
    const metaNodes = metas.map((m) => ({
        tagName: "META",
        nodeType: 1,
        removed: false,
        getAttribute: (n) => (n === "content" ? m.content : n === "http-equiv" ? "refresh" : null),
        remove() {
            this.removed = true;
        },
    }));
    const document = {
        documentElement: { outerHTML: "" },
        addEventListener: (type, fn) => {
            (listeners[type] = listeners[type] || []).push(fn);
        },
        removeEventListener: () => {},
        querySelectorAll: (sel) => (sel.indexOf('meta[http-equiv="refresh"') >= 0 ? metaNodes : []),
        createElement: () => ({ style: {}, setAttribute: () => {}, focus: () => {}, select: () => {} }),
        body: { appendChild: () => {}, removeChild: () => {} },
    };
    const sandbox = {
        window: {},
        document,
        navigator: {},
        console,
        setTimeout,
        clearTimeout,
        Promise,
        JSON,
        Object,
        Array,
        String,
        Error,
        URL,
        Blob: class {},
    };
    sandbox.window.location = { href, protocol: "http:", hostname: "127.0.0.1", port: "9338" };
    sandbox.window.top = sandbox.window;
    sandbox.window.webkit = { messageHandlers: { external: { postMessage: (m) => posted.push(m) } } };
    sandbox.window.chrome = undefined;
    sandbox.window.addEventListener = () => {};
    sandbox.window.removeEventListener = () => {};
    sandbox.self = sandbox.window;
    sandbox.globalThis = sandbox;
    sandbox.atob = (s) => Buffer.from(s, "base64").toString("binary");
    sandbox.btoa = (s) => Buffer.from(s, "binary").toString("base64");
    sandbox.TextEncoder = TextEncoder;
    sandbox.TextDecoder = TextDecoder;
    sandbox.Uint8Array = Uint8Array;
    sandbox.ArrayBuffer = ArrayBuffer;
    sandbox.DataView = DataView;
    sandbox.crypto = { getRandomValues: (a) => require("node:crypto").randomFillSync(a) };
    for (const n of STUBS) {
        if (sandbox[n] === undefined) {
            if (n === "fetch") sandbox[n] = () => Promise.reject(new Error("no fetch"));
            else if (n === "matchMedia") sandbox[n] = () => ({ matches: false, addEventListener: () => {} });
            else if (n === "getComputedStyle") sandbox[n] = () => ({});
            else if (["requestAnimationFrame", "queueMicrotask"].includes(n)) sandbox[n] = (f) => setTimeout(f, 0);
            else if (["cancelAnimationFrame"].includes(n)) sandbox[n] = () => {};
            else if (["addEventListener", "removeEventListener", "dispatchEvent", "alert", "confirm", "prompt", "open", "close", "focus", "blur", "print", "postMessage"].includes(n)) sandbox[n] = () => {};
            else if (n === "performance") sandbox[n] = { now: () => Date.now() };
            else if (n === "screen") sandbox[n] = { width: 1920, height: 1080 };
            else if (n === "history" || n === "location") sandbox[n] = {};
            else sandbox[n] = class {};
        }
    }
    sandbox.window.document = sandbox.document;
    sandbox.window.navigator = sandbox.navigator;
    sandbox.window.self = sandbox.window;
    sandbox.window.top = sandbox.window.top;
    sandbox.window.parent = sandbox.window;
    sandbox.window.frames = sandbox.window;
    sandbox.window.innerWidth = 1920;
    sandbox.window.innerHeight = 1080;
    sandbox.window.devicePixelRatio = 1;
    sandbox.window.scrollTo = () => {};
    sandbox.window.scroll = () => {};
    sandbox.window.requestAnimationFrame = sandbox.requestAnimationFrame;
    sandbox.window.matchMedia = sandbox.matchMedia;
    sandbox.window.getComputedStyle = sandbox.getComputedStyle;
    sandbox.window.addEventListener = () => {};
    sandbox.window.removeEventListener = () => {};
    sandbox.window.dispatchEvent = () => {};
    sandbox.window.atob = sandbox.atob;
    sandbox.window.btoa = sandbox.btoa;
    sandbox.window.TextEncoder = TextEncoder;
    sandbox.window.TextDecoder = TextDecoder;
    sandbox.window.Uint8Array = Uint8Array;
    sandbox.window.ArrayBuffer = ArrayBuffer;
    sandbox.window.crypto = sandbox.crypto;
    sandbox.window.Blob = class {};
    sandbox.window.FileReader = class {};
    sandbox.window.URL = URL;
    sandbox.window.URLSearchParams = URLSearchParams;
    sandbox.window.setTimeout = setTimeout;
    sandbox.window.clearTimeout = clearTimeout;
    sandbox.window.Promise = Promise;
    sandbox.window.JSON = JSON;
    sandbox.window.Object = Object;
    sandbox.window.Array = Array;
    sandbox.window.String = String;
    sandbox.window.Number = Number;
    sandbox.window.Boolean = Boolean;
    sandbox.window.Error = Error;
    sandbox.window.Date = Date;
    sandbox.window.Math = Math;
    sandbox.window.RegExp = RegExp;
    sandbox.window.Map = Map;
    sandbox.window.Set = Set;
    sandbox.window.parseInt = parseInt;
    sandbox.window.parseFloat = parseFloat;
    sandbox.window.isNaN = isNaN;
    sandbox.window.isFinite = isFinite;
    sandbox.window.encodeURIComponent = encodeURIComponent;
    sandbox.window.decodeURIComponent = decodeURIComponent;
    sandbox.window.NaN = NaN;
    sandbox.window.Infinity = Infinity;
    sandbox.window.undefined = undefined;
    vm.createContext(sandbox);
    vm.runInContext(bridgeSrc, sandbox);
    return { sandbox, posted, listeners, metaNodes };
}

function parsedMessages(posted) {
    return posted
        .map((m) => {
            try {
                return JSON.parse(m);
            } catch {
                return null;
            }
        })
        .filter(Boolean);
}

function submitEvent(listeners, action) {
    const prevented = [];
    const evt = {
        target: { action },
        preventDefault: () => prevented.push(true),
        stopPropagation: () => {},
    };
    listeners.submit[0](evt);
    return prevented.length > 0;
}

describe("desktop bridge navigation guards", () => {
    it("reports page-url on __init", () => {
        const { sandbox, posted } = loadBridge();
        sandbox.window.__desktopBridge.__init("tok");
        const msgs = parsedMessages(posted).filter((m) => m.method === "page-url");
        expect(msgs).toHaveLength(1);
        expect(msgs[0].args[0]).toBe("http://127.0.0.1:9338/");
        expect(msgs[0].t).toBe("tok");
    });

    it("cancels form submits to foreign origins", () => {
        const { listeners } = loadBridge();
        expect(submitEvent(listeners, "https://evil.example/phish")).toBe(true);
        expect(submitEvent(listeners, "data:text/html,x")).toBe(true);
    });

    it("allows same-origin, relative and local-backend form actions", () => {
        const { listeners } = loadBridge();
        for (const action of ["http://127.0.0.1:9338/submit", "http://127.0.0.1:9337/api", "/relative", ""]) {
            expect(submitEvent(listeners, action), action).toBe(false);
        }
    });

    it("routes cancelled foreign form actions to open-external", () => {
        const { sandbox, posted, listeners } = loadBridge();
        submitEvent(listeners, "https://example.com/x");
        sandbox.window.__desktopBridge.__init("tok");
        const ext = parsedMessages(posted).filter((m) => m.method === "open-external");
        expect(ext).toHaveLength(1);
        expect(ext[0].args[0]).toBe("https://example.com/x");
    });

    it("strips foreign meta refresh but keeps local ones", () => {
        const { metaNodes } = loadBridge({
            metas: [
                { content: "0; url=https://evil.example/" },
                { content: "5; url=http://127.0.0.1:9338/next" },
            ],
        });
        expect(metaNodes[0].removed).toBe(true);
        expect(metaNodes[1].removed).toBe(false);
    });
});
