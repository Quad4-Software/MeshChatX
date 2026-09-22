import { describe, it, expect, vi, beforeEach } from "vitest";
import { getMyIdentityUri, openLxmfQr } from "../../meshchatx/src/frontend/features/app-shell/lib/appShellIdentity.js";
import { handleProtocolLink } from "../../meshchatx/src/frontend/features/app-shell/lib/appShellLinks.js";

vi.mock("qrcode", () => ({
    default: {
        toDataURL: vi.fn().mockResolvedValue("data:image/png;base64,abc123"),
    },
}));

describe("app-shell QR and protocol URI handling", () => {
    beforeEach(() => {
        vi.clearAllMocks();
    });

    it("generates lxma QR URI when public key is available", async () => {
        const state = {
            config: {
                lxmf_address_hash: "a".repeat(32),
                identity_public_key: "b".repeat(128),
            },
            lxmfQrDataUrl: null,
            showLxmfQr: false,
        };

        await openLxmfQr(state);

        expect(state.showLxmfQr).toBe(true);
        expect(state.lxmfQrDataUrl).toBe("data:image/png;base64,abc123");
        expect(getMyIdentityUri(state)).toBe(`lxma://${"a".repeat(32)}:${"b".repeat(128)}`);
    });

    it("parses lxma protocol links and routes by destination hash", () => {
        const push = vi.fn();
        const destinationHash = "c".repeat(32);
        const publicKey = "d".repeat(128);

        handleProtocolLink({ push }, `lxma://${destinationHash}:${publicKey}`);

        expect(push).toHaveBeenCalledWith({
            name: "messages",
            params: {
                destinationHash,
            },
        });
    });
});
