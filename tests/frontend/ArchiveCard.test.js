// SPDX-License-Identifier: 0BSD

import { mount } from "@vue/test-utils";
import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import ArchiveCard from "@/components/archives/ArchiveCard.vue";
import { createTestI18n } from "./testI18n.js";

const archive = {
    id: 7,
    destination_hash: "ab".repeat(16),
    node_name: "Node",
    page_path: "/page/index.mu",
    hash: "aabbccddeeff0011",
    created_at: "2024-01-01T00:00:00Z",
};

describe("ArchiveCard.vue", () => {
    let observerCallback;
    let observeSpy;
    let disconnectSpy;
    let originalIO;

    beforeEach(() => {
        originalIO = globalThis.IntersectionObserver;
        observeSpy = vi.fn();
        disconnectSpy = vi.fn();
        observerCallback = null;
        globalThis.IntersectionObserver = class {
            constructor(cb) {
                observerCallback = cb;
            }
            observe(el) {
                observeSpy(el);
            }
            disconnect() {
                disconnectSpy();
            }
            unobserve() {}
        };
    });

    afterEach(() => {
        globalThis.IntersectionObserver = originalIO;
    });

    const mountCard = (props = {}) =>
        mount(ArchiveCard, {
            props: {
                archive,
                renderPreview: vi.fn(() => "<p>preview</p>"),
                ...props,
            },
            global: {
                plugins: [createTestI18n()],
            },
        });

    const intersect = () => {
        observerCallback([{ isIntersecting: true }]);
    };

    it("defers preview rendering until the card is in view", async () => {
        const renderPreview = vi.fn(() => "<p>preview</p>");
        const wrapper = mountCard({ renderPreview });
        await wrapper.vm.$nextTick();

        expect(observeSpy).toHaveBeenCalled();
        expect(renderPreview).not.toHaveBeenCalled();
        expect(wrapper.findAll(".animate-pulse").length).toBeGreaterThan(0);

        intersect();
        await wrapper.vm.$nextTick();

        expect(renderPreview).toHaveBeenCalledWith(archive);
        expect(wrapper.html()).toContain("preview");
        expect(disconnectSpy).toHaveBeenCalled();
    });

    it("emits open on click and export without bubbling", async () => {
        const wrapper = mountCard();
        await wrapper.trigger("click");
        expect(wrapper.emitted("open")).toBeTruthy();

        const exportBtn = wrapper.find('button[title="Export .mu"]');
        await exportBtn.trigger("click");
        expect(wrapper.emitted("export")).toBeTruthy();
        expect(wrapper.emitted("open")).toHaveLength(1);
    });

    it("re-renders the preview when previewEpoch changes while in view", async () => {
        const renderPreview = vi.fn(() => "<p>v1</p>");
        const wrapper = mountCard({ renderPreview });
        intersect();
        await wrapper.vm.$nextTick();
        expect(renderPreview).toHaveBeenCalledTimes(1);

        await wrapper.setProps({ previewEpoch: 1 });
        expect(renderPreview).toHaveBeenCalledTimes(2);
    });
});
