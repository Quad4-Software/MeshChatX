// SPDX-License-Identifier: 0BSD

import { beforeEach, describe, expect, it, vi } from "vitest";
import { useReticulumInstance } from "../../meshchatx/src/frontend/js/settings/useReticulumInstance.js";

vi.mock("../../meshchatx/src/frontend/js/settings/settingsReticulumInstanceService.js", () => ({
    fetchReticulumInstanceSettings: vi.fn(async () => ({
        share_instance: false,
        instance_name: "node-x",
        remote_management_allowed: ["AA", "bb"],
    })),
    applyReticulumInstanceSettings: vi.fn(async () => ({ data: { message: "Saved" } })),
}));

import {
    applyReticulumInstanceSettings,
    fetchReticulumInstanceSettings,
} from "../../meshchatx/src/frontend/js/settings/settingsReticulumInstanceService.js";

describe("useReticulumInstance", () => {
    beforeEach(() => {
        vi.clearAllMocks();
        window.api = {};
    });

    it("loads settings and normalizes fields", async () => {
        const r = useReticulumInstance();
        await r.loadReticulumInstanceSettings();
        expect(r.reticulumInstance.value.share_instance).toBe(false);
        expect(r.reticulumInstance.value.instance_name).toBe("node-x");
        expect(r.remoteManagementAllowedText.value).toBe("AA\nbb");
    });

    it("load failure keeps defaults", async () => {
        fetchReticulumInstanceSettings.mockRejectedValueOnce(new Error("down"));
        const r = useReticulumInstance();
        await r.loadReticulumInstanceSettings();
        expect(r.reticulumInstance.value.instance_name).toBe("default");
    });

    it("change handlers patch the backend", async () => {
        const r = useReticulumInstance();
        await r.onShareInstanceChange(true);
        expect(applyReticulumInstanceSettings).toHaveBeenCalledWith({ share_instance: true }, window.api);
        await r.onRespondToProbesChange(false);
        expect(applyReticulumInstanceSettings).toHaveBeenCalledWith({ respond_to_probes: false }, window.api);
    });

    it("saveRemoteManagementAllowed normalizes the text to hashes", async () => {
        const r = useReticulumInstance();
        r.remoteManagementAllowedText.value = "AA bb  , CC\nDD";
        await r.saveRemoteManagementAllowed();
        expect(applyReticulumInstanceSettings).toHaveBeenCalledWith(
            { remote_management_allowed: ["aa", "bb", "cc", "dd"] },
            window.api
        );
    });

    it("patch failure reloads and is guarded while saving", async () => {
        const r = useReticulumInstance();
        r.reticulumInstanceSaving.value = true;
        await r.patchReticulumInstance({ share_instance: true });
        expect(applyReticulumInstanceSettings).not.toHaveBeenCalled();
    });

    it("rpc snippet is redacted unless the key is visible", () => {
        const snippet = "host = 1.2.3.4\nrpc_key = supersecretkey";
        const hidden = useReticulumInstance({ t: (k) => k, getRpcKeyVisible: () => false });
        hidden.reticulumInstance.value = { ...hidden.reticulumInstance.value, rpc_config_snippet: snippet };
        expect(hidden.displayedRpcConfigSnippet.value).toContain("rpc_key = •");
        expect(hidden.displayedRpcConfigSnippet.value).not.toContain("supersecretkey");

        const shown = useReticulumInstance({ t: (k) => k, getRpcKeyVisible: () => true });
        shown.reticulumInstance.value = { ...shown.reticulumInstance.value, rpc_config_snippet: snippet };
        expect(shown.displayedRpcConfigSnippet.value).toBe(snippet);
    });
});
