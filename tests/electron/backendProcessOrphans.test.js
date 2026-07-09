import { describe, expect, it } from "vitest";
import {
    isHeadlessBackendArgs,
} from "../../electron/backendProcessOrphans.js";

describe("electron/backendProcessOrphans", () => {
    it("detects headless backend command lines", () => {
        expect(
            isHeadlessBackendArgs(
                "/tmp/.mount_x/resources/backend/ReticulumMeshChatX --headless --port 9337"
            )
        ).toBe(true);
        expect(
            isHeadlessBackendArgs(
                "/home/user/ReticulumMeshChatX --headless"
            )
        ).toBe(true);
    });

    it("ignores non-backend and non-headless processes", () => {
        expect(isHeadlessBackendArgs("reticulum-meshchatx --type=renderer")).toBe(false);
        expect(isHeadlessBackendArgs("/tmp/ReticulumMeshChatX")).toBe(false);
        expect(isHeadlessBackendArgs("")).toBe(false);
        expect(isHeadlessBackendArgs(null)).toBe(false);
    });
});
