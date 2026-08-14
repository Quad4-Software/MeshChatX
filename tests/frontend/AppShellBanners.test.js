// SPDX-License-Identifier: 0BSD

import { describe, expect, it } from "vitest";
import { mount } from "@vue/test-utils";
import AppShellBanners from "@/components/layout/AppShellBanners.vue";

describe("AppShellBanners LAN bind warning", () => {
    it("shows the LAN banner, emits open-settings, and dismiss", async () => {
        const wrapper = mount(AppShellBanners, {
            props: {
                showLanBindNoAuth: true,
                lanBindNoAuthLabel: "LAN bind without a password",
                openSettingsLabel: "Open settings",
                dismissLanBindNoAuthLabel: "Dismiss",
            },
        });
        expect(wrapper.text()).toContain("LAN bind without a password");
        const settingsButton = wrapper.findAll("button").find((b) => b.text() === "Open settings");
        expect(settingsButton).toBeTruthy();
        await settingsButton.trigger("click");
        expect(wrapper.emitted("open-settings")).toHaveLength(1);
        const dismissButton = wrapper.findAll("button").find((b) => b.text() === "Dismiss");
        expect(dismissButton).toBeTruthy();
        await dismissButton.trigger("click");
        expect(wrapper.emitted("dismiss-lan-bind-no-auth")).toHaveLength(1);
        wrapper.unmount();
    });

    it("hides the LAN banner when the prop is off", () => {
        const wrapper = mount(AppShellBanners, {
            props: {
                showLanBindNoAuth: false,
                lanBindNoAuthLabel: "LAN bind without a password",
                openSettingsLabel: "Open settings",
                dismissLanBindNoAuthLabel: "Dismiss",
            },
        });
        expect(wrapper.text()).not.toContain("LAN bind without a password");
        wrapper.unmount();
    });
});
