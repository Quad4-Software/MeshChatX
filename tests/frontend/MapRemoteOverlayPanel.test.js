// SPDX-License-Identifier: 0BSD

import { describe, expect, it, vi, beforeEach, afterEach } from "vitest";
import { mount, flushPromises } from "@vue/test-utils";
import { nextTick } from "vue";
import MapRemoteOverlayPanel from "../../meshchatx/src/frontend/components/map/internal/MapRemoteOverlayPanel.vue";

describe("MapRemoteOverlayPanel", () => {
    beforeEach(() => {
        window.api = {
            get: vi.fn(async (url) => {
                if (url === "/api/v1/map/overlays") {
                    return { overlays: [] };
                }
                return {};
            }),
            post: vi.fn(async () => ({
                job_id: "j1",
                overlays: [{ id: 1, name: "a", status: "fetching", visible: 1 }],
            })),
            patch: vi.fn(async () => ({})),
            delete: vi.fn(async () => ({})),
        };
    });

    afterEach(() => {
        vi.useRealTimers();
        delete window.api;
    });

    it("loads overlays on mount", async () => {
        const wrapper = mount(MapRemoteOverlayPanel, {
            global: {
                mocks: {
                    $t: (k) => k,
                },
            },
        });
        await flushPromises();
        expect(window.api.get).toHaveBeenCalledWith("/api/v1/map/overlays");
        wrapper.unmount();
    });

    it("posts nomadnet import payload", async () => {
        const wrapper = mount(MapRemoteOverlayPanel, {
            global: {
                mocks: {
                    $t: (k) => k,
                },
            },
        });
        await flushPromises();
        await wrapper.setData({
            kind: "nomadnet_file",
            url: "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa:/file/a.geojson",
        });
        await wrapper.vm.importSources();
        expect(window.api.post).toHaveBeenCalledWith(
            "/api/v1/map/overlays",
            expect.objectContaining({
                kind: "nomadnet_file",
                url: "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa:/file/a.geojson",
            })
        );
        wrapper.unmount();
    });

    it("ignores stale job poll after newer generation", async () => {
        vi.useFakeTimers();
        let jobCalls = 0;
        window.api.get = vi.fn(async (url) => {
            if (url === "/api/v1/map/overlays") {
                return { overlays: [] };
            }
            if (url.includes("/jobs/")) {
                jobCalls += 1;
                return { status: "running", phase: "transferring" };
            }
            return {};
        });
        const wrapper = mount(MapRemoteOverlayPanel, {
            global: { mocks: { $t: (k) => k } },
        });
        await flushPromises();
        wrapper.vm.watchJob("old");
        const genAfterFirst = wrapper.vm.jobGeneration;
        wrapper.vm.watchJob("new");
        expect(wrapper.vm.jobGeneration).toBeGreaterThan(genAfterFirst);
        await vi.advanceTimersByTimeAsync(1500);
        await flushPromises();
        // Only the latest job id should keep polling meaningfully
        const jobUrls = window.api.get.mock.calls.map((c) => c[0]).filter((u) => String(u).includes("/jobs/"));
        expect(jobUrls.some((u) => String(u).includes("new"))).toBe(true);
        wrapper.unmount();
    });
});
