import { describe, expect, it } from "vitest";
import {
    batteryHistoryFromTelemetryItems,
    buildTelemetryBatteryChartSpec,
    interpolateBatteryByTime,
} from "../../meshchatx/src/frontend/js/telemetryBatteryChartSpec.js";

describe("telemetryBatteryChartSpec", () => {
    it("buildTelemetryBatteryChartSpec returns null for short history", () => {
        expect(buildTelemetryBatteryChartSpec([{ x: 1, y: 50 }], "a")).toBeNull();
        expect(buildTelemetryBatteryChartSpec([], "a")).toBeNull();
    });

    it("buildTelemetryBatteryChartSpec returns paths and stable ids", () => {
        const spec = buildTelemetryBatteryChartSpec(
            [
                { x: 1000, y: 80 },
                { x: 2000, y: 60 },
                { x: 3000, y: 90 },
            ],
            "ab12"
        );
        expect(spec).not.toBeNull();
        expect(spec.linePath).toMatch(/^M /);
        expect(spec.areaPath).toContain("Z");
        expect(spec.gradientId).toBe("tb-fill-ab12");
        expect(spec.strokeGradientId).toBe("tb-stroke-ab12");
        expect(spec.first.x).toBeLessThan(spec.last.x);
        expect(spec.layout.minX).toBe(1000);
        expect(spec.layout.maxX).toBe(3000);
        expect(spec.viewBox).toBe("0 0 100 46");
    });

    it("interpolateBatteryByTime clamps and interpolates", () => {
        const h = [
            { x: 0, y: 0 },
            { x: 100, y: 100 },
        ];
        expect(interpolateBatteryByTime(h, 50).y).toBe(50);
        expect(interpolateBatteryByTime(h, -1).y).toBe(0);
        expect(interpolateBatteryByTime(h, 200).y).toBe(100);
    });

    it("batteryHistoryFromTelemetryItems sorts by timestamp", () => {
        const items = [
            {
                lxmf_message: {
                    timestamp: 300,
                    fields: { telemetry: { battery: { charge_percent: 10 } } },
                },
            },
            {
                lxmf_message: {
                    timestamp: 100,
                    fields: { telemetry: { battery: { charge_percent: 50 } } },
                },
            },
        ];
        const h = batteryHistoryFromTelemetryItems(items);
        expect(h.map((p) => p.x)).toEqual([100, 300]);
        expect(h.map((p) => p.y)).toEqual([50, 10]);
    });
});
