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
 * Touch gestures inside the sandboxed renderer frame never reach the shell
 * document, so the frame detects edge swipe-back and pull-to-refresh itself
 * and forwards progress through postMessage. These tests drive the frame
 * listeners with synthetic touch events.
 */

let postSpy;
let rafCallbacks;

function installRafStub() {
    rafCallbacks = [];
    window.requestAnimationFrame = (cb) => {
        rafCallbacks.push(cb);
        return rafCallbacks.length;
    };
    window.cancelAnimationFrame = (id) => {
        if (id >= 1 && id <= rafCallbacks.length) {
            rafCallbacks[id - 1] = null;
        }
    };
}

function flushRaf() {
    const pending = rafCallbacks.splice(0);
    for (const cb of pending) {
        if (cb) {
            cb(performance.now());
        }
    }
}

function gesturePosts(type) {
    return postSpy.mock.calls.map(([msg]) => msg).filter((msg) => msg && msg.type === type);
}

function touch(id, x, y) {
    return { identifier: id, clientX: x, clientY: y };
}

function dispatchTouch(type, touches, changedTouches) {
    const event = new Event(type, { bubbles: true, cancelable: true });
    event.touches = touches;
    event.changedTouches = changedTouches || touches;
    document.dispatchEvent(event);
}

function touchStart(touches) {
    dispatchTouch("touchstart", touches);
}

function touchMove(touches) {
    dispatchTouch("touchmove", touches);
}

function touchEnd(changed, remaining = []) {
    dispatchTouch("touchend", remaining, changed);
}

function touchCancel(changed, remaining = []) {
    dispatchTouch("touchcancel", remaining, changed);
}

beforeAll(async () => {
    installRafStub();
    // The module caches the #root element at import time.
    document.body.innerHTML = '<div id="root"></div>';
    await import("../../meshchatx/src/frontend/js/nomadCrashTabMain.js");
});

beforeEach(() => {
    postSpy = vi.spyOn(window, "postMessage").mockImplementation(() => {});
    document.body.scrollTop = 0;
    document.body.scrollLeft = 0;
});

describe("nomad crash-tab nav gesture forwarding", () => {
    it("forwards edge swipe-back progress capped at 140 and the final distance", () => {
        touchStart([touch(1, 10, 100)]);
        touchMove([touch(1, 110, 100)]);
        flushRaf();

        const progress = gesturePosts("nav-swipe-back-progress");
        expect(progress).toHaveLength(1);
        expect(progress[0].distance).toBe(100);

        touchMove([touch(1, 260, 100)]);
        flushRaf();
        const capped = gesturePosts("nav-swipe-back-progress");
        expect(capped[capped.length - 1].distance).toBe(140);

        touchEnd([touch(1, 260, 100)]);
        const ends = gesturePosts("nav-swipe-back-end");
        expect(ends).toHaveLength(1);
        expect(ends[0].distance).toBe(140);
    });

    it("does not forward swipe-back when the frame can pan right (scrollLeft > 0)", () => {
        document.body.scrollLeft = 30;
        touchStart([touch(1, 10, 100)]);
        document.body.scrollLeft = 0;
        touchMove([touch(1, 150, 100)]);
        flushRaf();
        touchEnd([touch(1, 150, 100)]);

        expect(gesturePosts("nav-swipe-back-progress")).toHaveLength(0);
        expect(gesturePosts("nav-swipe-back-end")).toHaveLength(0);
    });

    it("does not forward swipe-back outside the edge zone", () => {
        touchStart([touch(1, 200, 100)]);
        touchMove([touch(1, 320, 100)]);
        flushRaf();
        touchEnd([touch(1, 320, 100)]);

        expect(gesturePosts("nav-swipe-back-progress")).toHaveLength(0);
        expect(gesturePosts("nav-swipe-back-end")).toHaveLength(0);
    });

    it("posts distance 0 when the swipe reverses mid-gesture", () => {
        touchStart([touch(1, 10, 100)]);
        touchMove([touch(1, 110, 100)]);
        flushRaf();
        expect(gesturePosts("nav-swipe-back-progress")).toHaveLength(1);

        // finger drifts back and up before release
        touchMove([touch(1, 30, 60)]);
        flushRaf();
        const progress = gesturePosts("nav-swipe-back-progress");
        expect(progress[progress.length - 1].distance).toBe(0);

        // the reversal already zeroed the shell state, so a redundant end
        // echo is suppressed
        touchEnd([touch(1, 30, 60)]);
        expect(gesturePosts("nav-swipe-back-end")).toHaveLength(0);
    });

    it("forwards pull-to-refresh progress capped at 160 and the final distance", () => {
        touchStart([touch(1, 200, 100)]);
        touchMove([touch(1, 200, 220)]);
        flushRaf();

        const progress = gesturePosts("nav-pull-progress");
        expect(progress).toHaveLength(1);
        expect(progress[0].distance).toBe(120);

        touchMove([touch(1, 200, 400)]);
        flushRaf();
        const capped = gesturePosts("nav-pull-progress");
        expect(capped[capped.length - 1].distance).toBe(160);

        touchEnd([touch(1, 200, 400)]);
        const ends = gesturePosts("nav-pull-end");
        expect(ends).toHaveLength(1);
        expect(ends[0].distance).toBe(160);
    });

    it("does not arm pull-to-refresh when the page started scrolled", () => {
        document.body.scrollTop = 50;
        touchStart([touch(1, 200, 100)]);
        document.body.scrollTop = 0;
        touchMove([touch(1, 200, 240)]);
        flushRaf();
        touchEnd([touch(1, 200, 240)]);

        expect(gesturePosts("nav-pull-progress")).toHaveLength(0);
        expect(gesturePosts("nav-pull-end")).toHaveLength(0);
    });

    it("posts pull-cancel only after the gesture showed progress", () => {
        touchStart([touch(1, 200, 100)]);
        touchMove([touch(1, 200, 220)]);
        flushRaf();
        touchCancel([touch(1, 200, 220)]);
        expect(gesturePosts("nav-pull-cancel")).toHaveLength(1);

        touchStart([touch(1, 200, 100)]);
        touchCancel([touch(1, 200, 100)]);
        expect(gesturePosts("nav-pull-cancel")).toHaveLength(1);
    });

    it("posts swipe-back-cancel only after the gesture showed progress", () => {
        touchStart([touch(1, 10, 100)]);
        touchMove([touch(1, 110, 100)]);
        flushRaf();
        touchCancel([touch(1, 110, 100)]);
        expect(gesturePosts("nav-swipe-back-cancel")).toHaveLength(1);

        touchStart([touch(1, 10, 100)]);
        touchCancel([touch(1, 10, 100)]);
        expect(gesturePosts("nav-swipe-back-cancel")).toHaveLength(1);
    });

    it("a plain tap forwards nothing", () => {
        touchStart([touch(1, 10, 100)]);
        touchEnd([touch(1, 10, 100)]);

        expect(gesturePosts("nav-swipe-back-progress")).toHaveLength(0);
        expect(gesturePosts("nav-swipe-back-end")).toHaveLength(0);
        expect(gesturePosts("nav-pull-progress")).toHaveLength(0);
        expect(gesturePosts("nav-pull-end")).toHaveLength(0);
    });

    it("ends with the reversal-aware distance even when the last move never flushed", () => {
        touchStart([touch(1, 10, 100)]);
        touchMove([touch(1, 110, 100)]);
        flushRaf();
        expect(gesturePosts("nav-swipe-back-progress")).toHaveLength(1);

        // reversal happens but the frame is torn down before the rAF flush
        touchMove([touch(1, 20, 40)]);
        touchEnd([touch(1, 20, 40)]);
        const ends = gesturePosts("nav-swipe-back-end");
        expect(ends).toHaveLength(1);
        expect(ends[0].distance).toBe(0);
    });

    it("ignores extra touches during a tracked gesture", () => {
        touchStart([touch(1, 10, 100)]);
        // second finger lands; the tracker must keep following the first
        touchStart([touch(1, 10, 100), touch(2, 300, 300)]);
        touchMove([touch(1, 110, 100), touch(2, 300, 300)]);
        flushRaf();

        const progress = gesturePosts("nav-swipe-back-progress");
        expect(progress).toHaveLength(1);
        expect(progress[0].distance).toBe(100);

        // second finger lifting must not end the tracked gesture
        touchEnd([touch(2, 300, 300)], [touch(1, 110, 100)]);
        expect(gesturePosts("nav-swipe-back-end")).toHaveLength(0);

        touchEnd([touch(1, 110, 100)]);
        expect(gesturePosts("nav-swipe-back-end")).toHaveLength(1);
    });

    it("keeps horizontal panning unambiguous: vertical scroll at scrollLeft 0 is not swipe-back", () => {
        touchStart([touch(1, 10, 100)]);
        touchMove([touch(1, 14, 160)]);
        flushRaf();
        // vertical-dominant: no swipe distance is ever posted, and the pull
        // branch owns the gesture instead
        expect(gesturePosts("nav-swipe-back-progress")).toHaveLength(0);
        expect(gesturePosts("nav-pull-progress").length).toBeGreaterThan(0);
        touchEnd([touch(1, 14, 160)]);
    });
});
