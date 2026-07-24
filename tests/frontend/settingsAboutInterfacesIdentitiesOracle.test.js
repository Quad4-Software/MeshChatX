// SPDX-License-Identifier: 0BSD

import { readFileSync } from "fs";
import { join } from "path";
import { describe, expect, it, vi, afterEach, beforeEach } from "vitest";
import { mount } from "@vue/test-utils";
import IdentitiesPage from "../../meshchatx/src/frontend/components/settings/IdentitiesPage.vue";
import AboutPage from "../../meshchatx/src/frontend/components/about/AboutPage.vue";
import GlobalEmitter from "../../meshchatx/src/frontend/js/GlobalEmitter";
import DialogUtils from "../../meshchatx/src/frontend/js/DialogUtils";
import ToastUtils from "../../meshchatx/src/frontend/js/ToastUtils";
import ElectronUtils from "../../meshchatx/src/frontend/js/ElectronUtils";

vi.mock("../../meshchatx/src/frontend/js/ToastUtils", () => ({
    default: {
        success: vi.fn(),
        error: vi.fn(),
        warning: vi.fn(),
        info: vi.fn(),
    },
}));

vi.mock("../../meshchatx/src/frontend/js/DialogUtils", () => ({
    default: {
        confirm: vi.fn().mockResolvedValue(true),
        alert: vi.fn(),
    },
}));

vi.mock("../../meshchatx/src/frontend/js/DownloadUtils", () => ({
    default: {
        downloadFromApiResponse: vi.fn(),
        downloadFile: vi.fn(),
    },
}));

vi.mock("../../meshchatx/src/frontend/js/ElectronUtils", () => ({
    default: {
        isElectron: () => false,
        relaunch: vi.fn(),
        getMemoryUsage: vi.fn(),
    },
}));

vi.mock("../../meshchatx/src/frontend/js/registries/wsEventRegistry.js", () => ({
    onWsEvent: vi.fn(),
    offWsEvent: vi.fn(),
}));

vi.mock("../../meshchatx/src/frontend/js/deviceBattery.js", () => ({
    appBatteryUsageToneClass: () => "",
    batteryStatusIconName: () => "battery",
    formatAppBatteryShareLabel: () => "",
    formatAppBatteryUsageLabel: () => "",
    formatProcessUptime: () => "",
    getDeviceBatteryStatus: vi.fn().mockResolvedValue(null),
    isNativeBatteryStatus: () => false,
}));

describe("settings/about/interfaces/identities exploratory oracles", () => {
    afterEach(() => {
        vi.clearAllMocks();
        vi.useRealTimers();
        delete window.api;
    });

    it("failed identity switch does not emit identity-switched (avoids wiping keep-alive UI)", async () => {
        const emitSpy = vi.spyOn(GlobalEmitter, "emit");
        window.api = {
            get: vi.fn().mockResolvedValue({
                data: {
                    identities: [
                        { hash: "hash1", display_name: "A", is_current: true },
                        { hash: "hash2", display_name: "B", is_current: false },
                    ],
                },
            }),
            post: vi.fn().mockRejectedValue({ response: { data: { message: "busy" } } }),
        };

        const wrapper = mount(IdentitiesPage, {
            global: {
                stubs: {
                    MaterialDesignIcon: true,
                    LxmfUserIcon: true,
                },
                mocks: {
                    $t: (k) => k,
                },
            },
        });
        await wrapper.vm.$nextTick();
        await wrapper.vm.getIdentities();
        emitSpy.mockClear();

        await wrapper.vm.switchIdentity({
            hash: "hash2",
            display_name: "B",
            is_current: false,
        });

        const emitted = emitSpy.mock.calls.map((c) => c[0]);
        expect(emitted).toContain("identity-switching-start");
        expect(emitted).toContain("identity-switching-abort");
        expect(emitted).not.toContain("identity-switched");
        expect(emitted).not.toContain("identity-switched-apply");
        expect(ToastUtils.error).toHaveBeenCalled();
        wrapper.unmount();
        emitSpy.mockRestore();
    });

    it("SettingsPage listens for identity-switched and refreshes config", () => {
        const src = readFileSync(
            join(process.cwd(), "meshchatx/src/frontend/components/settings/SettingsPage.vue"),
            "utf8"
        );
        expect(src).toContain('GlobalEmitter.on("identity-switched"');
        expect(src).toContain("onIdentitySwitched()");
        expect(src).toMatch(/onIdentitySwitched\(\)\s*\{[\s\S]*getConfig\(\)/);
    });

    it("AboutPage listens for identity-switched and refreshes backups/snapshots", () => {
        const src = readFileSync(
            join(process.cwd(), "meshchatx/src/frontend/components/about/AboutPage.vue"),
            "utf8"
        );
        expect(src).toContain('GlobalEmitter.on("identity-switched"');
        expect(src).toMatch(/onIdentitySwitched\(\)\s*\{[\s\S]*listSnapshots\(\)/);
        expect(src).toMatch(/onIdentitySwitched\(\)\s*\{[\s\S]*listAutoBackups\(\)/);
    });

    it("InterfacesPage listens for identity-switched and reloads interface lists", () => {
        const src = readFileSync(
            join(process.cwd(), "meshchatx/src/frontend/components/interfaces/InterfacesPage.vue"),
            "utf8"
        );
        expect(src).toContain('GlobalEmitter.on("identity-switched"');
        expect(src).toMatch(/onIdentitySwitched\(\)\s*\{[\s\S]*loadInterfaces\(\)/);
    });

    it("About restoreFromSnapshot guards restoreInProgress and reloads web UI", async () => {
        vi.useFakeTimers();
        const reloadSpy = vi.fn();
        const originalLocation = window.location;
        Object.defineProperty(window, "location", {
            configurable: true,
            value: { reload: reloadSpy },
        });

        const ctx = {
            restoreInProgress: false,
            isElectron: false,
            $t: (k) => k,
            scheduleRestoreRelaunch: AboutPage.methods.scheduleRestoreRelaunch,
        };
        ctx.scheduleRestoreRelaunch = AboutPage.methods.scheduleRestoreRelaunch.bind(ctx);

        window.api = {
            post: vi.fn().mockResolvedValue({ data: { status: "success" } }),
        };

        const first = AboutPage.methods.restoreFromSnapshot.call(ctx, "/storage/snapshots/a.zip");
        expect(ctx.restoreInProgress).toBe(true);
        const second = AboutPage.methods.restoreFromSnapshot.call(ctx, "/storage/snapshots/b.zip");
        await Promise.all([first, second]);

        expect(window.api.post).toHaveBeenCalledTimes(1);
        expect(DialogUtils.confirm).toHaveBeenCalledTimes(1);
        expect(ToastUtils.success).toHaveBeenCalled();

        await vi.advanceTimersByTimeAsync(2000);
        expect(reloadSpy).toHaveBeenCalled();
        expect(ElectronUtils.relaunch).not.toHaveBeenCalled();
        expect(ctx.restoreInProgress).toBe(false);

        Object.defineProperty(window, "location", {
            configurable: true,
            value: originalLocation,
        });
    });
});
