// SPDX-License-Identifier: 0BSD

import { mount } from "@vue/test-utils";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import UpdatesSettingsSection from "../../meshchatx/src/frontend/components/settings/sections/UpdatesSettingsSection.vue";

vi.mock("../../meshchatx/src/frontend/js/DesktopUtils", () => ({
    default: {
        isDesktop: () => false,
        showPathInFolder: vi.fn(),
        copyTextToClipboard: vi.fn().mockResolvedValue(true),
    },
}));

const STATUS_DISABLED = {
    data: {
        enabled: false,
        current_version: "4.12.0",
        channel: "stable",
        settings: {
            enabled: false,
            auto_check: false,
            auto_download: false,
            peer_relay: false,
            apply_policy: "manual",
            channel: "",
            transport: "auto",
            custom_mirrors: [],
            signer_hashes: [],
            rns_seeds: [],
            max_download_mb: 2048,
            check_interval_hours: 24,
            rns_rate_kbps: 256,
            slow_link_kbps: 1000,
        },
        disclosure: {
            mirrors: [
                { name: "github", url: "https://github.com/Quad4-Software/MeshChatX" },
                { name: "forgejo", url: "https://git.quad4.io/reticulum/MeshChatX" },
                { name: "cdn", url: "https://cdn.quad4.io" },
            ],
            rns_destination: "meshchatx.update",
            signer_hashes: ["e46112d44649266d71fe2193e00a4710"],
            channel: "stable",
            note: "signed manifest only",
        },
        last_check: null,
        progress: { phase: "idle" },
        pending: null,
        peer_relay_active: false,
    },
};

const STATUS_ENABLED = {
    data: {
        ...STATUS_DISABLED.data,
        enabled: true,
        settings: { ...STATUS_DISABLED.data.settings, enabled: true },
    },
};

function makeApi(overrides = {}) {
    return {
        get: vi.fn((path) => {
            if (path.endsWith("/update/status")) {
                return Promise.resolve(overrides.status || STATUS_DISABLED);
            }
            if (path.endsWith("/update/pending")) {
                return Promise.resolve({ data: { pending: null } });
            }
            if (path.endsWith("/update/progress")) {
                return Promise.resolve({ data: { phase: "idle" } });
            }
            return Promise.resolve({ data: {} });
        }),
        post: vi.fn(() => Promise.resolve({ data: { status: "ok" } })),
        ...overrides.api,
    };
}

function mountSection(api) {
    window.api = api;
    return mount(UpdatesSettingsSection, {
        props: { visible: true },
        global: {
            mocks: {
                $t: (key, params) =>
                    params ? `${key}(${JSON.stringify(params)})` : key,
            },
        },
    });
}

describe("UpdatesSettingsSection", () => {
    beforeEach(() => {
        vi.useFakeTimers({ shouldAdvanceTime: true });
    });
    afterEach(() => {
        vi.useRealTimers();
        delete window.api;
    });

    it("shows disclosure and stays disabled by default", async () => {
        const api = makeApi();
        const wrapper = mountSection(api);
        await vi.waitFor(() => expect(wrapper.text()).toContain("4.12.0"));
        const text = wrapper.text();
        expect(text).toContain("updates.disclosure_title");
        expect(text).toContain("github.com/Quad4-Software/MeshChatX");
        expect(text).toContain("git.quad4.io/reticulum/MeshChatX");
        expect(text).toContain("cdn.quad4.io");
        expect(text).toContain("meshchatx.update");
        // disabled state: no opt-in controls visible, check button disabled
        const checkBtn = wrapper.findAll("button").find((b) =>
            b.text().includes("updates.check_now"),
        );
        expect(checkBtn.attributes("disabled")).toBeDefined();
        // only status/pending reads on mount; no check or settings writes
        const posts = api.post.mock.calls.map((c) => c[0]);
        expect(posts.filter((p) => p.includes("/update/check"))).toHaveLength(0);
        expect(posts.filter((p) => p.includes("/update/settings"))).toHaveLength(0);
        wrapper.unmount();
    });

    it("enables updates through the settings endpoint", async () => {
        // disabled status: exactly one checkbox (the enable toggle) is shown
        const api = makeApi({ status: STATUS_DISABLED });
        const wrapper = mountSection(api);
        await vi.waitFor(() => expect(wrapper.text()).toContain("4.12.0"));
        const boxes = wrapper.findAll('input[type="checkbox"]');
        expect(boxes).toHaveLength(1);
        const enableBox = boxes[0];
        expect(enableBox.element.checked).toBe(false);
        await enableBox.setValue(true);
        await vi.waitFor(() =>
            expect(
                api.post.mock.calls.some(
                    (c) =>
                        c[0].endsWith("/update/settings") &&
                        c[1] && c[1].enabled === true,
                ),
            ).toBe(true),
        );
        wrapper.unmount();
    });

    it("does not call check until the user asks", async () => {
        const api = makeApi({ status: STATUS_ENABLED });
        const wrapper = mountSection(api);
        await vi.waitFor(() => expect(wrapper.text()).toContain("4.12.0"));
        // enabled state shows controls; still no automatic check
        expect(
            api.post.mock.calls.filter((c) => c[0].endsWith("/update/check")),
        ).toHaveLength(0);
        const checkBtn = wrapper
            .findAll("button")
            .find((b) => b.text().includes("updates.check_now"));
        await checkBtn.trigger("click");
        await vi.waitFor(() =>
            expect(
                api.post.mock.calls.some((c) => c[0].endsWith("/update/check")),
            ).toBe(true),
        );
        wrapper.unmount();
    });

    it("shows pending update panel when one exists", async () => {
        const api = makeApi({
            status: {
                data: {
                    ...STATUS_ENABLED.data,
                    pending: {
                        file: "pkg.whl",
                        sha256: "ab".repeat(32),
                        kind: "wheel",
                        apply_policy: "manual",
                        artifacts: [
                            {
                                file: "pkg.whl",
                                version: "99.0.0",
                                apply: { mode: "manual", instructions: "install it" },
                            },
                        ],
                    },
                },
            },
        });
        // pending comes from /update/pending, override get
        api.get = vi.fn((path) => {
            if (path.endsWith("/update/status")) {
                return Promise.resolve({
                    data: { ...STATUS_ENABLED.data, pending: null },
                });
            }
            if (path.endsWith("/update/pending")) {
                return Promise.resolve({
                    data: {
                        pending: {
                            file: "pkg.whl",
                            apply_policy: "manual",
                            artifacts: [
                                {
                                    file: "pkg.whl",
                                    version: "99.0.0",
                                    apply: {
                                        mode: "manual",
                                        instructions: "install it manually",
                                    },
                                },
                            ],
                        },
                    },
                });
            }
            return Promise.resolve({ data: { phase: "idle" } });
        });
        const wrapper = mountSection(api);
        await vi.waitFor(() =>
            expect(wrapper.text()).toContain("updates.pending_ready"),
        );
        expect(wrapper.text()).toContain("pkg.whl");
        expect(wrapper.text()).toContain("install it manually");
        wrapper.unmount();
    });
});
