import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { readFileSync } from "node:fs";
import { resolve } from "node:path";
import vm from "node:vm";

const bridgeSrc = readFileSync(resolve(__dirname, "../../desktop/shell/desktop-bridge.js"), "utf8");

function loadBridge({ topSame = true } = {}) {
    const posted = [];
    const sandbox = {
        window: {},
        document: {
            documentElement: { outerHTML: "" },
            addEventListener: () => {},
            removeEventListener: () => {},
            createElement: () => ({ style: {}, setAttribute: () => {}, focus: () => {}, select: () => {} }),
            body: { appendChild: () => {}, removeChild: () => {} },
        },
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
    sandbox.window.location = { href: "http://127.0.0.1:9338/", protocol: "http:", hostname: "127.0.0.1", port: "9338" };
    sandbox.window.top = topSame ? sandbox.window : {};
    sandbox.window.webkit = {
        messageHandlers: {
            external: {
                postMessage: (msg) => posted.push(msg),
            },
        },
    };
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
    for (const n of ["HTMLAnchorElement","HTMLInputElement","HTMLElement","HTMLButtonElement","Node","Element","Event","CustomEvent","KeyboardEvent","MouseEvent","FocusEvent","InputEvent","DragEvent","ClipboardEvent","FileReader","Image","Option","DocumentFragment","MutationObserver","ResizeObserver","IntersectionObserver","XMLHttpRequest","fetch","Headers","Request","Response","FormData","URLSearchParams","DOMParser","XMLSerializer","CSS","matchMedia","getComputedStyle","requestAnimationFrame","cancelAnimationFrame","queueMicrotask","structuredClone","performance","screen","history","location","alert","confirm","prompt","open","close","focus","blur","print","postMessage","addEventListener","removeEventListener","dispatchEvent","btoa","atob"]) {
        if (sandbox[n] === undefined) {
            if (n === "fetch") sandbox[n] = () => Promise.reject(new Error("no fetch"));
            else if (n === "matchMedia") sandbox[n] = () => ({ matches: false, addEventListener: () => {} });
            else if (n === "getComputedStyle") sandbox[n] = () => ({});
            else if (["requestAnimationFrame","queueMicrotask"].includes(n)) sandbox[n] = (f) => setTimeout(f, 0);
            else if (["cancelAnimationFrame"].includes(n)) sandbox[n] = () => {};
            else if (["addEventListener","removeEventListener","dispatchEvent","alert","confirm","prompt","open","close","focus","blur","print","postMessage"].includes(n)) sandbox[n] = () => {};
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
    sandbox.window.length = 0;
    sandbox.window.innerWidth = 1920; sandbox.window.innerHeight = 1080;
    sandbox.window.devicePixelRatio = 1;
    sandbox.window.scrollTo = () => {}; sandbox.window.scroll = () => {};
    sandbox.window.requestAnimationFrame = sandbox.requestAnimationFrame;
    sandbox.window.matchMedia = sandbox.matchMedia;
    sandbox.window.getComputedStyle = sandbox.getComputedStyle;
    sandbox.window.addEventListener = () => {};
    sandbox.window.removeEventListener = () => {};
    sandbox.window.dispatchEvent = () => {};
    sandbox.window.atob = sandbox.atob; sandbox.window.btoa = sandbox.btoa;
    sandbox.window.TextEncoder = TextEncoder; sandbox.window.TextDecoder = TextDecoder;
    sandbox.window.Uint8Array = Uint8Array; sandbox.window.ArrayBuffer = ArrayBuffer;
    sandbox.window.crypto = sandbox.crypto;
    sandbox.window.Blob = class {}; sandbox.window.FileReader = class {};
    sandbox.window.URL = URL; sandbox.window.URLSearchParams = URLSearchParams;
    sandbox.window.setTimeout = setTimeout; sandbox.window.clearTimeout = clearTimeout;
    sandbox.window.setInterval = setInterval; sandbox.window.clearInterval = clearInterval;
    sandbox.window.Promise = Promise; sandbox.window.JSON = JSON;
    sandbox.window.Object = Object; sandbox.window.Array = Array;
    sandbox.window.String = String; sandbox.window.Number = Number;
    sandbox.window.Boolean = Boolean; sandbox.window.Error = Error;
    sandbox.window.TypeError = TypeError; sandbox.window.RangeError = RangeError;
    sandbox.window.Date = Date; sandbox.window.Math = Math;
    sandbox.window.RegExp = RegExp; sandbox.window.Symbol = Symbol;
    sandbox.window.Map = Map; sandbox.window.Set = Set; sandbox.window.WeakMap = WeakMap;
    sandbox.window.WeakSet = WeakSet; sandbox.window.Proxy = Proxy;
    sandbox.window.Reflect = Reflect; sandbox.window.Promise = Promise;
    sandbox.window.parseInt = parseInt; sandbox.window.parseFloat = parseFloat;
    sandbox.window.isNaN = isNaN; sandbox.window.isFinite = isFinite;
    sandbox.window.encodeURIComponent = encodeURIComponent;
    sandbox.window.decodeURIComponent = decodeURIComponent;
    sandbox.window.encodeURI = encodeURI; sandbox.window.decodeURI = decodeURI;
    sandbox.window.escape = escape; sandbox.window.unescape = unescape;
    sandbox.window.NaN = NaN; sandbox.window.Infinity = Infinity;
    sandbox.window.undefined = undefined;
    for (const n of ["HTMLAnchorElement","HTMLInputElement","HTMLElement","HTMLButtonElement","Node","Element","Event","CustomEvent","KeyboardEvent","MouseEvent","FocusEvent","InputEvent","DragEvent","ClipboardEvent","FileReader","Image","Option","DocumentFragment","MutationObserver","ResizeObserver","IntersectionObserver","XMLHttpRequest","Headers","Request","Response","FormData","DOMParser","XMLSerializer","CSS","matchMedia","getComputedStyle","performance","screen","history","location","alert","confirm","prompt","open","close","focus","blur","print","postMessage","addEventListener","removeEventListener","dispatchEvent","btoa","atob","atob","TextEncoder","TextDecoder","Uint8Array","ArrayBuffer","DataView","Blob","URL","URLSearchParams","Promise","JSON","Object","Array","String","Number","Boolean","Error","TypeError","RangeError","Date","Math","RegExp","Symbol","Map","Set","WeakMap","WeakSet","Proxy","Reflect","parseInt","parseFloat","isNaN","isFinite","encodeURIComponent","decodeURIComponent","encodeURI","decodeURI","escape","unescape","NaN","Infinity","undefined","self","top","parent","frames","length","innerWidth","innerHeight","devicePixelRatio","scrollTo","scroll","requestAnimationFrame","crypto","navigator","document","location","console","setTimeout","clearTimeout","setInterval","clearInterval","queueMicrotask","structuredClone","fetch","FormData","WebSocket","RTCPeerConnection","MediaRecorder","AudioContext","webkitAudioContext","Notification","indexedDB","caches","serviceWorker","visualViewport","speechSynthesis","Notification"]) {
        if (sandbox.window[n] === undefined) {
            if (["addEventListener","removeEventListener","dispatchEvent","alert","confirm","prompt","open","close","focus","blur","print","postMessage","scrollTo","scroll","queueMicrotask"].includes(n)) sandbox.window[n] = () => {};
            else if (n === "matchMedia") sandbox.window[n] = () => ({ matches: false, addEventListener: () => {} });
            else if (n === "getComputedStyle") sandbox.window[n] = () => ({});
            else if (n === "requestAnimationFrame") sandbox.window[n] = (f) => setTimeout(f, 0);
            else if (n === "performance") sandbox.window[n] = { now: () => Date.now() };
            else if (n === "screen") sandbox.window[n] = { width: 1920, height: 1080 };
            else if (["history","location"].includes(n)) sandbox.window[n] = {};
            else if (["parseInt","parseFloat","isNaN","isFinite","encodeURIComponent","decodeURIComponent","encodeURI","decodeURI","escape","unescape"].includes(n)) sandbox.window[n] = globalThis[n];
            else if (["NaN","Infinity","undefined"].includes(n)) sandbox.window[n] = globalThis[n];
            else if (typeof globalThis[n] !== "undefined") sandbox.window[n] = globalThis[n];
            else sandbox.window[n] = class {};
        }
    }
    vm.createContext(sandbox);
    vm.runInContext(bridgeSrc, sandbox);
    return { sandbox, posted };
}

describe("desktop bridge page token", () => {
    it("queues calls before __init and flushes with token", async () => {
        const { sandbox, posted } = loadBridge();
        const desktop = sandbox.window.desktop;
        expect(desktop).toBeDefined();
        const p = desktop.appVersion();
        // not posted yet
        expect(posted.filter((m) => m.includes('"app-version"'))).toHaveLength(0);
        sandbox.window.__desktopBridge.__init("tok1");
        await Promise.resolve();
        await Promise.resolve();
        const msgs = posted.filter((m) => m.includes('"app-version"'));
        expect(msgs).toHaveLength(1);
        const parsed = JSON.parse(msgs[0]);
        expect(parsed.t).toBe("tok1");
        // resolve it
        sandbox.window.__desktopBridge.resolve(parsed.id, true, '"4.12.0"');
        await expect(p).resolves.toBe("4.12.0");
    });

    it("later calls carry the token; second __init switches it", async () => {
        const { sandbox, posted } = loadBridge();
        const desktop = sandbox.window.desktop;
        sandbox.window.__desktopBridge.__init("tokA");
        await Promise.resolve();
        const p1 = desktop.appVersion();
        await Promise.resolve();
        const m1 = JSON.parse(posted.filter((m) => m.includes('"app-version"')).pop());
        expect(m1.t).toBe("tokA");
        sandbox.window.__desktopBridge.resolve(m1.id, true, '"1"');
        await p1;
        sandbox.window.__desktopBridge.__init("tokB");
        const p2 = desktop.appVersion();
        await Promise.resolve();
        const m2 = JSON.parse(posted.filter((m) => m.includes('"app-version"')).pop());
        expect(m2.t).toBe("tokB");
        sandbox.window.__desktopBridge.resolve(m2.id, true, '"2"');
        await p2;
    });

    it("queue cap 64 rejects the 65th pre-init call", async () => {
        const { sandbox } = loadBridge();
        const desktop = sandbox.window.desktop;
        const ps = [];
        for (let i = 0; i < 65; i++) {
            ps.push(desktop.appVersion().catch((e) => e));
        }
        const results = await Promise.all(ps);
        const errs = results.filter((r) => r instanceof Error);
        expect(errs.length).toBeGreaterThanOrEqual(1);
    });

    it("token is not discoverable on window or DOM", () => {
        const { sandbox } = loadBridge();
        sandbox.window.__desktopBridge.__init("supersecret-token-xyz");
        const names = Object.getOwnPropertyNames(sandbox.window);
        expect(JSON.stringify(names)).not.toContain("supersecret-token-xyz");
        const desktopStr = JSON.stringify(Object.getOwnPropertyNames(sandbox.window.desktop || {}));
        expect(desktopStr).not.toContain("supersecret-token-xyz");
        const bridgeStr = JSON.stringify(Object.getOwnPropertyNames(sandbox.window.__desktopBridge || {}));
        expect(bridgeStr).not.toContain("supersecret-token-xyz");
        expect(sandbox.document.documentElement.outerHTML).not.toContain("supersecret-token-xyz");
    });

    it("no desktop API in a subframe", () => {
        const { sandbox } = loadBridge({ topSame: false });
        expect(sandbox.window.desktop).toBeUndefined();
    });
});

describe("open-protocol-link replay buffer", () => {
    const tick = () => new Promise((r) => setTimeout(r, 10));
    const emitLink = (sandbox, url) =>
        sandbox.window.__desktopBridge.emit("open-protocol-link", JSON.stringify({ url }));

    it("replays a link emitted before the listener registers", async () => {
        const { sandbox } = loadBridge();
        emitLink(sandbox, "lxmf://early");
        const seen = [];
        sandbox.window.desktop.onProtocolLink((u) => seen.push(u));
        await tick();
        expect(seen).toEqual(["lxmf://early"]);
    });

    it("caps the replay buffer at 8, keeping the newest", async () => {
        const { sandbox } = loadBridge();
        for (let i = 1; i <= 10; i++) emitLink(sandbox, `lxmf://n${i}`);
        const seen = [];
        sandbox.window.desktop.onProtocolLink((u) => seen.push(u));
        await tick();
        expect(seen).toHaveLength(8);
        expect(seen[0]).toBe("lxmf://n3");
        expect(seen[7]).toBe("lxmf://n10");
    });

    it("does not replay twice to later listeners", async () => {
        const { sandbox } = loadBridge();
        emitLink(sandbox, "lxmf://once");
        const first = [];
        sandbox.window.desktop.onProtocolLink((u) => first.push(u));
        await tick();
        const second = [];
        sandbox.window.desktop.onProtocolLink((u) => second.push(u));
        await tick();
        expect(first).toEqual(["lxmf://once"]);
        expect(second).toEqual([]);
        // live events still reach both listeners
        emitLink(sandbox, "lxmf://live");
        await tick();
        expect(first).toEqual(["lxmf://once", "lxmf://live"]);
        expect(second).toEqual(["lxmf://live"]);
    });
});
