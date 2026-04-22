import { describe, it, expect } from "vitest";
import { extentDiagonal, buildClusterItems, getFeatureCoord } from "@/components/map/internal/clusterUtils.js";
import { getDiscoveredIconName } from "@/components/map/internal/discoveredIcons.js";
import { dedupeDiscoveredMapNodes, dedupeTelemetryMarkersForMap } from "@/components/map/internal/mapDedupe.js";

function feature(props, coord) {
    const geom = coord ? { getCoordinates: () => coord } : null;
    return {
        get: (key) => props[key],
        set: (key, value) => {
            props[key] = value;
        },
        getGeometry: () => geom,
    };
}

describe("clusterUtils.extentDiagonal", () => {
    it("returns 0 for invalid extents", () => {
        expect(extentDiagonal(null)).toBe(0);
        expect(extentDiagonal(undefined)).toBe(0);
        expect(extentDiagonal([])).toBe(0);
        expect(extentDiagonal([1, 2, 3])).toBe(0);
        expect(extentDiagonal([Infinity, Infinity, -Infinity, -Infinity])).toBe(0);
    });

    it("returns the diagonal length for valid extents", () => {
        expect(extentDiagonal([0, 0, 3, 4])).toBeCloseTo(5);
        expect(extentDiagonal([10, 10, 10, 10])).toBe(0);
        expect(extentDiagonal([-2, -2, 2, 2])).toBeCloseTo(Math.sqrt(32));
    });
});

describe("clusterUtils.getFeatureCoord", () => {
    it("returns the originalCoord when set", () => {
        const f = feature({ originalCoord: [11, 22] }, [99, 99]);
        expect(getFeatureCoord(f)).toEqual([11, 22]);
    });

    it("falls back to the geometry's coordinates", () => {
        const f = feature({}, [33, 44]);
        expect(getFeatureCoord(f)).toEqual([33, 44]);
    });

    it("returns null for missing feature or geometry", () => {
        expect(getFeatureCoord(null)).toBeNull();
        expect(getFeatureCoord(feature({}, null))).toBeNull();
    });
});

describe("clusterUtils.buildClusterItems", () => {
    it("returns an empty array for missing features or empty clusters", () => {
        expect(buildClusterItems(null)).toEqual([]);
        expect(buildClusterItems(feature({ clusterItems: [] }, [0, 0]))).toEqual([]);
    });

    it("normalises telemetry, discovered, and unknown items", () => {
        const items = [
            feature(
                {
                    telemetry: { destination_hash: "deadbeefcafe1234" },
                    peer: { display_name: "Alice" },
                    originalCoord: [10, 20],
                },
                [10, 20]
            ),
            feature(
                {
                    discovered: { name: "RNode", interface: "AutoIf", type: "AutoInterface" },
                    originalCoord: [11, 21],
                },
                [11, 21]
            ),
            feature({ originalCoord: [12, 22] }, [12, 22]),
        ];
        const cluster = feature({ clusterItems: items }, [11, 21]);
        const out = buildClusterItems(cluster);
        expect(out).toHaveLength(3);
        expect(out[0]).toMatchObject({ kind: "telemetry", label: "Alice", identifier: "deadbeefcafe1234" });
        expect(out[1]).toMatchObject({ kind: "discovered", label: "RNode", identifier: "AutoIf" });
        expect(out[2]).toMatchObject({ kind: "unknown", label: "Unknown" });
    });

    it("falls back to a truncated destination hash when no peer name is available", () => {
        const items = [feature({ telemetry: { destination_hash: "abcdef0123456789" } }, [0, 0])];
        const cluster = feature({ clusterItems: items }, [0, 0]);
        expect(buildClusterItems(cluster)[0].label).toBe("abcdef01");
    });

    it("ignores nullish entries inside the cluster", () => {
        const cluster = feature(
            { clusterItems: [null, feature({ telemetry: { destination_hash: "x" } }, [0, 0])] },
            [0, 0]
        );
        expect(buildClusterItems(cluster)).toHaveLength(1);
    });
});

describe("discoveredIcons.getDiscoveredIconName", () => {
    it("falls back to a generic icon for null/empty input", () => {
        expect(getDiscoveredIconName(null)).toBe("map-marker-radius");
        expect(getDiscoveredIconName(undefined)).toBe("map-marker-radius");
        expect(getDiscoveredIconName({})).toBe("server-network");
    });

    it("maps known interface types to their MDI names", () => {
        expect(getDiscoveredIconName({ type: "AutoInterface" })).toBe("home-automation");
        expect(getDiscoveredIconName({ type: "RNodeMultiInterface" })).toBe("access-point-network");
        expect(getDiscoveredIconName({ type: "TCPClientInterface" })).toBe("lan-connect");
        expect(getDiscoveredIconName({ type: "BackboneInterface" })).toBe("lan-connect");
        expect(getDiscoveredIconName({ type: "TCPServerInterface" })).toBe("lan");
        expect(getDiscoveredIconName({ type: "UDPInterface" })).toBe("wan");
        expect(getDiscoveredIconName({ type: "SerialInterface" })).toBe("usb-port");
        expect(getDiscoveredIconName({ type: "KISSInterface" })).toBe("antenna");
        expect(getDiscoveredIconName({ type: "AX25KISSInterface" })).toBe("antenna");
        expect(getDiscoveredIconName({ type: "I2PInterface" })).toBe("eye");
        expect(getDiscoveredIconName({ type: "PipeInterface" })).toBe("pipe");
    });

    it("differentiates serial vs TCP for RNodeInterface based on port", () => {
        expect(getDiscoveredIconName({ type: "RNodeInterface" })).toBe("radio-tower");
        expect(getDiscoveredIconName({ type: "RNodeInterface", port: "/dev/ttyUSB0" })).toBe("radio-tower");
        expect(getDiscoveredIconName({ type: "RNodeInterface", port: "tcp://10.0.0.1:4242" })).toBe("lan-connect");
    });

    it("uses interface_type as a fallback when type is missing", () => {
        expect(getDiscoveredIconName({ interface_type: "AutoInterface" })).toBe("home-automation");
    });
});

describe("mapDedupe.dedupeDiscoveredMapNodes", () => {
    it("returns an empty array for invalid input", () => {
        expect(dedupeDiscoveredMapNodes(null)).toEqual([]);
        expect(dedupeDiscoveredMapNodes(undefined)).toEqual([]);
        expect(dedupeDiscoveredMapNodes([])).toEqual([]);
    });

    it("preserves nameless entries even at the same location", () => {
        const nodes = [
            { name: "", latitude: 1, longitude: 1, last_heard: 100 },
            { name: "", latitude: 1, longitude: 1, last_heard: 200 },
        ];
        expect(dedupeDiscoveredMapNodes(nodes)).toHaveLength(2);
    });

    it("collapses same-name nearby duplicates and keeps the freshest", () => {
        const nodes = [
            { name: "Alpha", latitude: 1, longitude: 1, last_heard: 100 },
            { name: "alpha", latitude: 1.001, longitude: 1.001, last_heard: 500 },
            { name: "Beta", latitude: 5, longitude: 5, last_heard: 300 },
        ];
        const out = dedupeDiscoveredMapNodes(nodes);
        expect(out).toHaveLength(2);
        const alpha = out.find((n) => n.name.toLowerCase() === "alpha");
        expect(alpha.last_heard).toBe(500);
    });

    it("keeps same-name nodes that are far apart", () => {
        const nodes = [
            { name: "Hub", latitude: 0, longitude: 0, last_heard: 100 },
            { name: "Hub", latitude: 10, longitude: 10, last_heard: 200 },
        ];
        expect(dedupeDiscoveredMapNodes(nodes)).toHaveLength(2);
    });
});

describe("mapDedupe.dedupeTelemetryMarkersForMap", () => {
    const peers = {
        AAA: { display_name: "Alice" },
        BBB: { display_name: "Alice" },
        CCC: { display_name: "Bob" },
    };

    function entry(hash, lat, lon, ts) {
        return {
            destination_hash: hash,
            updated_at: new Date(ts * 1000).toISOString(),
            telemetry: { location: { latitude: lat, longitude: lon } },
        };
    }

    it("returns an empty array for invalid input", () => {
        expect(dedupeTelemetryMarkersForMap(null)).toEqual([]);
        expect(dedupeTelemetryMarkersForMap(undefined)).toEqual([]);
        expect(dedupeTelemetryMarkersForMap([])).toEqual([]);
    });

    it("collapses peers with the same display name in the same place", () => {
        const list = [entry("AAA", 1, 1, 100), entry("BBB", 1.001, 1.001, 200), entry("CCC", 1, 1, 50)];
        const out = dedupeTelemetryMarkersForMap(list, peers);
        expect(out).toHaveLength(2);
        expect(out[0].destination_hash).toBe("BBB");
    });

    it("keeps same-name peers that are far apart", () => {
        const list = [entry("AAA", 0, 0, 100), entry("BBB", 10, 10, 200)];
        expect(dedupeTelemetryMarkersForMap(list, peers)).toHaveLength(2);
    });

    it("falls back to a truncated hash when no peer name is registered", () => {
        const list = [entry("ffffff0011", 0, 0, 100), entry("ffffff0011", 0.001, 0.001, 200)];
        const out = dedupeTelemetryMarkersForMap(list, {});
        expect(out).toHaveLength(1);
        expect(out[0].updated_at).toBe(list[1].updated_at);
    });

    it("preserves entries whose location is missing from comparison", () => {
        const list = [entry("AAA", 0, 0, 100), { destination_hash: "AAA", updated_at: list1Time(200) }];
        const out = dedupeTelemetryMarkersForMap(list, peers);
        expect(out).toHaveLength(2);
    });
});

function list1Time(ts) {
    return new Date(ts * 1000).toISOString();
}
