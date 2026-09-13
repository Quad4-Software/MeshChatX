// SPDX-License-Identifier: 0BSD

import { render, cleanup } from "@testing-library/svelte";
import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import MapDrawingToolbar from "@/features/map/components/MapDrawingToolbar.svelte";
import { MapDrawManager } from "@/features/map/lib/mapDrawManager.js";
import { registerFallbackMessages, registerTranslator } from "@/js/i18n.js";
import en from "@/locales/en.json";

const DRAWING_TOOLS = [
    { type: "Point", icon: "map-marker-plus" },
    { type: "LineString", icon: "vector-line" },
    { type: "Polygon", icon: "vector-polygon" },
    { type: "Circle", icon: "circle-outline" },
];

describe("MapDrawing tests", () => {
    beforeEach(() => {
        registerTranslator(null);
        registerFallbackMessages(en);
    });

    afterEach(() => {
        cleanup();
    });

    it("renders drawing tool buttons", () => {
        const { container } = render(MapDrawingToolbar, {
            tools: DRAWING_TOOLS,
            drawType: null,
            measuring: false,
            bearingMode: false,
            bearingFromGps: false,
            exportMode: false,
            selectedFeature: null,
        });

        for (const tool of DRAWING_TOOLS) {
            const btn = container.querySelector(
                `button[title="${en.map[`tool_${tool.type.toLowerCase()}`] || `map.tool_${tool.type.toLowerCase()}`}"]`
            );
            expect(btn).toBeTruthy();
        }
        expect(container.querySelector(`button[title="${en.map.tool_measure}"]`)).toBeTruthy();
        expect(container.querySelector(`button[title="${en.map.tool_clear}"]`)).toBeTruthy();
    });

    it("handles draw manager initialization and cleanup", () => {
        const mockMap = {
            addInteraction: vi.fn(),
            removeInteraction: vi.fn(),
            addOverlay: vi.fn(),
            removeOverlay: vi.fn(),
        };
        const mockSource = {
            clear: vi.fn(),
            addFeature: vi.fn(),
            removeFeature: vi.fn(),
        };

        const manager = new MapDrawManager({
            map: mockMap,
            drawSource: mockSource,
        });

        expect(manager).toBeDefined();
        manager.destroy();
        expect(mockMap.removeInteraction).toHaveBeenCalled();
    });
});
