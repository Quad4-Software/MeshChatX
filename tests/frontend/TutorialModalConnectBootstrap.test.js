/* SPDX-License-Identifier: 0BSD */
/**
 * Adversarial / race oracles for tutorial connect + bootstrap flows.
 * Each case states an invariant and asserts an exact postcondition.
 */
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
        info: vi.fn(),
    },
}));

vi.mock("../../meshchatx/src/frontend/js/DialogUtils", () => ({
    default: {
        confirm: vi.fn().mockResolvedValue(true),
    },
}));

const axiosMock = { get: vi.fn(), post: vi.fn(), patch: vi.fn() };
const vuetify = createVuetify();
const i18n = createI18n({
    legacy: false,
    locale: "en",
    messages: { en },
});

const dialogStubs = {
    LanguageSelector: true,
    MaterialDesignIcon: true,
    Toggle: true,
    TutorialPrivacyStep: true,
    VIcon: { template: '<span class="v-icon-stub"/>' },
    VProgressCircular: { template: '<span class="progress-stub"/>' },
};

function tcpCommunity(n) {
    return Array.from({ length: n }, (_, i) => ({
        name: `Node ${i + 1}`,
        type: "TCPClientInterface",
        target_host: `10.0.0.${i + 1}`,
        target_port: 4242 + i,
        description: "community tcp",
    }));
}

function apiHandlers(communityInterfaces = []) {
    return (url) => {
        if (url === "/api/v1/app/info") {
            return Promise.resolve({ data: { app_info: { migration: { show_choice: false } } } });
        }
        if (url === "/api/v1/reticulum/discovery") {
            return Promise.resolve({ data: { discovery: { default_bootstrap_only: false } } });
        }
        if (url === "/api/v1/community-interfaces") {
            return Promise.resolve({ data: { interfaces: communityInterfaces } });
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

async function mountTutorial(communityInterfaces = tcpCommunity(6)) {
    axiosMock.get.mockImplementation(apiHandlers(communityInterfaces));
    axiosMock.post.mockResolvedValue({ data: { message: "ok" } });
    axiosMock.patch.mockResolvedValue({ data: { message: "ok" } });

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
    return wrapper;
}

describe("TutorialModal connect/bootstrap adversarial oracles", () => {
    beforeEach(() => {
        window.api = axiosMock;
        vi.clearAllMocks();
    });

    afterEach(() => {
        vi.useRealTimers();
    });

    it("H1: footer must not expose Finish Setup on connect or bootstrap steps", async () => {
        const wrapper = await mountTutorial();
        for (const step of [3, 4]) {
            wrapper.vm.currentStep = step;
            await wrapper.vm.$nextTick();
            expect(wrapper.vm.showFooterContinue).toBe(false);
            expect(wrapper.vm.currentStep === wrapper.vm.totalSteps).toBe(false);
            const finishButtons = wrapper.findAll("button").filter((b) => b.text().includes(en.tutorial.finish_setup));
            expect(finishButtons.length, `finish visible on step ${step}`).toBe(0);
        }
        wrapper.unmount();
    });

    it("H2: nextStep with recommended mode must enter bootstrap step 4 not skip to 5", async () => {
        const wrapper = await mountTutorial();
        wrapper.vm.currentStep = 3;
        wrapper.vm.connectionMode = "recommended";
        wrapper.vm.nextStep();
        expect(wrapper.vm.currentStep).toBe(4);
        wrapper.unmount();
    });

    it("H3: previousStep from propagation after recommended returns to bootstrap step 4", async () => {
        const wrapper = await mountTutorial();
        wrapper.vm.connectionMode = "recommended";
        wrapper.vm.currentStep = 5;
        wrapper.vm.previousStep();
        expect(wrapper.vm.currentStep).toBe(4);
        wrapper.unmount();
    });

    it("H4: concurrent auto pickRandom must not interleave (second call no-ops while busy)", async () => {
        const wrapper = await mountTutorial(tcpCommunity(8));
        wrapper.vm.currentStep = 4;
        wrapper.vm.connectionMode = "discovery";
        wrapper.vm.communityInterfaces = tcpCommunity(8);
        const shuffleSpy = vi.spyOn(wrapper.vm, "shuffleArrayInPlace");

        const p1 = wrapper.vm.pickRandomTcpBootstraps({ silent: true, auto: true, count: 3 });
        expect(wrapper.vm.pickingRandomBootstraps).toBe(true);
        const p2 = wrapper.vm.pickRandomTcpBootstraps({ silent: true, auto: true, count: 3 });
        await Promise.all([p1, p2]);
        await flushPromises();

        expect(shuffleSpy).toHaveBeenCalledTimes(1);
        expect(wrapper.vm.selectedBootstrapKeys.length).toBe(3);
        expect(wrapper.vm.pickingRandomBootstraps).toBe(false);
        wrapper.unmount();
    });

    it("H5: useDiscoveryMode resets auto-pick latch so a second visit can pick again", async () => {
        const wrapper = await mountTutorial(tcpCommunity(5));
        wrapper.vm.currentStep = 3;
        wrapper.vm.bootstrapAutoPickDone = true;
        wrapper.vm.selectedBootstrapKeys = [];
        wrapper.vm.communityInterfaces = tcpCommunity(5);

        await wrapper.vm.useDiscoveryMode();
        await flushPromises();
        await wrapper.vm.$nextTick();
        await flushPromises();

        expect(wrapper.vm.currentStep).toBe(4);
        expect(wrapper.vm.connectionMode).toBe("discovery");
        expect(wrapper.vm.pickingRandomBootstraps).toBe(false);
        expect(wrapper.vm.selectedBootstrapKeys.length).toBe(3);
        expect(wrapper.vm.bootstrapAutoPickDone).toBe(true);
        wrapper.unmount();
    });

    it("H5b: watcher must not mark auto-pick done when pick is already in flight", async () => {
        const wrapper = await mountTutorial(tcpCommunity(5));
        wrapper.vm.currentStep = 4;
        wrapper.vm.connectionMode = "discovery";
        wrapper.vm.bootstrapAutoPickDone = false;
        wrapper.vm.selectedBootstrapKeys = [];
        wrapper.vm.communityInterfaces = tcpCommunity(5);
        wrapper.vm.pickingRandomBootstraps = true;

        await wrapper.vm.maybeAutoPickBootstrapTcp();
        expect(wrapper.vm.bootstrapAutoPickDone).toBe(false);
        expect(wrapper.vm.selectedBootstrapKeys.length).toBe(0);
        wrapper.unmount();
    });

    it("H6: useRecommendedMode adds AutoInterface, enables discovery, picks exactly 3 TCP", async () => {
        const wrapper = await mountTutorial(tcpCommunity(7));
        wrapper.vm.currentStep = 3;

        await wrapper.vm.useRecommendedMode();
        await flushPromises();

        expect(axiosMock.post).toHaveBeenCalledWith("/api/v1/reticulum/interfaces/add", {
            name: "Local Network",
            type: "AutoInterface",
            enabled: true,
        });
        expect(axiosMock.patch).toHaveBeenCalledWith(
            "/api/v1/reticulum/discovery",
            expect.objectContaining({
                discover_interfaces: true,
                autoconnect_discovered_interfaces: 3,
            })
        );
        expect(wrapper.vm.currentStep).toBe(4);
        expect(wrapper.vm.connectionMode).toBe("recommended");
        expect(wrapper.vm.selectedBootstrapKeys.length).toBe(3);
        expect(wrapper.vm.selectedBootstrapKeys.every((k) => k.startsWith("comm:"))).toBe(true);
        expect(wrapper.vm.addingRecommended).toBe(false);
        wrapper.unmount();
    });

    it("H7: connection mode buttons stay locked while discovery is in flight", async () => {
        let resolvePatch;
        axiosMock.get.mockImplementation(apiHandlers(tcpCommunity(4)));
        axiosMock.patch.mockImplementation(
            () =>
                new Promise((resolve) => {
                    resolvePatch = resolve;
                })
        );
        axiosMock.post.mockResolvedValue({ data: {} });

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

        const pending = wrapper.vm.useDiscoveryMode();
        await wrapper.vm.$nextTick();
        expect(wrapper.vm.connectionSetupBusy).toBe(true);
        expect(wrapper.vm.tutorialNavBusy).toBe(true);

        // Adversarial second click must not start another discovery patch
        const patchCallsBefore = axiosMock.patch.mock.calls.length;
        await wrapper.vm.useDiscoveryMode();
        await wrapper.vm.useRecommendedMode();
        await wrapper.vm.useLocalMode();
        expect(axiosMock.patch.mock.calls.length).toBe(patchCallsBefore);

        resolvePatch({ data: { message: "ok" } });
        await pending;
        await flushPromises();
        expect(wrapper.vm.connectionSetupBusy).toBe(false);
        wrapper.unmount();
    });

    it("H8: skip/confirm bootstraps are ignored while random pick is busy", async () => {
        const wrapper = await mountTutorial(tcpCommunity(5));
        wrapper.vm.currentStep = 4;
        wrapper.vm.connectionMode = "discovery";
        wrapper.vm.pickingRandomBootstraps = true;
        wrapper.vm.selectedBootstrapKeys = ["comm:Node 1"];

        wrapper.vm.skipBootstraps();
        expect(wrapper.vm.currentStep).toBe(4);

        await wrapper.vm.confirmBootstraps();
        expect(wrapper.vm.currentStep).toBe(4);
        expect(axiosMock.post).not.toHaveBeenCalledWith(
            "/api/v1/reticulum/interfaces/add",
            expect.objectContaining({ name: "Node 1" })
        );
        wrapper.unmount();
    });

    it("H9: yggdrasil / ygg-labelled community presets are excluded from random pick", async () => {
        const mixed = [
            {
                name: "Yggdrasil Bridge",
                type: "TCPClientInterface",
                target_host: "1.1.1.1",
                target_port: 4242,
                description: "ygg only",
            },
            {
                name: "Normal A",
                type: "TCPClientInterface",
                target_host: "2.2.2.2",
                target_port: 4242,
            },
            {
                name: "Normal B",
                type: "TCPClientInterface",
                target_host: "3.3.3.3",
                target_port: 4242,
            },
            {
                name: "Normal C",
                type: "TCPClientInterface",
                target_host: "4.4.4.4",
                target_port: 4242,
            },
            {
                name: "Normal D",
                type: "TCPClientInterface",
                target_host: "5.5.5.5",
                target_port: 4242,
            },
        ];
        const wrapper = await mountTutorial(mixed);
        wrapper.vm.communityInterfaces = mixed;
        await wrapper.vm.pickRandomTcpBootstraps({ silent: true, auto: true, count: 3 });
        expect(wrapper.vm.selectedBootstrapKeys).not.toContain("comm:Yggdrasil Bridge");
        expect(wrapper.vm.selectedBootstrapKeys.length).toBe(3);
        wrapper.unmount();
    });

    it("H10: random pick prefers at most available eligible nodes and never selects hostless entries", async () => {
        const sparse = [
            { name: "Good1", type: "TCPClientInterface", target_host: "8.8.8.8", target_port: 4242 },
            { name: "NoHost", type: "TCPClientInterface", target_host: "", target_port: 4242 },
            { name: "UDP", type: "UDPInterface", target_host: "9.9.9.9", target_port: 4242 },
            { name: "Good2", type: "TCPClientInterface", target_host: "8.8.4.4", target_port: 4242 },
        ];
        const wrapper = await mountTutorial(sparse);
        wrapper.vm.communityInterfaces = sparse;
        await wrapper.vm.pickRandomTcpBootstraps({ count: 99 });
        expect(wrapper.vm.selectedBootstrapKeys.sort()).toEqual(["comm:Good1", "comm:Good2"].sort());
        wrapper.unmount();
    });

    it("H11: useRecommendedMode failure after AutoInterface add does not advance step", async () => {
        axiosMock.get.mockImplementation(apiHandlers(tcpCommunity(3)));
        axiosMock.post.mockResolvedValue({ data: { message: "added" } });
        axiosMock.patch.mockRejectedValue({ response: { data: { message: "discovery failed" } } });

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

        await wrapper.vm.useRecommendedMode();
        await flushPromises();

        expect(wrapper.vm.currentStep).toBe(3);
        expect(wrapper.vm.connectionMode).toBeNull();
        expect(wrapper.vm.addingRecommended).toBe(false);
        expect(ToastUtils.error).toHaveBeenCalled();
        wrapper.unmount();
    });

    it("H12: theme/language controls are in-flow (not absolute overlay) so titles are not covered", async () => {
        const wrapper = await mountTutorial();
        expect(wrapper.find(".absolute.top-4.left-4").exists()).toBe(false);
        expect(wrapper.find(".absolute.top-4.right-4").exists()).toBe(false);
        wrapper.unmount();
    });

    it("H13: double finishTutorial is race-safe while connect busy", async () => {
        const wrapper = await mountTutorial();
        wrapper.vm.currentStep = 3;
        wrapper.vm.savingDiscovery = true;
        await wrapper.vm.finishTutorial();
        expect(wrapper.vm.visible).toBe(true);
        expect(wrapper.vm.finishingTutorial).toBe(false);
        wrapper.unmount();
    });
});
