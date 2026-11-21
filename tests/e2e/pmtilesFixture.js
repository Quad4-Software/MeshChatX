// Minimal PMTiles v3 archive builder. Header layout matches
// node_modules/pmtiles/src/index.ts bytesToHeader. The root directory is
// varint encoded: entry count, tileId deltas, runLengths, lengths, offsets.
function writeVarint(out, v) {
    let remaining = v;
    while (remaining > 0x7f) {
        out.push((remaining & 0x7f) | 0x80);
        remaining = Math.floor(remaining / 128);
    }
    out.push(remaining);
}

// Hilbert tile id, same ordering pmtiles uses for clustered archives.
function zxyToTileId(z, x, y) {
    if (z === 0) return 0;
    const acc = ((1 << (z * 2)) - 1) / 3;
    const n = 1 << z;
    let tx = x;
    let ty = y;
    let d = 0;
    for (let s = n / 2; s > 0; s = s / 2) {
        const rx = tx & s ? 1 : 0;
        const ry = ty & s ? 1 : 0;
        d += s * s * ((3 * rx) ^ ry);
        if (ry === 0) {
            if (rx === 1) {
                tx = n - 1 - tx;
                ty = n - 1 - ty;
            }
            const t = tx;
            tx = ty;
            ty = t;
        }
    }
    return acc + d;
}

// One valid empty MVT layer per tile: field 3 (layers), len 11, name "a",
// version 2. Enough for ol/format/MVT to parse without features.
const TILE_BYTES = Buffer.from([0x1a, 0x0b, 0x0a, 0x01, 0x61, 0x12, 0x02, 0x32, 0x00, 0x78, 0x02]);

function buildArchive(tiles, opts = {}) {
    const entries = tiles
        .map((t) => ({ ...t, id: zxyToTileId(t.z, t.x, t.y), data: t.data || TILE_BYTES }))
        .sort((a, b) => a.id - b.id);
    const dir = [];
    writeVarint(dir, entries.length);
    let last = 0;
    for (const e of entries) {
        writeVarint(dir, e.id - last);
        last = e.id;
    }
    for (const e of entries) writeVarint(dir, 1); // runLength
    for (const e of entries) writeVarint(dir, e.data.length);
    let cursor = 0;
    for (const e of entries) {
        writeVarint(dir, e.offset === undefined ? cursor + 1 : e.offset + 1);
        cursor += e.data.length;
    }
    const dirLen = dir.length;
    const metadata = opts.metadata ? Buffer.from(JSON.stringify(opts.metadata), "utf8") : Buffer.alloc(0);
    const metadataOffset = metadata.length ? 127 + dirLen : 0;
    const tileDataOffset = 127 + dirLen + metadata.length;
    const tileDataLength = entries.reduce((a, e) => a + e.data.length, 0);
    const total = tileDataOffset + tileDataLength;
    const buf = Buffer.alloc(total);
    buf.write("PMTiles", 0, "ascii");
    buf.writeUInt8(3, 7);
    const u64 = (off, v) => buf.writeBigUInt64LE(BigInt(v), off);
    u64(8, 127); // rootDirectoryOffset
    u64(16, dirLen); // rootDirectoryLength
    u64(24, metadataOffset); // jsonMetadataOffset
    u64(32, metadata.length); // jsonMetadataLength
    u64(40, 0); // leafDirectoryOffset
    u64(48, 0); // leafDirectoryLength
    u64(56, tileDataOffset);
    u64(64, tileDataLength);
    u64(72, entries.length); // numAddressedTiles
    u64(80, entries.length); // numTileEntries
    u64(88, entries.length); // numTileContents
    buf.writeUInt8(1, 96); // clustered
    buf.writeUInt8(1, 97); // internalCompression: none
    buf.writeUInt8(1, 98); // tileCompression: none
    buf.writeUInt8(1, 99); // tileType: MVT
    buf.writeUInt8(0, 100); // minZoom
    buf.writeUInt8(15, 101); // maxZoom
    buf.writeInt32LE(-180 * 1e7, 102);
    buf.writeInt32LE(-85 * 1e7, 106);
    buf.writeInt32LE(180 * 1e7, 110);
    buf.writeInt32LE(85 * 1e7, 114);
    buf.writeUInt8(1, 118); // centerZoom
    buf.writeInt32LE(0, 119);
    buf.writeInt32LE(0, 123);
    Buffer.from(dir).copy(buf, 127);
    if (metadata.length) {
        metadata.copy(buf, metadataOffset);
    }
    let off = tileDataOffset;
    for (const e of entries) {
        e.data.copy(buf, off);
        off += e.data.length;
    }
    return buf;
}

module.exports = { buildArchive, zxyToTileId };
