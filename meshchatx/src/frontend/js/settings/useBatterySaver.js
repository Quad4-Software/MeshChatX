// @ts-check

import { ref } from "vue";

import { apiPath } from "../constants.js";
import ToastUtils from "../ToastUtils.js";
import { loadBatterySaverPrefs, saveBatterySaverPrefs } from "./batterySaverPrefs.js";
import { applyBatterySaverBitrateLimits, restoreBatterySaverBitrateLimits } from "./batterySaverBitrateApply.js";

/**
 * Battery saver prefs and interface bitrate limits for the battery
 * section of SettingsPage: stored prefs, per-interface bitrate rows,
 * busy flag, and apply/restore actions.
 *
 * options.t is the host i18n function so toasts keep the component locale.
 */
export function useBatterySaver(options = {}) {
    const t = options.t || ((key) => key);

    const batterySaver = ref(loadBatterySaverPrefs());
    const batteryInterfaceRows = ref([]);
    const batteryBitrateBusy = ref(false);

    function loadBatterySaverPrefsFromStorage() {
        batterySaver.value = loadBatterySaverPrefs();
        if (!batterySaver.value.interfaceBitrateLimits) {
            batterySaver.value.interfaceBitrateLimits = {};
        }
    }

    async function loadBatteryInterfaceRows() {
        try {
            const response = await window.api.get(apiPath("/reticulum/interfaces"));
            const interfaces = response?.data?.interfaces || {};
            batteryInterfaceRows.value = Object.entries(interfaces)
                .map(([name, iface]) => ({
                    name,
                    type: iface?.type || "",
                    bitrate: iface?.bitrate ?? null,
                }))
                .sort((a, b) => a.name.localeCompare(b.name));
            for (const row of batteryInterfaceRows.value) {
                if (batterySaver.value.interfaceBitrateLimits[row.name] == null && row.bitrate != null) {
                    const n = Number(row.bitrate);
                    if (Number.isFinite(n) && n >= 0) {
                        // leave unset so empty means "no forced limit"
                    }
                }
            }
        } catch {
            batteryInterfaceRows.value = [];
        }
    }

    function patchBatterySaver(patch) {
        batterySaver.value = saveBatterySaverPrefs(patch);
        if (!batterySaver.value.interfaceBitrateLimits) {
            batterySaver.value.interfaceBitrateLimits = {};
        }
    }

    function onBatterySaverEnabledChange(val) {
        const enabled = val === true;
        patchBatterySaver({ enabled });
        if (enabled && batterySaver.value.applyInterfaceBitrateLimits) {
            applyBatteryBitrateLimitsNow();
        } else if (!enabled && Object.keys(batterySaver.value.interfaceBitratePrevious || {}).length > 0) {
            restoreBatteryBitrateLimitsNow();
        }
    }

    function onBatteryBitrateLimitChange(name) {
        // The v-model can write raw strings ("" when cleared) before this runs.
        /** @type {Record<string, any>} */
        const limits = { ...(batterySaver.value.interfaceBitrateLimits || {}) };
        const raw = limits[name];
        if (raw === "" || raw == null || Number.isNaN(Number(raw))) {
            delete limits[name];
        } else {
            limits[name] = Math.max(0, Math.round(Number(raw)));
        }
        patchBatterySaver({ interfaceBitrateLimits: limits });
    }

    async function applyBatteryBitrateLimitsNow() {
        if (batteryBitrateBusy.value) return;
        batteryBitrateBusy.value = true;
        try {
            patchBatterySaver({
                applyInterfaceBitrateLimits: true,
                interfaceBitrateLimits: { ...(batterySaver.value.interfaceBitrateLimits || {}) },
            });
            const result = await applyBatterySaverBitrateLimits({ reload: true });
            loadBatterySaverPrefsFromStorage();
            if (result.updated.length === 0) {
                ToastUtils.error(t("settings.battery.bitrates_none_applied"));
            } else {
                ToastUtils.success(t("settings.battery.bitrates_applied", { count: result.updated.length }));
            }
            await loadBatteryInterfaceRows();
        } catch (e) {
            console.error(e);
            ToastUtils.error(t("settings.battery.bitrates_apply_failed"));
        } finally {
            batteryBitrateBusy.value = false;
        }
    }

    async function restoreBatteryBitrateLimitsNow() {
        if (batteryBitrateBusy.value) return;
        batteryBitrateBusy.value = true;
        try {
            const result = await restoreBatterySaverBitrateLimits({ reload: true });
            loadBatterySaverPrefsFromStorage();
            if (result.updated.length === 0) {
                ToastUtils.error(t("settings.battery.bitrates_none_restored"));
            } else {
                ToastUtils.success(t("settings.battery.bitrates_restored", { count: result.updated.length }));
            }
            await loadBatteryInterfaceRows();
        } catch (e) {
            console.error(e);
            ToastUtils.error(t("settings.battery.bitrates_restore_failed"));
        } finally {
            batteryBitrateBusy.value = false;
        }
    }

    return {
        batterySaver,
        batteryInterfaceRows,
        batteryBitrateBusy,
        loadBatterySaverPrefsFromStorage,
        loadBatteryInterfaceRows,
        patchBatterySaver,
        onBatterySaverEnabledChange,
        onBatteryBitrateLimitChange,
        applyBatteryBitrateLimitsNow,
        restoreBatteryBitrateLimitsNow,
    };
}
