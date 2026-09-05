// SPDX-License-Identifier: 0BSD

import { readFileSync } from "fs";
import { join } from "path";
import { describe, expect, it, vi, afterEach, beforeEach } from "vitest";
import { render, fireEvent, waitFor } from "@testing-library/svelte";
import IdentitiesPage from "../../meshchatx/src/frontend/features/settings/components/IdentitiesPage.svelte";
import { restoreFromSnapshot } from "../../meshchatx/src/frontend/features/about/lib/backupApi.ts";
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

describe("identity switch and settings UI contracts", () => {
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

        const { findByTitle } = render(IdentitiesPage);
        const switchBtn = await findByTitle("identities.switch");
        emitSpy.mockClear();

        await fireEvent.click(switchBtn);

        await waitFor(() => {
            const emitted = emitSpy.mock.calls.map((c) => c[0]);
            expect(emitted).toContain("identity-switching-start");
            expect(emitted).toContain("identity-switching-abort");
            expect(emitted).not.toContain("identity-switched");
            expect(emitted).not.toContain("identity-switched-apply");
            expect(ToastUtils.error).toHaveBeenCalled();
        });
        emitSpy.mockRestore();
    });

    it("SettingsPage listens for identity-switched and refreshes config", () => {
        const src = readFileSync(
            join(process.cwd(), "meshchatx/src/frontend/features/settings/components/SettingsPage.svelte"),
            "utf8"
        );
        expect(src).toContain('GlobalEmitter.on("identity-switched"');
        expect(src).toMatch(/on\("identity-switched"[\s\S]*getConfig\(\)/);
    });

    it("AboutPage listens for identity-switched and refreshes backups/snapshots", () => {
        const src = readFileSync(join(process.cwd(), "meshchatx/src/frontend/features/about/AboutPage.svelte"), "utf8");
        expect(src).toContain('GlobalEmitter.on("identity-switched"');
        expect(src).toMatch(/onIdentitySwitched\(\)[\s\S]*loadSnapshots\(\)/);
        expect(src).toMatch(/onIdentitySwitched\(\)[\s\S]*loadAutoBackups\(\)/);
    });

    it("InterfacesPage listens for identity-switched and reloads interface lists", () => {
        const src = readFileSync(
            join(process.cwd(), "meshchatx/src/frontend/features/interfaces/InterfacesPage.svelte"),
            "utf8"
        );
        expect(src).toContain('GlobalEmitter.on("identity-switched"');
        expect(src).toMatch(/handleIdentitySwitched\(\)\s*\{[\s\S]*loadInterfaces\(\)/);
    });

    it("About restoreFromSnapshot reloads web UI on success", async () => {
        vi.useFakeTimers();
        const reloadSpy = vi.fn();
        const originalLocation = window.location;
        Object.defineProperty(window, "location", {
            configurable: true,
            value: { reload: reloadSpy },
        });

        window.api = {
            post: vi.fn().mockResolvedValue({ data: { status: "success" } }),
        };

        const result = await restoreFromSnapshot("/storage/snapshots/a.zip", false);
        expect(result).toBe(true);

        expect(window.api.post).toHaveBeenCalledWith("/api/v1/database/restore", { path: "/storage/snapshots/a.zip" });
        expect(DialogUtils.confirm).toHaveBeenCalledTimes(1);
        expect(ToastUtils.success).toHaveBeenCalled();

        await vi.advanceTimersByTimeAsync(2000);
        expect(reloadSpy).toHaveBeenCalled();
        expect(ElectronUtils.relaunch).not.toHaveBeenCalled();

        Object.defineProperty(window, "location", {
            configurable: true,
            value: originalLocation,
        });
    });
});
