// SPDX-License-Identifier: 0BSD

import GlobalEmitter from "../../../js/GlobalEmitter.js";
import { BATTERY_SAVER_CHANGED_EVENT } from "../../../js/settings/batterySaverPrefs.js";
import { VISUALISER_DISPLAY_PREFS_CHANGED } from "./visualiserPrefs.js";

export function bindVisualiserEvents(options: {
    onConfigUpdated: () => void;
    onPrefsChanged: () => void;
    onBatterySaverChanged: () => void;
    onIdentitySwitched: () => void;
    onThemeChanged: () => void;
}): () => void {
    GlobalEmitter.on("config-updated", options.onConfigUpdated);
    GlobalEmitter.on(VISUALISER_DISPLAY_PREFS_CHANGED, options.onPrefsChanged);
    GlobalEmitter.on(BATTERY_SAVER_CHANGED_EVENT, options.onBatterySaverChanged);
    GlobalEmitter.on("identity-switched", options.onIdentitySwitched);

    let themeObserver: MutationObserver | null = null;
    if (typeof document !== "undefined") {
        themeObserver = new MutationObserver(options.onThemeChanged);
        themeObserver.observe(document.documentElement, { attributes: true, attributeFilter: ["class"] });
    }

    return () => {
        GlobalEmitter.off("config-updated", options.onConfigUpdated);
        GlobalEmitter.off(VISUALISER_DISPLAY_PREFS_CHANGED, options.onPrefsChanged);
        GlobalEmitter.off(BATTERY_SAVER_CHANGED_EVENT, options.onBatterySaverChanged);
        GlobalEmitter.off("identity-switched", options.onIdentitySwitched);
        if (themeObserver) {
            themeObserver.disconnect();
        }
    };
}
