// SPDX-License-Identifier: 0BSD

import { describe, expect, it, vi, beforeEach, afterEach } from "vitest";
import { mount } from "@vue/test-utils";
import ConversationDropDownMenu from "../../meshchatx/src/frontend/components/messages/ConversationDropDownMenu.vue";

vi.mock("../../meshchatx/src/frontend/js/DialogUtils", () => ({
    default: {
        confirm: vi.fn(async () => true),
        alert: vi.fn(),
    },
}));

vi.mock("../../meshchatx/src/frontend/js/GlobalEmitter", () => ({
    default: {
        on: vi.fn(),
        off: vi.fn(),
        emit: vi.fn(),
    },
}));

vi.mock("../../meshchatx/src/frontend/js/GlobalState", () => ({
    default: {
        blockedDestinations: [],
        config: { telemetry_enabled: false },
    },
}));

const shareApkMock = vi.fn(() => true);

vi.mock("../../meshchatx/src/frontend/js/rnode/AndroidBridge.js", () => ({
    default: class AndroidBridge {
        shareApk() {
            return shareApkMock();
        }
    },
}));

vi.mock("../../meshchatx/src/frontend/js/ToastUtils", () => ({
    default: {
        error: vi.fn(),
        success: vi.fn(),
    },
}));

const peer = {
    destination_hash: "a".repeat(32),
    display_name: "Peer",
};

function mountMenu(compact = true) {
    return mount(ConversationDropDownMenu, {
        props: { peer, compact, hasFailedMessages: false },
        global: {
            mocks: { $t: (k) => k },
            stubs: {
                DropDownMenu: {
                    template: "<div><slot name='button' /><slot name='items' /></div>",
                },
                DropDownMenuItem: { template: "<button @click='$emit(\"click\")'><slot /></button>" },
                IconButton: {
                    props: ["title"],
                    template: "<button :title='title' @click='$emit(\"click\")'><slot /></button>",
                },
                MaterialDesignIcon: true,
            },
        },
    });
}

describe("ConversationDropDownMenu share APK", () => {
    beforeEach(() => {
        shareApkMock.mockReset().mockReturnValue(true);
        delete window.MeshChatXAndroid;
    });

    afterEach(() => {
        delete window.MeshChatXAndroid;
    });

    it("hides share APK when not on Android", () => {
        const wrapper = mountMenu(true);
        expect(wrapper.text()).not.toContain("messages.share_apk");
        wrapper.unmount();
    });

    it("shows share APK on Android and opens share sheet", async () => {
        window.MeshChatXAndroid = {
            getPlatform: () => "android",
            shareApk: vi.fn(),
        };
        const wrapper = mountMenu(true);
        expect(wrapper.text()).toContain("messages.share_apk");
        await wrapper.vm.onShareApk();
        expect(shareApkMock).toHaveBeenCalled();
        wrapper.unmount();
    });

    it("shows share APK in non-compact Android overflow menu", () => {
        window.MeshChatXAndroid = {
            getPlatform: () => "android",
            shareApk: vi.fn(),
        };
        const wrapper = mountMenu(false);
        expect(wrapper.text()).toContain("messages.share_apk");
        wrapper.unmount();
    });
});
