// SPDX-License-Identifier: 0BSD

import { beforeEach, describe, expect, it, vi } from "vitest";

const messageHandlers = [];

vi.mock("../../meshchatx/src/frontend/js/liveTransport.js", () => ({
    default: {
        on: vi.fn((event, handler) => {
            if (event === "message") {
                messageHandlers.push(handler);
            }
        }),
        off: vi.fn((event, handler) => {
            if (event !== "message") {
                return;
            }
            const index = messageHandlers.indexOf(handler);
            if (index >= 0) {
                messageHandlers.splice(index, 1);
            }
        }),
    },
}));

import LiveTransport from "../../meshchatx/src/frontend/js/liveTransport.js";
import {
    installWsEventBridge,
    resetWsEventBridgeForTests,
} from "../../meshchatx/src/frontend/js/registries/wsEventBridge.js";
import { onWsEvent, offWsEvent } from "../../meshchatx/src/frontend/js/registries/wsEventRegistry";

describe("wsEventBridge", () => {
    beforeEach(() => {
        resetWsEventBridgeForTests();
        messageHandlers.length = 0;
        vi.clearAllMocks();
    });

    it("registers a single message handler once", () => {
        installWsEventBridge();
        installWsEventBridge();
        expect(messageHandlers).toHaveLength(1);
    });

    it("removes the message listener on reset", () => {
        installWsEventBridge();
        expect(messageHandlers).toHaveLength(1);
        resetWsEventBridgeForTests();
        expect(LiveTransport.off).toHaveBeenCalledWith("message", expect.any(Function));
        expect(messageHandlers).toHaveLength(0);
    });

    it("does not double-dispatch after reset and reinstall", async () => {
        installWsEventBridge();
        resetWsEventBridgeForTests();
        installWsEventBridge();
        expect(messageHandlers).toHaveLength(1);

        const spy = vi.fn();
        onWsEvent("announce", spy);
        const message = { data: JSON.stringify({ type: "announce", announce: {} }) };
        await Promise.all(messageHandlers.map((handler) => handler(message)));
        expect(spy).toHaveBeenCalledTimes(1);
        offWsEvent("announce", spy);
    });
});
