// SPDX-License-Identifier: 0BSD

import { describe, it, expect, beforeEach, afterEach, vi } from "vitest";
import { mount } from "@vue/test-utils";
import { createI18n } from "vue-i18n";
import { createVuetify } from "vuetify";
import PostInstallPromptHost from "../../meshchatx/src/frontend/components/PostInstallPromptHost.vue";
import {
    POST_INSTALL_PROMPTS_STORAGE_KEY,
    clearPromptSeenState,
    getSeenRevision,
    markPromptSeen,
    readSeenMap,
    shouldShowPrompt,
    writeSeenMap,
} from "../../meshchatx/src/frontend/js/postInstallPromptState.js";
import {
    postInstallPromptRegistry,
    registerPostInstallPrompt,
    unregisterPostInstallPrompt,
    listPostInstallPrompts,
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

function mountHost() {
    return mount(PostInstallPromptHost, {
        global: { plugins: [i18n, vuetify] },
    });
}

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

    it("does not lower a previously seen revision", () => {
        markPromptSeen("demo", 5);
        markPromptSeen("demo", 2);
        expect(getSeenRevision("demo")).toBe(5);
        expect(shouldShowPrompt("demo", 5)).toBe(false);
        expect(shouldShowPrompt("demo", 6)).toBe(true);
    });

    it("ignores empty ids and non-positive revisions", () => {
        expect(shouldShowPrompt("", 1)).toBe(false);
        expect(shouldShowPrompt("demo", 0)).toBe(false);
        expect(shouldShowPrompt("demo", -1)).toBe(false);
        markPromptSeen("", 1);
        expect(readSeenMap()).toEqual({});
    });

    it("round-trips the seen map through localStorage", () => {
        writeSeenMap({ a: 1, b: 3 });
        expect(readSeenMap()).toEqual({ a: 1, b: 3 });
        expect(localStorage.getItem(POST_INSTALL_PROMPTS_STORAGE_KEY)).toContain('"b":3');
    });

    it("tolerates corrupt and non-object localStorage values", () => {
        localStorage.setItem(POST_INSTALL_PROMPTS_STORAGE_KEY, "not-json");
        expect(readSeenMap()).toEqual({});
        localStorage.setItem(POST_INSTALL_PROMPTS_STORAGE_KEY, JSON.stringify(["x"]));
        expect(readSeenMap()).toEqual({});
        localStorage.setItem(POST_INSTALL_PROMPTS_STORAGE_KEY, JSON.stringify({ ok: 2, bad: "nope", neg: -1 }));
        expect(readSeenMap()).toEqual({ ok: 2 });
    });

    it("floors fractional revisions when marking seen", () => {
        markPromptSeen("demo", 2.9);
        expect(getSeenRevision("demo")).toBe(2);
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
            }),
        ).toThrow(/revision/);
    });

    it("rejects missing id and titleKey", () => {
        expect(() => registerPostInstallPrompt({ revision: 1, titleKey: "x" })).toThrow(/id/);
        expect(() => registerPostInstallPrompt({ id: "no_title", revision: 1 })).toThrow(/titleKey/);
    });

    it("normalizes defaults and supports unregister", () => {
        registerPostInstallPrompt({
            id: "defaults",
            revision: 2.7,
            titleKey: "post_install.demo_title",
        });
        const entry = listPostInstallPrompts()[0];
        expect(entry.revision).toBe(2);
        expect(entry.priority).toBe(0);
        expect(entry.dismissOnPrimary).toBe(true);
        expect(entry.dismissOnSecondary).toBe(true);
        unregisterPostInstallPrompt("defaults");
        expect(listPostInstallPrompts()).toHaveLength(0);
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

        const wrapper = mountHost();
        expect(await wrapper.vm.showNext()).toBe(true);
        await wrapper.vm.$nextTick();
        expect(wrapper.vm.visible).toBe(true);
        expect(wrapper.vm.activeEntry?.id).toBe("high");
        expect(wrapper.vm.resolvedTitle).toBe("Demo title");
        expect(wrapper.vm.resolvedDescription).toBe("Demo body");
        expect(wrapper.vm.resolvedPrimaryLabel).toBe("Got it");
    });

    it("showNext returns true without switching when already visible", async () => {
        registerPostInstallPrompt({
            id: "once",
            revision: 1,
            titleKey: "post_install.demo_title",
        });
        const wrapper = mountHost();
        expect(await wrapper.vm.showNext()).toBe(true);
        expect(await wrapper.vm.showNext()).toBe(true);
        expect(wrapper.vm.activeEntry?.id).toBe("once");
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

        const wrapper = mountHost();
        await wrapper.vm.showNext();
        await wrapper.vm.onPrimary();
        expect(onPrimary).toHaveBeenCalled();
        expect(wrapper.vm.visible).toBe(false);
        expect(getSeenRevision("once")).toBe(3);
        expect(await wrapper.vm.showNext()).toBe(false);
        expect(wrapper.emitted("completed")?.[0]?.[0]).toEqual({ id: "once", revision: 3 });
    });

    it("keeps the dialog open when onPrimary returns false", async () => {
        registerPostInstallPrompt({
            id: "keep",
            revision: 1,
            titleKey: "post_install.demo_title",
            onPrimary: () => false,
        });
        const wrapper = mountHost();
        await wrapper.vm.showNext();
        await wrapper.vm.onPrimary();
        expect(wrapper.vm.visible).toBe(true);
        expect(getSeenRevision("keep")).toBe(0);
    });

    it("secondary dismisses when secondaryLabelKey is set", async () => {
        const onSecondary = vi.fn();
        registerPostInstallPrompt({
            id: "two_btn",
            revision: 1,
            titleKey: "post_install.demo_title",
            secondaryLabelKey: "post_install.demo_secondary",
            onSecondary,
        });
        const wrapper = mountHost();
        await wrapper.vm.showNext();
        expect(wrapper.vm.resolvedSecondaryLabel).toBe("Later");
        await wrapper.vm.onSecondary();
        expect(onSecondary).toHaveBeenCalled();
        expect(wrapper.vm.visible).toBe(false);
        expect(getSeenRevision("two_btn")).toBe(1);
    });

    it("ignores secondary when no secondary label is configured", async () => {
        registerPostInstallPrompt({
            id: "primary_only",
            revision: 1,
            titleKey: "post_install.demo_title",
        });
        const wrapper = mountHost();
        await wrapper.vm.showNext();
        await wrapper.vm.onSecondary();
        expect(wrapper.vm.visible).toBe(true);
        expect(getSeenRevision("primary_only")).toBe(0);
    });

    it("does not mark seen when dismissOnPrimary is false", async () => {
        registerPostInstallPrompt({
            id: "no_dismiss",
            revision: 1,
            titleKey: "post_install.demo_title",
            dismissOnPrimary: false,
        });
        const wrapper = mountHost();
        await wrapper.vm.showNext();
        await wrapper.vm.onPrimary();
        expect(wrapper.vm.visible).toBe(false);
        expect(getSeenRevision("no_dismiss")).toBe(0);
        expect(wrapper.emitted("completed")?.[0]?.[0]).toEqual({ id: "no_dismiss", revision: 1 });
    });

    it("skips prompts when shouldShow returns false", async () => {
        registerPostInstallPrompt({
            id: "gated",
            revision: 1,
            titleKey: "post_install.demo_title",
            shouldShow: () => false,
        });
        const wrapper = mountHost();
        expect(await wrapper.vm.showNext()).toBe(false);
    });

    it("skips prompts when shouldShow throws and continues to the next", async () => {
        const errSpy = vi.spyOn(console, "error").mockImplementation(() => {});
        registerPostInstallPrompt({
            id: "broken",
            revision: 1,
            priority: 100,
            titleKey: "post_install.demo_title",
            shouldShow: () => {
                throw new Error("boom");
            },
        });
        registerPostInstallPrompt({
            id: "ok",
            revision: 1,
            priority: 1,
            titleKey: "post_install.demo_title",
        });
        const wrapper = mountHost();
        expect(await wrapper.vm.showNext()).toBe(true);
        expect(wrapper.vm.activeEntry?.id).toBe("ok");
        errSpy.mockRestore();
    });

    it("awaits async shouldShow", async () => {
        registerPostInstallPrompt({
            id: "async_ok",
            revision: 1,
            titleKey: "post_install.demo_title",
            shouldShow: async () => true,
        });
        const wrapper = mountHost();
        expect(await wrapper.vm.showNext()).toBe(true);
        expect(wrapper.vm.activeEntry?.id).toBe("async_ok");
    });

    it("emits dismissed when visibility is cleared", async () => {
        registerPostInstallPrompt({
            id: "dismiss_emit",
            revision: 1,
            titleKey: "post_install.demo_title",
        });
        const wrapper = mountHost();
        await wrapper.vm.showNext();
        wrapper.vm.onVisibleUpdate(false);
        expect(wrapper.emitted("dismissed")).toBeTruthy();
        expect(wrapper.vm.activeEntry).toBeNull();
    });

    it("defaults primary label to common.continue", async () => {
        registerPostInstallPrompt({
            id: "default_label",
            revision: 1,
            titleKey: "post_install.demo_title",
        });
        const wrapper = mountHost();
        await wrapper.vm.showNext();
        expect(wrapper.vm.resolvedPrimaryLabel).toBe("Continue");
    });
});
