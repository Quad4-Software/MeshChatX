// SPDX-License-Identifier: 0BSD

import { render, cleanup, fireEvent, waitFor } from "@testing-library/svelte";
import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import MapDiscoverPanel from "@/features/map/components/MapDiscoverPanel.svelte";
import ToastUtils from "@/js/ToastUtils";
import { t, registerFallbackMessages, registerTranslator } from "@/js/i18n.js";
import en from "@/locales/en.json";

const HASH = "ab".repeat(16);

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

describe("MapDiscoverPanel", () => {
    beforeEach(() => {
        vi.clearAllMocks();
        registerTranslator(null);
        registerFallbackMessages(en);
        window.api = {
            get: vi.fn().mockResolvedValue({
                data: {
                    announces: [{ destination_hash: HASH, map_name: "Camp maps", map_count: 2 }],
                },
            }),
            post: vi.fn().mockResolvedValue({ data: { maps: [{ id: "a".repeat(16), name: "Camp", size: 12 }] } }),
        };
    });

    afterEach(() => {
        cleanup();
        delete window.api;
    });

    it("loads heard map-data-v1 announces through window.api", async () => {
        const { container } = render(MapDiscoverPanel, {
            listenEnabled: true,
        });

        await waitFor(() => {
            expect(window.api.get).toHaveBeenCalledWith("/api/v1/map/data/heard", {
                params: { search: undefined, limit: 250 },
            });
            expect(container.textContent).toContain("Camp maps");
            expect(container.textContent).toContain(HASH);
        });
    });

    it("fetches a catalog over window.api.post", async () => {
        const { container } = render(MapDiscoverPanel, {
            listenEnabled: true,
        });

        await waitFor(() => {
            expect(container.textContent).toContain("Camp maps");
        });

        const fetchButton = container.querySelector("button");
        if (fetchButton) {
            await fireEvent.click(fetchButton);
        }

        await waitFor(() => {
            expect(window.api.post).toHaveBeenCalledWith("/api/v1/map/data/catalog", {
                destination_hash: HASH,
            });
            expect(container.textContent).toContain("Camp");
            expect(ToastUtils.loading).toHaveBeenCalled();
            expect(ToastUtils.success).toHaveBeenCalled();
        });
    });

    it("shows empty catalog copy when the node lists no maps", async () => {
        window.api.post = vi.fn().mockResolvedValue({ data: { maps: [] } });
        const { container } = render(MapDiscoverPanel, {
            listenEnabled: true,
        });

        await waitFor(() => {
            expect(container.textContent).toContain("Camp maps");
        });

        const fetchButton = container.querySelector("button");
        if (fetchButton) {
            await fireEvent.click(fetchButton);
        }

        await waitFor(() => {
            expect(container.textContent).toContain(t("map.data_catalog_empty"));
            expect(ToastUtils.info).toHaveBeenCalled();
        });
    });

    it("does not fetch heard announces while listening is off", async () => {
        const { container } = render(MapDiscoverPanel, {
            listenEnabled: false,
        });

        await waitFor(() => {
            expect(window.api.get).not.toHaveBeenCalled();
            expect(container.textContent).toContain(t("map.data_listen_off"));
        });
    });
});
