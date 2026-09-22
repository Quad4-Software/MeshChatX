// SPDX-License-Identifier: 0BSD
import { describe, it, expect } from "vitest";
import { readFileSync } from "fs";
import { join } from "path";

function src(rel) {
    return readFileSync(join(process.cwd(), rel), "utf8");
}

describe("app-shell propagation sync wiring", () => {
    it("propagation helper owns sync, poll, stop, and status refresh", () => {
        const prop = src("meshchatx/src/frontend/features/app-shell/lib/appShellPropagation.ts");
        expect(prop).toContain("export async function syncPropagationNode");
        expect(prop).toContain("export async function stopSyncingPropagationNode");
        expect(prop).toContain("export async function updatePropagationNodeStatus");
        expect(prop).toContain("/api/v1/lxmf/propagation-node/sync");
        expect(prop).toContain("/api/v1/lxmf/propagation-node/status");
        expect(prop).toContain("PROPAGATION_SYNC_TOAST_KEY");
        expect(prop).toContain("propagationSyncLiveToastMessage");
        expect(prop).toContain("path_timeout");
    });
});
