// SPDX-License-Identifier: 0BSD

import { render, cleanup, waitFor } from "@testing-library/svelte";
import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import MapPublishPanel from "@/features/map/components/MapPublishPanel.svelte";
import ToastUtils from "@/js/ToastUtils";
import { t, registerFallbackMessages, registerTranslator } from "@/js/i18n.js";
import en from "@/locales/en.json";

vi.mock("@/js/ToastUtils", () => ({
    default: {
        success: vi.fn(),
        error: vi.fn(),
        warning: vi.fn(),
        info: vi.fn(),
        loading: vi.fn(),
        dismiss: vi.fn(),
    },
}));

describe("MapPublishPanel", () => {
    beforeEach(() => {
        vi.clearAllMocks();
        registerTranslator(null);
        registerFallbackMessages(en);
        window.api = {
            get: vi.fn().mockImplementation((url) => {
                if (url.includes("/status")) {
                    return Promise.resolve({
                        data: {
                            display_name: "Maps",
                            announce_enabled: false,
                            announce_interval: 900,
                            published_count: 0,
                        },
                    });
                }
                return Promise.resolve({ data: { maps: [] } });
            }),
            post: vi.fn().mockResolvedValue({ data: {} }),
            patch: vi.fn().mockResolvedValue({ data: {} }),
            delete: vi.fn().mockResolvedValue({ data: {} }),
        };
    });

    afterEach(() => {
        cleanup();
        delete window.api;
    });

    it("keeps announce controls off until a map is published", async () => {
        const { container } = render(MapPublishPanel);

        await waitFor(() => {
            const checkbox = container.querySelector('input[type="checkbox"]');
            expect(checkbox).toBeTruthy();
            expect(checkbox.checked).toBe(false);
            expect(checkbox.disabled).toBe(true);
            expect(container.textContent).toContain(t("map.data_announce_needs_publish"));
            const buttons = Array.from(container.querySelectorAll("button"));
            const announceNow = buttons.find((btn) => btn.textContent?.includes(t("map.data_announce_now")));
            expect(announceNow?.hasAttribute("disabled")).toBe(true);
        });
    });

    it("enables announce after a published map is listed", async () => {
        window.api.get = vi.fn().mockImplementation((url) => {
            if (url.includes("/status")) {
                return Promise.resolve({
                    data: {
                        display_name: "Maps",
                        announce_enabled: false,
                        announce_interval: 900,
                        published_count: 1,
                    },
                });
            }
            return Promise.resolve({
                data: { maps: [{ map_id: "a".repeat(16), name: "Camp", format: "geojson", size: 12 }] },
            });
        });

        const { container } = render(MapPublishPanel);

        await waitFor(() => {
            const checkbox = container.querySelector('input[type="checkbox"]');
            expect(checkbox).toBeTruthy();
            expect(checkbox.disabled).toBe(false);
            const buttons = Array.from(container.querySelectorAll("button"));
            const announceNow = buttons.find((btn) => btn.textContent?.includes(t("map.data_announce_now")));
            expect(announceNow?.hasAttribute("disabled")).toBe(false);
        });
    });
});
