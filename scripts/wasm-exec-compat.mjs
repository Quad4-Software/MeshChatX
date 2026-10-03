// SPDX-License-Identifier: 0BSD
// Verify that a copied wasm_exec.js provides every import field the wasm
// binary requires. A stale or cross-toolchain exec pair fails at instantiate
// time with "import object field X is not a Function" in the browser, so the
// pair is checked here at build time instead.
import fs from "node:fs";

function readU32(buf, pos) {
    let value = 0;
    let shift = 0;
    while (true) {
        const byte = buf[pos];
        pos += 1;
        value |= (byte & 0x7f) << shift;
        if (!(byte & 0x80)) {
            return [value, pos];
        }
        shift += 7;
    }
}

function readName(buf, pos) {
    const [len, start] = readU32(buf, pos);
    return [buf.subarray(start, start + len).toString("utf8"), start + len];
}

export function wasmImportFieldNames(wasmBuf) {
    // Section id 2 holds the import table. Entries are (module, field, kind).
    const fields = [];
    let pos = 8;
    while (pos < wasmBuf.length) {
        const sectionId = wasmBuf[pos];
        pos += 1;
        const [size, bodyStart] = readU32(wasmBuf, pos);
        pos = bodyStart;
        if (sectionId !== 2) {
            pos += size;
            continue;
        }
        const end = pos + size;
        const [count, countEnd] = readU32(wasmBuf, pos);
        pos = countEnd;
        for (let i = 0; i < count && pos < end; i += 1) {
            let name;
            [name, pos] = readName(wasmBuf, pos); // module
            [name, pos] = readName(wasmBuf, pos); // field
            const kind = wasmBuf[pos];
            pos += 1;
            if (kind === 0) {
                [, pos] = readU32(wasmBuf, pos); // func type index
            } else if (kind === 1) {
                pos += 1; // table reftype
                const flags = wasmBuf[pos];
                pos += 1;
                [, pos] = readU32(wasmBuf, pos); // min
                if (flags & 1) {
                    [, pos] = readU32(wasmBuf, pos); // max
                }
            } else if (kind === 2) {
                const flags = wasmBuf[pos];
                pos += 1;
                [, pos] = readU32(wasmBuf, pos);
                if (flags & 1) {
                    [, pos] = readU32(wasmBuf, pos);
                }
            } else if (kind === 3) {
                pos += 2; // global: valtype + mutability
            }
            if (name) {
                fields.push(name);
            }
        }
        break;
    }
    return fields;
}

export function assertWasmExecCompat(wasmPath, execPath, label) {
    const wasmBuf = fs.readFileSync(wasmPath);
    const execSrc = fs.readFileSync(execPath, "utf8");
    const missing = wasmImportFieldNames(wasmBuf).filter(
        (field) =>
            !execSrc.includes(`"${field}":`) &&
            // eslint-disable-next-line security/detect-non-literal-regexp -- field is escaped above
            !new RegExp(`\\b${field.replace(/[.*+?^${}()|[\]\\]/g, "\\$&")}\\s*:`).test(execSrc)
    );
    if (missing.length > 0) {
        console.error(
            `${label}: wasm_exec.js does not define imported fields: ${missing.join(", ")}. ` +
                "Rebuild wasm_exec.js from the toolchain that produced the wasm."
        );
        process.exit(1);
    }
}
