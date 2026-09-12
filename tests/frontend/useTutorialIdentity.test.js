// SPDX-License-Identifier: 0BSD

import { describe, expect, it, vi, beforeEach } from "vitest";
import { useTutorialIdentity } from "../../meshchatx/src/frontend/js/tutorial/useTutorialIdentity.js";
import { useConfigStore } from "../../meshchatx/src/frontend/js/stores/configStore.js";
import GlobalEmitter from "../../meshchatx/src/frontend/js/GlobalEmitter.js";
import ToastUtils from "../../meshchatx/src/frontend/js/ToastUtils.js";

vi.mock("../../meshchatx/src/frontend/js/ToastUtils.js", () => ({
    default: {
        success: vi.fn(),
        error: vi.fn(),
        warning: vi.fn(),
        info: vi.fn(),
    },
}));

const t = (key) => key;

function makeIdentity(options = {}) {
    return useTutorialIdentity({ t, ...options });
}

describe("useTutorialIdentity", () => {
    beforeEach(() => {
        window.api = { get: vi.fn(), post: vi.fn(), patch: vi.fn(), delete: vi.fn() };
        vi.clearAllMocks();
    });

    it("starts with new-identity defaults", () => {
        const id = makeIdentity();
        expect(id.identityMode.value).toBe("new");
        expect(id.identityName.value).toBe("");
        expect(id.identityImportedHash.value).toBeNull();
        expect(id.originalIdentityHash.value).toBeNull();
        expect(id.defaultUsername.value).toBe("Anonymous Peer");
    });

    it("setIdentityMode clears import fields when switching back to new", () => {
        const id = makeIdentity();
        id.setIdentityMode("import");
        id.identityImportBase32.value = "ABCD";
        id.identityImportFile.value = { name: "id.key" };
        id.identityImportedHash.value = "hash";
        id.setIdentityMode("new");
        expect(id.identityMode.value).toBe("new");
        expect(id.identityImportFile.value).toBeNull();
        expect(id.identityImportBase32.value).toBe("");
        expect(id.identityImportedHash.value).toBeNull();
    });

    it("normalizeBase32 strips whitespace and hasIdentityImportInput tracks input", () => {
        const id = makeIdentity();
        expect(id.normalizeBase32(" AB CD\n1234 ")).toBe("ABCD1234");
        expect(id.hasIdentityImportInput.value).toBe(false);
        id.identityImportBase32.value = "   ";
        expect(id.hasIdentityImportInput.value).toBe(false);
        id.identityImportBase32.value = "AB CD";
        expect(id.hasIdentityImportInput.value).toBe(true);
        id.identityImportBase32.value = "";
        id.identityImportFile.value = { name: "id.key" };
        expect(id.hasIdentityImportInput.value).toBe(true);
    });

    it("onIdentityImportFileChange rejects empty and oversized files", () => {
        const id = makeIdentity();
        const target = { files: [{ size: 0 }], value: "pick" };
        id.onIdentityImportFileChange({ target });
        expect(id.identityImportFile.value).toBeNull();
        expect(id.identityImportError.value).toBe("tutorial.identity_import_empty_file");
        expect(target.value).toBe("");

        id.onIdentityImportFileChange({ target: { files: [{ size: 70000 }], value: "pick" } });
        expect(id.identityImportError.value).toBe("tutorial.identity_import_file_too_large");

        id.onIdentityImportFileChange({ target: { files: [{ size: 100, name: "id.key" }], value: "pick" } });
        expect(id.identityImportFile.value).toEqual({ size: 100, name: "id.key" });
        expect(id.identityImportError.value).toBe("");
    });

    it("loadIdentitySetupDefaults fills name and original hash from the api", async () => {
        window.api.get.mockImplementation((url) => {
            if (url === "/api/v1/identities") {
                return Promise.resolve({ data: { identities: [{ hash: "orig", is_current: true }] } });
            }
            return Promise.resolve({ data: { config: { display_name: "Mesh User" } } });
        });
        const id = makeIdentity();
        await id.loadIdentitySetupDefaults();
        expect(id.originalIdentityHash.value).toBe("orig");
        expect(id.identityName.value).toBe("Mesh User");
    });

    it("loadIdentitySetupDefaults falls back to the default username on failure", async () => {
        window.api.get.mockRejectedValue(new Error("offline"));
        const id = makeIdentity();
        await id.loadIdentitySetupDefaults();
        expect(id.identityName.value).toBe("Anonymous Peer");
    });

    it("handleIdentityContinue saves the display name in new mode and advances", async () => {
        window.api.patch.mockResolvedValue({ data: {} });
        const goToStep = vi.fn();
        const id = makeIdentity({ goToStep });
        id.identityName.value = "Mesh User";
        await id.handleIdentityContinue();
        expect(window.api.patch).toHaveBeenCalledWith("/api/v1/config", { display_name: "Mesh User" });
        expect(useConfigStore().config.display_name).toBe("Mesh User");
        expect(goToStep).toHaveBeenCalledWith(3);
    });

    it("handleIdentityContinue requires import input in import mode", async () => {
        const goToStep = vi.fn();
        const id = makeIdentity({ goToStep });
        id.setIdentityMode("import");
        await id.handleIdentityContinue();
        expect(id.identityImportError.value).toBe("tutorial.identity_import_required");
        expect(goToStep).not.toHaveBeenCalled();
    });

    it("handleIdentityContinue imports via base32 and advances", async () => {
        window.api.post.mockResolvedValue({ data: { identity: { hash: "imported_hash" } } });
        const goToStep = vi.fn();
        const id = makeIdentity({ goToStep });
        id.setIdentityMode("import");
        id.identityName.value = "Imported User";
        id.identityImportBase32.value = "AB CD 1234";
        await id.handleIdentityContinue();
        expect(window.api.post).toHaveBeenCalledWith("/api/v1/identity/restore", {
            base32: "ABCD1234",
            display_name: "Imported User",
        });
        expect(id.identityImportedHash.value).toBe("imported_hash");
        expect(id.identityImportBase32.value).toBe("");
        expect(id.identityImportInProgress.value).toBe(false);
        expect(goToStep).toHaveBeenCalledWith(3);
    });

    it("handleIdentityContinue surfaces api errors and resets the busy flag", async () => {
        window.api.post.mockRejectedValue({ response: { data: { message: "bad key" } } });
        const id = makeIdentity();
        id.setIdentityMode("import");
        id.identityImportBase32.value = "BROKEN";
        await id.handleIdentityContinue();
        expect(id.identityImportError.value).toBe("bad key");
        expect(id.identityImportInProgress.value).toBe(false);
        expect(id.identityImportedHash.value).toBeNull();
    });

    it("resetIdentitySetupState clears all identity and finishing state", () => {
        const id = makeIdentity();
        id.setIdentityMode("import");
        id.identityName.value = "X";
        id.identityImportBase32.value = "AB";
        id.identityImportedHash.value = "h";
        id.originalIdentityHash.value = "o";
        id.finishingTutorial.value = true;
        id.resetIdentitySetupState();
        expect(id.identityMode.value).toBe("new");
        expect(id.identityName.value).toBe("");
        expect(id.identityImportBase32.value).toBe("");
        expect(id.identityImportedHash.value).toBeNull();
        expect(id.originalIdentityHash.value).toBeNull();
        expect(id.finishingTutorial.value).toBe(false);
    });

    it("activateImportedIdentity is a no-op without a pending import", async () => {
        const id = makeIdentity();
        expect(await id.activateImportedIdentity()).toBe(true);
        id.identityImportedHash.value = "same";
        id.originalIdentityHash.value = "same";
        expect(await id.activateImportedIdentity()).toBe(true);
        expect(window.api.post).not.toHaveBeenCalled();
    });

    it("activateImportedIdentity switches, deletes the original, and emits apply", async () => {
        window.api.post.mockResolvedValue({
            data: { hotswapped: true, identity_hash: "new_hash", display_name: "N" },
        });
        window.api.delete.mockResolvedValue({ data: {} });
        const emit = vi.spyOn(GlobalEmitter, "emit");
        const id = makeIdentity();
        id.identityImportedHash.value = "new_hash";
        id.originalIdentityHash.value = "orig";
        expect(await id.activateImportedIdentity()).toBe(true);
        expect(window.api.post).toHaveBeenCalledWith("/api/v1/identities/switch", {
            identity_hash: "new_hash",
        });
        expect(window.api.delete).toHaveBeenCalledWith("/api/v1/identities/orig");
        expect(id.identityImportedHash.value).toBeNull();
        expect(emit).toHaveBeenCalledWith(
            "identity-switched-apply",
            expect.objectContaining({ identity_hash: "new_hash", display_name: "N" })
        );
        emit.mockRestore();
    });

    it("activateImportedIdentity reports failure and aborts on api error", async () => {
        window.api.post.mockRejectedValue({ response: { data: { message: "switch failed" } } });
        const emit = vi.spyOn(GlobalEmitter, "emit");
        const id = makeIdentity();
        id.identityImportedHash.value = "new_hash";
        expect(await id.activateImportedIdentity()).toBe(false);
        expect(ToastUtils.error).toHaveBeenCalledWith("switch failed");
        expect(emit).toHaveBeenCalledWith("identity-switching-abort");
        emit.mockRestore();
    });
});
