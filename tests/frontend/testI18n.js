import { createI18n } from "vue-i18n";
import en from "../../meshchatx/src/frontend/locales/en.json";

export function createTestI18n() {
    return createI18n({
        legacy: false,
        locale: "en",
        fallbackLocale: "en",
        messages: { en },
    });
}

export function mountToolsPageGlobals() {
    const i18n = createTestI18n();
    return {
        plugins: [i18n],
        stubs: {
            MaterialDesignIcon: {
                template: '<div class="mdi-stub" :data-icon-name="iconName"></div>',
                props: ["iconName"],
            },
        },
    };
}
