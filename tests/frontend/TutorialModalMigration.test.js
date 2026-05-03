import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { mount, flushPromises } from "@vue/test-utils";
import { createRouter, createWebHashHistory } from "vue-router";
import { createI18n } from "vue-i18n";
import { createVuetify } from "vuetify";
import TutorialModal from "../../meshchatx/src/frontend/components/TutorialModal.vue";
import en from "../../meshchatx/src/frontend/locales/en.json";
import ToastUtils from "../../meshchatx/src/frontend/js/ToastUtils";

vi.mock("../../meshchatx/src/frontend/js/GlobalState", () => ({
    default: {
        config: { theme: "light", language: "en" },
        hasPendingInterfaceChanges: false,
        modifiedInterfaceNames: new Set(),
    },
}));

vi.mock("../../meshchatx/src/frontend/js/ToastUtils", () => ({
    default: {
        success: vi.fn(),
        error: vi.fn(),
        warning: vi.fn(),
    },
}));

const axiosMock = { get: vi.fn(), post: vi.fn(), patch: vi.fn() };

const vuetify = createVuetify();

const i18n = createI18n({
    legacy: false,
    locale: "en",
    messages: { en },
});

function discoveryApiHandlers(migrationPayload) {
    return (url) => {
        if (url === "/api/v1/app/info") {
            return Promise.resolve({
                data: {
                    app_info: {
                        migration: migrationPayload,
                    },
                },
            });
        }
        if (url === "/api/v1/reticulum/discovery") {
            return Promise.resolve({ data: { discovery: {} } });
        }
        if (url === "/api/v1/community-interfaces") {
            return Promise.resolve({ data: { interfaces: [] } });
        }
        if (url === "/api/v1/reticulum/discovered-interfaces") {
            return Promise.resolve({ data: { interfaces: [], active: [] } });
        }
        return Promise.resolve({ data: {} });
    };
}

const dialogStubs = {
    LanguageSelector: true,
    MaterialDesignIcon: true,
    Toggle: true,
    VIcon: { template: '<span class="v-icon-stub"/>' },
};

const pageStubs = {
    VIcon: { template: '<span class="v-icon-stub"/>' },
    LanguageSelector: true,
    MaterialDesignIcon: true,
    Toggle: true,
};

describe("TutorialModal getting started migration", () => {
    beforeEach(() => {
        window.api = axiosMock;
        vi.clearAllMocks();
    });

    afterEach(() => {
        delete window.electron;
    });

    it("dialog show() loads migration offer when app_info reports show_choice", async () => {
        axiosMock.get.mockImplementation(
            discoveryApiHandlers({
                show_choice: true,
                legacy_path: "/home/x/.reticulum-meshchat",
                target_path: "/home/x/.reticulum-meshchatx",
                mode: "redirect_to_legacy",
            })
        );

        const router = createRouter({
            history: createWebHashHistory(),
            routes: [{ path: "/", name: "home", component: { template: "<div/>" } }],
        });
        await router.push("/");
        await router.isReady();

        const wrapper = mount(TutorialModal, {
            attachTo: document.body,
            global: { plugins: [router, vuetify, i18n], stubs: dialogStubs },
        });

        await wrapper.vm.show();
        await flushPromises();
        await wrapper.vm.$nextTick();

        expect(wrapper.vm.migrationOffer).toEqual(
            expect.objectContaining({
                show_choice: true,
                legacy_path: "/home/x/.reticulum-meshchat",
                target_path: "/home/x/.reticulum-meshchatx",
            })
        );
        await vi.waitFor(
            () => {
                const t = document.body.textContent || "";
                return (
                    t.includes(en.tutorial.migration_title) &&
                    t.includes(en.tutorial.migration_migrate) &&
                    t.includes(en.tutorial.migration_fresh)
                );
            },
            { timeout: 4000 }
        );

        wrapper.unmount();
    });

    it("dialog migrate posts storage-migration and toasts success", async () => {
        axiosMock.get.mockImplementation(
            discoveryApiHandlers({
                show_choice: true,
                legacy_path: "/a/.reticulum-meshchat",
                target_path: "/a/.reticulum-meshchatx",
            })
        );
        axiosMock.post.mockImplementation((url, body) => {
            if (url === "/api/v1/setup/storage-migration") {
                expect(body).toEqual({ action: "migrate" });
                return Promise.resolve({ data: { ok: true, restart_required: true } });
            }
            return Promise.resolve({ data: {} });
        });
        window.electron = { relaunch: vi.fn().mockResolvedValue(undefined) };

        const router = createRouter({
            history: createWebHashHistory(),
            routes: [{ path: "/", name: "home", component: { template: "<div/>" } }],
        });
        await router.push("/");
        await router.isReady();

        const wrapper = mount(TutorialModal, {
            attachTo: document.body,
            global: { plugins: [router, vuetify, i18n], stubs: dialogStubs },
        });

        await wrapper.vm.show();
        await flushPromises();
        await wrapper.vm.$nextTick();

        await wrapper.vm.migrationMigrate();
        await flushPromises();

        expect(axiosMock.post).toHaveBeenCalledWith("/api/v1/setup/storage-migration", { action: "migrate" });
        expect(ToastUtils.success).toHaveBeenCalledWith(en.tutorial.migration_done_restart);
        expect(window.electron.relaunch).toHaveBeenCalled();

        wrapper.unmount();
    });

    it("dialog fresh posts action fresh", async () => {
        axiosMock.get.mockImplementation(
            discoveryApiHandlers({
                show_choice: true,
                legacy_path: "/a/.reticulum-meshchat",
                target_path: "/a/.reticulum-meshchatx",
            })
        );
        axiosMock.post.mockResolvedValue({ data: { ok: true, restart_required: true } });

        const router = createRouter({
            history: createWebHashHistory(),
            routes: [{ path: "/", name: "home", component: { template: "<div/>" } }],
        });
        await router.push("/");
        await router.isReady();

        const wrapper = mount(TutorialModal, {
            attachTo: document.body,
            global: { plugins: [router, vuetify, i18n], stubs: dialogStubs },
        });

        await wrapper.vm.show();
        await flushPromises();
        await wrapper.vm.$nextTick();

        await wrapper.vm.migrationFresh();
        await flushPromises();

        expect(axiosMock.post).toHaveBeenCalledWith("/api/v1/setup/storage-migration", { action: "fresh" });
        expect(ToastUtils.success).toHaveBeenCalledWith(en.tutorial.migration_done_restart);

        wrapper.unmount();
    });

    it("dialog migration API error calls ToastUtils.error", async () => {
        axiosMock.get.mockImplementation(
            discoveryApiHandlers({
                show_choice: true,
                legacy_path: "/a/.reticulum-meshchat",
                target_path: "/a/.reticulum-meshchatx",
            })
        );
        axiosMock.post.mockRejectedValue({
            response: { data: { error: "target already has data" } },
        });

        const router = createRouter({
            history: createWebHashHistory(),
            routes: [{ path: "/", name: "home", component: { template: "<div/>" } }],
        });
        await router.push("/");
        await router.isReady();

        const wrapper = mount(TutorialModal, {
            attachTo: document.body,
            global: { plugins: [router, vuetify, i18n], stubs: dialogStubs },
        });

        await wrapper.vm.show();
        await flushPromises();
        await wrapper.vm.$nextTick();

        await wrapper.vm.migrationMigrate();
        await flushPromises();

        expect(ToastUtils.error).toHaveBeenCalledWith("target already has data");

        wrapper.unmount();
    });

    it("migrationMigrate does nothing when migrationOffer is null", async () => {
        axiosMock.get.mockImplementation(discoveryApiHandlers({ show_choice: false }));

        const router = createRouter({
            history: createWebHashHistory(),
            routes: [{ path: "/", name: "home", component: { template: "<div/>" } }],
        });
        await router.push("/");
        await router.isReady();

        const wrapper = mount(TutorialModal, {
            attachTo: document.body,
            global: { plugins: [router, vuetify, i18n], stubs: dialogStubs },
        });

        await wrapper.vm.show();
        await flushPromises();
        expect(wrapper.vm.migrationOffer).toBeNull();

        await wrapper.vm.migrationMigrate();
        await flushPromises();

        expect(axiosMock.post).not.toHaveBeenCalled();

        wrapper.unmount();
    });

    it("dialog omits migration panel when show_choice is false", async () => {
        axiosMock.get.mockImplementation(discoveryApiHandlers({ show_choice: false }));

        const router = createRouter({
            history: createWebHashHistory(),
            routes: [{ path: "/", name: "home", component: { template: "<div/>" } }],
        });
        await router.push("/");
        await router.isReady();

        const wrapper = mount(TutorialModal, {
            attachTo: document.body,
            global: { plugins: [router, vuetify, i18n], stubs: dialogStubs },
        });

        await wrapper.vm.show();
        await flushPromises();

        expect(wrapper.vm.migrationOffer).toBeNull();

        wrapper.unmount();
    });

    it("tutorial page mode loads migration offer on mount", async () => {
        axiosMock.get.mockImplementation(
            discoveryApiHandlers({
                show_choice: true,
                legacy_path: "/z/.reticulum-meshchat",
                target_path: "/z/.reticulum-meshchatx",
            })
        );

        const router = createRouter({
            history: createWebHashHistory(),
            routes: [
                {
                    path: "/tutorial",
                    name: "tutorial",
                    meta: { isPage: true },
                    component: { template: "<div/>" },
                },
            ],
        });
        await router.push("/tutorial");
        await router.isReady();

        const wrapper = mount(TutorialModal, {
            global: { plugins: [router, vuetify, i18n], stubs: pageStubs },
        });

        await flushPromises();
        await flushPromises();

        expect(wrapper.vm.migrationOffer).toEqual(
            expect.objectContaining({
                show_choice: true,
                legacy_path: "/z/.reticulum-meshchat",
            })
        );
        expect(wrapper.text()).toContain(en.tutorial.migration_title);

        wrapper.unmount();
    });

    it("refreshMigrationOffer leaves migration null when app_info has no migration", async () => {
        axiosMock.get.mockImplementation((url) => {
            if (url === "/api/v1/app/info") {
                return Promise.resolve({ data: { app_info: { version: "1.0.0" } } });
            }
            if (url === "/api/v1/reticulum/discovery") {
                return Promise.resolve({ data: { discovery: {} } });
            }
            if (url === "/api/v1/community-interfaces") {
                return Promise.resolve({ data: { interfaces: [] } });
            }
            if (url === "/api/v1/reticulum/discovered-interfaces") {
                return Promise.resolve({ data: { interfaces: [], active: [] } });
            }
            return Promise.resolve({ data: {} });
        });

        const router = createRouter({
            history: createWebHashHistory(),
            routes: [{ path: "/", name: "home", component: { template: "<div/>" } }],
        });
        await router.push("/");
        await router.isReady();

        const wrapper = mount(TutorialModal, {
            attachTo: document.body,
            global: { plugins: [router, vuetify, i18n], stubs: dialogStubs },
        });

        await wrapper.vm.refreshMigrationOffer();
        await flushPromises();

        expect(wrapper.vm.migrationOffer).toBeNull();

        wrapper.unmount();
    });
});
