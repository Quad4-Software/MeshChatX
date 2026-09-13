// SPDX-License-Identifier: 0BSD

import { describe, it, expect } from "vitest";
import { extentDiagonal, buildClusterItems } from "@/features/map/lib/clusterUtils.js";
import { MapMarkerManager } from "@/features/map/lib/mapMarkerManager.js";

describe("MapPage cluster behaviour and helpers", () => {
    describe("extentDiagonal", () => {
        it("returns 0 for empty/invalid extents", () => {
            expect(extentDiagonal(null)).toBe(0);
            expect(extentDiagonal([])).toBe(0);
            expect(extentDiagonal([Infinity, Infinity, -Infinity, -Infinity])).toBe(0);
        });

        it("computes the diagonal length for a normal extent", () => {
            expect(extentDiagonal([0, 0, 3, 4])).toBeCloseTo(5);
            expect(extentDiagonal([10, 10, 10, 10])).toBe(0);
        });
    });

    describe("buildClusterItems", () => {
        it("extracts and normalizes cluster items from a feature", () => {
            const subFeature1 = {
                get: (k) => {
                    if (k === "telemetry") return { destination_hash: "abcd" };
                    if (k === "peer") return { display_name: "Alice" };
                    if (k === "originalCoord") return [10, 20];
                    return null;
                },
                getGeometry: () => ({ getCoordinates: () => [10, 20] }),
            };
            const mockClusterFeature = {
                get: (k) => {
                    if (k === "clusterItems") return [subFeature1];
                    return null;
                },
            };
            const items = buildClusterItems(mockClusterFeature);
            expect(items.length).toBe(1);
            expect(items[0].kind).toBe("telemetry");
            expect(items[0].label).toBe("Alice");
        });
    });

    describe("MapMarkerManager", () => {
        it("updates data and clears/adds markers to vector source", () => {
            const features = [];
            const mockSource = {
                clear: () => {
                    features.length = 0;
                },
                addFeature: (f) => {
                    features.push(f);
                },
            };
            const manager = new MapMarkerManager({ markerSource: mockSource });
            const announces = [
                {
                    destination_hash: "a".repeat(32),
                    display_name: "TestNode",
                    latitude: 51.5,
                    longitude: -0.1,
                    aspect: "node",
                    hops: 1,
                },
            ];
            manager.updateData(announces, [], []);
            expect(features.length).toBe(1);
        });
    });
});
