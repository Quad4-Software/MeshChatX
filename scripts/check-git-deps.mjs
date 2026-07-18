#!/usr/bin/env node
// SPDX-License-Identifier: 0BSD
/**
 * Fail when git-hosted deps or remote download URLs drift from scripts/deps-allowlist.json.
 * Covers package.json github:/git+ specs, pnpm-lock pins, flatpak git sources, and Micron WASM URLs.
 */
import fs from "node:fs";
import path from "node:path";
import process from "node:process";
import { fileURLToPath } from "node:url";
import { MICRON_PARSER_GO_RELEASE_TAG } from "./micron-parser-go-version.mjs";

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const ROOT = path.resolve(__dirname, "..");
const ALLOWLIST_PATH = path.join(ROOT, "scripts", "deps-allowlist.json");
const PACKAGE_JSON_PATH = path.join(ROOT, "package.json");
const LOCKFILE_PATH = path.join(ROOT, "pnpm-lock.yaml");
const FETCH_MICRON_WASM_PATH = path.join(ROOT, "scripts", "fetch-micron-wasm.mjs");

const GIT_SPEC_RE = /^(github:|git\+|git:)/i;
const FULL_COMMIT_RE = /^[0-9a-f]{40}$/i;
const CODELOAD_COMMIT_RE = /codeload\.github\.com\/[^/]+\/[^/]+\/tar\.gz\/([0-9a-f]{40})/i;

/**
 * Glob-style match with only "*" wildcards (no RegExp constructor).
 *
 * @param {string} pattern
 * @param {string} value
 */
function matchPattern(pattern, value) {
    const parts = pattern.split("*");
    if (parts.length === 1) {
        return pattern === value;
    }
    if (!value.startsWith(parts[0])) {
        return false;
    }
    let cursor = parts[0].length;
    for (let i = 1; i < parts.length; i++) {
        const part = parts[i];
        if (part.length === 0) {
            if (i === parts.length - 1) {
                return true;
            }
            continue;
        }
        const found = value.indexOf(part, cursor);
        if (found < 0) {
            return false;
        }
        cursor = found + part.length;
    }
    return cursor === value.length || pattern.endsWith("*");
}

/**
 * @param {string} spec
 */
function splitGitSpec(spec) {
    const hashIndex = spec.indexOf("#");
    if (hashIndex < 0) {
        return { base: spec, ref: null };
    }
    return {
        base: spec.slice(0, hashIndex),
        ref: spec.slice(hashIndex + 1),
    };
}

/**
 * Escape is unnecessary here: package names are matched as exact lockfile headers.
 *
 * @param {string} lockText
 * @param {string} name
 */
function lockfileCommitForPackage(lockText, name) {
    const header = `    ${name}:`;
    const lines = lockText.split(/\r?\n/);
    let inPackage = false;
    for (const line of lines) {
        if (line === header) {
            inPackage = true;
            continue;
        }
        if (inPackage) {
            if (/^\s{4}\S/.test(line) && !line.startsWith(header)) {
                break;
            }
            const versionMatch = line.match(/^\s+version:\s+(\S+)\s*$/);
            if (versionMatch) {
                const codeload = versionMatch[1].match(CODELOAD_COMMIT_RE);
                if (codeload) {
                    return codeload[1].toLowerCase();
                }
            }
            const tarballMarker = "tarball: ";
            const tarballAt = line.indexOf(tarballMarker);
            if (tarballAt >= 0) {
                const rest = line.slice(tarballAt + tarballMarker.length);
                const codeload = rest.match(CODELOAD_COMMIT_RE);
                if (codeload) {
                    return codeload[1].toLowerCase();
                }
            }
        }
    }

    const marker = `${name}@https://codeload.github.com/`;
    const markerAt = lockText.indexOf(marker);
    if (markerAt >= 0) {
        const slice = lockText.slice(markerAt, markerAt + marker.length + 200);
        const codeload = slice.match(CODELOAD_COMMIT_RE);
        if (codeload) {
            return codeload[1].toLowerCase();
        }
    }
    return null;
}

/**
 * @param {string} text
 * @param {string} constName
 */
function readExportedStringConst(text, constName) {
    const needle = `const ${constName} = `;
    const idx = text.indexOf(needle);
    if (idx < 0) {
        return null;
    }
    const after = text.slice(idx + needle.length).trimStart();
    const quote = after[0];
    if (quote !== '"' && quote !== "'" && quote !== "`") {
        return null;
    }
    const end = after.indexOf(quote, 1);
    if (end < 0) {
        return null;
    }
    return after.slice(1, end);
}

function main() {
    /** @type {string[]} */
    const errors = [];

    if (!fs.existsSync(ALLOWLIST_PATH)) {
        console.error(`check-git-deps: missing allowlist ${path.relative(ROOT, ALLOWLIST_PATH)}`);
        process.exit(1);
    }

    const allowlist = JSON.parse(fs.readFileSync(ALLOWLIST_PATH, "utf8"));
    const packageJson = JSON.parse(fs.readFileSync(PACKAGE_JSON_PATH, "utf8"));
    const lockText = fs.readFileSync(LOCKFILE_PATH, "utf8");
    const fetchMicronText = fs.readFileSync(FETCH_MICRON_WASM_PATH, "utf8");

    const depSections = ["dependencies", "devDependencies", "optionalDependencies", "peerDependencies"];
    /** @type {{ name: string, spec: string }[]} */
    const gitDeps = [];
    for (const section of depSections) {
        const block = packageJson[section];
        if (!block || typeof block !== "object") continue;
        for (const [name, spec] of Object.entries(block)) {
            if (typeof spec === "string" && GIT_SPEC_RE.test(spec)) {
                gitDeps.push({ name, spec });
            }
        }
    }

    const allowByName = new Map((allowlist.git_dependencies || []).map((entry) => [entry.name, entry]));

    for (const dep of gitDeps) {
        const allowed = allowByName.get(dep.name);
        if (!allowed) {
            errors.push(`git dependency "${dep.name}" (${dep.spec}) is not in deps-allowlist.json`);
            continue;
        }

        const { base, ref } = splitGitSpec(dep.spec);
        const allowedBases = new Set((allowed.specifiers || []).map((spec) => splitGitSpec(spec).base));
        if (!allowedBases.has(base) && !(allowed.specifiers || []).includes(dep.spec)) {
            errors.push(
                `git dependency "${dep.name}" specifier base "${base}" is not allowlisted (have: ${(allowed.specifiers || []).join(", ")})`
            );
        }

        const lockCommit = lockfileCommitForPackage(lockText, dep.name);
        if (!lockCommit) {
            errors.push(`git dependency "${dep.name}" is unpinned in pnpm-lock.yaml (no 40-char commit)`);
            continue;
        }
        if (!FULL_COMMIT_RE.test(lockCommit)) {
            errors.push(`git dependency "${dep.name}" lock commit is not a full SHA: ${lockCommit}`);
            continue;
        }
        if (lockCommit !== String(allowed.commit).toLowerCase()) {
            errors.push(
                `git dependency "${dep.name}" lock commit ${lockCommit} drifts from allowlist ${allowed.commit}`
            );
        }
        if (ref && FULL_COMMIT_RE.test(ref) && ref.toLowerCase() !== String(allowed.commit).toLowerCase()) {
            errors.push(
                `git dependency "${dep.name}" package.json ref #${ref} drifts from allowlist ${allowed.commit}`
            );
        }
        if (!ref) {
            errors.push(
                `git dependency "${dep.name}" package.json specifier is floating (${dep.spec}). Pin with #${allowed.commit}`
            );
        }
    }

    for (const allowed of allowlist.git_dependencies || []) {
        if (!gitDeps.some((dep) => dep.name === allowed.name)) {
            errors.push(
                `allowlist git dependency "${allowed.name}" is missing from package.json (remove from allowlist or restore dep)`
            );
        }
    }

    const flatpakModules = packageJson.build?.flatpak?.modules || [];
    const allowGitSources = allowlist.git_sources || [];
    /** @type {object[]} */
    const declaredGitSources = [];
    for (const mod of flatpakModules) {
        for (const source of mod.sources || []) {
            if (source && source.type === "git" && source.url) {
                declaredGitSources.push(source);
            }
        }
    }

    for (const source of declaredGitSources) {
        const allowed = allowGitSources.find((entry) => entry.url === source.url);
        if (!allowed) {
            errors.push(`flatpak git source ${source.url} is not in deps-allowlist.json`);
            continue;
        }
        if (allowed.commit && source.commit && source.commit !== allowed.commit) {
            errors.push(
                `flatpak git source ${source.url} commit ${source.commit} drifts from allowlist ${allowed.commit}`
            );
        }
        if (allowed.tag && source.tag && source.tag !== allowed.tag) {
            errors.push(`flatpak git source ${source.url} tag ${source.tag} drifts from allowlist ${allowed.tag}`);
        }
        if (!source.commit) {
            errors.push(`flatpak git source ${source.url} is missing commit pin`);
        }
    }

    for (const allowed of allowGitSources) {
        if (!declaredGitSources.some((source) => source.url === allowed.url)) {
            errors.push(`allowlist git source ${allowed.url} is missing from package.json flatpak modules`);
        }
    }

    const wasmUrlTemplate = readExportedStringConst(fetchMicronText, "DEFAULT_WASM_URL");
    const wasmExecUrl = readExportedStringConst(fetchMicronText, "DEFAULT_WASM_EXEC_URL");
    const wasmUrlResolved = `https://github.com/Quad4-Software/Micron-Parser-Go/releases/download/${MICRON_PARSER_GO_RELEASE_TAG}/micron-parser-go.wasm`;

    for (const entry of allowlist.download_urls || []) {
        if (entry.name === "micron-parser-go-wasm") {
            if (entry.pinned_tag && entry.pinned_tag !== MICRON_PARSER_GO_RELEASE_TAG) {
                errors.push(
                    `Micron WASM tag ${MICRON_PARSER_GO_RELEASE_TAG} drifts from allowlist ${entry.pinned_tag}`
                );
            }
            if (entry.pattern && !matchPattern(entry.pattern, wasmUrlResolved)) {
                errors.push(`Micron WASM URL ${wasmUrlResolved} does not match allowlist pattern ${entry.pattern}`);
            }
            if (wasmUrlTemplate && !wasmUrlTemplate.includes("Micron-Parser-Go/releases/download/")) {
                errors.push(`fetch-micron-wasm.mjs DEFAULT_WASM_URL looks unexpected: ${wasmUrlTemplate}`);
            }
        }
        if (entry.name === "golang-wasm-exec") {
            if (!wasmExecUrl) {
                errors.push("fetch-micron-wasm.mjs DEFAULT_WASM_EXEC_URL missing");
            } else if (entry.url && wasmExecUrl !== entry.url) {
                errors.push(`wasm_exec URL ${wasmExecUrl} drifts from allowlist ${entry.url}`);
            }
        }
    }

    if (errors.length > 0) {
        console.error("check-git-deps: failed");
        for (const error of errors) {
            console.error(`  - ${error}`);
        }
        process.exit(1);
    }

    console.log("check-git-deps: ok");
    console.log(`  micron-parser commit: ${(allowByName.get("micron-parser") || {}).commit}`);
    console.log(`  micron wasm tag: ${MICRON_PARSER_GO_RELEASE_TAG}`);
}

main();
