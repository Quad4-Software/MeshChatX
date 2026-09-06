import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import {
    applyIdentitySwitched,
    onIdentitySwitchedApplyShell,
    onIdentitySwitchingAbortShell,
} from "../../meshchatx/src/frontend/features/app-shell/lib/appShellIdentity.js";
import ToastUtils from "../../meshchatx/src/frontend/js/ToastUtils";
import GlobalEmitter from "../../meshchatx/src/frontend/js/GlobalEmitter";
import GlobalState from "../../meshchatx/src/frontend/js/GlobalState";
import { clearMessagePanes } from "../../meshchatx/src/frontend/js/browserLayoutStore";
import { micronStorage } from "../../meshchatx/src/frontend/js/MicronStorage";
import { registerFallbackMessages, registerTranslator } from "../../meshchatx/src/frontend/js/i18n.js";

const getConfig = vi.fn().mockResolvedValue(undefined);
const getAppInfo = vi.fn().mockResolvedValue(undefined);
const getBlockedDestinations = vi.fn().mockResolvedValue(undefined);
const updateRingtonePlayer = vi.fn().mockResolvedValue(undefined);
const updateTelephoneStatus = vi.fn();
const updateUnreadConversationsCount = vi.fn();
const updateRelayChatUnreadCount = vi.fn();
const navigate = vi.fn().mockResolvedValue(undefined);

vi.mock("../../meshchatx/src/frontend/js/csrfToken.js", () => ({
    fetchCsrfToken: vi.fn().mockResolvedValue(undefined),
}));

vi.mock("../../meshchatx/src/frontend/js/browserLayoutStore.js", async (importOriginal) => {
    const actual = await importOriginal();
    return {
        ...actual,
        clearMessagePanes: vi.fn(),
    };
});

vi.mock("../../meshchatx/src/frontend/js/MicronStorage", () => ({
    micronStorage: {
        clearAll: vi.fn().mockResolvedValue(undefined),
        loadTabs: vi.fn().mockResolvedValue([]),
        saveTabs: vi.fn().mockResolvedValue(undefined),
    },
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

vi.mock("../../meshchatx/src/frontend/features/app-shell/lib/appShellConfig.js", async (importOriginal) => {
    const actual = await importOriginal();
    return {
        ...actual,
        getConfig: (...args) => getConfig(...args),
        getAppInfo: (...args) => getAppInfo(...args),
        getBlockedDestinations: (...args) => getBlockedDestinations(...args),
    };
});

vi.mock("../../meshchatx/src/frontend/features/app-shell/lib/appShellTelephony.js", async (importOriginal) => {
    const actual = await importOriginal();
    return {
        ...actual,
        updateRingtonePlayer: (...args) => updateRingtonePlayer(...args),
        updateTelephoneStatus: (...args) => updateTelephoneStatus(...args),
    };
});

vi.mock("../../meshchatx/src/frontend/features/app-shell/lib/appShellNav.js", async (importOriginal) => {
    const actual = await importOriginal();
    return {
        ...actual,
        updateUnreadConversationsCount: (...args) => updateUnreadConversationsCount(...args),
        updateRelayChatUnreadCount: (...args) => updateRelayChatUnreadCount(...args),
    };
});

vi.mock("../../meshchatx/src/frontend/shell/hashRouter.js", async (importOriginal) => {
    const actual = await importOriginal();
    return {
        ...actual,
        navigate: (...args) => navigate(...args),
    };
});

function makeState(overrides = {}) {
    return {
        identitySwitchDedupeHash: null,
        identitySwitchDedupeAt: 0,
        isSwitchingIdentity: true,
        isAuthRoute: false,
        wsLiveSyncHandle: null,
        ...overrides,
    };
}

describe("app-shell applyIdentitySwitched", () => {
    beforeEach(() => {
        vi.clearAllMocks();
        registerTranslator(null);
        registerFallbackMessages({
            identities: {
                switched: "identities.switched",
                sign_in_after_switch: "identities.sign_in_after_switch",
                failed_switch: "identities.failed_switch",
            },
        });
        GlobalState.unreadConversationsCount = 3;
        GlobalState.missedCallsCount = 2;
        GlobalState.relayChatUnreadCount = 7;
        GlobalState.blockedDestinations = [{ destination_hash: "old" }];
        GlobalState.authEnabled = false;
        GlobalState.authenticated = false;
    });

    afterEach(() => {
        GlobalState.unreadConversationsCount = 0;
        GlobalState.missedCallsCount = 0;
        GlobalState.relayChatUnreadCount = 0;
        GlobalState.blockedDestinations = [];
        GlobalState.authEnabled = false;
        vi.useRealTimers();
    });

    it("applies identity switch, resets unread, and clears overlay", async () => {
        const state = makeState();
        await applyIdentitySwitched(state, {
            identity_hash: "h1",
            display_name: "User One",
        });
        expect(ToastUtils.success).toHaveBeenCalledWith("identities.switched");
        expect(GlobalState.unreadConversationsCount).toBe(0);
        expect(GlobalState.missedCallsCount).toBe(0);
        expect(GlobalState.relayChatUnreadCount).toBe(0);
        expect(getConfig).toHaveBeenCalledTimes(1);
        expect(updateRingtonePlayer).toHaveBeenCalledTimes(1);
        expect(getAppInfo).toHaveBeenCalledTimes(1);
        expect(getBlockedDestinations).toHaveBeenCalledTimes(1);
        expect(updateTelephoneStatus).toHaveBeenCalledTimes(1);
        expect(updateUnreadConversationsCount).toHaveBeenCalledTimes(1);
        expect(updateRelayChatUnreadCount).toHaveBeenCalledTimes(1);
        expect(GlobalState.blockedDestinations).toEqual([]);
        expect(state.isSwitchingIdentity).toBe(false);
        expect(clearMessagePanes).toHaveBeenCalled();
        expect(micronStorage.clearAll).toHaveBeenCalled();
        expect(GlobalEmitter.emit).toHaveBeenCalledWith(
            "identity-switched",
            expect.objectContaining({
                identity_hash: "h1",
                display_name: "User One",
            })
        );
    });

    it("dedupes rapid duplicate applies for the same hash (WS + HTTP race)", async () => {
        const state = makeState();
        await applyIdentitySwitched(state, {
            identity_hash: "same",
            display_name: "First",
        });
        await applyIdentitySwitched(state, {
            identity_hash: "same",
            display_name: "Second",
        });
        expect(getConfig).toHaveBeenCalledTimes(1);
        expect(ToastUtils.success).toHaveBeenCalledTimes(1);
        expect(GlobalEmitter.emit).toHaveBeenCalledTimes(1);
        expect(state.isSwitchingIdentity).toBe(false);
    });

    it("applies again for a different identity hash", async () => {
        const state = makeState();
        await applyIdentitySwitched(state, {
            identity_hash: "h1",
            display_name: "A",
        });
        await applyIdentitySwitched(state, {
            identity_hash: "h2",
            display_name: "B",
        });
        expect(getConfig).toHaveBeenCalledTimes(2);
        expect(ToastUtils.success).toHaveBeenCalledTimes(2);
    });

    it("no-ops when identity_hash is empty", async () => {
        const state = makeState();
        await applyIdentitySwitched(state, {
            identity_hash: "",
            display_name: "X",
        });
        expect(getConfig).not.toHaveBeenCalled();
        expect(GlobalEmitter.emit).toHaveBeenCalledWith("identity-switching-abort");
        expect(state.isSwitchingIdentity).toBe(false);
    });

    it("no-ops when identity_hash is missing", async () => {
        const state = makeState();
        await applyIdentitySwitched(state, {
            display_name: "X",
        });
        expect(getConfig).not.toHaveBeenCalled();
        expect(GlobalEmitter.emit).toHaveBeenCalledWith("identity-switching-abort");
        expect(state.isSwitchingIdentity).toBe(false);
    });

    it("re-applies same hash after dedupe window expires", async () => {
        vi.useFakeTimers();
        vi.setSystemTime(1_000_000);
        const state = makeState();
        await applyIdentitySwitched(state, {
            identity_hash: "h1",
            display_name: "A",
        });
        expect(getConfig).toHaveBeenCalledTimes(1);
        vi.setSystemTime(1_000_000 + 10_001);
        vi.clearAllMocks();
        await applyIdentitySwitched(state, {
            identity_hash: "h1",
            display_name: "B",
        });
        expect(getConfig).toHaveBeenCalledTimes(1);
        expect(ToastUtils.success).toHaveBeenCalledTimes(1);
        expect(GlobalEmitter.emit).toHaveBeenCalledTimes(1);
    });

    it("requires reauth without wiping UI via identity-switched", async () => {
        GlobalState.authEnabled = true;
        const state = makeState({ isAuthRoute: false });
        await applyIdentitySwitched(state, {
            identity_hash: "h1",
            requires_reauth: true,
        });
        expect(ToastUtils.info).toHaveBeenCalledWith("identities.sign_in_after_switch");
        expect(ToastUtils.success).not.toHaveBeenCalled();
        expect(getConfig).not.toHaveBeenCalled();
        expect(GlobalEmitter.emit).toHaveBeenCalledWith("identity-switching-abort");
        expect(GlobalEmitter.emit).not.toHaveBeenCalledWith("identity-switched", expect.anything());
        expect(navigate).toHaveBeenCalledWith("/auth");
        expect(state.isSwitchingIdentity).toBe(false);
    });

    it("onIdentitySwitchedApplyShell schedules apply without throwing", () => {
        const state = makeState();
        expect(() => onIdentitySwitchedApplyShell(state, { identity_hash: "x", display_name: "Y" })).not.toThrow();
    });

    it("onIdentitySwitchingAbortShell clears overlay", () => {
        const state = makeState({ isSwitchingIdentity: true });
        onIdentitySwitchingAbortShell(state);
        expect(state.isSwitchingIdentity).toBe(false);
    });
});
