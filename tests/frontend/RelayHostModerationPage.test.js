import { mount } from "@vue/test-utils";
import { beforeEach, describe, expect, it, vi } from "vitest";

import RelayHostModerationPage from "@/components/relay/RelayHostModerationPage.vue";
import DialogUtils from "@/js/DialogUtils";
import ToastUtils from "@/js/ToastUtils";
import { mountToolsPageGlobals } from "./testI18n.js";

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

describe("RelayHostModerationPage.vue", () => {
    beforeEach(() => {
        vi.clearAllMocks();
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

    const mountPage = (props = {}) =>
        mount(RelayHostModerationPage, {
            props: {
                hub: makeHub(),
                initialTab: "members",
                roomFilter: null,
                ...props,
            },
            global: mountToolsPageGlobals(),
        });

    it("status tab fetches stats and renders stat cards and events", async () => {
        const wrapper = mountPage();
        window.api.get.mockImplementation(async (url) => {
            if (url === "/api/v1/config") {
                return { data: { identity_hash: LOCAL_HASH } };
            }
            if (url.includes("/stats")) {
                return {
                    data: {
                        stats: {
                            sessions: 2,
                            links_total: 5,
                            messages_relayed: 42,
                            rate_limited_drops: 3,
                            control_drops: 1,
                            session_cap_drops: 0,
                            peer_cap_drops: 0,
                            kicks: 1,
                            bans: 0,
                            banned_disconnects: 0,
                            uptime_s: 120,
                        },
                        events: [
                            { ts: 1700000000, type: "join", peer: "a".repeat(64), room: "general", detail: null },
                            { ts: 1700000050, type: "rate_limited", peer: "b".repeat(64), room: null, detail: "msg" },
                        ],
                    },
                };
            }
            return { data: {} };
        });

        wrapper.vm.setTab("status");
        await wrapper.vm.$nextTick();
        await vi.waitFor(() => expect(wrapper.vm.hubStats).toBeTruthy());

        expect(wrapper.vm.statCards.find((c) => c.key === "messages").value).toBe(42);
        expect(wrapper.vm.statCards.find((c) => c.key === "drops").value).toBe(4);
        expect(wrapper.vm.statCards.find((c) => c.key === "drops").warn).toBe(true);
        expect(wrapper.vm.eventLabel({ type: "join" })).toBe("joined");
        expect(wrapper.vm.eventLabel({ type: "unknown_type" })).toBe("unknown_type");
        expect(wrapper.vm.isWarnEvent({ type: "rate_limited" })).toBe(true);
        expect(wrapper.vm.isWarnEvent({ type: "join" })).toBe(false);
        expect(wrapper.vm.formatTimeAgo(Date.now() / 1000 - 5)).toMatch(/s$/);
    });

    it("kicks using the member room when there is no room filter", async () => {
        const wrapper = mountPage();
        await wrapper.vm.fetchMembers();

        await wrapper.vm.moderate(makeMember(), "kick");

        expect(window.api.post).toHaveBeenCalledWith(`/api/v1/rrc/servers/${HUB_ID}/moderate`, {
            action: "kick",
            peer: PEER_HASH,
            room: "lobby",
        });
    });

    it("uses the room filter when set", async () => {
        const wrapper = mountPage({ roomFilter: "ops" });
        await wrapper.vm.fetchMembers();

        await wrapper.vm.moderate(makeMember({ rooms: ["lobby", "ops"] }), "kick");

        expect(window.api.post).toHaveBeenCalledWith(`/api/v1/rrc/servers/${HUB_ID}/moderate`, {
            action: "kick",
            peer: PEER_HASH,
            room: "ops",
        });
    });

    it("blocks moderating the local identity", async () => {
        const wrapper = mountPage();
        await wrapper.vm.ensureLocalIdentity();

        await wrapper.vm.moderate(makeMember({ hash: LOCAL_HASH }), "kick");

        expect(window.api.post).not.toHaveBeenCalled();
        expect(ToastUtils.warning).toHaveBeenCalled();
    });
});
