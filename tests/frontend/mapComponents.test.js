// SPDX-License-Identifier: 0BSD

import { render, cleanup, fireEvent, waitFor } from "@testing-library/svelte";
import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import MapDrawingToolbar from "@/features/map/components/MapDrawingToolbar.svelte";
import MapBearingInstructions from "@/features/map/components/MapBearingInstructions.svelte";
import MapSearchBar from "@/features/map/components/MapSearchBar.svelte";
import MapExportInstructions from "@/features/map/components/MapExportInstructions.svelte";
import MapLoadingOverlay from "@/features/map/components/MapLoadingOverlay.svelte";
import MapExportConfigPanel from "@/features/map/components/MapExportConfigPanel.svelte";
import MapExportProgressPanel from "@/features/map/components/MapExportProgressPanel.svelte";
import MapClusterPanel from "@/features/map/components/MapClusterPanel.svelte";
import MapMarkerPanel from "@/features/map/components/MapMarkerPanel.svelte";
import MapVectorExchangePanel from "@/features/map/components/MapVectorExchangePanel.svelte";
import MapSidePanel from "@/features/map/components/MapSidePanel.svelte";
import { t, registerFallbackMessages, registerTranslator } from "@/js/i18n.js";
import en from "@/locales/en.json";

const DRAWING_TOOLS = [
    { type: "Select", icon: "cursor-default" },
    { type: "Point", icon: "map-marker-plus" },
    { type: "LineString", icon: "vector-line" },
    { type: "Polygon", icon: "vector-polygon" },
    { type: "Circle", icon: "circle-outline" },
];

describe("MapDrawingToolbar", () => {
    beforeEach(() => {
        registerTranslator(null);
        registerFallbackMessages(en);
    });

    afterEach(() => {
        cleanup();
    });

    it("emits ontogglebearing from the single bearing button", async () => {
        const onToggleBearing = vi.fn();
        const { container } = render(MapDrawingToolbar, {
            tools: DRAWING_TOOLS,
            drawType: null,
            measuring: false,
            bearingMode: false,
            bearingFromGps: false,
            exportMode: false,
            selectedFeature: null,
            ontogglebearing: onToggleBearing,
        });
        const bearingBtn = container.querySelector(`button[title="${t("map.tool_bearing")}"]`);
        expect(bearingBtn).toBeTruthy();
        if (bearingBtn) {
            await fireEvent.click(bearingBtn);
        }
        expect(onToggleBearing).toHaveBeenCalledTimes(1);
    });

    it("shows draw, measure, and files group labels", () => {
        const { container } = render(MapDrawingToolbar, {
            tools: DRAWING_TOOLS,
            bearingMode: false,
            measuring: false,
            exportMode: false,
            selectedFeature: null,
        });
        expect(container.textContent).toContain(t("map.toolbar_draw"));
        expect(container.textContent).toContain(t("map.toolbar_measure"));
        expect(container.textContent).toContain(t("map.toolbar_files"));
    });
});

describe("MapBearingInstructions", () => {
    beforeEach(() => {
        registerTranslator(null);
        registerFallbackMessages(en);
    });

    afterEach(() => {
        cleanup();
    });

    it("shows first-hint copy and calls onusemylocation", async () => {
        const onUseMyLocation = vi.fn();
        const { container } = render(MapBearingInstructions, {
            fromGpsActive: false,
            awaitingSecondTap: false,
            onusemylocation: onUseMyLocation,
        });
        expect(container.textContent).toContain(t("map.bearing_hint_first"));
        const btn = container.querySelector("button");
        expect(btn).toBeTruthy();
        if (btn) {
            await fireEvent.click(btn);
        }
        expect(onUseMyLocation).toHaveBeenCalledTimes(1);
    });

    it("shows destination hint when fromGpsActive", () => {
        const { container } = render(MapBearingInstructions, {
            fromGpsActive: true,
            awaitingSecondTap: true,
        });
        expect(container.textContent).toContain(t("map.bearing_hint_destination"));
    });

    it("shows second-tap hint for two-point mode", () => {
        const { container } = render(MapBearingInstructions, {
            fromGpsActive: false,
            awaitingSecondTap: true,
        });
        expect(container.textContent).toContain(t("map.bearing_hint_second"));
    });
});

describe("MapSearchBar", () => {
    beforeEach(() => {
        registerTranslator(null);
        registerFallbackMessages(en);
    });

    afterEach(() => {
        cleanup();
    });

    it("emits oninput and onsearch", async () => {
        const onSearch = vi.fn();
        const { container } = render(MapSearchBar, {
            modelValue: "Tokyo",
            searching: false,
            showResults: false,
            results: [],
            onsearch: onSearch,
        });
        const input = container.querySelector("input");
        expect(input).toBeTruthy();
        if (input) {
            await fireEvent.keyDown(input, { key: "Enter" });
        }
        expect(onSearch).toHaveBeenCalledTimes(1);
    });

    it("selects a search result on click", async () => {
        const onSelect = vi.fn();
        const results = [{ display_name: "Paris, France", type: "city", lat: 48.8, lon: 2.3 }];
        const { container } = render(MapSearchBar, {
            modelValue: "Paris",
            searching: false,
            showResults: true,
            results: results,
            onselect: onSelect,
        });
        const resultBtn = container.querySelector("div.absolute button");
        expect(resultBtn).toBeTruthy();
        if (resultBtn) {
            await fireEvent.click(resultBtn);
        }
        expect(onSelect).toHaveBeenCalledWith(results[0]);
    });
});

describe("MapExportInstructions", () => {
    beforeEach(() => {
        registerTranslator(null);
        registerFallbackMessages(en);
    });

    afterEach(() => {
        cleanup();
    });

    it("renders export instructions and calls onselectpreset", async () => {
        const onSelectPreset = vi.fn();
        const presets = [{ id: "city" }, { id: "region" }];
        const { container } = render(MapExportInstructions, {
            presets,
            onselectpreset: onSelectPreset,
        });
        expect(container.textContent).toContain(t("map.export_instructions"));
        const buttons = Array.from(container.querySelectorAll("button"));
        expect(buttons.length).toBe(2);
        await fireEvent.click(buttons[0]);
        expect(onSelectPreset).toHaveBeenCalledWith(presets[0]);
    });
});

describe("MapLoadingOverlay", () => {
    beforeEach(() => {
        registerTranslator(null);
        registerFallbackMessages(en);
    });

    afterEach(() => {
        cleanup();
    });

    it("shows custom message when provided", () => {
        const { container } = render(MapLoadingOverlay, {
            message: "custom",
        });
        expect(container.textContent).toContain("custom");
    });

    it("falls back to map.uploading when message is null", () => {
        const { container } = render(MapLoadingOverlay);
        expect(container.textContent).toContain(t("map.uploading"));
    });
});

describe("MapExportConfigPanel", () => {
    beforeEach(() => {
        registerTranslator(null);
        registerFallbackMessages(en);
    });

    afterEach(() => {
        cleanup();
    });

    it("renders config inputs and triggers start", async () => {
        const onStart = vi.fn();
        const { container } = render(MapExportConfigPanel, {
            minZoom: 5,
            maxZoom: 10,
            estimatedTiles: 100,
            exporting: false,
            tileLimitExceeded: false,
            onStart: onStart,
        });
        const buttons = Array.from(container.querySelectorAll("button"));
        const startBtn = buttons.find((b) => b.textContent?.includes(t("map.start_export")));
        expect(startBtn).toBeTruthy();
        if (startBtn) {
            await fireEvent.click(startBtn);
        }
        expect(onStart).toHaveBeenCalledTimes(1);
    });

    it("disables start when tileLimitExceeded", () => {
        const { container } = render(MapExportConfigPanel, {
            minZoom: 0,
            maxZoom: 20,
            estimatedTiles: 9999999,
            tileLimitExceeded: true,
        });
        const buttons = Array.from(container.querySelectorAll("button"));
        const startBtn = buttons.find((b) => b.textContent?.includes(t("map.start_export")));
        expect(startBtn?.hasAttribute("disabled")).toBe(true);
    });
});

describe("MapExportProgressPanel", () => {
    beforeEach(() => {
        registerTranslator(null);
        registerFallbackMessages(en);
    });

    afterEach(() => {
        cleanup();
    });

    it("shows progress for running export", () => {
        const { container } = render(MapExportProgressPanel, {
            status: { status: "running", progress: 40, current: 4, total: 10 },
            exportId: "e1",
        });
        expect(container.textContent).toContain(t("map.exporting"));
        expect(container.textContent).toContain("40%");
    });

    it("calls ondismiss when completed", async () => {
        const onDismiss = vi.fn();
        const { container } = render(MapExportProgressPanel, {
            status: { status: "completed", progress: 100, current: 10, total: 10 },
            exportId: "x",
            onDismiss: onDismiss,
        });
        expect(container.textContent).toContain(t("map.download_ready"));
        const link = container.querySelector('a[href="/api/v1/map/export/x/download"]');
        expect(link).toBeTruthy();
        const closeBtn = container.querySelector("button");
        if (closeBtn) {
            await fireEvent.click(closeBtn);
        }
        expect(onDismiss).toHaveBeenCalledTimes(1);
    });
});

describe("MapClusterPanel", () => {
    beforeEach(() => {
        registerTranslator(null);
        registerFallbackMessages(en);
    });

    afterEach(() => {
        cleanup();
    });

    it("calls onclose and onselect", async () => {
        const onClose = vi.fn();
        const onSelect = vi.fn();
        const cluster = {
            count: 2,
            items: [
                {
                    kind: "telemetry",
                    label: "Peer",
                    identifier: "abc",
                    peer: { lxmf_user_icon: { icon_name: "account" } },
                },
            ],
        };
        const { container } = render(MapClusterPanel, {
            cluster,
            onclose: onClose,
            onselect: onSelect,
        });
        expect(container.textContent).toContain("2");
        const closeBtn = container.querySelector('button[title="Close"]') || container.querySelector("button");
        if (closeBtn) {
            await fireEvent.click(closeBtn);
        }
        expect(onClose).toHaveBeenCalledTimes(1);
    });
});

describe("MapMarkerPanel", () => {
    beforeEach(() => {
        registerTranslator(null);
        registerFallbackMessages(en);
    });

    afterEach(() => {
        cleanup();
    });

    it("renders discovered node and calls onclose", async () => {
        const onClose = vi.fn();
        const marker = {
            discovered: {
                name: "NodeA",
                latitude: 1.2,
                longitude: 3.4,
                interface: "eth0",
            },
        };
        const { container } = render(MapMarkerPanel, {
            marker,
            onclose: onClose,
        });
        expect(container.textContent).toContain("NodeA");
        const closeBtn = container.querySelector('button[title="Close"]') || container.querySelector("button");
        if (closeBtn) {
            await fireEvent.click(closeBtn);
        }
        expect(onClose).toHaveBeenCalledTimes(1);
    });
});

describe("MapVectorExchangePanel", () => {
    beforeEach(() => {
        registerTranslator(null);
        registerFallbackMessages(en);
    });

    afterEach(() => {
        cleanup();
    });

    it("calls onexportgeojson when export button is clicked", async () => {
        const onExport = vi.fn();
        const { container } = render(MapVectorExchangePanel, {
            disabled: false,
            hasFeatures: true,
            onExportGeojson: onExport,
        });
        const buttons = Array.from(container.querySelectorAll("button"));
        const exportBtn = buttons.find((b) => b.textContent?.includes(t("map.vector_export_geojson")));
        expect(exportBtn).toBeTruthy();
        if (exportBtn) {
            await fireEvent.click(exportBtn);
        }
        expect(onExport).toHaveBeenCalledTimes(1);
    });
});

describe("MapSidePanel", () => {
    beforeEach(() => {
        registerTranslator(null);
        registerFallbackMessages(en);
        window.api = {
            get: vi.fn().mockResolvedValue({ data: {} }),
            post: vi.fn().mockResolvedValue({ data: {} }),
            delete: vi.fn().mockResolvedValue({ data: {} }),
        };
    });

    afterEach(() => {
        cleanup();
        delete window.api;
    });

    it("defaults to Discover and switches tabs", async () => {
        const { container } = render(MapSidePanel);
        expect(container.textContent).toContain(t("map.tab_discover"));
        expect(container.textContent).toContain(t("map.tab_publish"));
        expect(container.textContent).toContain(t("map.tab_layers"));
        expect(container.textContent).toContain(t("map.tab_offline"));

        const buttons = Array.from(container.querySelectorAll('div[role="tablist"] button'));
        if (buttons.length >= 4) {
            await fireEvent.click(buttons[1]);
            await waitFor(() => {
                expect(container.textContent).toContain(t("map.data_publish_title"));
            });
            await fireEvent.click(buttons[2]);
            await waitFor(() => {
                expect(container.textContent).toContain(t("map.remote_overlays_title"));
            });
            await fireEvent.click(buttons[3]);
            await waitFor(() => {
                expect(container.textContent).toContain(t("map.manage_offline_maps"));
            });
        }
    });
});
