// SPDX-License-Identifier: 0BSD
import { cleanup, fireEvent, render } from "@testing-library/svelte";
import { afterEach, describe, expect, it, vi } from "vitest";
import AppShellBanners from "@/features/app-shell/components/AppShellBanners.svelte";

describe("AppShellBanners LAN bind warning", () => {
    afterEach(() => cleanup());

    it("shows the LAN banner, emits open-settings, and dismiss", async () => {
        const onopensettings = vi.fn();
        const ondismisslanbindnoauth = vi.fn();
        const { container } = render(AppShellBanners, {
            showLanBindNoAuth: true,
            lanBindNoAuthLabel: "LAN bind without a password",
            openSettingsLabel: "Open settings",
            dismissLanBindNoAuthLabel: "Dismiss",
            onopensettings,
            ondismisslanbindnoauth,
        });
        expect(container.textContent).toContain("LAN bind without a password");
        const buttons = [...container.querySelectorAll("button")];
        await fireEvent.click(buttons.find((b) => b.textContent === "Open settings"));
        expect(onopensettings).toHaveBeenCalledTimes(1);
        await fireEvent.click(buttons.find((b) => b.textContent === "Dismiss"));
        expect(ondismisslanbindnoauth).toHaveBeenCalledTimes(1);
    });

    it("hides the LAN banner when the prop is off", () => {
        const { container } = render(AppShellBanners, {
            showLanBindNoAuth: false,
            lanBindNoAuthLabel: "LAN bind without a password",
            openSettingsLabel: "Open settings",
            dismissLanBindNoAuthLabel: "Dismiss",
        });
        expect(container.textContent).not.toContain("LAN bind without a password");
    });
});
