// SPDX-License-Identifier: 0BSD

import { mount } from "@vue/test-utils";
import { describe, it, expect } from "vitest";
import MapDrawingToolbar from "@/components/map/internal/MapDrawingToolbar.vue";
import MapBearingInstructions from "@/components/map/internal/MapBearingInstructions.vue";
import MapSearchBar from "@/components/map/internal/MapSearchBar.vue";
import MapExportInstructions from "@/components/map/internal/MapExportInstructions.vue";
import MapLoadingOverlay from "@/components/map/internal/MapLoadingOverlay.vue";
import MapExportConfigPanel from "@/components/map/internal/MapExportConfigPanel.vue";
import MapExportProgressPanel from "@/components/map/internal/MapExportProgressPanel.vue";
import MapClusterPanel from "@/components/map/internal/MapClusterPanel.vue";
import MapMarkerPanel from "@/components/map/internal/MapMarkerPanel.vue";
import MapVectorExchangePanel from "@/components/map/internal/MapVectorExchangePanel.vue";

const DRAWING_TOOLS = [
    { type: "Select", icon: "cursor-default" },
    { type: "Point", icon: "map-marker-plus" },
    { type: "LineString", icon: "vector-line" },
    { type: "Polygon", icon: "vector-polygon" },
    { type: "Circle", icon: "circle-outline" },
    { type: "Export", icon: "crop-free" },
];

function t(key) {
    return key;
}

describe("MapDrawingToolbar", () => {
    it("emits toggle-bearing and bearing-from-here", async () => {
        const wrapper = mount(MapDrawingToolbar, {
            props: {
                tools: DRAWING_TOOLS,
                drawType: null,
                measuring: false,
                bearingMode: false,
                bearingFromGps: false,
                exportMode: false,
                selectedFeature: null,
            },
            global: { mocks: { $t: t } },
        });
        await wrapper.find('button[title="map.tool_bearing"]').trigger("click");
        expect(wrapper.emitted("toggle-bearing")).toHaveLength(1);
        await wrapper.find('button[title="map.tool_bearing_from_here"]').trigger("click");
        expect(wrapper.emitted("bearing-from-here")).toHaveLength(1);
    });

    it("applies bearing highlight classes when bearingMode is true", () => {
        const wrapper = mount(MapDrawingToolbar, {
            props: {
                tools: DRAWING_TOOLS,
                bearingMode: true,
                bearingFromGps: false,
                measuring: false,
                exportMode: false,
                selectedFeature: null,
            },
            global: { mocks: { $t: t } },
        });
        const bearingBtn = wrapper.find('button[title="map.tool_bearing"]');
        expect(bearingBtn.classes().some((c) => c.includes("teal"))).toBe(true);
    });

    it("emits toggle-measure and toggle-draw", async () => {
        const wrapper = mount(MapDrawingToolbar, {
            props: {
                tools: DRAWING_TOOLS,
                bearingMode: false,
                measuring: false,
                exportMode: false,
                selectedFeature: null,
            },
            global: { mocks: { $t: t } },
        });
        await wrapper.find('button[title="map.tool_measure"]').trigger("click");
        expect(wrapper.emitted("toggle-measure")).toHaveLength(1);
        await wrapper.find('button[title="map.tool_point"]').trigger("click");
        expect(wrapper.emitted("toggle-draw")).toEqual([["Point"]]);
    });
});

describe("MapBearingInstructions", () => {
    it("shows first-hint copy and emits use-my-location", async () => {
        const wrapper = mount(MapBearingInstructions, {
            props: { fromGpsActive: false, awaitingSecondTap: false },
            global: { mocks: { $t: t } },
        });
        expect(wrapper.text()).toContain("map.bearing_hint_first");
        await wrapper.find("button").trigger("click");
        expect(wrapper.emitted("use-my-location")).toHaveLength(1);
    });

    it("shows destination hint when fromGpsActive", () => {
        const wrapper = mount(MapBearingInstructions, {
            props: { fromGpsActive: true, awaitingSecondTap: true },
            global: { mocks: { $t: t } },
        });
        expect(wrapper.text()).toContain("map.bearing_hint_destination");
        expect(wrapper.find("button").exists()).toBe(false);
    });

    it("shows second-tap hint for two-point mode", () => {
        const wrapper = mount(MapBearingInstructions, {
            props: { fromGpsActive: false, awaitingSecondTap: true },
            global: { mocks: { $t: t } },
        });
        expect(wrapper.text()).toContain("map.bearing_hint_second");
    });
});

describe("MapSearchBar", () => {
    it("updates modelValue, search, clear, and select", async () => {
        const wrapper = mount(MapSearchBar, {
            props: {
                modelValue: "",
                results: [{ display_name: "Somewhere", type: "city" }],
                error: null,
                searching: false,
                showResults: true,
            },
            global: { mocks: { $t: t } },
        });
        const input = wrapper.find("input");
        await input.setValue("q");
        expect(wrapper.emitted("update:modelValue")).toEqual([["q"]]);
        await wrapper.setProps({ modelValue: "q" });
        await input.trigger("keydown.enter");
        expect(wrapper.emitted("search")).toHaveLength(1);
        await wrapper.findAll("button").at(0).trigger("click");
        expect(wrapper.emitted("clear")).toHaveLength(1);
    });

    it("renders error state when error is set", () => {
        const wrapper = mount(MapSearchBar, {
            props: {
                modelValue: "x",
                results: [],
                error: "map.search_error",
                searching: false,
                showResults: true,
            },
            global: { mocks: { $t: t } },
        });
        expect(wrapper.text()).toContain("map.search_error");
    });

    it("emits select when a result row is clicked", async () => {
        const row = { display_name: "A", type: "town" };
        const wrapper = mount(MapSearchBar, {
            props: {
                modelValue: "a",
                results: [row],
                showResults: true,
            },
            global: { mocks: { $t: t } },
        });
        await wrapper.find("button.w-full").trigger("click");
        expect(wrapper.emitted("select")).toEqual([[row]]);
    });
});

describe("MapExportInstructions", () => {
    it("emits select-preset for a preset button", async () => {
        const presets = [{ id: "europe" }];
        const wrapper = mount(MapExportInstructions, {
            props: { presets },
            global: { mocks: { $t: t } },
        });
        await wrapper.find("button").trigger("click");
        expect(wrapper.emitted("select-preset")).toEqual([[presets[0]]]);
    });
});

describe("MapLoadingOverlay", () => {
    it("shows custom message when provided", () => {
        const wrapper = mount(MapLoadingOverlay, {
            props: { message: "custom" },
            global: { mocks: { $t: t } },
        });
        expect(wrapper.text()).toContain("custom");
    });

    it("falls back to map.uploading when message is null", () => {
        const wrapper = mount(MapLoadingOverlay, {
            global: { mocks: { $t: t } },
        });
        expect(wrapper.text()).toContain("map.uploading");
    });
});

describe("MapExportConfigPanel", () => {
    it("emits update:minZoom and start", async () => {
        const wrapper = mount(MapExportConfigPanel, {
            props: { minZoom: 5, maxZoom: 10, estimatedTiles: 100, exporting: false, tileLimitExceeded: false },
            global: { mocks: { $t: t } },
        });
        const inputs = wrapper.findAll('input[type="number"]');
        await inputs.at(0).setValue(6);
        expect(wrapper.emitted("update:minZoom")).toEqual([[6]]);
        await wrapper
            .findAll("button")
            .filter((b) => b.text().includes("map.start_export"))
            .at(0)
            .trigger("click");
        expect(wrapper.emitted("start")).toHaveLength(1);
    });

    it("disables start when tileLimitExceeded", () => {
        const wrapper = mount(MapExportConfigPanel, {
            props: {
                minZoom: 0,
                maxZoom: 20,
                estimatedTiles: 9999999,
                tileLimitExceeded: true,
            },
            global: { mocks: { $t: t } },
        });
        const startBtn = wrapper
            .findAll("button")
            .filter((b) => b.text().includes("map.start_export"))
            .at(0);
        expect(startBtn.attributes("disabled")).toBeDefined();
    });
});

describe("MapExportProgressPanel", () => {
    it("shows progress for running export", () => {
        const wrapper = mount(MapExportProgressPanel, {
            props: {
                status: { status: "running", progress: 40, current: 4, total: 10 },
                exportId: "e1",
            },
            global: { mocks: { $t: t } },
        });
        expect(wrapper.text()).toContain("map.exporting");
        expect(wrapper.text()).toContain("40%");
    });

    it("emits dismiss when completed", async () => {
        const wrapper = mount(MapExportProgressPanel, {
            props: {
                status: { status: "completed", progress: 100, current: 10, total: 10 },
                exportId: "x",
            },
            global: { mocks: { $t: t } },
        });
        expect(wrapper.text()).toContain("map.download_ready");
        const link = wrapper.find('a[href="/api/v1/map/export/x/download"]');
        expect(link.exists()).toBe(true);
        await wrapper.find("button.text-gray-400").trigger("click");
        expect(wrapper.emitted("dismiss")).toHaveLength(1);
    });

    it("emits cancel while running", async () => {
        const wrapper = mount(MapExportProgressPanel, {
            props: {
                status: { status: "running", progress: 1, current: 1, total: 99 },
            },
            global: { mocks: { $t: t } },
        });
        await wrapper.find("button.text-red-500").trigger("click");
        expect(wrapper.emitted("cancel")).toHaveLength(1);
    });
});

describe("MapClusterPanel", () => {
    it("emits close and select", async () => {
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
        const wrapper = mount(MapClusterPanel, {
            props: { cluster },
            global: { mocks: { $t: t } },
        });
        expect(wrapper.text()).toContain("2");
        await wrapper.find('button[title="Close"]').trigger("click");
        expect(wrapper.emitted("close")).toHaveLength(1);
        await wrapper.find("button.w-full").trigger("click");
        expect(wrapper.emitted("select")).toEqual([[cluster.items[0]]]);
    });
});

describe("MapMarkerPanel", () => {
    it("renders discovered node and emits close", async () => {
        const marker = {
            discovered: {
                name: "NodeA",
                latitude: 1.2,
                longitude: 3.4,
                interface: "eth0",
            },
        };
        const wrapper = mount(MapMarkerPanel, {
            props: { marker },
            global: {
                mocks: { $t: t },
                stubs: { MiniChat: { template: "<div class='mini-chat-stub'></div>" } },
            },
        });
        expect(wrapper.text()).toContain("NodeA");
        expect(wrapper.text()).toContain("1.200000");
        await wrapper.find("button.text-gray-500").trigger("click");
        expect(wrapper.emitted("close")).toHaveLength(1);
    });
});

describe("MapVectorExchangePanel", () => {
    it("emits export-geojson when export button is clicked", async () => {
        const wrapper = mount(MapVectorExchangePanel, {
            props: { disabled: false, hasFeatures: true },
            global: { mocks: { $t: t } },
        });
        const exportBtn = wrapper
            .findAll("button")
            .filter((b) => b.text().includes("map.vector_export_geojson"))
            .at(0);
        await exportBtn.trigger("click");
        expect(wrapper.emitted("export-geojson")).toHaveLength(1);
    });

    it("toggle merge checkbox changes mergeImport", async () => {
        const wrapper = mount(MapVectorExchangePanel, {
            props: { hasFeatures: false },
            global: { mocks: { $t: t } },
        });
        expect(wrapper.vm.mergeImport).toBe(true);
        const cb = wrapper.find('input[type="checkbox"]');
        await cb.setValue(false);
        expect(wrapper.vm.mergeImport).toBe(false);
    });
});
