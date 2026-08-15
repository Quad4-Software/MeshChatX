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
