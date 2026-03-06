import { describe, it, expect, vi, beforeEach } from "vitest";
import App from "../../meshchatx/src/frontend/components/App.vue";

vi.mock("qrcode", () => ({
    default: {
        toDataURL: vi.fn().mockResolvedValue("data:image/png;base64,abc123"),
    },
}));

describe("App.vue QR and protocol URI handling", () => {
    beforeEach(() => {
        vi.clearAllMocks();
    });

    it("generates lxma QR URI when public key is available", async () => {
        const ctx = {
            config: {
                lxmf_address_hash: "a".repeat(32),
                identity_public_key: "b".repeat(128),
            },
            lxmfQrDataUrl: null,
            showLxmfQr: false,
            getMyIdentityUri: App.methods.getMyIdentityUri,
            $t: (k) => k,
        };

        await App.methods.openLxmfQr.call(ctx);

        expect(ctx.showLxmfQr).toBe(true);
        expect(ctx.lxmfQrDataUrl).toBe("data:image/png;base64,abc123");
    });

    it("parses lxma protocol links and routes by destination hash", () => {
        const push = vi.fn();
        const ctx = {
            $router: {
                push,
            },
        };
        const destinationHash = "c".repeat(32);
        const publicKey = "d".repeat(128);

        App.methods.handleProtocolLink.call(ctx, `lxma://${destinationHash}:${publicKey}`);

        expect(push).toHaveBeenCalledWith({
            name: "messages",
            params: {
                destinationHash,
            },
        });
    });
});
