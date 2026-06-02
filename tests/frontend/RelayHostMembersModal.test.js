import { mount } from "@vue/test-utils";
import { beforeEach, describe, expect, it, vi } from "vitest";

import RelayHostMembersModal from "@/components/relay/RelayHostMembersModal.vue";
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
    return { id: HUB_ID, name: "Hosted" };
}

function makeMember(overrides = {}) {
    return {
        hash: PEER_HASH,
        name: "alice",
        rooms: ["lobby"],
        ...overrides,
    };
}

describe("RelayHostMembersModal.vue", () => {
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
                return { data: {} };
            }),
            post: vi.fn(async () => ({ data: { message: "ok" } })),
        };
    });

    const mountModal = (props = {}) =>
        mount(RelayHostMembersModal, {
            props: {
                open: true,
                hub: makeHub(),
                room: null,
                ...props,
            },
            global: mountToolsPageGlobals(),
        });

    it("kicks using the member room when the modal has no room filter", async () => {
        const wrapper = mountModal();
        await wrapper.vm.fetchMembers();

        await wrapper.vm.moderate(makeMember(), "kick");

        expect(window.api.post).toHaveBeenCalledWith(`/api/v1/rrc/servers/${HUB_ID}/moderate`, {
            action: "kick",
            peer: PEER_HASH,
            room: "lobby",
        });
    });

    it("uses the modal room filter when set", async () => {
        const wrapper = mountModal({ room: "ops" });
        await wrapper.vm.fetchMembers();

        await wrapper.vm.moderate(makeMember({ rooms: ["lobby", "ops"] }), "kick");

        expect(window.api.post).toHaveBeenCalledWith(`/api/v1/rrc/servers/${HUB_ID}/moderate`, {
            action: "kick",
            peer: PEER_HASH,
            room: "ops",
        });
    });

    it("blocks moderating the local identity", async () => {
        const wrapper = mountModal();
        await wrapper.vm.ensureLocalIdentity();

        await wrapper.vm.moderate(makeMember({ hash: LOCAL_HASH }), "kick");

        expect(window.api.post).not.toHaveBeenCalled();
        expect(ToastUtils.warning).toHaveBeenCalled();
    });
});
