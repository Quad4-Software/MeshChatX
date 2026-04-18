import { mount, flushPromises } from "@vue/test-utils";
import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import SettingsPage from "../../meshchatx/src/frontend/components/settings/SettingsPage.vue";
import Toggle from "../../meshchatx/src/frontend/components/forms/Toggle.vue";
import GlobalEmitter from "../../meshchatx/src/frontend/js/GlobalEmitter";
import GlobalState from "../../meshchatx/src/frontend/js/GlobalState";
import WebSocketConnection from "../../meshchatx/src/frontend/js/WebSocketConnection";
import { buildFullServerConfig, createWindowApi } from "./fixtures/settingsPageTestApi.js";

vi.mock("../../meshchatx/src/frontend/js/WebSocketConnection", () => ({
    default: {
        on: vi.fn(),
        off: vi.fn(),
        emit: vi.fn(),
        send: vi.fn(),
    },
}));

vi.mock("../../meshchatx/src/frontend/js/ToastUtils", () => ({
    default: {
        success: vi.fn(),
        error: vi.fn(),
        warning: vi.fn(),
        info: vi.fn(),
        loading: vi.fn(),
        dismiss: vi.fn(),
    },
}));

vi.mock("../../meshchatx/src/frontend/js/DialogUtils", () => ({
    default: {
        confirm: vi.fn().mockResolvedValue(true),
    },
}));

vi.mock("../../meshchatx/src/frontend/js/KeyboardShortcuts", () => ({
    default: {
        getDefaultShortcuts: vi.fn(() => []),
        send: vi.fn(),
    },
}));

vi.mock("../../meshchatx/src/frontend/js/ElectronUtils", () => ({
    default: {
        isElectron: vi.fn(() => false),
    },
}));

async function mountSettingsPage(api, router = { push: vi.fn() }) {
    window.api = api;
    const wrapper = mount(SettingsPage, {
        global: {
            stubs: {
                MaterialDesignIcon: { template: "<span class='mdi'></span>" },
                Toggle,
                ShortcutRecorder: { template: "<div></div>" },
                RouterLink: { template: "<a><slot /></a>" },
                SettingsSectionBlock: { template: "<div class='settings-section-block'><slot /></div>" },
            },
            mocks: {
                $t: (key) => key,
                $router: router,
            },
        },
    });
    await flushPromises();
    await wrapper.vm.$nextTick();
    return wrapper;
}

describe("SettingsPage — config persistence (PATCH and related)", () => {
    let serverConfigRef;
    let api;

    beforeEach(() => {
        serverConfigRef = { current: buildFullServerConfig() };
        api = createWindowApi(serverConfigRef);
        vi.useFakeTimers();
    });

    afterEach(() => {
        vi.useRealTimers();
        delete window.api;
        vi.clearAllMocks();
    });

    it("onThemeChange PATCHes theme", async () => {
        const w = await mountSettingsPage(api);
        w.vm.config.theme = "light";
        await w.vm.onThemeChange();
        expect(api.patch).toHaveBeenCalledWith("/api/v1/config", { theme: "light" });
    });

    it("onLanguageChange PATCHes language", async () => {
        const w = await mountSettingsPage(api);
        w.vm.config.language = "de";
        await w.vm.onLanguageChange();
        expect(api.patch).toHaveBeenCalledWith("/api/v1/config", { language: "de" });
    });

    it("onMessageFontSizeChange PATCHes after debounce", async () => {
        const w = await mountSettingsPage(api);
        w.vm.config.message_font_size = 18;
        await w.vm.onMessageFontSizeChange();
        await vi.advanceTimersByTimeAsync(1000);
        expect(api.patch).toHaveBeenCalledWith("/api/v1/config", { message_font_size: 18 });
    });

    it("onDisplayNameChange PATCHes after debounce", async () => {
        const w = await mountSettingsPage(api);
        w.vm.config.display_name = "New Name";
        await w.vm.onDisplayNameChange();
        await vi.advanceTimersByTimeAsync(600);
        expect(api.patch).toHaveBeenCalledWith("/api/v1/config", { display_name: "New Name" });
    });

    it("onMessageIconSizeChange PATCHes after debounce", async () => {
        const w = await mountSettingsPage(api);
        w.vm.config.message_icon_size = 40;
        await w.vm.onMessageIconSizeChange();
        await vi.advanceTimersByTimeAsync(1000);
        expect(api.patch).toHaveBeenCalledWith("/api/v1/config", { message_icon_size: 40 });
    });

    it("onUiTransparencyChange PATCHes clamped value after debounce", async () => {
        const w = await mountSettingsPage(api);
        w.vm.config.ui_transparency = 77;
        w.vm.onUiTransparencyChange();
        await vi.advanceTimersByTimeAsync(400);
        expect(api.patch).toHaveBeenCalledWith("/api/v1/config", { ui_transparency: 77 });
    });

    it("onUiGlassEnabledChange PATCHes ui_glass_enabled", async () => {
        const w = await mountSettingsPage(api);
        w.vm.config.ui_glass_enabled = false;
        await w.vm.onUiGlassEnabledChange();
        expect(api.patch).toHaveBeenCalledWith("/api/v1/config", { ui_glass_enabled: false });
    });

    it("onMessagesSidebarPositionChange PATCHes messages_sidebar_position", async () => {
        const w = await mountSettingsPage(api);
        w.vm.config.messages_sidebar_position = "right";
        await w.vm.onMessagesSidebarPositionChange();
        expect(api.patch).toHaveBeenCalledWith("/api/v1/config", { messages_sidebar_position: "right" });
    });

    it("resetAppearanceDefaults PATCHes full appearance payload", async () => {
        const w = await mountSettingsPage(api);
        await w.vm.resetAppearanceDefaults();
        expect(api.patch).toHaveBeenCalledWith(
            "/api/v1/config",
            expect.objectContaining({
                theme: "light",
                messages_sidebar_position: "left",
                message_font_size: 14,
                message_icon_size: 28,
                ui_transparency: 0,
                ui_glass_enabled: true,
                message_outbound_bubble_color: "#4f46e5",
                message_inbound_bubble_color: null,
                message_failed_bubble_color: "#ef4444",
                message_waiting_bubble_color: "#e5e7eb",
            })
        );
    });

    it("onMessageBubbleColorChange PATCHes outbound after debounce", async () => {
        const w = await mountSettingsPage(api);
        w.vm.config.message_outbound_bubble_color = "#112233";
        await w.vm.onMessageBubbleColorChange("outbound");
        await vi.advanceTimersByTimeAsync(1000);
        expect(api.patch).toHaveBeenCalledWith("/api/v1/config", {
            message_outbound_bubble_color: "#112233",
        });
    });

    it("updateConfig can PATCH blackhole_integration_enabled (inline control)", async () => {
        const w = await mountSettingsPage(api);
        w.vm.config.blackhole_integration_enabled = false;
        await w.vm.updateConfig({ blackhole_integration_enabled: false }, "blackhole_integration_enabled");
        expect(api.patch).toHaveBeenCalledWith("/api/v1/config", { blackhole_integration_enabled: false });
    });

    it("onAnnounceLimitsChange PATCHes announce and discovery caps", async () => {
        const w = await mountSettingsPage(api);
        w.vm.config.announce_max_stored_lxmf_delivery = 900;
        await w.vm.onAnnounceLimitsChange();
        expect(api.patch).toHaveBeenCalledWith(
            "/api/v1/config",
            expect.objectContaining({
                announce_max_stored_lxmf_delivery: 900,
                discovered_interfaces_max_return: 500,
            })
        );
    });

    it("message reliability toggles PATCH expected keys", async () => {
        const w = await mountSettingsPage(api);
        await w.vm.onAutoResendFailedMessagesWhenAnnounceReceivedChange();
        expect(api.patch).toHaveBeenCalledWith(
            "/api/v1/config",
            expect.objectContaining({
                auto_resend_failed_messages_when_announce_received: true,
            })
        );
        await w.vm.onAllowAutoResendingFailedMessagesWithAttachmentsChange();
        expect(api.patch).toHaveBeenCalledWith(
            "/api/v1/config",
            expect.objectContaining({
                allow_auto_resending_failed_messages_with_attachments: true,
            })
        );
        await w.vm.onAutoSendFailedMessagesToPropagationNodeChange();
        expect(api.patch).toHaveBeenCalledWith(
            "/api/v1/config",
            expect.objectContaining({
                auto_send_failed_messages_to_propagation_node: false,
            })
        );
    });

    it("onShowSuggestedCommunityInterfacesChange PATCHes flag", async () => {
        const w = await mountSettingsPage(api);
        w.vm.config.show_suggested_community_interfaces = false;
        await w.vm.onShowSuggestedCommunityInterfacesChange();
        expect(api.patch).toHaveBeenCalledWith("/api/v1/config", {
            show_suggested_community_interfaces: false,
        });
    });

    it("onLxmfPreferredPropagationNodeDestinationHashChange PATCHes after debounce", async () => {
        const w = await mountSettingsPage(api);
        w.vm.config.lxmf_preferred_propagation_node_destination_hash = "deadbeef";
        await w.vm.onLxmfPreferredPropagationNodeDestinationHashChange();
        await vi.advanceTimersByTimeAsync(1000);
        expect(api.patch).toHaveBeenCalledWith("/api/v1/config", {
            lxmf_preferred_propagation_node_destination_hash: "deadbeef",
        });
    });

    it("onLxmfPreferredPropagationNodeAutoSelectChange PATCHes", async () => {
        const w = await mountSettingsPage(api);
        w.vm.config.lxmf_preferred_propagation_node_auto_select = true;
        await w.vm.onLxmfPreferredPropagationNodeAutoSelectChange();
        expect(api.patch).toHaveBeenCalledWith("/api/v1/config", {
            lxmf_preferred_propagation_node_auto_select: true,
        });
    });

    it("onLxmfLocalPropagationNodeEnabledChange PATCHes", async () => {
        const w = await mountSettingsPage(api);
        await w.vm.onLxmfLocalPropagationNodeEnabledChange();
        expect(api.patch).toHaveBeenCalledWith("/api/v1/config", {
            lxmf_local_propagation_node_enabled: false,
        });
    });

    it("onLxmfPreferredPropagationNodeAutoSyncIntervalSecondsChange PATCHes", async () => {
        const w = await mountSettingsPage(api);
        w.vm.config.lxmf_preferred_propagation_node_auto_sync_interval_seconds = 7200;
        await w.vm.onLxmfPreferredPropagationNodeAutoSyncIntervalSecondsChange();
        expect(api.patch).toHaveBeenCalledWith("/api/v1/config", {
            lxmf_preferred_propagation_node_auto_sync_interval_seconds: 7200,
        });
    });

    it("onLxmfIncomingDeliveryPresetChange PATCHes preset size", async () => {
        const w = await mountSettingsPage(api);
        w.vm.lxmfIncomingDeliveryPreset = "1gb";
        await w.vm.onLxmfIncomingDeliveryPresetChange();
        expect(api.patch).toHaveBeenCalledWith("/api/v1/config", {
            lxmf_delivery_transfer_limit_in_bytes: 1_000_000_000,
        });
    });

    it("LXMF transfer/sync limits PATCH after debounce", async () => {
        const w = await mountSettingsPage(api);
        w.vm.lxmfIncomingDeliveryPreset = "custom";
        w.vm.lxmfIncomingDeliveryCustomAmount = 9;
        w.vm.lxmfIncomingDeliveryCustomUnit = "mb";
        await w.vm.onLxmfIncomingDeliveryCustomChange();
        await vi.advanceTimersByTimeAsync(1000);
        expect(api.patch).toHaveBeenCalledWith("/api/v1/config", {
            lxmf_delivery_transfer_limit_in_bytes: 9_000_000,
        });

        w.vm.lxmfPropagationTransferLimitInputMb = 0.3;
        await w.vm.onLxmfPropagationTransferLimitChange();
        await vi.advanceTimersByTimeAsync(1000);
        expect(api.patch).toHaveBeenCalledWith("/api/v1/config", {
            lxmf_propagation_transfer_limit_in_bytes: 300_000,
        });

        w.vm.lxmfPropagationSyncLimitInputMb = 9;
        await w.vm.onLxmfPropagationSyncLimitChange();
        await vi.advanceTimersByTimeAsync(1000);
        expect(api.patch).toHaveBeenCalledWith("/api/v1/config", {
            lxmf_propagation_sync_limit_in_bytes: 9_000_000,
        });
    });

    it("onLxmfInboundStampCostChange PATCHes after debounce", async () => {
        const w = await mountSettingsPage(api);
        w.vm.config.lxmf_inbound_stamp_cost = 12;
        await w.vm.onLxmfInboundStampCostChange();
        await vi.advanceTimersByTimeAsync(1000);
        expect(api.patch).toHaveBeenCalledWith("/api/v1/config", { lxmf_inbound_stamp_cost: 12 });
    });

    it("onInboundStampsEnabledChange(false) PATCHes zero stamp cost", async () => {
        const w = await mountSettingsPage(api);
        w.vm.config.lxmf_inbound_stamp_cost = 12;
        await w.vm.onInboundStampsEnabledChange(false);
        expect(api.patch).toHaveBeenCalledWith("/api/v1/config", { lxmf_inbound_stamp_cost: 0 });
    });

    it("onInboundStampsEnabledChange(true) restores stamp cost", async () => {
        const w = await mountSettingsPage(api);
        w.vm.lastRememberedInboundStampCost = 16;
        w.vm.config.lxmf_inbound_stamp_cost = 0;
        await w.vm.onInboundStampsEnabledChange(true);
        expect(api.patch).toHaveBeenCalledWith("/api/v1/config", { lxmf_inbound_stamp_cost: 16 });
    });

    it("onLxmfPropagationNodeStampCostChange PATCHes after debounce", async () => {
        const w = await mountSettingsPage(api);
        w.vm.config.lxmf_propagation_node_stamp_cost = 20;
        await w.vm.onLxmfPropagationNodeStampCostChange();
        await vi.advanceTimersByTimeAsync(1000);
        expect(api.patch).toHaveBeenCalledWith("/api/v1/config", { lxmf_propagation_node_stamp_cost: 20 });
    });

    it("page archiver toggles and numeric config PATCH", async () => {
        const w = await mountSettingsPage(api);
        await w.vm.onPageArchiverEnabledChangeWrapper(true);
        expect(api.patch).toHaveBeenCalledWith("/api/v1/config", { page_archiver_enabled: true });

        w.vm.config.page_archiver_max_versions = 12;
        w.vm.config.archives_max_storage_gb = 2;
        await w.vm.onPageArchiverConfigChange();
        await vi.advanceTimersByTimeAsync(1000);
        expect(api.patch).toHaveBeenCalledWith("/api/v1/config", {
            page_archiver_max_versions: 12,
            archives_max_storage_gb: 2,
        });
    });

    it("Nomad renderer toggles and default path PATCH", async () => {
        const w = await mountSettingsPage(api);
        await w.vm.onNomadRendererMarkdownToggle(false);
        expect(api.patch).toHaveBeenCalledWith("/api/v1/config", { nomad_render_markdown_enabled: false });
        await w.vm.onNomadRendererHtmlToggle(false);
        expect(api.patch).toHaveBeenCalledWith("/api/v1/config", { nomad_render_html_enabled: false });
        await w.vm.onNomadRendererPlaintextToggle(false);
        expect(api.patch).toHaveBeenCalledWith("/api/v1/config", { nomad_render_plaintext_enabled: false });
        w.vm.config.nomad_default_page_path = "/page/custom.mu";
        await w.vm.onNomadDefaultPagePathChange();
        expect(api.patch).toHaveBeenCalledWith("/api/v1/config", { nomad_default_page_path: "/page/custom.mu" });
    });

    it("stranger protection PATCHes each flag", async () => {
        const w = await mountSettingsPage(api);
        await w.vm.onStrangerAttachmentBlockChange(false);
        expect(api.patch).toHaveBeenCalledWith("/api/v1/config", { block_attachments_from_strangers: false });
        await w.vm.onBlockAllFromStrangersChange(true);
        expect(api.patch).toHaveBeenCalledWith("/api/v1/config", { block_all_from_strangers: true });
        await w.vm.onShowUnknownContactBannerChange(false);
        expect(api.patch).toHaveBeenCalledWith("/api/v1/config", { show_unknown_contact_banner: false });
        await w.vm.onWarnOnStrangerLinksChange(false);
        expect(api.patch).toHaveBeenCalledWith("/api/v1/config", { warn_on_stranger_links: false });
    });

    it("banishment PATCHes toggle and debounced text/color", async () => {
        const w = await mountSettingsPage(api);
        await w.vm.onBanishedEffectEnabledChange(false);
        expect(api.patch).toHaveBeenCalledWith("/api/v1/config", { banished_effect_enabled: false });
        w.vm.config.banished_text = "OUT";
        w.vm.config.banished_color = "#ff0000";
        await w.vm.onBanishedConfigChange();
        await vi.advanceTimersByTimeAsync(1000);
        expect(api.patch).toHaveBeenCalledWith(
            "/api/v1/config",
            expect.objectContaining({ banished_text: "OUT", banished_color: "#ff0000" })
        );
    });

    it("crawler enabled and debounced crawler fields PATCH", async () => {
        const w = await mountSettingsPage(api);
        await w.vm.onCrawlerEnabledChange(true);
        expect(api.patch).toHaveBeenCalledWith("/api/v1/config", { crawler_enabled: true });
        w.vm.config.crawler_max_retries = 5;
        w.vm.config.crawler_retry_delay_seconds = 60;
        w.vm.config.crawler_max_concurrent = 3;
        await w.vm.onCrawlerConfigChange();
        await vi.advanceTimersByTimeAsync(1000);
        expect(api.patch).toHaveBeenCalledWith("/api/v1/config", {
            crawler_max_retries: 5,
            crawler_retry_delay_seconds: 60,
            crawler_max_concurrent: 3,
        });
    });

    it("desktop toggles PATCH", async () => {
        const w = await mountSettingsPage(api);
        await w.vm.onDesktopOpenCallsInSeparateWindowChange(true);
        expect(api.patch).toHaveBeenCalledWith("/api/v1/config", { desktop_open_calls_in_separate_window: true });
        await w.vm.onDesktopHardwareAccelerationEnabledChange(false);
        expect(api.patch).toHaveBeenCalledWith("/api/v1/config", { desktop_hardware_acceleration_enabled: false });
    });

    it("onAuthEnabledChange PATCHes auth and does not push router when disabling", async () => {
        const router = { push: vi.fn() };
        const w = await mountSettingsPage(api, router);
        await w.vm.onAuthEnabledChange(false);
        expect(api.patch).toHaveBeenCalledWith("/api/v1/config", { auth_enabled: false });
        expect(router.push).not.toHaveBeenCalled();
    });

    it("onAuthEnabledChange pushes auth route when enabling", async () => {
        const router = { push: vi.fn() };
        const w = await mountSettingsPage(api, router);
        await w.vm.onAuthEnabledChange(true);
        expect(api.patch).toHaveBeenCalledWith("/api/v1/config", { auth_enabled: true });
        expect(router.push).toHaveBeenCalledWith({ name: "auth" });
    });

    it("translator toggle and debounced URL PATCH", async () => {
        const w = await mountSettingsPage(api);
        await w.vm.onTranslatorEnabledChange(true);
        expect(api.patch).toHaveBeenCalledWith("/api/v1/config", { translator_enabled: true });
        w.vm.config.libretranslate_url = "http://translate.example";
        await w.vm.onTranslatorConfigChange();
        await vi.advanceTimersByTimeAsync(1000);
        expect(api.patch).toHaveBeenCalledWith("/api/v1/config", {
            libretranslate_url: "http://translate.example",
        });
    });

    it("onGiteaConfigChange PATCHes after debounce", async () => {
        const w = await mountSettingsPage(api);
        w.vm.config.gitea_base_url = "https://gitea.example";
        w.vm.config.docs_download_urls = "https://docs.example";
        await w.vm.onGiteaConfigChange();
        await vi.advanceTimersByTimeAsync(1000);
        expect(api.patch).toHaveBeenCalledWith(
            "/api/v1/config",
            expect.objectContaining({
                gitea_base_url: "https://gitea.example",
                docs_download_urls: "https://docs.example",
            })
        );
    });

    it("onCspConfigChange PATCHes CSP fields after debounce", async () => {
        const w = await mountSettingsPage(api);
        w.vm.config.csp_extra_connect_src = "wss://a.example";
        w.vm.config.csp_extra_img_src = "https://img.example";
        w.vm.config.csp_extra_frame_src = "https://frame.example";
        w.vm.config.csp_extra_script_src = "https://js.example";
        w.vm.config.csp_extra_style_src = "https://css.example";
        await w.vm.onCspConfigChange();
        await vi.advanceTimersByTimeAsync(1000);
        expect(api.patch).toHaveBeenCalledWith(
            "/api/v1/config",
            expect.objectContaining({
                csp_extra_connect_src: "wss://a.example",
                csp_extra_style_src: "https://css.example",
            })
        );
    });

    it("onBackupConfigChange PATCHes backup_max_count after debounce", async () => {
        const w = await mountSettingsPage(api);
        w.vm.config.backup_max_count = 8;
        await w.vm.onBackupConfigChange();
        await vi.advanceTimersByTimeAsync(1000);
        expect(api.patch).toHaveBeenCalledWith("/api/v1/config", { backup_max_count: 8 });
    });

    it("inline location and telemetry PATCH via updateConfig", async () => {
        const w = await mountSettingsPage(api);
        w.vm.config.location_source = "manual";
        await w.vm.updateConfig({ location_source: "manual" }, "location_source");
        expect(api.patch).toHaveBeenCalledWith("/api/v1/config", { location_source: "manual" });
        await w.vm.updateConfig({ telemetry_enabled: true }, "telemetry");
        expect(api.patch).toHaveBeenCalledWith("/api/v1/config", { telemetry_enabled: true });
    });
});

describe("SettingsPage — transport mode (POST, not PATCH)", () => {
    let serverConfigRef;
    let api;

    beforeEach(() => {
        serverConfigRef = { current: buildFullServerConfig() };
        api = createWindowApi(serverConfigRef);
    });

    afterEach(() => {
        delete window.api;
        vi.clearAllMocks();
    });

    it("onIsTransportEnabledChange POSTs enable when turning on", async () => {
        const w = await mountSettingsPage(api);
        w.vm.config.is_transport_enabled = true;
        await w.vm.onIsTransportEnabledChange();
        expect(api.post).toHaveBeenCalledWith("/api/v1/reticulum/enable-transport");
    });

    it("onIsTransportEnabledChange POSTs disable when turning off", async () => {
        serverConfigRef.current = buildFullServerConfig({ is_transport_enabled: true });
        const w = await mountSettingsPage(api);
        w.vm.config.is_transport_enabled = false;
        await w.vm.onIsTransportEnabledChange();
        expect(api.post).toHaveBeenCalledWith("/api/v1/reticulum/disable-transport");
    });
});

describe("SettingsPage — visualiser display prefs (localStorage + emitter)", () => {
    let serverConfigRef;
    let api;

    beforeEach(() => {
        serverConfigRef = { current: buildFullServerConfig() };
        api = createWindowApi(serverConfigRef);
        vi.spyOn(GlobalEmitter, "emit");
        localStorage.clear();
    });

    afterEach(() => {
        delete window.api;
        GlobalEmitter.emit.mockRestore();
        vi.clearAllMocks();
    });

    it("onVisualiserShowDisabledChange persists and emits", async () => {
        const w = await mountSettingsPage(api);
        w.vm.onVisualiserShowDisabledChange(true);
        expect(localStorage.getItem("meshchatx.visualiser.showDisabledInterfaces")).toBe("true");
        expect(GlobalEmitter.emit).toHaveBeenCalledWith("visualiser-display-prefs-changed");
    });

    it("onVisualiserShowDiscoveredChange persists and emits", async () => {
        const w = await mountSettingsPage(api);
        w.vm.onVisualiserShowDiscoveredChange(true);
        expect(localStorage.getItem("meshchatx.visualiser.showDiscoveredInterfaces")).toBe("true");
        expect(GlobalEmitter.emit).toHaveBeenCalledWith("visualiser-display-prefs-changed");
    });

    it("onDetailedOutboundSendStatusChange updates GlobalState and localStorage", async () => {
        localStorage.removeItem("meshchatx_detailed_outbound_send_status");
        const w = await mountSettingsPage(api);
        await w.vm.onDetailedOutboundSendStatusChange({ target: { checked: true } });
        expect(GlobalState.detailedOutboundSendStatus).toBe(true);
        expect(localStorage.getItem("meshchatx_detailed_outbound_send_status")).toBe("true");
        await w.vm.onDetailedOutboundSendStatusChange({ target: { checked: false } });
        expect(GlobalState.detailedOutboundSendStatus).toBe(false);
        expect(localStorage.getItem("meshchatx_detailed_outbound_send_status")).toBe("false");
    });
});

describe("SettingsPage — maintenance, exports, telemetry trust, RNS reload", () => {
    let serverConfigRef;
    let api;

    beforeEach(() => {
        serverConfigRef = { current: buildFullServerConfig() };
        api = createWindowApi(serverConfigRef);
        vi.clearAllMocks();
    });

    afterEach(() => {
        delete window.api;
    });

    it("reloadRns POSTs reticulum reload", async () => {
        const w = await mountSettingsPage(api);
        await w.vm.reloadRns();
        expect(api.post).toHaveBeenCalledWith("/api/v1/reticulum/reload");
    });

    it("clearMessages DELETEs maintenance messages", async () => {
        const w = await mountSettingsPage(api);
        await w.vm.clearMessages();
        expect(api.delete).toHaveBeenCalledWith("/api/v1/maintenance/messages");
    });

    it("clearAnnounces DELETEs announces", async () => {
        const w = await mountSettingsPage(api);
        await w.vm.clearAnnounces();
        expect(api.delete).toHaveBeenCalledWith("/api/v1/maintenance/announces");
    });

    it("clearNomadnetFavorites DELETEs with aspect param", async () => {
        const w = await mountSettingsPage(api);
        await w.vm.clearNomadnetFavorites();
        expect(api.delete).toHaveBeenCalledWith("/api/v1/maintenance/favourites", {
            params: { aspect: "nomadnetwork.node" },
        });
    });

    it("clearLxmfIcons DELETEs lxmf-icons", async () => {
        const w = await mountSettingsPage(api);
        await w.vm.clearLxmfIcons();
        expect(api.delete).toHaveBeenCalledWith("/api/v1/maintenance/lxmf-icons");
    });

    it("clearStickers DELETEs stickers", async () => {
        const w = await mountSettingsPage(api);
        await w.vm.clearStickers();
        expect(api.delete).toHaveBeenCalledWith("/api/v1/maintenance/stickers");
    });

    it("clearArchives DELETEs archives", async () => {
        const w = await mountSettingsPage(api);
        await w.vm.clearArchives();
        expect(api.delete).toHaveBeenCalledWith("/api/v1/maintenance/archives");
    });

    it("clearReticulumDocs DELETEs docs", async () => {
        const w = await mountSettingsPage(api);
        await w.vm.clearReticulumDocs();
        expect(api.delete).toHaveBeenCalledWith("/api/v1/maintenance/docs/reticulum");
    });

    it("exportMessages GETs export endpoint", async () => {
        const w = await mountSettingsPage(api);
        await w.vm.exportMessages();
        expect(api.get).toHaveBeenCalledWith("/api/v1/maintenance/messages/export");
    });

    it("exportFolders GETs folders export", async () => {
        const w = await mountSettingsPage(api);
        await w.vm.exportFolders();
        expect(api.get).toHaveBeenCalledWith("/api/v1/lxmf/folders/export");
    });

    it("exportStickers GETs stickers export", async () => {
        const w = await mountSettingsPage(api);
        await w.vm.exportStickers();
        expect(api.get).toHaveBeenCalledWith("/api/v1/stickers/export");
    });

    it("flushArchivedPages sends websocket flush after confirm", async () => {
        const w = await mountSettingsPage(api);
        await w.vm.flushArchivedPages();
        expect(WebSocketConnection.send).toHaveBeenCalledWith(JSON.stringify({ type: "nomadnet.page.archive.flush" }));
    });

    it("revokeTelemetryTrust PATCHes contact telemetry flag", async () => {
        const w = await mountSettingsPage(api);
        await w.vm.revokeTelemetryTrust({ id: "c1", name: "Peer" });
        expect(api.patch).toHaveBeenCalledWith("/api/v1/telephone/contacts/c1", {
            is_telemetry_trusted: false,
        });
    });
});
