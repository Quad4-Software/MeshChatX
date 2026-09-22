import en from "../../meshchatx/src/frontend/locales/en.json";
import { registerFallbackMessages, t } from "../../meshchatx/src/frontend/js/i18n.js";

/**
 * Ensure the framework-free t() lookup has English messages for tests.
 * setup.js already registers en on boot. Call again when a test clears translators.
 */
export function createTestI18n() {
    registerFallbackMessages(en);
    return { t, locale: "en" };
}

export function mountToolsPageGlobals() {
    createTestI18n();
    return {
        t,
        stubs: {
            MaterialDesignIcon: true,
        },
    };
}
