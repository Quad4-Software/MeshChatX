import { describe, it, expect, vi, beforeEach } from "vitest";
import { mount } from "@vue/test-utils";
import { createI18n } from "vue-i18n";
import { createVuetify } from "vuetify";
import AndroidStorageChoicePrompt from "../../meshchatx/src/frontend/components/AndroidStorageChoicePrompt.vue";
import en from "../../meshchatx/src/frontend/locales/en.json";

const scheduleCopyToExternalAndRestart = vi.fn(() => true);
const keepInternalAndDismiss = vi.fn(() => true);
const restartApp = vi.fn(() => true);
const getStatus = vi.fn(() => ({
    needs_upgrade_prompt: true,
    active_path: "/data/user/0/com.meshchatx/files/meshchatx",
}));

vi.mock("../../meshchatx/src/frontend/js/AndroidStorageBridge.js", () => ({
    default: class MockAndroidStorageBridge {
        isAndroidHost() {
            return true;
        }

        getStatus() {
            return getStatus();
        }

        scheduleCopyToExternalAndRestart() {
            return scheduleCopyToExternalAndRestart();
        }

        keepInternalAndDismiss() {
            return keepInternalAndDismiss();
        }

        restartApp() {
            return restartApp();
        }
    },
}));

const i18n = createI18n({ legacy: false, locale: "en", messages: { en } });
const vuetify = createVuetify();

describe("AndroidStorageChoicePrompt", () => {
    beforeEach(() => {
        vi.clearAllMocks();
    });

    it("showUpgrade opens dialog when status requires prompt", async () => {
        const wrapper = mount(AndroidStorageChoicePrompt, {
            props: { variant: "upgrade" },
            global: { plugins: [i18n, vuetify] },
        });
        expect(wrapper.vm.showUpgrade()).toBe(true);
        await wrapper.vm.$nextTick();
        expect(wrapper.vm.visible).toBe(true);
    });

    it("primary action schedules copy and restarts", async () => {
        const wrapper = mount(AndroidStorageChoicePrompt, {
            props: { variant: "upgrade" },
            global: { plugins: [i18n, vuetify] },
        });
        wrapper.vm.showUpgrade();
        await wrapper.vm.onPrimary();
        expect(scheduleCopyToExternalAndRestart).toHaveBeenCalled();
        expect(restartApp).toHaveBeenCalled();
    });
});
