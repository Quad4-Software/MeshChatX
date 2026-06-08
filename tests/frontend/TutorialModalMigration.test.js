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
        if (url === "/api/v1/config") {
            return Promise.resolve({ data: { config: { display_name: "Anonymous Peer" } } });
        }
        if (url === "/api/v1/identities") {
            return Promise.resolve({
                data: {
                    identities: [{ hash: "default_identity", display_name: "Anonymous Peer", is_current: true }],
                },
            });
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

    it("identity step new mode applies display name and continues", async () => {
        axiosMock.get.mockImplementation(discoveryApiHandlers({ show_choice: false }));
        axiosMock.patch.mockResolvedValue({ data: {} });

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
        wrapper.vm.currentStep = 2;
        wrapper.vm.identityMode = "new";
        wrapper.vm.identityName = "Mesh User";
        await wrapper.vm.handlePrimaryAction();

        expect(axiosMock.patch).toHaveBeenCalledWith("/api/v1/config", { display_name: "Mesh User" });
        expect(wrapper.vm.currentStep).toBe(3);
        wrapper.unmount();
    });

    it("identity step import base32 switches to imported and deletes default on finish", async () => {
        axiosMock.get.mockImplementation(discoveryApiHandlers({ show_choice: false }));
        axiosMock.post.mockImplementation((url, body) => {
            if (url === "/api/v1/identity/restore") {
                expect(body).toEqual({
                    base32: "ABCD1234",
                    display_name: "Imported User",
                });
                return Promise.resolve({
                    data: { identity: { hash: "imported_hash" }, message: "ok" },
                });
            }
            if (url === "/api/v1/identities/switch") {
                expect(body).toEqual({ identity_hash: "imported_hash" });
                return Promise.resolve({ data: { hotswapped: true } });
            }
            if (url === "/api/v1/app/tutorial/seen") {
                return Promise.resolve({ data: {} });
            }
            return Promise.resolve({ data: {} });
        });
        axiosMock.delete = vi.fn().mockResolvedValue({ data: {} });

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

        wrapper.vm.currentStep = 2;
        wrapper.vm.identityMode = "import";
        wrapper.vm.identityName = "Imported User";
        wrapper.vm.identityImportBase32 = "ABCD1234";
        await wrapper.vm.handlePrimaryAction();

        expect(wrapper.vm.identityImportedHash).toBe("imported_hash");
        expect(wrapper.vm.currentStep).toBe(3);

        wrapper.vm.currentStep = wrapper.vm.totalSteps;
        await wrapper.vm.finishTutorial();
        expect(axiosMock.post).toHaveBeenCalledWith("/api/v1/identities/switch", {
            identity_hash: "imported_hash",
        });
        expect(axiosMock.delete).toHaveBeenCalledWith("/api/v1/identities/default_identity");
        wrapper.unmount();
    });

    it("identity import mode requires file or base32 input", async () => {
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

        wrapper.vm.currentStep = 2;
        wrapper.vm.identityMode = "import";
        wrapper.vm.identityImportBase32 = "   ";
        await wrapper.vm.handlePrimaryAction();

        expect(wrapper.vm.currentStep).toBe(2);
        expect(wrapper.vm.identityImportError).toBe(en.tutorial.identity_import_required);
        expect(axiosMock.post).not.toHaveBeenCalled();
        wrapper.unmount();
    });

    it("identity step new mode falls back to default username for blank input", async () => {
        axiosMock.get.mockImplementation(discoveryApiHandlers({ show_choice: false }));
        axiosMock.patch.mockResolvedValue({ data: {} });

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
        wrapper.vm.currentStep = 2;
        wrapper.vm.identityMode = "new";
        wrapper.vm.identityName = "   ";
        await wrapper.vm.handlePrimaryAction();

        expect(axiosMock.patch).toHaveBeenCalledWith("/api/v1/config", { display_name: "Anonymous Peer" });
        expect(wrapper.vm.currentStep).toBe(3);
        wrapper.unmount();
    });

    it("identity import continue is race-safe and only submits one restore request", async () => {
        axiosMock.get.mockImplementation(discoveryApiHandlers({ show_choice: false }));
        let resolveRestore;
        const restorePromise = new Promise((resolve) => {
            resolveRestore = resolve;
        });
        axiosMock.post.mockImplementation((url) => {
            if (url === "/api/v1/identity/restore") {
                return restorePromise;
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

        await wrapper.vm.show();
        await flushPromises();
        wrapper.vm.currentStep = 2;
        wrapper.vm.identityMode = "import";
        wrapper.vm.identityName = "Race User";
        wrapper.vm.identityImportBase32 = "RACEKEY";

        const p1 = wrapper.vm.handlePrimaryAction();
        const p2 = wrapper.vm.handlePrimaryAction();
        await flushPromises();

        expect(axiosMock.post).toHaveBeenCalledTimes(1);
        resolveRestore({
            data: {
                identity: { hash: "race_hash" },
            },
        });
        await Promise.all([p1, p2]);

        expect(wrapper.vm.identityImportedHash).toBe("race_hash");
        expect(wrapper.vm.currentStep).toBe(3);
        wrapper.unmount();
    });

    it("hides footer Continue on connection and bootstrap steps", async () => {
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

        wrapper.vm.currentStep = 3;
        await wrapper.vm.$nextTick();
        expect(wrapper.vm.showFooterContinue).toBe(false);

        wrapper.vm.currentStep = 4;
        await wrapper.vm.$nextTick();
        expect(wrapper.vm.showFooterContinue).toBe(false);

        wrapper.vm.currentStep = 5;
        await wrapper.vm.$nextTick();
        expect(wrapper.vm.showFooterContinue).toBe(true);

        wrapper.unmount();
    });

    it("nextStep on connection step without a mode shows warning and does not advance", async () => {
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
        wrapper.vm.currentStep = 3;
        wrapper.vm.connectionMode = null;
        wrapper.vm.nextStep();

        expect(wrapper.vm.currentStep).toBe(3);
        expect(ToastUtils.warning).toHaveBeenCalledWith(en.tutorial.connect_mode_required);

        wrapper.unmount();
    });

    it("useLocalMode stays on connection step when Reticulum reload fails", async () => {
        axiosMock.get.mockImplementation(discoveryApiHandlers({ show_choice: false }));
        axiosMock.post.mockImplementation((url) => {
            if (url === "/api/v1/reticulum/interfaces/add") {
                return Promise.resolve({ data: { message: "added" } });
            }
            if (url === "/api/v1/reticulum/reload") {
                return Promise.reject({ response: { data: { error: "reload failed" } } });
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

        await wrapper.vm.show();
        await flushPromises();
        wrapper.vm.currentStep = 3;
        await wrapper.vm.useLocalMode();
        await flushPromises();

        expect(axiosMock.post).toHaveBeenCalledWith("/api/v1/reticulum/interfaces/add", {
            name: "Local Network",
            type: "AutoInterface",
            enabled: true,
        });
        expect(wrapper.vm.currentStep).toBe(3);
        expect(ToastUtils.error).toHaveBeenCalledWith(en.tutorial.failed_reload_rns);

        wrapper.unmount();
    });

    it("confirmBootstraps reload failure keeps user on bootstrap step", async () => {
        axiosMock.get.mockImplementation((url) => {
            if (url === "/api/v1/community-interfaces") {
                return Promise.resolve({
                    data: {
                        interfaces: [
                            {
                                name: "Test TCP",
                                type: "TCPClientInterface",
                                target_host: "1.2.3.4",
                                target_port: 4242,
                            },
                        ],
                    },
                });
            }
            return discoveryApiHandlers({ show_choice: false })(url);
        });
        axiosMock.post.mockImplementation((url) => {
            if (url === "/api/v1/reticulum/interfaces/add") {
                return Promise.resolve({ data: { message: "added" } });
            }
            if (url === "/api/v1/reticulum/reload") {
                return Promise.reject({ response: { data: { error: "reload failed" } } });
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

        await wrapper.vm.show();
        await flushPromises();
        wrapper.vm.currentStep = 4;
        wrapper.vm.connectionMode = "discovery";
        wrapper.vm.selectedBootstrapKeys = ["comm:Test TCP"];
        await wrapper.vm.confirmBootstraps();
        await flushPromises();

        expect(wrapper.vm.currentStep).toBe(4);
        expect(ToastUtils.error).toHaveBeenCalledWith(en.tutorial.failed_reload_rns);

        wrapper.unmount();
    });

    it("finishTutorial blocks when pending interface reload fails", async () => {
        const GlobalState = (await import("../../meshchatx/src/frontend/js/GlobalState.js")).default;
        GlobalState.hasPendingInterfaceChanges = true;

        axiosMock.get.mockImplementation(discoveryApiHandlers({ show_choice: false }));
        axiosMock.post.mockImplementation((url) => {
            if (url === "/api/v1/reticulum/reload") {
                return Promise.reject({ response: { data: { error: "reload failed" } } });
            }
            if (url === "/api/v1/app/tutorial/seen") {
                return Promise.resolve({ data: {} });
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

        await wrapper.vm.show();
        await flushPromises();
        wrapper.vm.visible = true;
        wrapper.vm.currentStep = wrapper.vm.totalSteps;
        await wrapper.vm.finishTutorial();
        await flushPromises();

        expect(wrapper.vm.visible).toBe(true);
        expect(axiosMock.post).not.toHaveBeenCalledWith("/api/v1/app/tutorial/seen", expect.anything());

        GlobalState.hasPendingInterfaceChanges = false;
        wrapper.unmount();
    });

    it("finishTutorial keeps modal open and reports error when identity switch fails", async () => {
        axiosMock.get.mockImplementation(discoveryApiHandlers({ show_choice: false }));
        axiosMock.post.mockImplementation((url) => {
            if (url === "/api/v1/identities/switch") {
                return Promise.reject({ response: { data: { message: "switch failed" } } });
            }
            return Promise.resolve({ data: {} });
        });
        axiosMock.delete = vi.fn().mockResolvedValue({ data: {} });

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
        wrapper.vm.visible = true;
        wrapper.vm.currentStep = wrapper.vm.totalSteps;
        wrapper.vm.identityImportedHash = "imported_hash";
        wrapper.vm.originalIdentityHash = "default_identity";

        await wrapper.vm.finishTutorial();

        expect(wrapper.vm.visible).toBe(true);
        expect(axiosMock.delete).not.toHaveBeenCalled();
        expect(ToastUtils.error).toHaveBeenCalledWith("switch failed");
        wrapper.unmount();
    });
});
