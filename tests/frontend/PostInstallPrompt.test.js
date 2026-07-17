// SPDX-License-Identifier: 0BSD

import { describe, it, expect, beforeEach, afterEach, vi } from "vitest";
import { mount } from "@vue/test-utils";
import { createI18n } from "vue-i18n";
import { createVuetify } from "vuetify";
import PostInstallPromptHost from "../../meshchatx/src/frontend/components/PostInstallPromptHost.vue";
import {
    clearPromptSeenState,
    getSeenRevision,
    markPromptSeen,
    shouldShowPrompt,
} from "../../meshchatx/src/frontend/js/postInstallPromptState.js";
import {
    postInstallPromptRegistry,
    registerPostInstallPrompt,
    listPostInstallPromptsByPriority,
} from "../../meshchatx/src/frontend/js/registries/postInstallPromptRegistry.js";

const i18n = createI18n({
    legacy: false,
    locale: "en",
    messages: {
        en: {
            common: { continue: "Continue" },
            post_install: {
                demo_title: "Demo title",
                demo_desc: "Demo body",
                demo_primary: "Got it",
                demo_secondary: "Later",
            },
        },
    },
});
const vuetify = createVuetify();

describe("postInstallPromptState", () => {
    beforeEach(() => {
        clearPromptSeenState();
    });

    it("shows until revision is marked seen", () => {
        expect(shouldShowPrompt("demo", 1)).toBe(true);
        markPromptSeen("demo", 1);
        expect(shouldShowPrompt("demo", 1)).toBe(false);
        expect(getSeenRevision("demo")).toBe(1);
    });

    it("re-shows when revision is bumped", () => {
        markPromptSeen("demo", 1);
        expect(shouldShowPrompt("demo", 2)).toBe(true);
        markPromptSeen("demo", 2);
        expect(shouldShowPrompt("demo", 2)).toBe(false);
    });
});

describe("postInstallPromptRegistry", () => {
    beforeEach(() => {
        postInstallPromptRegistry.clear();
    });

    it("orders by priority then id", () => {
        registerPostInstallPrompt({
            id: "b_low",
            revision: 1,
            priority: 1,
            titleKey: "post_install.demo_title",
        });
        registerPostInstallPrompt({
            id: "a_high",
            revision: 1,
            priority: 10,
            titleKey: "post_install.demo_title",
        });
        registerPostInstallPrompt({
            id: "c_high",
            revision: 1,
            priority: 10,
            titleKey: "post_install.demo_title",
        });
        expect(listPostInstallPromptsByPriority().map((e) => e.id)).toEqual(["a_high", "c_high", "b_low"]);
    });

    it("rejects revision below 1", () => {
        expect(() =>
            registerPostInstallPrompt({
                id: "bad",
                revision: 0,
                titleKey: "post_install.demo_title",
            })
        ).toThrow(/revision/);
    });
});

describe("PostInstallPromptHost", () => {
    beforeEach(() => {
        clearPromptSeenState();
        postInstallPromptRegistry.clear();
    });

    afterEach(() => {
        clearPromptSeenState();
        postInstallPromptRegistry.clear();
    });

    it("showNext opens the highest priority pending prompt", async () => {
        registerPostInstallPrompt({
            id: "low",
            revision: 1,
            priority: 1,
            titleKey: "post_install.demo_title",
            descriptionKey: "post_install.demo_desc",
            primaryLabelKey: "post_install.demo_primary",
        });
        registerPostInstallPrompt({
            id: "high",
            revision: 1,
            priority: 50,
            titleKey: "post_install.demo_title",
            descriptionKey: "post_install.demo_desc",
            primaryLabelKey: "post_install.demo_primary",
        });

        const wrapper = mount(PostInstallPromptHost, {
            global: { plugins: [i18n, vuetify] },
        });
        expect(await wrapper.vm.showNext()).toBe(true);
        await wrapper.vm.$nextTick();
        expect(wrapper.vm.visible).toBe(true);
        expect(wrapper.vm.activeEntry?.id).toBe("high");
    });

    it("primary dismisses and marks the revision seen", async () => {
        const onPrimary = vi.fn();
        registerPostInstallPrompt({
            id: "once",
            revision: 3,
            titleKey: "post_install.demo_title",
            primaryLabelKey: "post_install.demo_primary",
            onPrimary,
        });

        const wrapper = mount(PostInstallPromptHost, {
            global: { plugins: [i18n, vuetify] },
        });
        await wrapper.vm.showNext();
        await wrapper.vm.onPrimary();
        expect(onPrimary).toHaveBeenCalled();
        expect(wrapper.vm.visible).toBe(false);
        expect(getSeenRevision("once")).toBe(3);
        expect(await wrapper.vm.showNext()).toBe(false);
    });

    it("skips prompts when shouldShow returns false", async () => {
        registerPostInstallPrompt({
            id: "gated",
            revision: 1,
            titleKey: "post_install.demo_title",
            shouldShow: () => false,
        });
        const wrapper = mount(PostInstallPromptHost, {
            global: { plugins: [i18n, vuetify] },
        });
        expect(await wrapper.vm.showNext()).toBe(false);
    });
});
