// SPDX-License-Identifier: 0BSD
// Hostile-props mounts: components must not throw or inject raw HTML.

import { mount } from "@vue/test-utils";
import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import ArchiveCard from "@/components/archives/ArchiveCard.vue";
import { createTestI18n } from "./testI18n.js";

const XSS = '<img src=x onerror="globalThis.__pwned=1"><script>globalThis.__pwned=1</script>';
const LONG_UNBROKEN = "x".repeat(5000);
const RTL_EMOJI = "‮‬ مرحبا \U0001F600";

const baseArchive = {
    id: 7,
    destination_hash: "ab".repeat(16),
    node_name: "Node",
    page_path: "/page/index.mu",
    hash: "aabbccddeeff0011",
    created_at: "2024-01-01T00:00:00Z",
};

const hostileProps = [
    { node_name: XSS },
    { node_name: null },
    { node_name: undefined },
    { node_name: LONG_UNBROKEN },
    { node_name: RTL_EMOJI },
    { page_path: XSS },
    { page_path: null },
    { created_at: null },
    { id: null },
    { hash: null },
    { node_name: '"><svg onload=1>' },
];

describe("ArchiveCard hostile mounts", () => {
    beforeEach(() => {
        globalThis.IntersectionObserver = class {
            constructor(cb) {}
            observe() {}
            disconnect() {}
            unobserve() {}
        };
        globalThis.__pwned = 0;
    });
    afterEach(() => {
        delete globalThis.IntersectionObserver;
        delete globalThis.__pwned;
    });

    for (const [i, patch] of hostileProps.entries()) {
        it(`mounts without throw or HTML injection (${i}: ${JSON.stringify(patch).slice(0, 60)})`, () => {
            const renderPreview = vi.fn(() => "<p>safe</p>");
            const w = mount(ArchiveCard, {
                props: {
                    archive: { ...baseArchive, ...patch },
                    renderPreview,
                },
                global: { plugins: [createTestI18n()] },
            });
            // Interpolated text is escaped, so assert no hostile string
            // materialized as a real element or attribute.
            expect(w.findAll("script")).toHaveLength(0);
            expect(w.findAll("img").length).toBe(0);
            for (const el of w.element.querySelectorAll("*")) {
                for (const attr of el.attributes) {
                    expect(attr.name).not.toMatch(/^on/);
                }
            }
            expect(globalThis.__pwned).toBe(0);
            w.unmount();
        });
    }

    it("handles null archive object without throwing", () => {
        const renderPreview = vi.fn(() => "");
        let w;
        try {
            w = mount(ArchiveCard, {
                props: { archive: null, renderPreview },
                global: { plugins: [createTestI18n()] },
            });
        } catch (e) {
            // A throw on null archive is a real robustness gap.
            throw new Error(`mount threw on null archive: ${e.message}`);
        }
        w.unmount();
    });
});
