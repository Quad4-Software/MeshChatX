#!/usr/bin/env node
/**
 * Ensure the packaged starter world MBTiles exists under backend/data/map/.
 * Prefers a pinned download when STARTER_MBTILES_URL is set; otherwise generates
 * a low-zoom placeholder via Python (stdlib, no clearnet required).
 */
import fs from "fs";
import path from "path";
import crypto from "crypto";
import { spawnSync } from "child_process";
import { fileURLToPath } from "url";

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const REPO_ROOT = path.resolve(__dirname, "..");
const OUT_DIR = path.join(REPO_ROOT, "meshchatx", "src", "backend", "data", "map");
const OUT_FILE = path.join(OUT_DIR, "starter_world.mbtiles");

function sha256File(filePath) {
    const hash = crypto.createHash("sha256");
    hash.update(fs.readFileSync(filePath));
    return hash.digest("hex");
}

function generateWithPython() {
    const py = spawnSync(
        "uv",
        [
            "run",
            "python",
            "-c",
            "from meshchatx.src.backend.map_starter_mbtiles import ensure_bundled_starter_file; print(ensure_bundled_starter_file())",
        ],
        { cwd: REPO_ROOT, encoding: "utf8" }
    );
    if (py.status !== 0) {
        const fallback = spawnSync(
            "python3",
            [
                "-c",
                "from meshchatx.src.backend.map_starter_mbtiles import ensure_bundled_starter_file; print(ensure_bundled_starter_file())",
            ],
            { cwd: REPO_ROOT, encoding: "utf8", env: { ...process.env, PYTHONPATH: REPO_ROOT } }
        );
        if (fallback.status !== 0) {
            console.error(py.stderr || py.stdout || fallback.stderr || fallback.stdout || "starter generate failed");
            process.exit(1);
        }
        console.log(`fetch-starter-mbtiles: generated ${fallback.stdout.trim()}`);
        return;
    }
    console.log(`fetch-starter-mbtiles: generated ${py.stdout.trim()}`);
}

async function downloadPinned(url, expectedSha256) {
    fs.mkdirSync(OUT_DIR, { recursive: true });
    const res = await fetch(url);
    if (!res.ok) {
        throw new Error(`download failed HTTP ${res.status}`);
    }
    const buf = Buffer.from(await res.arrayBuffer());
    if (expectedSha256) {
        const actual = crypto.createHash("sha256").update(buf).digest("hex");
        if (actual !== expectedSha256) {
            throw new Error(`sha256 mismatch: got ${actual} want ${expectedSha256}`);
        }
    }
    fs.writeFileSync(OUT_FILE, buf);
    console.log(`fetch-starter-mbtiles: downloaded ${OUT_FILE} (${buf.length} bytes, sha256=${sha256File(OUT_FILE)})`);
}

async function main() {
    if (process.env.STARTER_MBTILES_SKIP === "1") {
        console.log("fetch-starter-mbtiles: STARTER_MBTILES_SKIP=1, skipping.");
        process.exit(0);
    }

    const url = process.env.STARTER_MBTILES_URL || "";
    const expected = process.env.STARTER_MBTILES_SHA256 || "";

    if (url) {
        try {
            await downloadPinned(url, expected || null);
            process.exit(0);
        } catch (e) {
            console.warn(`fetch-starter-mbtiles: download failed (${e.message}), generating placeholder.`);
        }
    }

    if (process.env.MESHCHATX_OFFLINE_BUILD === "1" && fs.existsSync(OUT_FILE)) {
        console.log("fetch-starter-mbtiles: offline build, using existing starter.");
        process.exit(0);
    }

    generateWithPython();
}

main().catch((e) => {
    console.error(e);
    process.exit(1);
});
