// Dense synthetic MVT fixture for the basemap profiler. Hand-rolled protobuf
// writer (MVT spec 2.1) so no extra dependency is needed. Tiles carry ~300
// features across the layer names the Protomaps style filters on, which is
// representative decode work for a mid-zoom urban tile. Geometry is synthetic:
// random walks and rects, not real geography.
const { buildArchive, zxyToTileId } = require("../../tests/e2e/pmtilesFixture");

function vint(v) {
    const o = [];
    let r = v;
    while (r > 0x7f) {
        o.push((r & 0x7f) | 0x80);
        r = Math.floor(r / 128);
    }
    o.push(r);
    return o;
}

function fieldVarint(f, v) {
    return [...vint((f << 3) | 0), ...vint(v)];
}

function fieldBytes(f, bytes) {
    return [...vint((f << 3) | 2), ...vint(bytes.length), ...bytes];
}

function fieldStr(f, s) {
    return fieldBytes(f, [...Buffer.from(s, "utf8")]);
}

function zig(v) {
    return v < 0 ? -v * 2 - 1 : v * 2;
}

function cmd(id, count) {
    return (id & 0x7) | (count << 3);
}

// Delta-encoded linestring geometry ints.
function lineGeom(pts) {
    const ints = [cmd(1, 1), zig(pts[0][0]), zig(pts[0][1]), cmd(2, pts.length - 1)];
    for (let i = 1; i < pts.length; i++) {
        ints.push(zig(pts[i][0] - pts[i - 1][0]), zig(pts[i][1] - pts[i - 1][1]));
    }
    return ints;
}

// Delta-encoded polygon (single ring) geometry ints.
function polyGeom(ring) {
    const ints = [cmd(1, 1), zig(ring[0][0]), zig(ring[0][1]), cmd(2, ring.length - 2)];
    for (let i = 1; i < ring.length - 1; i++) {
        ints.push(zig(ring[i][0] - ring[i - 1][0]), zig(ring[i][1] - ring[i - 1][1]));
    }
    ints.push(cmd(7, 1));
    return ints;
}

function rect(x, y, w, h) {
    return [
        [x, y],
        [x + w, y],
        [x + w, y + h],
        [x, y + h],
        [x, y],
    ];
}

function encodeValue(v) {
    if (typeof v === "string") return fieldStr(1, v);
    if (typeof v === "boolean") return fieldVarint(7, v ? 1 : 0);
    if (typeof v === "number") return fieldVarint(4, v);
    return fieldStr(1, String(v));
}

class LayerWriter {
    constructor(name, extent = 4096) {
        this.name = name;
        this.extent = extent;
        this.feats = [];
        this.keys = [];
        this.values = [];
        this.keyIdx = new Map();
        this.valIdx = new Map();
        this.nextId = 1;
    }

    valueIndex(v) {
        const key = typeof v + ":" + v;
        let idx = this.valIdx.get(key);
        if (idx === undefined) {
            idx = this.values.length;
            this.values.push(encodeValue(v));
            this.valIdx.set(key, idx);
        }
        return idx;
    }

    keyIndex(k) {
        let idx = this.keyIdx.get(k);
        if (idx === undefined) {
            idx = this.keys.length;
            this.keys.push(k);
            this.keyIdx.set(k, idx);
        }
        return idx;
    }

    add(type, geom, attrs) {
        const tags = [];
        for (const [k, v] of Object.entries(attrs || {})) {
            tags.push(this.keyIndex(k), this.valueIndex(v));
        }
        let body = fieldVarint(1, this.nextId++);
        if (tags.length) {
            body = body.concat(fieldBytes(2, tags.flatMap((t) => vint(t))));
        }
        body = body.concat(fieldVarint(3, type), fieldBytes(4, geom.flatMap((g) => vint(g))));
        this.feats.push(body);
    }

    encode() {
        let b = fieldVarint(15, 2).concat(fieldStr(1, this.name));
        for (const f of this.feats) b = b.concat(fieldBytes(2, f));
        for (const k of this.keys) b = b.concat(fieldStr(3, k));
        for (const v of this.values) b = b.concat(fieldBytes(4, v));
        b = b.concat(fieldVarint(5, this.extent));
        return b;
    }
}

// mulberry32: deterministic per-tile PRNG so archives are reproducible.
function mulberry32(seed) {
    let a = seed >>> 0;
    return function () {
        a |= 0;
        a = (a + 0x6d2b79f5) | 0;
        let t = Math.imul(a ^ (a >>> 15), 1 | a);
        t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t;
        return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
    };
}

const ROAD_KINDS = ["motorway", "trunk", "primary_road", "secondary_road", "tertiary_road", "residential", "service", "track", "path"];
const LANDUSE_KINDS = ["park", "forest", "residential", "commercial", "industrial", "farmland", "grass", "cemetery"];
const PLACE_KINDS = ["locality", "neighbourhood", "suburb", "town", "village"];
const POI_KINDS = ["cafe", "restaurant", "shop", "school", "hospital", "bus_stop", "parking"];
const CLIP = (v) => Math.max(0, Math.min(4095, Math.round(v)));

function buildTile(z, x, y) {
    const rand = mulberry32(((z + 1) * 2654435761 + x * 40503 + y * 7919) >>> 0);
    const ri = (n) => Math.floor(rand() * n);
    const pick = (arr) => arr[ri(arr.length)];

    const earth = new LayerWriter("earth");
    earth.add(3, polyGeom(rect(0, 0, 4096, 4096)), { kind: "earth" });

    const water = new LayerWriter("water");
    for (let i = 0; i < 3; i++) {
        water.add(3, polyGeom(rect(ri(3400), ri(3400), 400 + ri(600), 300 + ri(500))), { kind: "water" });
    }

    const landuse = new LayerWriter("landuse");
    for (let i = 0; i < 25; i++) {
        landuse.add(3, polyGeom(rect(ri(3800), ri(3800), 60 + ri(300), 60 + ri(300))), { kind: pick(LANDUSE_KINDS) });
    }

    const boundaries = new LayerWriter("boundaries");
    for (let i = 0; i < 4; i++) {
        const pts = [];
        let px = ri(4096);
        let py = ri(4096);
        for (let s = 0; s < 8; s++) {
            pts.push([CLIP(px), CLIP(py)]);
            px += 200 + ri(500);
            py += ri(400) - 200;
        }
        boundaries.add(2, lineGeom(pts), { kind: "admin_boundary", admin_level: 4 });
    }

    const roads = new LayerWriter("roads");
    for (let i = 0; i < 80; i++) {
        const segs = 3 + ri(6);
        const pts = [];
        let px = ri(4096);
        let py = ri(4096);
        for (let s = 0; s < segs; s++) {
            pts.push([CLIP(px), CLIP(py)]);
            px += ri(600) - 300;
            py += ri(600) - 300;
        }
        roads.add(2, lineGeom(pts), {
            kind: pick(ROAD_KINDS),
            ref: "R" + (1 + ri(999)),
            "name:en": "Road " + ri(10000),
        });
    }

    const buildings = new LayerWriter("buildings");
    for (let i = 0; i < 130; i++) {
        buildings.add(3, polyGeom(rect(ri(4000), ri(4000), 15 + ri(80), 15 + ri(80))), { kind: "building", kind_detail: "yes" });
    }

    const places = new LayerWriter("places");
    for (let i = 0; i < 18; i++) {
        places.add(1, [cmd(1, 1), zig(ri(4096)), zig(ri(4096))], {
            kind: pick(PLACE_KINDS),
            name: "Place " + ri(100000),
            "name:en": "Place " + ri(100000),
        });
    }

    const pois = new LayerWriter("pois");
    for (let i = 0; i < 25; i++) {
        pois.add(1, [cmd(1, 1), zig(ri(4096)), zig(ri(4096))], {
            kind: pick(POI_KINDS),
            name: "Poi " + ri(100000),
        });
    }

    const tile = [];
    for (const lw of [earth, water, landuse, boundaries, roads, buildings, places, pois]) {
        const enc = lw.encode();
        tile.push(...vint((3 << 3) | 2), ...vint(enc.length), ...enc);
    }
    return Buffer.from(tile);
}

function lonLatToTile(lon, lat, z) {
    const n = 1 << z;
    const x = Math.floor(((lon + 180) / 360) * n);
    const latRad = (lat * Math.PI) / 180;
    const y = Math.floor(((1 - Math.log(Math.tan(latRad) + 1 / Math.cos(latRad)) / Math.PI) / 2) * n);
    return { x, y };
}

const LAYER_FIELDS = {
    earth: { kind: "String" },
    water: { kind: "String" },
    landuse: { kind: "String" },
    boundaries: { kind: "String", admin_level: "Number" },
    roads: { kind: "String", ref: "String", "name:en": "String" },
    buildings: { kind: "String", kind_detail: "String" },
    places: { kind: "String", name: "String", "name:en": "String" },
    pois: { kind: "String", name: "String" },
};

/**
 * All tiles z0-z4 so world-view pans are covered anywhere, plus 13x13 windows
 * around lon 0 / lat 0 for z5-z8 (the profile zooms in toward the center).
 * ~800 tiles at ~15KB each makes a ~12MB uncompressed archive.
 */
function buildDenseArchive() {
    const tiles = [];
    const seen = new Set();
    const push = (z, x, y) => {
        const n = 1 << z;
        if (x < 0 || y < 0 || x >= n || y >= n) return;
        const key = `${z}/${x}/${y}`;
        if (seen.has(key)) return;
        seen.add(key);
        tiles.push({ z, x, y, data: buildTile(z, x, y) });
    };
    for (let z = 0; z <= 4; z++) {
        for (let x = 0; x < 1 << z; x++) {
            for (let y = 0; y < 1 << z; y++) {
                push(z, x, y);
            }
        }
    }
    const half = 6;
    for (let z = 5; z <= 8; z++) {
        const c = lonLatToTile(0, 0, z);
        for (let dx = -half; dx <= half; dx++) {
            for (let dy = -half; dy <= half; dy++) {
                push(z, c.x + dx, c.y + dy);
            }
        }
    }
    const metadata = {
        name: "synthetic-dense",
        format: "pbf",
        vector_layers: Object.entries(LAYER_FIELDS).map(([id, fields]) => ({ id, fields })),
    };
    return buildArchive(tiles, { metadata });
}

module.exports = { buildDenseArchive, buildTile, lonLatToTile };
