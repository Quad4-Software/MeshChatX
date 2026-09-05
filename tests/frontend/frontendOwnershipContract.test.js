// SPDX-License-Identifier: 0BSD

import { existsSync, readFileSync, writeFileSync } from "fs";
import { join } from "path";
import { describe, expect, it } from "vitest";
import {
    assertStringsInSources,
    discoverMegaPageOwnership,
    joinFeatureSources,
    loadJsonFixture,
    readUtf8,
    writeOwnershipFixture,
} from "./helpers/frontendOwnershipHelpers.js";

const repoRoot = process.cwd();
const ownershipFixtureRel = "tests/frontend/fixtures/frontend_mega_page_ownership.json";
const continuityDirRel = "tests/frontend/fixtures/frontend_symbol_continuity";

describe("frontend mega-page ownership contracts", () => {
    it("ownership_fixture matches discovered on-disk inventory", () => {
        const fixturePath = join(repoRoot, ownershipFixtureRel);
        const discovered = discoverMegaPageOwnership(repoRoot);
        if (process.env.UPDATE_FRONTEND_OWNERSHIP === "1") {
            writeOwnershipFixture(repoRoot, fixturePath);
        }
        expect(existsSync(fixturePath)).toBe(true);
        const fixture = JSON.parse(readFileSync(fixturePath, "utf8"));
        expect(fixture).toEqual(discovered);
    });

    it("required children exist and shells import declared symbols", () => {
        const fixture = loadJsonFixture(repoRoot, ownershipFixtureRel);
        for (const page of fixture.pages) {
            for (const child of page.required_children) {
                expect(existsSync(join(repoRoot, child)), `${page.id} missing child ${child}`).toBe(true);
            }
            const shellSrc = readUtf8(join(repoRoot, page.shell));
            for (const symbol of page.required_shell_imports) {
                expect(shellSrc.includes(symbol), `${page.id} shell missing import/use of ${symbol}`).toBe(true);
            }
        }
    });

    it("symbol continuity fixtures remain present in feature trees", () => {
        const pages = ["settings", "map", "messages", "call", "app"];
        for (const id of pages) {
            const continuity = loadJsonFixture(repoRoot, `${continuityDirRel}/${id}.json`);
            const sourceText = joinFeatureSources(repoRoot, continuity.scan_dirs);
            expect(() =>
                assertStringsInSources(sourceText, continuity.required_strings, `${id} continuity`)
            ).not.toThrow();
        }
    });

    it("ownership pages do not invent unknown top-level child roots", () => {
        const fixture = loadJsonFixture(repoRoot, ownershipFixtureRel);
        const allowedRoots = [
            "meshchatx/src/frontend/features/settings",
            "meshchatx/src/frontend/features/map",
            "meshchatx/src/frontend/features/messages",
            "meshchatx/src/frontend/features/call",
            "meshchatx/src/frontend/components/layout",
            "meshchatx/src/frontend/js",
        ];
        for (const page of fixture.pages) {
            for (const dir of page.allowed_child_dirs) {
                const ok = allowedRoots.some((root) => dir === root || dir.startsWith(`${root}/`));
                expect(ok, `unexpected allowed dir ${dir} for ${page.id}`).toBe(true);
            }
        }
    });
});
