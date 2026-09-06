// SPDX-License-Identifier: 0BSD
import { describe, it, expect } from "vitest";
import { readFileSync } from "fs";
import { join } from "path";

function src(rel) {
    return readFileSync(join(process.cwd(), rel), "utf8");
}

describe("call codec2 shell wiring", () => {
    it("CallOverlay remains mounted and codec2 status endpoint stays named", () => {
        const overlays = src("meshchatx/src/frontend/features/app-shell/components/AppShellOverlays.svelte");
        const constants = src("meshchatx/src/frontend/features/call/lib/constants.ts");
        const api = src("meshchatx/src/frontend/features/call/lib/callApi.ts");
        expect(overlays).toContain("CallOverlay");
        expect(constants).toContain("TELEPHONE_CODEC2_STATUS_ENDPOINT");
        expect(api).toContain("fetchCodec2Status");
    });
});
