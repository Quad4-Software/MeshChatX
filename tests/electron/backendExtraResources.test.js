// SPDX-License-Identifier: 0BSD

import { existsSync, readdirSync, readFileSync, statSync } from "node:fs";
import { join, relative, resolve } from "node:path";
import { minimatch } from "minimatch";
import { describe, expect, it } from "vitest";

const ROOT = resolve(import.meta.dirname, "../..");

function readRepo(relPath) {
    return readFileSync(resolve(ROOT, relPath), "utf8");
}

// Mirror of getFiles() in scripts/build-backend.js: plain readdir recursion,
// which DOES include dotfiles. The manifest hashes whatever this walk returns.
function walkFiles(dir, out = []) {
    for (const name of readdirSync(dir)) {
        const full = join(dir, name);
        let st;
        try {
            st = statSync(full);
        } catch {
            continue;
        }
        if (st.isDirectory()) {
            walkFiles(full, out);
        } else {
            out.push(full);
        }
    }
    return out;
}

// cx_Freeze copies the meshchatx package tree into lib/meshchatx, then
// build-backend.js strips frontend sources (except the repository index),
// lib/meshchatx/public, bytecode caches and pydoc/setuptools/numpy test dirs.
// Keep-marker dotfiles (.gitkeep) are packaged but never hashed into
// backend-manifest.json, so they are not part of the integrity surface.
function packagedBackendPaths() {
    const paths = [];
    const meshchatxDir = join(ROOT, "meshchatx");
    for (const abs of walkFiles(meshchatxDir)) {
        const rel = relative(meshchatxDir, abs).split("\\").join("/");
        if (rel.includes("__pycache__/") || /\.(pyc|pyo)$/.test(rel)) continue;
        if (rel.startsWith("public/")) continue;
        if (rel.startsWith("src/frontend/") && rel !== "src/frontend/public/repository-server-index.html") {
            continue;
        }
        if (rel.endsWith("/.gitkeep")) continue;
        paths.push(`lib/meshchatx/${rel}`);
    }
    // meshchatx/public is frontend build output; absent from a clean checkout.
    const publicDir = join(meshchatxDir, "public");
    if (existsSync(publicDir)) {
        for (const abs of walkFiles(publicDir)) {
            paths.push(`public/${relative(publicDir, abs).split("\\").join("/")}`);
        }
    }
    for (const name of ["CHANGELOG.md", "licenses_frontend.json", "licenses_backend.json", "THIRD_PARTY_NOTICES.txt"]) {
        paths.push(name);
    }
    for (const dir of ["logo", "bin"]) {
        const abs = join(ROOT, dir);
        if (existsSync(abs)) {
            for (const f of walkFiles(abs)) {
                paths.push(`${dir}/${relative(abs, f).split("\\").join("/")}`);
            }
        }
    }
    paths.push("backend-manifest.json");
    return paths;
}

// electron-builder FileMatcher semantics on the filter list: a file is
// packaged when it matches a positive glob and is not re-excluded by a
// negated glob. Real electron-builder evaluates filters with minimatch
// dot:true, so **/* already covers dotfiles; the explicit **/.gitkeep entry
// only documents intent for readers of package.json.
function filterVerdict(filter, relPath) {
    let included = false;
    let excluded = false;
    for (const raw of filter || []) {
        if (raw.startsWith("!")) {
            if (minimatch(relPath, raw.slice(1), { partial: false, dot: true })) excluded = true;
        } else if (minimatch(relPath, raw, { dot: true })) {
            included = true;
        }
    }
    return { included, excluded };
}

function backendResourceFilters() {
    const pkg = JSON.parse(readRepo("package.json"));
    const filters = [];
    for (const osKey of ["mac", "win", "linux"]) {
        const entries = pkg.build?.[osKey]?.extraResources || [];
        for (const entry of entries) {
            if (entry.to === "backend" && Array.isArray(entry.filter)) {
                filters.push({ os: osKey, filter: entry.filter });
            }
        }
    }
    return filters;
}

describe("backend extraResources packaging oracle", () => {
    it("every file the manifest can hash is either packaged or deliberately excluded", () => {
        const filters = backendResourceFilters();
        expect(filters.length).toBeGreaterThan(0);
        const paths = packagedBackendPaths();
        expect(paths.length).toBeGreaterThan(0);
        for (const { os, filter } of filters) {
            const orphaned = paths.filter((p) => {
                const v = filterVerdict(filter, p);
                return !v.included && !v.excluded;
            });
            expect(orphaned, `${os} backend filter silently drops packaged files`).toEqual([]);
        }
    });

    it("does not hash keep-marker placeholders into the integrity surface", () => {
        // .gitkeep files are packaging placeholders with no content value.
        // build-backend.js skips them when hashing backend-manifest.json so a
        // dropped dotfile can never report Missing and block onboarding.
        const markers = packagedBackendPaths().filter((p) => p.endsWith(".gitkeep"));
        expect(markers).toEqual([]);
    });

    it("still packages keep-marker dotfiles when present", () => {
        const filters = backendResourceFilters();
        for (const { os, filter } of filters) {
            const v = filterVerdict(filter, "lib/meshchatx/src/backend/data/map/.gitkeep");
            expect(v.included, `${os} must package .gitkeep`).toBe(true);
            expect(v.excluded, `${os} must not exclude .gitkeep`).toBe(false);
        }
    });
});
