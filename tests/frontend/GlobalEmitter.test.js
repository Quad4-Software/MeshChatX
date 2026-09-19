import { afterEach, describe, expect, it } from "vitest";
import GlobalEmitter from "../../meshchatx/src/frontend/js/GlobalEmitter";

describe("GlobalEmitter.listenerCount", () => {
    const event = "test-listener-count";

    afterEach(() => {
        GlobalEmitter.off(event);
    });

    it("returns 0 when no handlers are registered", () => {
        expect(GlobalEmitter.listenerCount(event)).toBe(0);
    });

    it("counts registered handlers", () => {
        const first = () => {};
        const second = () => {};
        GlobalEmitter.on(event, first);
        expect(GlobalEmitter.listenerCount(event)).toBe(1);
        GlobalEmitter.on(event, second);
        expect(GlobalEmitter.listenerCount(event)).toBe(2);
        GlobalEmitter.off(event, first);
        expect(GlobalEmitter.listenerCount(event)).toBe(1);
    });
});

describe("GlobalEmitter.emit isolation", () => {
    const event = "test-emit-isolation";

    afterEach(() => {
        GlobalEmitter.off(event);
    });

    it("a throwing handler does not starve later handlers", () => {
        const calls = [];
        const consoleError = console.error;
        console.error = () => {};
        try {
            GlobalEmitter.on(event, () => {
                throw new Error("boom");
            });
            GlobalEmitter.on(event, () => calls.push("second"));
            GlobalEmitter.emit(event, { n: 1 });
        } finally {
            console.error = consoleError;
        }
        expect(calls).toEqual(["second"]);
    });
});
