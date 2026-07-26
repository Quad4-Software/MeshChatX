import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import App from "../../meshchatx/src/frontend/components/App.vue";
import ToastUtils from "../../meshchatx/src/frontend/js/ToastUtils";
import GlobalEmitter from "../../meshchatx/src/frontend/js/GlobalEmitter";
import GlobalState from "../../meshchatx/src/frontend/js/GlobalState";

vi.mock("../../meshchatx/src/frontend/js/csrfToken.js", () => ({
    fetchCsrfToken: vi.fn().mockResolvedValue(undefined),
}));

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
        getBlockedDestinations: vi.fn().mockResolvedValue(undefined),
        updateTelephoneStatus: vi.fn(),
        $t: (key) => key,
    };
}

describe("App.vue applyIdentitySwitched", () => {
    beforeEach(() => {
        vi.clearAllMocks();
        GlobalState.unreadConversationsCount = 3;
        GlobalState.missedCallsCount = 2;
        GlobalState.blockedDestinations = [{ destination_hash: "old" }];
    });

    afterEach(() => {
        GlobalState.unreadConversationsCount = 0;
        GlobalState.missedCallsCount = 0;
        GlobalState.blockedDestinations = [];
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
        expect(GlobalState.missedCallsCount).toBe(0);
        expect(ctx.getConfig).toHaveBeenCalledTimes(1);
        expect(ctx.updateRingtonePlayer).toHaveBeenCalledTimes(1);
        expect(ctx.getAppInfo).toHaveBeenCalledTimes(1);
        expect(ctx.getBlockedDestinations).toHaveBeenCalledTimes(1);
        expect(ctx.updateTelephoneStatus).toHaveBeenCalledTimes(1);
        expect(GlobalState.blockedDestinations).toEqual([]);
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
        expect(ctx.isSwitchingIdentity).toBe(false);
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
        expect(GlobalEmitter.emit).toHaveBeenCalledWith("identity-switching-abort");
        expect(ctx.isSwitchingIdentity).toBe(false);
    });

    it("no-ops when identity_hash is missing", async () => {
        const ctx = makeCtx();
        await App.methods.applyIdentitySwitched.call(ctx, {
            display_name: "X",
        });
        expect(ctx.getConfig).not.toHaveBeenCalled();
        expect(GlobalEmitter.emit).toHaveBeenCalledWith("identity-switching-abort");
        expect(ctx.isSwitchingIdentity).toBe(false);
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

    it("requires reauth without wiping UI via identity-switched", async () => {
        GlobalState.authEnabled = true;
        const ctx = {
            ...makeCtx(),
            $route: { name: "settings" },
            $router: { push: vi.fn() },
        };
        await App.methods.applyIdentitySwitched.call(ctx, {
            identity_hash: "h1",
            requires_reauth: true,
        });
        expect(ToastUtils.info).toHaveBeenCalledWith("identities.sign_in_after_switch");
        expect(ToastUtils.success).not.toHaveBeenCalled();
        expect(ctx.getConfig).not.toHaveBeenCalled();
        expect(GlobalEmitter.emit).toHaveBeenCalledWith("identity-switching-abort");
        expect(GlobalEmitter.emit).not.toHaveBeenCalledWith("identity-switched", expect.anything());
        expect(ctx.$router.push).toHaveBeenCalledWith("/auth");
        expect(ctx.isSwitchingIdentity).toBe(false);
    });

    it("shows error and aborts when post-switch refresh fails", async () => {
        const ctx = makeCtx();
        ctx.getConfig.mockRejectedValueOnce(new Error("network"));
        await App.methods.applyIdentitySwitched.call(ctx, {
            identity_hash: "h1",
        });
        expect(ToastUtils.error).toHaveBeenCalledWith("identities.failed_switch");
        expect(GlobalEmitter.emit).toHaveBeenCalledWith("identity-switching-abort");
        expect(ctx.isSwitchingIdentity).toBe(false);
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

    it("onIdentitySwitchingAbortShell clears the switching overlay", () => {
        const ctx = { isSwitchingIdentity: true };
        App.methods.onIdentitySwitchingAbortShell.call(ctx);
        expect(ctx.isSwitchingIdentity).toBe(false);
    });
});
