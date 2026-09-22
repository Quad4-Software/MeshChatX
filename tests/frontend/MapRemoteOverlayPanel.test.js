// SPDX-License-Identifier: 0BSD

import { describe, expect, it, vi, beforeEach, afterEach } from "vitest";
import { render, cleanup, waitFor, fireEvent } from "@testing-library/svelte";
import MapRemoteOverlayPanel from "@/features/map/components/MapRemoteOverlayPanel.svelte";
import { t, registerFallbackMessages, registerTranslator } from "@/js/i18n.js";
import en from "@/locales/en.json";

describe("MapRemoteOverlayPanel", () => {
    beforeEach(() => {
        vi.clearAllMocks();
        registerTranslator(null);
        registerFallbackMessages(en);
        window.api = {
            get: vi.fn(async (url) => {
                if (url === "/api/v1/map/overlays") {
                    return { data: { overlays: [] } };
                }
                return { data: {} };
            }),
            post: vi.fn(async () => ({
                data: {
                    job_id: "j1",
                    overlays: [{ id: 1, name: "a", status: "fetching", visible: 1 }],
                },
            })),
            patch: vi.fn(async () => ({ data: {} })),
            delete: vi.fn(async () => ({ data: {} })),
        };
    });

    afterEach(() => {
        cleanup();
        delete window.api;
    });

    it("loads overlays on mount", async () => {
        render(MapRemoteOverlayPanel);
        await waitFor(() => {
            expect(window.api.get).toHaveBeenCalledWith("/api/v1/map/overlays");
        });
    });

    it("posts nomadnet import payload", async () => {
        const { container } = render(MapRemoteOverlayPanel);
        await waitFor(() => {
            expect(window.api.get).toHaveBeenCalledWith("/api/v1/map/overlays");
        });

        const urlInput = container.querySelector('input[type="text"]');
        if (urlInput) {
            await fireEvent.input(urlInput, {
                target: { value: "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa:/file/a.geojson" },
            });
        }

        const importButton = Array.from(container.querySelectorAll("button")).find((btn) =>
            btn.textContent?.includes(t("map.remote_overlays_import"))
        );
        if (importButton) {
            await fireEvent.click(importButton);
        }

        await waitFor(() => {
            expect(window.api.post).toHaveBeenCalledWith(
                "/api/v1/map/overlays",
                expect.objectContaining({
                    url: "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa:/file/a.geojson",
                })
            );
        });
    });
});
