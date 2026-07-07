// SPDX-License-Identifier: 0BSD

import { describe, expect, it, vi } from "vitest";
import { dispatchWsEvent, onWsEvent, offWsEvent } from "../../meshchatx/src/frontend/js/registries/wsEventRegistry.js";

describe("wsEventRegistry", () => {
    it("dispatches to registered handlers by type", async () => {
        const handler = vi.fn();
        onWsEvent("config", handler);
        await dispatchWsEvent("config", { type: "config", config: { theme: "dark" } });
        expect(handler).toHaveBeenCalledWith({ type: "config", config: { theme: "dark" } });
        offWsEvent("config", handler);
    });

    it("supports multiple handlers for one type", async () => {
        const first = vi.fn();
        const second = vi.fn();
        onWsEvent("announce", first);
        onWsEvent("announce", second);
        await dispatchWsEvent("announce", { type: "announce" });
        expect(first).toHaveBeenCalled();
        expect(second).toHaveBeenCalled();
        offWsEvent("announce", first);
        offWsEvent("announce", second);
    });
});
