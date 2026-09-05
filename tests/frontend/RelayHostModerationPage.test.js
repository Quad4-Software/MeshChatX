// SPDX-License-Identifier: 0BSD
import { render, cleanup, fireEvent, waitFor } from "@testing-library/svelte";
import { beforeEach, afterEach, describe, expect, it, vi } from "vitest";
import RelayHostModerationPage from "@/features/relay-chat/components/RelayHostModerationPage.svelte";
import DialogUtils from "@/js/DialogUtils";
import ToastUtils from "@/js/ToastUtils";
import { t, registerFallbackMessages, registerTranslator } from "@/js/i18n.js";
import en from "@/locales/en.json";

vi.mock("@/js/DialogUtils", () => ({
    default: {
        confirm: vi.fn(),
        prompt: vi.fn(),
    },
}));

vi.mock("@/js/ToastUtils", () => ({
    default: {
        success: vi.fn(),
        error: vi.fn(),
        warning: vi.fn(),
    },
}));

const HUB_ID = "deadbeefdeadbeefdeadbeefdeadbeef";
const PEER_HASH = "00112233445566778899aabbccddeeff";
const LOCAL_HASH = "ffeeddccbbaa99887766554433221100";

function makeHub() {
    return { id: HUB_ID, name: "Hosted", running: true };
}

function makeMember(overrides = {}) {
    return {
        hash: PEER_HASH,
        name: "alice",
        rooms: ["lobby"],
        ...overrides,
    };
}

describe("RelayHostModerationPage.svelte", () => {
    beforeEach(() => {
        vi.clearAllMocks();
        DialogUtils.confirm.mockResolvedValue(true);
        registerTranslator(null);
        registerFallbackMessages(en);
        DialogUtils.confirm.mockResolvedValue(true);
        window.api = {
            get: vi.fn(async (url) => {
                if (url === "/api/v1/config") {
                    return { data: { identity_hash: LOCAL_HASH } };
                }
                if (url.includes("/members")) {
                    return { data: { members: [makeMember()] } };
                }
                if (url.includes("/activity")) {
                    return { data: { rooms: [], recent: [] } };
                }
                return { data: {} };
            }),
            post: vi.fn(async () => ({ data: { message: "ok" } })),
        };
    });

    afterEach(() => {
        cleanup();
        delete window.api;
    });

    it("fetches config and members on mount", async () => {
        render(RelayHostModerationPage, {
            hub: makeHub(),
            initialTab: "members",
        });

        await waitFor(() => {
            expect(window.api.get).toHaveBeenCalledWith("/api/v1/config");
            expect(window.api.get).toHaveBeenCalledWith(expect.stringContaining("/members"));
        });
    });

    it("renders member in list and shows kick button", async () => {
        const { getByText, getByTitle } = render(RelayHostModerationPage, {
            hub: makeHub(),
            initialTab: "members",
        });

        await waitFor(() => {
            expect(getByText("alice")).toBeTruthy();
            expect(getByTitle(t("relay_chat.kick_member"))).toBeTruthy();
        });
    });

    it("kicks member when kick button is clicked", async () => {
        const { getByTitle } = render(RelayHostModerationPage, {
            hub: makeHub(),
            initialTab: "members",
        });

        await waitFor(() => {
            expect(getByTitle(t("relay_chat.kick_member"))).toBeTruthy();
        });

        const kickBtn = getByTitle(t("relay_chat.kick_member"));
        await fireEvent.click(kickBtn);

        await waitFor(() => {
            expect(window.api.post).toHaveBeenCalledWith(
                `/api/v1/rrc/servers/${HUB_ID}/moderate`,
                expect.objectContaining({ action: "kick", peer: PEER_HASH })
            );
            expect(ToastUtils.success).toHaveBeenCalled();
        });
    });
});
