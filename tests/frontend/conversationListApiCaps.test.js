// SPDX-License-Identifier: 0BSD

/**
 * Map and NetworkVisualiser must pass an explicit conversations limit.
 */

import { readFileSync } from "node:fs";
import { resolve } from "node:path";
import { describe, expect, it } from "vitest";

const ROOT = resolve(process.cwd());

describe("conversation list API caps", () => {
    it("NetworkVisualiser requests conversations with an explicit limit", () => {
        const src = readFileSync(
            resolve(ROOT, "meshchatx/src/frontend/components/network-visualiser/NetworkVisualiser.vue"),
            "utf8"
        );
        const apiSrc = readFileSync(resolve(ROOT, "meshchatx/src/frontend/js/api/lxmf.js"), "utf8");
        expect(apiSrc).toContain('apiPath("/lxmf/conversations")');
        expect(src).toMatch(/listConversations\(/);
        expect(src).toMatch(/params:\s*\{\s*limit:\s*2000\s*\}/);
    });

    it("MapPage requests conversations with an explicit limit", () => {
        const src = readFileSync(resolve(ROOT, "meshchatx/src/frontend/components/map/MapPage.vue"), "utf8");
        const apiSrc = readFileSync(resolve(ROOT, "meshchatx/src/frontend/js/api/lxmf.js"), "utf8");
        expect(apiSrc).toContain('apiPath("/lxmf/conversations")');
        expect(src).toMatch(/listConversations\(/);
        expect(src).toMatch(/params:\s*\{\s*limit:\s*2000\s*\}/);
    });

    it("MessagesPage skips poll when document is hidden and uses a longer interval", () => {
        const src = readFileSync(resolve(ROOT, "meshchatx/src/frontend/components/messages/MessagesPage.vue"), "utf8");
        expect(src).toMatch(/visibilityState === "hidden"/);
        expect(src).toMatch(/15000/);
        expect(src).not.toMatch(
            /setInterval\(\(\) => \{\s*this\.getConversations\(\);\s*this\.getFolders\(\);\s*\}, 5000\)/
        );
    });
});
