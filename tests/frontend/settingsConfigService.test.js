import { describe, it, expect, vi } from "vitest";
import {
    numOrNull,
    sanitizeColorConfigFields,
    fetchMergedConfig,
    patchServerConfig,
} from "../../meshchatx/src/frontend/js/settings/settingsConfigService.js";

describe("settingsConfigService", () => {
    it("numOrNull returns null for empty input", () => {
        expect(numOrNull("")).toBeNull();
        expect(numOrNull(null)).toBeNull();
    });

    it("numOrNull parses finite numbers", () => {
        expect(numOrNull("12")).toBe(12);
        expect(numOrNull(3.5)).toBe(3.5);
    });

    it("sanitizeColorConfigFields normalizes hex and inbound bubble", () => {
        const config = {
            banished_color: "#ff00ff",
            message_outbound_bubble_color: "bad",
            message_inbound_bubble_color: "#aabbcc",
            message_failed_bubble_color: "",
            message_waiting_bubble_color: "#010203",
        };
        sanitizeColorConfigFields(config);
        expect(config.banished_color).toBe("#ff00ff");
        expect(config.message_outbound_bubble_color).toBe("#4f46e5");
        expect(config.message_inbound_bubble_color).toBe("#aabbcc");
        expect(config.message_failed_bubble_color).toBe("#ef4444");
    });

    it("fetchMergedConfig merges server config onto base", async () => {
        const api = {
            get: vi.fn().mockResolvedValue({
                data: { config: { theme: "light", display_name: "X" } },
            }),
        };
        const base = { theme: "dark", extra: 1 };
        const merged = await fetchMergedConfig(api, base);
        expect(merged).toEqual({ theme: "light", extra: 1, display_name: "X" });
    });

    it("patchServerConfig returns config from response", async () => {
        const api = {
            patch: vi.fn().mockResolvedValue({ data: { config: { theme: "light" } } }),
        };
        const out = await patchServerConfig({ theme: "light" }, api);
        expect(out).toEqual({ theme: "light" });
    });
});
