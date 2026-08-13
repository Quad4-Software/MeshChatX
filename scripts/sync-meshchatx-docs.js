/**
 * Copy docs/ tree into meshchatx/src/frontend/public/meshchatx-docs/ for in-app serving.
 * Source of truth: docs/ at repo root.
 * Agent guidance lives under .agents/ at repo root, not under docs/.
 */

const fs = require("fs");
const path = require("path");

const root = path.resolve(__dirname, "..");
const srcDir = path.join(root, "docs");
const destDir = path.join(root, "meshchatx", "src", "frontend", "public", "meshchatx-docs");

const COPY_EXTENSIONS = new Set([".md", ".txt", ".json"]);
const SKIP_TOP_LEVEL_DIRS = new Set();

function walkSync(dir, callback, relBase = "") {
    for (const entry of fs.readdirSync(dir, { withFileTypes: true })) {
        const rel = relBase ? path.join(relBase, entry.name) : entry.name;
        if (!relBase && entry.isDirectory() && SKIP_TOP_LEVEL_DIRS.has(entry.name)) {
            continue;
        }
        const fullPath = path.join(dir, entry.name);
        if (entry.isDirectory()) {
            walkSync(fullPath, callback, rel);
        } else {
            callback(fullPath);
        }
    }
}

function relativeFromDocs(filePath) {
    return path.relative(srcDir, filePath);
}

if (!fs.existsSync(srcDir)) {
    console.error(`Missing docs directory: ${srcDir}`);
    process.exit(1);
}

fs.mkdirSync(destDir, { recursive: true });

const sourceRelPaths = new Set();

walkSync(srcDir, (filePath) => {
    const ext = path.extname(filePath);
    const base = path.basename(filePath);
    if (base !== "manifest.json" && !COPY_EXTENSIONS.has(ext)) {
        return;
    }
    const rel = relativeFromDocs(filePath);
    sourceRelPaths.add(rel);
    const dest = path.join(destDir, rel);
    fs.mkdirSync(path.dirname(dest), { recursive: true });
    const content = fs.readFileSync(filePath);
    const prev = fs.existsSync(dest) ? fs.readFileSync(dest) : null;
    if (!prev || !prev.equals(content)) {
        fs.writeFileSync(dest, content);
        console.log(`Synced meshchatx-docs/${rel.replace(/\\/g, "/")}`);
    }
});

function walkDest(dir, relBase = "") {
    for (const entry of fs.readdirSync(dir, { withFileTypes: true })) {
        const rel = relBase ? path.join(relBase, entry.name) : entry.name;
        const full = path.join(dir, entry.name);
        if (entry.isDirectory()) {
            walkDest(full, rel);
            continue;
        }
        const ext = path.extname(entry.name);
        const base = entry.name;
        if (base !== "manifest.json" && !COPY_EXTENSIONS.has(ext)) {
            continue;
        }
        if (!sourceRelPaths.has(rel)) {
            fs.unlinkSync(full);
            console.log(`Removed stale meshchatx-docs/${rel.replace(/\\/g, "/")}`);
        }
    }
}

walkDest(destDir);
