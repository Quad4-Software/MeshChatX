import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import App from "../../meshchatx/src/frontend/components/App.vue";
import ToastUtils from "../../meshchatx/src/frontend/js/ToastUtils";
import GlobalEmitter from "../../meshchatx/src/frontend/js/GlobalEmitter";
import GlobalState from "../../meshchatx/src/frontend/js/GlobalState";

vi.mock("../../meshchatx/src/frontend/js/ToastUtils", () => ({
    default: {
        success: vi.fn(),
        error: vi.fn(),
        warning: vi.fn(),
        info: vi.fn(),
    },
}));

vi.mock("../../meshchatx/src/frontend/js/GlobalEmitter", () => ({
    default: {
        emit: vi.fn(),
        on: vi.fn(),
        off: vi.fn(),
    },
}));

function makeCtx() {
    return {
        identitySwitchDedupeHash: null,
        identitySwitchDedupeAt: 0,
        isSwitchingIdentity: true,
        getConfig: vi.fn().mockResolvedValue(undefined),
        updateRingtonePlayer: vi.fn().mockResolvedValue(undefined),
        getAppInfo: vi.fn().mockResolvedValue(undefined),
        $t: (key) => key,
    };
}

describe("App.vue applyIdentitySwitched", () => {
    beforeEach(() => {
        vi.clearAllMocks();
        GlobalState.unreadConversationsCount = 3;
    });

    afterEach(() => {
        GlobalState.unreadConversationsCount = 0;
        vi.useRealTimers();
    });

    it("applies identity switch, resets unread, and clears overlay", async () => {
        const ctx = makeCtx();
        await App.methods.applyIdentitySwitched.call(ctx, {
            identity_hash: "h1",
            display_name: "User One",
        });
        expect(ToastUtils.success).toHaveBeenCalledWith("identities.switched");
        expect(GlobalState.unreadConversationsCount).toBe(0);
        expect(ctx.getConfig).toHaveBeenCalledTimes(1);
        expect(ctx.updateRingtonePlayer).toHaveBeenCalledTimes(1);
        expect(ctx.getAppInfo).toHaveBeenCalledTimes(1);
        expect(ctx.isSwitchingIdentity).toBe(false);
        expect(GlobalEmitter.emit).toHaveBeenCalledWith(
            "identity-switched",
            expect.objectContaining({
                identity_hash: "h1",
                display_name: "User One",
            })
        );
    });

    it("dedupes rapid duplicate applies for the same hash (WS + HTTP race)", async () => {
        const ctx = makeCtx();
        await App.methods.applyIdentitySwitched.call(ctx, {
            identity_hash: "same",
            display_name: "First",
        });
        await App.methods.applyIdentitySwitched.call(ctx, {
            identity_hash: "same",
            display_name: "Second",
        });
        expect(ctx.getConfig).toHaveBeenCalledTimes(1);
        expect(ToastUtils.success).toHaveBeenCalledTimes(1);
        expect(GlobalEmitter.emit).toHaveBeenCalledTimes(1);
    });

    it("applies again for a different identity hash", async () => {
        const ctx = makeCtx();
        await App.methods.applyIdentitySwitched.call(ctx, {
            identity_hash: "h1",
            display_name: "A",
        });
        await App.methods.applyIdentitySwitched.call(ctx, {
            identity_hash: "h2",
            display_name: "B",
        });
        expect(ctx.getConfig).toHaveBeenCalledTimes(2);
        expect(ToastUtils.success).toHaveBeenCalledTimes(2);
    });

    it("no-ops when identity_hash is empty", async () => {
        const ctx = makeCtx();
        await App.methods.applyIdentitySwitched.call(ctx, {
            identity_hash: "",
            display_name: "X",
        });
        expect(ctx.getConfig).not.toHaveBeenCalled();
        expect(GlobalEmitter.emit).not.toHaveBeenCalled();
    });

    it("no-ops when identity_hash is missing", async () => {
        const ctx = makeCtx();
        await App.methods.applyIdentitySwitched.call(ctx, {
            display_name: "X",
        });
        expect(ctx.getConfig).not.toHaveBeenCalled();
    });

    it("re-applies same hash after dedupe window expires", async () => {
        vi.useFakeTimers();
        vi.setSystemTime(1_000_000);
        const ctx = makeCtx();
        await App.methods.applyIdentitySwitched.call(ctx, {
            identity_hash: "h1",
            display_name: "A",
        });
        expect(ctx.getConfig).toHaveBeenCalledTimes(1);
        vi.setSystemTime(1_000_000 + 10_001);
        vi.clearAllMocks();
        await App.methods.applyIdentitySwitched.call(ctx, {
            identity_hash: "h1",
            display_name: "B",
        });
        expect(ctx.getConfig).toHaveBeenCalledTimes(1);
        expect(ToastUtils.success).toHaveBeenCalledTimes(1);
        expect(GlobalEmitter.emit).toHaveBeenCalledTimes(1);
    });

    it("performance: dedupe path skips async work for many duplicate applies", async () => {
        const ctx = makeCtx();
        await App.methods.applyIdentitySwitched.call(ctx, {
            identity_hash: "hot",
            display_name: "A",
        });
        vi.clearAllMocks();
        const t0 = performance.now();
        const n = 2000;
        for (let i = 0; i < n; i++) {
            await App.methods.applyIdentitySwitched.call(ctx, {
                identity_hash: "hot",
                display_name: "A",
            });
        }
        expect(performance.now() - t0).toBeLessThan(1500);
        expect(ctx.getConfig).not.toHaveBeenCalled();
        expect(GlobalEmitter.emit).not.toHaveBeenCalled();
    });

    it("onIdentitySwitchedApplyShell delegates to this.applyIdentitySwitched", async () => {
        const inner = vi.fn().mockResolvedValue(undefined);
        const ctx = { applyIdentitySwitched: inner };
        App.methods.onIdentitySwitchedApplyShell.call(ctx, { identity_hash: "x", display_name: "Y" });
        await Promise.resolve();
        expect(inner).toHaveBeenCalledWith({ identity_hash: "x", display_name: "Y" });
    });
});
