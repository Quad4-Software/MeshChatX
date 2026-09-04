// SPDX-License-Identifier: 0BSD

import { describe, expect, it, vi } from "vitest";
import {
    altchaPayloadFromEvent,
    ensureAltchaPayload,
    readAltchaPayloadFromWidget,
} from "../../meshchatx/src/frontend/js/altchaWidget.js";

describe("altchaWidget helpers", () => {
    it("reads payload from the named hidden input", () => {
        const widget = document.createElement("div");
        const input = document.createElement("input");
        input.type = "hidden";
        input.name = "altcha";
        input.value = "solved-token";
        widget.appendChild(input);
        expect(readAltchaPayloadFromWidget(widget)).toBe("solved-token");
    });

    it("reads payload from verified event detail", () => {
        expect(altchaPayloadFromEvent({ detail: { payload: "from-event" } })).toBe("from-event");
        expect(altchaPayloadFromEvent({ detail: { state: "verified" } })).toBeNull();
    });

    it("calls widget.verify when no payload is present yet", async () => {
        const widget = {
            querySelectorAll: () => [],
            verify: vi.fn().mockResolvedValue({ payload: "verified-now" }),
        };
        await expect(ensureAltchaPayload(widget, "")).resolves.toBe("verified-now");
        expect(widget.verify).toHaveBeenCalledTimes(1);
    });

    it("prefers an existing payload over verify", async () => {
        const widget = {
            querySelectorAll: () => [],
            verify: vi.fn(),
        };
        await expect(ensureAltchaPayload(widget, "already")).resolves.toBe("already");
        expect(widget.verify).not.toHaveBeenCalled();
    });
});
