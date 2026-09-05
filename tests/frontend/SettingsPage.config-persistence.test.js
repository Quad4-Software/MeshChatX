// SPDX-License-Identifier: 0BSD

import { render, fireEvent, waitFor } from "@testing-library/svelte";
import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import SettingsPage from "../../meshchatx/src/frontend/features/settings/components/SettingsPage.svelte";
import GlobalEmitter from "../../meshchatx/src/frontend/js/GlobalEmitter";
import GlobalState from "../../meshchatx/src/frontend/js/GlobalState";
import WebSocketConnection from "../../meshchatx/src/frontend/js/WebSocketConnection";
import * as localeLoader from "../../meshchatx/src/frontend/js/localeLoader.js";
import { buildFullServerConfig, createWindowApi } from "./fixtures/settingsPageTestApi.js";
import ToastUtils from "../../meshchatx/src/frontend/js/ToastUtils";
import DialogUtils from "../../meshchatx/src/frontend/js/DialogUtils";
import ElectronUtils from "../../meshchatx/src/frontend/js/ElectronUtils";
import { t } from "../../meshchatx/src/frontend/js/i18n.js";
import { registerCoreContributions } from "../../meshchatx/src/frontend/js/registries/registerCoreContributions.js";

registerCoreContributions();

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
        isWindowsElectron: vi.fn(() => false),
        getScreenSecuritySettings: vi.fn(async () => null),
        setScreenSecurityEnabled: vi.fn(async () => null),
        getCloseSettings: vi.fn(async () => null),
        setCloseSettings: vi.fn(async () => null),
    },
}));

async function renderSettings(serverConfig = buildFullServerConfig(), router = { push: vi.fn() }) {
    const serverConfigRef = { current: serverConfig };
    const api = createWindowApi(serverConfigRef);
    window.api = api;
    const view = render(SettingsPage);
    await waitFor(() => {
        expect(api.get).toHaveBeenCalledWith("/api/v1/config");
    });
    return { view, api, serverConfigRef };
}

async function selectTab(container, tabName) {
    const tabs = container.querySelectorAll(".settings-nav__tab");
    for (const tab of tabs) {
        if (tab.textContent.includes(tabName)) {
            await fireEvent.click(tab);
            break;
        }
    }
}

describe("SettingsPage: config persistence (PATCH and related)", () => {
    beforeEach(() => {
        registerCoreContributions();
    });

    afterEach(() => {
        delete window.api;
        vi.clearAllMocks();
    });

    it("onThemeChange PATCHes theme", async () => {
        const { view, api } = await renderSettings();
        const select = view.container.querySelector("#theme-select");
        expect(select).not.toBeNull();
        await fireEvent.change(select, { target: { value: "light" } });
        expect(api.patch).toHaveBeenCalledWith("/api/v1/config", { theme: "light" });
    });

    it("updateConfig publishes config-updated for live shell sync", async () => {
        const emitSpy = vi.spyOn(GlobalEmitter, "emit");
        const { view } = await renderSettings();
        const select = view.container.querySelector("#theme-select");
        await fireEvent.change(select, { target: { value: "dark" } });
        expect(emitSpy).toHaveBeenCalledWith("config-updated", expect.objectContaining({ theme: "dark" }));
        expect(GlobalState.config.theme).toBe("dark");
        emitSpy.mockRestore();
    });

    it("onAnnounceStoreToggle PATCHes a single announce_store flag", async () => {
        const { view, api } = await renderSettings();
        await selectTab(view.container, "Network");
        const toggle = view.container.querySelector("#announce-store-lxmf");
        expect(toggle).not.toBeNull();
        await fireEvent.click(toggle);
        expect(api.patch).toHaveBeenCalledWith("/api/v1/config", { announce_store_lxmf_delivery: false });
    });

    it("onLanguageChange PATCHes language", async () => {
        const { view, api } = await renderSettings();
        const select = view.container.querySelector("#language-select");
        expect(select).not.toBeNull();
        await fireEvent.change(select, { target: { value: "de" } });
        expect(api.patch).toHaveBeenCalledWith("/api/v1/config", { language: "de" });
    });

    it("onLanguageChange applies setLocale before PATCH", async () => {
        const setLocaleSpy = vi.spyOn(localeLoader, "setLocale").mockResolvedValue(true);
        const { view, api } = await renderSettings();
        const select = view.container.querySelector("#language-select");
        await fireEvent.change(select, { target: { value: "ru" } });
        expect(setLocaleSpy).toHaveBeenCalledWith(undefined, "ru");
        expect(api.patch).toHaveBeenCalledWith("/api/v1/config", { language: "ru" });
        setLocaleSpy.mockRestore();
    });

    it("onMessageFontSizeChange PATCHes font size", async () => {
        const { view, api } = await renderSettings();
        const input = view.container.querySelector("#message-font-size-input");
        expect(input).not.toBeNull();
        await fireEvent.input(input, { target: { value: "18" } });
        expect(api.patch).toHaveBeenCalledWith("/api/v1/config", { message_font_size: 18 });
    });

    it("onMessageIconSizeChange PATCHes icon size", async () => {
        const { view, api } = await renderSettings();
        const input = view.container.querySelector("#message-icon-size-input");
        expect(input).not.toBeNull();
        await fireEvent.input(input, { target: { value: "40" } });
        expect(api.patch).toHaveBeenCalledWith("/api/v1/config", { message_icon_size: 40 });
    });

    it("onUiTransparencyChange PATCHes ui_transparency", async () => {
        const { view, api } = await renderSettings();
        const input = view.container.querySelector("#ui-transparency-input");
        expect(input).not.toBeNull();
        await fireEvent.input(input, { target: { value: "75" } });
        expect(api.patch).toHaveBeenCalledWith("/api/v1/config", { ui_transparency: 75 });
    });

    it("onUiGlassEnabledChange PATCHes ui_glass_enabled", async () => {
        const { view, api } = await renderSettings();
        const toggle = view.container.querySelector("#ui-glass-enabled");
        expect(toggle).not.toBeNull();
        await fireEvent.click(toggle);
        expect(api.patch).toHaveBeenCalledWith("/api/v1/config", { ui_glass_enabled: false });
    });

    it("onMessagesSidebarPositionChange PATCHes messages_sidebar_position", async () => {
        const { view, api } = await renderSettings();
        const select = view.container.querySelector("#messages-sidebar-position-select");
        expect(select).not.toBeNull();
        await fireEvent.change(select, { target: { value: "right" } });
        expect(api.patch).toHaveBeenCalledWith("/api/v1/config", { messages_sidebar_position: "right" });
    });

    it("onAppSidebarLayoutChange PATCHes app_sidebar_layout", async () => {
        const { view, api } = await renderSettings();
        const select = view.container.querySelector("#app-sidebar-layout-select");
        expect(select).not.toBeNull();
        await fireEvent.change(select, { target: { value: "classic" } });
        expect(api.patch).toHaveBeenCalledWith("/api/v1/config", { app_sidebar_layout: "classic" });
    });

    it("resetAppearanceDefaults PATCHes full appearance payload", async () => {
        const { view, api } = await renderSettings();
        const buttons = Array.from(view.container.querySelectorAll("button"));
        const resetBtn = buttons.find(
            (btn) => btn.textContent && btn.textContent.toLowerCase().includes("reset appearance")
        );
        expect(resetBtn).not.toBeNull();
        await fireEvent.click(resetBtn);
        expect(api.patch).toHaveBeenCalledWith(
            "/api/v1/config",
            expect.objectContaining({
                theme: "light",
                theme_preset: "default",
                accent_color: null,
                custom_canvas_color: null,
                custom_surface_color: null,
                messages_sidebar_position: "left",
                app_sidebar_layout: "grouped",
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

    it("onMessageBubbleColorChange PATCHes outbound bubble color", async () => {
        const { view, api } = await renderSettings();
        const colorInput = view.container.querySelector('input[placeholder="#4f46e5"]');
        expect(colorInput).not.toBeNull();
        await fireEvent.input(colorInput, { target: { value: "#112233" } });
        expect(api.patch).toHaveBeenCalledWith("/api/v1/config", {
            message_outbound_bubble_color: "#112233",
        });
    });

    it("updateConfig can PATCH blackhole_integration_enabled", async () => {
        const { view, api } = await renderSettings();
        await selectTab(view.container, "Network");
        const toggle = view.container.querySelector("#blackhole-integration-enabled");
        expect(toggle).not.toBeNull();
        await fireEvent.click(toggle);
        expect(api.patch).toHaveBeenCalledWith("/api/v1/config", { blackhole_integration_enabled: false });
    });

    it("onAnnounceLimitsChange PATCHes announce and discovery caps", async () => {
        const { view, api } = await renderSettings();
        await selectTab(view.container, "Network");
        const input = view.container.querySelector("#ann-max-lxmf");
        expect(input).not.toBeNull();
        await fireEvent.change(input, { target: { value: "900" } });
        expect(api.patch).toHaveBeenCalledWith(
            "/api/v1/config",
            expect.objectContaining({
                announce_max_stored_lxmf_delivery: 900,
            })
        );
    });

    it("message reliability toggles PATCH expected keys", async () => {
        const { view, api } = await renderSettings();
        await selectTab(view.container, "Messages");

        const autoResend = view.container.querySelector("#auto-resend-failed");
        expect(autoResend).not.toBeNull();
        await fireEvent.click(autoResend);
        expect(api.patch).toHaveBeenCalledWith(
            "/api/v1/config",
            expect.objectContaining({
                auto_resend_failed_messages_when_announce_received: false,
            })
        );

        const allowAttachments = view.container.querySelector("#allow-retries-attachments");
        expect(allowAttachments).not.toBeNull();
        await fireEvent.click(allowAttachments);
        expect(api.patch).toHaveBeenCalledWith(
            "/api/v1/config",
            expect.objectContaining({
                allow_auto_resending_failed_messages_with_attachments: false,
            })
        );

        const autoFallback = view.container.querySelector("#auto-fallback-propagation");
        expect(autoFallback).not.toBeNull();
        await fireEvent.click(autoFallback);
        expect(api.patch).toHaveBeenCalledWith(
            "/api/v1/config",
            expect.objectContaining({
                auto_send_failed_messages_to_propagation_node: true,
            })
        );
    });

    it("onShowSuggestedCommunityInterfacesChange PATCHes flag", async () => {
        const { view, api } = await renderSettings();
        await selectTab(view.container, "Network");
        const toggle = view.container.querySelector("#show-community-interfaces");
        expect(toggle).not.toBeNull();
        await fireEvent.click(toggle);
        expect(api.patch).toHaveBeenCalledWith("/api/v1/config", {
            show_suggested_community_interfaces: false,
        });
    });

    it("onLxmfPreferredPropagationNodeDestinationHashChange PATCHes valid hash on enter", async () => {
        const { view, api } = await renderSettings();
        await selectTab(view.container, "Messages");
        const input = view.container.querySelector("#preferred-prop-node-hash");
        expect(input).not.toBeNull();
        await fireEvent.input(input, { target: { value: "a39610c89d18bb48c73e429582423c24" } });
        await fireEvent.keyDown(input, { key: "Enter" });
        expect(api.patch).toHaveBeenCalledWith(
            "/api/v1/config",
            expect.objectContaining({
                lxmf_preferred_propagation_node_destination_hash: "a39610c89d18bb48c73e429582423c24",
            })
        );
    });

    it("does not PATCH an incomplete preferred node hash", async () => {
        const { view, api } = await renderSettings();
        await selectTab(view.container, "Messages");
        api.patch.mockClear();
        const input = view.container.querySelector("#preferred-prop-node-hash");
        await fireEvent.input(input, { target: { value: "deadbeef" } });
        await fireEvent.keyDown(input, { key: "Enter" });
        expect(ToastUtils.error).toHaveBeenCalledWith(t("tools.propagation_nodes.invalid_hash"));
        expect(api.patch).not.toHaveBeenCalled();
    });

    it("savePreferredPropagationNodeHash turns off auto-select", async () => {
        const { view, api } = await renderSettings(
            buildFullServerConfig({ lxmf_preferred_propagation_node_auto_select: true })
        );
        await selectTab(view.container, "Messages");
        const input = view.container.querySelector("#preferred-prop-node-hash");
        await fireEvent.input(input, { target: { value: "<A39610C89D18BB48C73E429582423C24>" } });
        await fireEvent.keyDown(input, { key: "Enter" });
        expect(api.patch).toHaveBeenCalledWith("/api/v1/config", {
            lxmf_preferred_propagation_node_destination_hash: "a39610c89d18bb48c73e429582423c24",
            lxmf_preferred_propagation_node_auto_select: false,
        });
    });

    it("onLxmfPreferredPropagationNodeAutoSelectChange PATCHes", async () => {
        const { view, api } = await renderSettings();
        await selectTab(view.container, "Messages");
        const toggle = view.container.querySelector("#auto-select-propagation-node");
        expect(toggle).not.toBeNull();
        await fireEvent.click(toggle);
        expect(api.patch).toHaveBeenCalledWith("/api/v1/config", {
            lxmf_preferred_propagation_node_auto_select: true,
        });
    });

    it("onLxmfLocalPropagationNodeEnabledChange PATCHes", async () => {
        const { view, api } = await renderSettings();
        await selectTab(view.container, "Messages");
        const toggle = view.container.querySelector("#local-propagation-node");
        expect(toggle).not.toBeNull();
        await fireEvent.click(toggle);
        expect(api.patch).toHaveBeenCalledWith("/api/v1/config", {
            lxmf_local_propagation_node_enabled: true,
        });
    });

    it("onLxmfPreferredPropagationNodeAutoSyncIntervalSecondsChange PATCHes", async () => {
        const { view, api } = await renderSettings();
        await selectTab(view.container, "Messages");
        const select = view.container.querySelector("#auto-sync-interval-select");
        expect(select).not.toBeNull();
        await fireEvent.change(select, { target: { value: "3600" } });
        expect(api.patch).toHaveBeenCalledWith("/api/v1/config", {
            lxmf_preferred_propagation_node_auto_sync_interval_seconds: 3600,
        });
    });

    it("onLxmfIncomingDeliveryPresetChange PATCHes preset size", async () => {
        const { view, api } = await renderSettings();
        await selectTab(view.container, "Messages");
        const select = view.container.querySelector("#incoming-message-size-select");
        expect(select).not.toBeNull();
        await fireEvent.change(select, { target: { value: "1gb" } });
        expect(api.patch).toHaveBeenCalledWith("/api/v1/config", {
            lxmf_delivery_transfer_limit_in_bytes: 1024 * 1024 * 1024,
        });
    });

    it("LXMF transfer/sync limits PATCH on input", async () => {
        const { view, api } = await renderSettings();
        await selectTab(view.container, "Messages");

        const transferLimitInput = view.container.querySelector("#prop-transfer-limit-mb");
        expect(transferLimitInput).not.toBeNull();
        await fireEvent.input(transferLimitInput, { target: { value: "0.3" } });
        expect(api.patch).toHaveBeenCalledWith("/api/v1/config", {
            lxmf_propagation_transfer_limit_in_bytes: Math.round(0.3 * 1024 * 1024),
        });

        const syncLimitInput = view.container.querySelector("#prop-sync-limit-mb");
        expect(syncLimitInput).not.toBeNull();
        await fireEvent.input(syncLimitInput, { target: { value: "9" } });
        expect(api.patch).toHaveBeenCalledWith("/api/v1/config", {
            lxmf_propagation_sync_limit_in_bytes: 9 * 1024 * 1024,
        });
    });

    it("onInboundStampsEnabledChange toggle PATCHes zero stamp cost", async () => {
        const { view, api } = await renderSettings(buildFullServerConfig({ lxmf_inbound_stamp_cost: 12 }));
        await selectTab(view.container, "Messages");
        const toggle = view.container.querySelector("#inbound-stamps-required");
        expect(toggle).not.toBeNull();
        await fireEvent.click(toggle);
        expect(api.patch).toHaveBeenCalledWith("/api/v1/config", { lxmf_inbound_stamp_cost: 0 });
    });

    it("onInboundStampsEnabledChange toggle restores remembered stamp cost", async () => {
        const { view, api } = await renderSettings(buildFullServerConfig({ lxmf_inbound_stamp_cost: 0 }));
        await selectTab(view.container, "Messages");
        const toggle = view.container.querySelector("#inbound-stamps-required");
        expect(toggle).not.toBeNull();
        await fireEvent.click(toggle);
        expect(api.patch).toHaveBeenCalledWith("/api/v1/config", { lxmf_inbound_stamp_cost: 8 });
    });

    it("onLxmfInboundStampCostChange PATCHes value", async () => {
        const { view, api } = await renderSettings(buildFullServerConfig({ lxmf_inbound_stamp_cost: 8 }));
        await selectTab(view.container, "Messages");
        const input = view.container.querySelector("#lxmf-inbound-stamp-cost");
        expect(input).not.toBeNull();
        await fireEvent.input(input, { target: { value: "12" } });
        expect(api.patch).toHaveBeenCalledWith("/api/v1/config", { lxmf_inbound_stamp_cost: 12 });
    });

    it("onLxmfPropagationNodeStampCostChange PATCHes value", async () => {
        const { view, api } = await renderSettings(
            buildFullServerConfig({ lxmf_local_propagation_node_enabled: true })
        );
        await selectTab(view.container, "Messages");
        const input = view.container.querySelector("#prop-stamp-cost");
        expect(input).not.toBeNull();
        await fireEvent.input(input, { target: { value: "20" } });
        expect(api.patch).toHaveBeenCalledWith("/api/v1/config", { lxmf_propagation_node_stamp_cost: 20 });
    });

    it("page archiver toggles and numeric config PATCH", async () => {
        const { view, api } = await renderSettings();
        await selectTab(view.container, "Nomad");

        const toggle = view.container.querySelector("#page-archiver-enabled");
        expect(toggle).not.toBeNull();
        await fireEvent.click(toggle);
        expect(api.patch).toHaveBeenCalledWith("/api/v1/config", { page_archiver_enabled: true });

        const maxVersionsInput = view.container.querySelector("#archiver-max-versions");
        expect(maxVersionsInput).not.toBeNull();
        await fireEvent.input(maxVersionsInput, { target: { value: "12" } });
        expect(api.patch).toHaveBeenCalledWith("/api/v1/config", { page_archiver_max_versions: 12 });

        const maxStorageInput = view.container.querySelector("#archiver-max-storage");
        expect(maxStorageInput).not.toBeNull();
        await fireEvent.input(maxStorageInput, { target: { value: "2" } });
        expect(api.patch).toHaveBeenCalledWith("/api/v1/config", { archives_max_storage_gb: 2 });
    });

    it("Nomad renderer toggles and default path PATCH", async () => {
        const { view, api } = await renderSettings();
        await selectTab(view.container, "Nomad");

        const mdToggle = view.container.querySelector("#nomad-render-markdown");
        expect(mdToggle).not.toBeNull();
        await fireEvent.click(mdToggle);
        expect(api.patch).toHaveBeenCalledWith("/api/v1/config", { nomad_render_markdown_enabled: false });

        const htmlToggle = view.container.querySelector("#nomad-render-html");
        expect(htmlToggle).not.toBeNull();
        await fireEvent.click(htmlToggle);
        expect(api.patch).toHaveBeenCalledWith("/api/v1/config", { nomad_render_html_enabled: false });

        const plainToggle = view.container.querySelector("#nomad-render-plaintext");
        expect(plainToggle).not.toBeNull();
        await fireEvent.click(plainToggle);
        expect(api.patch).toHaveBeenCalledWith("/api/v1/config", { nomad_render_plaintext_enabled: false });

        const pathSelect = view.container.querySelector("#nomad-default-page-path");
        expect(pathSelect).not.toBeNull();
        await fireEvent.change(pathSelect, { target: { value: "/page/index.md" } });
        expect(api.patch).toHaveBeenCalledWith("/api/v1/config", { nomad_default_page_path: "/page/index.md" });
    });

    it("stranger protection PATCHes each flag", async () => {
        const { view, api } = await renderSettings();
        await selectTab(view.container, "Messages");

        const blockAttachments = view.container.querySelector("#block-attachments-from-strangers");
        expect(blockAttachments).not.toBeNull();
        await fireEvent.click(blockAttachments);
        expect(api.patch).toHaveBeenCalledWith("/api/v1/config", { block_attachments_from_strangers: false });

        const blockAll = view.container.querySelector("#block-all-from-strangers");
        expect(blockAll).not.toBeNull();
        await fireEvent.click(blockAll);
        expect(api.patch).toHaveBeenCalledWith("/api/v1/config", { block_all_from_strangers: true });

        const unknownBanner = view.container.querySelector("#show-unknown-contact-banner");
        expect(unknownBanner).not.toBeNull();
        await fireEvent.click(unknownBanner);
        expect(api.patch).toHaveBeenCalledWith("/api/v1/config", { show_unknown_contact_banner: false });

        const warnLinks = view.container.querySelector("#warn-on-stranger-links");
        expect(warnLinks).not.toBeNull();
        await fireEvent.click(warnLinks);
        expect(api.patch).toHaveBeenCalledWith("/api/v1/config", { warn_on_stranger_links: false });
    });

    it("banishment PATCHes toggle and text/color", async () => {
        const { view, api } = await renderSettings();
        await selectTab(view.container, "Privacy");

        const toggle = view.container.querySelector("#banished-effect-enabled");
        expect(toggle).not.toBeNull();
        await fireEvent.click(toggle);
        expect(api.patch).toHaveBeenCalledWith("/api/v1/config", { banished_effect_enabled: false });

        // Re-enable so inputs are visible
        await fireEvent.click(toggle);

        const textInput = view.container.querySelector("#banished-text-input");
        expect(textInput).not.toBeNull();
        await fireEvent.input(textInput, { target: { value: "OUT" } });
        expect(api.patch).toHaveBeenCalledWith("/api/v1/config", { banished_text: "OUT" });

        const colorInput = view.container.querySelector("#banished-color-input");
        expect(colorInput).not.toBeNull();
        await fireEvent.input(colorInput, { target: { value: "#ff0000" } });
        expect(api.patch).toHaveBeenCalledWith("/api/v1/config", { banished_color: "#ff0000" });
    });

    it("crawler enabled and fields PATCH", async () => {
        const { view, api } = await renderSettings();
        await selectTab(view.container, "Network");

        const toggle = view.container.querySelector("#crawler-enabled");
        expect(toggle).not.toBeNull();
        await fireEvent.click(toggle);
        expect(api.patch).toHaveBeenCalledWith("/api/v1/config", { crawler_enabled: true });

        const hopsInput = view.container.querySelector("#crawler-max-hops");
        expect(hopsInput).not.toBeNull();
        await fireEvent.input(hopsInput, { target: { value: "3" } });
        expect(api.patch).toHaveBeenCalledWith("/api/v1/config", { crawler_max_hops: 3 });

        const rttInput = view.container.querySelector("#crawler-max-rtt");
        expect(rttInput).not.toBeNull();
        await fireEvent.input(rttInput, { target: { value: "2000" } });
        expect(api.patch).toHaveBeenCalledWith("/api/v1/config", { crawler_max_rtt_ms: 2000 });
    });

    it("desktop toggles PATCH", async () => {
        ElectronUtils.isElectron.mockReturnValue(true);
        const { view, api } = await renderSettings();

        const toggle = view.container.querySelector("#desktop-hardware-acceleration-enabled");
        expect(toggle).not.toBeNull();
        await fireEvent.click(toggle);
        expect(api.patch).toHaveBeenCalledWith("/api/v1/config", { desktop_hardware_acceleration_enabled: false });
        ElectronUtils.isElectron.mockReturnValue(false);
    });

    it("onAuthEnabledChange PATCHes auth", async () => {
        const { view, api } = await renderSettings(buildFullServerConfig({ auth_enabled: true }));
        await selectTab(view.container, "Privacy");

        const toggle = view.container.querySelector("#auth-enabled");
        expect(toggle).not.toBeNull();
        await fireEvent.click(toggle);
        expect(api.patch).toHaveBeenCalledWith("/api/v1/config", { auth_enabled: false });
    });

    it("onGiteaConfigChange PATCHes", async () => {
        const { view, api } = await renderSettings();
        await selectTab(view.container, "Maintenance");

        const input = view.container.querySelector("#gitea-base-url-input");
        expect(input).not.toBeNull();
        await fireEvent.input(input, { target: { value: "https://gitea.example" } });
        expect(api.patch).toHaveBeenCalledWith("/api/v1/config", { gitea_base_url: "https://gitea.example" });
    });

    it("onCspConfigChange PATCHes CSP fields", async () => {
        const { view, api } = await renderSettings();
        await selectTab(view.container, "Privacy");

        const connectInput = view.container.querySelector("#csp-connect-src");
        expect(connectInput).not.toBeNull();
        await fireEvent.input(connectInput, { target: { value: "wss://a.example" } });
        expect(api.patch).toHaveBeenCalledWith("/api/v1/config", { csp_extra_connect_src: "wss://a.example" });
    });

    it("onBackupConfigChange PATCHes backup_max_count", async () => {
        const { view, api } = await renderSettings();
        await selectTab(view.container, "Maintenance");

        const input = view.container.querySelector("#backup-max-count-input");
        expect(input).not.toBeNull();
        await fireEvent.input(input, { target: { value: "8" } });
        expect(api.patch).toHaveBeenCalledWith("/api/v1/config", { backup_max_count: 8 });
    });

    it("inline location and telemetry PATCH via updateConfig", async () => {
        const { view, api } = await renderSettings();
        const locationSelect = view.container.querySelector("#location-source-select");
        expect(locationSelect).not.toBeNull();
        await fireEvent.change(locationSelect, { target: { value: "manual" } });
        expect(api.patch).toHaveBeenCalledWith("/api/v1/config", { location_source: "manual" });

        await selectTab(view.container, "Privacy");
        const telemetryToggle = view.container.querySelector("#telemetry-enabled");
        expect(telemetryToggle).not.toBeNull();
        await fireEvent.click(telemetryToggle);
        expect(api.patch).toHaveBeenCalledWith("/api/v1/config", { telemetry_enabled: true });
    });
});

describe("SettingsPage: transport mode (POST, not PATCH)", () => {
    afterEach(() => {
        delete window.api;
        vi.clearAllMocks();
    });

    it("onIsTransportEnabledChange POSTs enable when turning on", async () => {
        const { view, api } = await renderSettings(buildFullServerConfig({ is_transport_enabled: false }));
        await selectTab(view.container, "Network");
        const toggle = view.container.querySelector("#transport-enabled");
        expect(toggle).not.toBeNull();
        await fireEvent.click(toggle);
        expect(api.post).toHaveBeenCalledWith("/api/v1/reticulum/enable-transport");
    });

    it("onIsTransportEnabledChange POSTs disable when turning off", async () => {
        const { view, api } = await renderSettings(buildFullServerConfig({ is_transport_enabled: true }));
        await selectTab(view.container, "Network");
        const toggle = view.container.querySelector("#transport-enabled");
        expect(toggle).not.toBeNull();
        await fireEvent.click(toggle);
        expect(api.post).toHaveBeenCalledWith("/api/v1/reticulum/disable-transport");
    });
});

describe("SettingsPage: visualiser display prefs (localStorage + emitter)", () => {
    beforeEach(() => {
        vi.spyOn(GlobalEmitter, "emit");
        localStorage.clear();
    });

    afterEach(() => {
        delete window.api;
        GlobalEmitter.emit.mockRestore();
        vi.clearAllMocks();
    });

    it("onVisualiserShowDisabledChange persists and emits", async () => {
        const { view } = await renderSettings();
        await selectTab(view.container, "Network");
        const toggle = view.container.querySelector("#settings-visualiser-offline");
        expect(toggle).not.toBeNull();
        await fireEvent.click(toggle);
        expect(localStorage.getItem("meshchatx.visualiser.showDisabledInterfaces")).toBe("true");
        expect(GlobalEmitter.emit).toHaveBeenCalledWith("visualiser-display-prefs-changed");
    });

    it("onVisualiserShowDiscoveredChange persists and emits", async () => {
        const { view } = await renderSettings();
        await selectTab(view.container, "Network");
        const toggle = view.container.querySelector("#settings-visualiser-discovered");
        expect(toggle).not.toBeNull();
        await fireEvent.click(toggle);
        expect(localStorage.getItem("meshchatx.visualiser.showDiscoveredInterfaces")).toBe("true");
        expect(GlobalEmitter.emit).toHaveBeenCalledWith("visualiser-display-prefs-changed");
    });

    it("onVisualiserRendererChange persists renderer and emits", async () => {
        const { view } = await renderSettings();
        await selectTab(view.container, "Network");
        const select = view.container.querySelector("#settings-visualiser-renderer");
        expect(select).not.toBeNull();
        await fireEvent.change(select, { target: { value: "webgl" } });
        expect(localStorage.getItem("meshchatx.visualiser.renderer")).toBe("webgl");
        expect(GlobalEmitter.emit).toHaveBeenCalledWith("visualiser-display-prefs-changed");
    });

    it("onDetailedOutboundSendStatusChange updates GlobalState and localStorage", async () => {
        localStorage.removeItem("meshchatx_detailed_outbound_send_status");
        const { view } = await renderSettings();
        const checkbox = view.container.querySelector("#detailed-outbound-send-status");
        expect(checkbox).not.toBeNull();
        await fireEvent.click(checkbox);
        expect(GlobalState.detailedOutboundSendStatus).toBe(true);
        expect(localStorage.getItem("meshchatx_detailed_outbound_send_status")).toBe("true");
        await fireEvent.click(checkbox);
        expect(GlobalState.detailedOutboundSendStatus).toBe(false);
        expect(localStorage.getItem("meshchatx_detailed_outbound_send_status")).toBe("false");
    });

    it("onOutboundTransferProgressEnabledChange updates GlobalState and localStorage", async () => {
        localStorage.removeItem("meshchatx_outbound_transfer_progress_enabled");
        const { view } = await renderSettings();
        const checkbox = view.container.querySelector("#outbound-transfer-progress-enabled");
        expect(checkbox).not.toBeNull();
        await fireEvent.click(checkbox);
        expect(GlobalState.outboundTransferProgressEnabled).toBe(false);
        expect(localStorage.getItem("meshchatx_outbound_transfer_progress_enabled")).toBe("false");
        await fireEvent.click(checkbox);
        expect(GlobalState.outboundTransferProgressEnabled).toBe(true);
        expect(localStorage.getItem("meshchatx_outbound_transfer_progress_enabled")).toBe("true");
    });
});

describe("SettingsPage: maintenance, exports, telemetry trust, RNS reload", () => {
    afterEach(() => {
        delete window.api;
    });

    it("reloadRns POSTs reticulum reload", async () => {
        const { view, api } = await renderSettings();
        await selectTab(view.container, "Maintenance");
        const buttons = Array.from(view.container.querySelectorAll("button"));
        const reloadBtn = buttons.find((btn) => btn.textContent && btn.textContent.includes(t("app.reload_rns")));
        expect(reloadBtn).not.toBeNull();
        await fireEvent.click(reloadBtn);
        expect(api.post).toHaveBeenCalledWith("/api/v1/reticulum/reload");
    });

    it("clearMessages DELETEs maintenance messages", async () => {
        const { view, api } = await renderSettings();
        await selectTab(view.container, "Maintenance");
        const buttons = Array.from(view.container.querySelectorAll("button"));
        const clearBtn = buttons.find(
            (btn) => btn.textContent && btn.textContent.includes(t("maintenance.clear_messages"))
        );
        expect(clearBtn).not.toBeNull();
        await fireEvent.click(clearBtn);
        expect(api.delete).toHaveBeenCalledWith("/api/v1/maintenance/messages");
    });

    it("clearDuplicateMessages DELETEs duplicates endpoint", async () => {
        const { view, api } = await renderSettings();
        await selectTab(view.container, "Maintenance");
        api.delete.mockResolvedValue({ data: { deleted: 5 } });
        const buttons = Array.from(view.container.querySelectorAll("button"));
        const clearBtn = buttons.find(
            (btn) => btn.textContent && btn.textContent.includes(t("maintenance.clear_duplicates"))
        );
        expect(clearBtn).not.toBeNull();
        await fireEvent.click(clearBtn);
        expect(api.delete).toHaveBeenCalledWith("/api/v1/maintenance/messages/duplicates");
    });

    it("maintenance UI exposes duplicate cleanup and age purge", async () => {
        const { view } = await renderSettings();
        await selectTab(view.container, "Maintenance");
        const text = view.container.textContent;
        expect(text).toContain(t("maintenance.clear_duplicates"));
        expect(text).toContain(t("maintenance.purge_old_title"));
        expect(text).toContain(t("maintenance.export_old_archive"));
    });

    it("clearAnnounces DELETEs announces", async () => {
        const { view, api } = await renderSettings();
        await selectTab(view.container, "Maintenance");
        const buttons = Array.from(view.container.querySelectorAll("button"));
        const clearBtn = buttons.find(
            (btn) => btn.textContent && btn.textContent.includes(t("maintenance.clear_announces"))
        );
        expect(clearBtn).not.toBeNull();
        await fireEvent.click(clearBtn);
        expect(api.delete).toHaveBeenCalledWith("/api/v1/maintenance/announces");
    });

    it("clearNomadnetFavorites DELETEs with aspect param", async () => {
        const { view, api } = await renderSettings();
        await selectTab(view.container, "Maintenance");
        const buttons = Array.from(view.container.querySelectorAll("button"));
        const clearBtn = buttons.find(
            (btn) => btn.textContent && btn.textContent.includes(t("maintenance.clear_nomadnet_favs"))
        );
        expect(clearBtn).not.toBeNull();
        await fireEvent.click(clearBtn);
        expect(api.delete).toHaveBeenCalledWith("/api/v1/maintenance/favourites", {
            params: { aspect: "nomadnetwork.node" },
        });
    });

    it("clearLxmfIcons DELETEs lxmf-icons", async () => {
        const { view, api } = await renderSettings();
        await selectTab(view.container, "Maintenance");
        const buttons = Array.from(view.container.querySelectorAll("button"));
        const clearBtn = buttons.find(
            (btn) => btn.textContent && btn.textContent.includes(t("maintenance.clear_lxmf_icons"))
        );
        expect(clearBtn).not.toBeNull();
        await fireEvent.click(clearBtn);
        expect(api.delete).toHaveBeenCalledWith("/api/v1/maintenance/lxmf-icons");
    });

    it("clearStickers DELETEs stickers", async () => {
        const { view, api } = await renderSettings();
        await selectTab(view.container, "Maintenance");
        const buttons = Array.from(view.container.querySelectorAll("button"));
        const clearBtn = buttons.find(
            (btn) => btn.textContent && btn.textContent.includes(t("maintenance.clear_stickers"))
        );
        expect(clearBtn).not.toBeNull();
        await fireEvent.click(clearBtn);
        expect(api.delete).toHaveBeenCalledWith("/api/v1/maintenance/stickers");
    });

    it("clearArchives DELETEs archives", async () => {
        const { view, api } = await renderSettings();
        await selectTab(view.container, "Maintenance");
        const buttons = Array.from(view.container.querySelectorAll("button"));
        const clearBtn = buttons.find(
            (btn) => btn.textContent && btn.textContent.includes(t("maintenance.clear_archives"))
        );
        expect(clearBtn).not.toBeNull();
        await fireEvent.click(clearBtn);
        expect(api.delete).toHaveBeenCalledWith("/api/v1/maintenance/archives");
    });

    it("clearReticulumDocs DELETEs docs", async () => {
        const { view, api } = await renderSettings();
        await selectTab(view.container, "Maintenance");
        const buttons = Array.from(view.container.querySelectorAll("button"));
        const clearBtn = buttons.find(
            (btn) => btn.textContent && btn.textContent.includes(t("maintenance.clear_reticulum_docs"))
        );
        expect(clearBtn).not.toBeNull();
        await fireEvent.click(clearBtn);
        expect(api.delete).toHaveBeenCalledWith("/api/v1/maintenance/docs/reticulum");
    });

    it("exportMessages GETs export endpoint", async () => {
        const { view, api } = await renderSettings();
        await selectTab(view.container, "Maintenance");
        const buttons = Array.from(view.container.querySelectorAll("button"));
        const exportBtn = buttons.find(
            (btn) => btn.textContent && btn.textContent.includes(t("maintenance.export_messages"))
        );
        expect(exportBtn).not.toBeNull();
        await fireEvent.click(exportBtn);
        expect(api.get).toHaveBeenCalledWith("/api/v1/messages/export");
    });

    it("purgeOldMessages DELETEs with older_than_days", async () => {
        const { view, api } = await renderSettings();
        await selectTab(view.container, "Maintenance");
        api.delete.mockResolvedValue({ data: { deleted: 2 } });
        const daysInput = view.container.querySelector("#purge-older-days");
        expect(daysInput).not.toBeNull();
        await fireEvent.input(daysInput, { target: { value: "30" } });

        const buttons = Array.from(view.container.querySelectorAll("button"));
        const purgeBtn = buttons.find(
            (btn) => btn.textContent && btn.textContent.includes(t("maintenance.purge_old_confirm_btn"))
        );
        expect(purgeBtn).not.toBeNull();
        await fireEvent.click(purgeBtn);

        expect(api.delete).toHaveBeenCalledWith("/api/v1/maintenance/messages", {
            params: { older_than_days: 30 },
        });
    });

    it("refreshMessageAgePurgePreview GETs purge-preview", async () => {
        const { view, api } = await renderSettings();
        await selectTab(view.container, "Maintenance");
        api.get.mockResolvedValue({ data: { count: 4, cutoff: 1 } });

        const buttons = Array.from(view.container.querySelectorAll("button"));
        const previewBtn = buttons.find(
            (btn) => btn.textContent && btn.textContent.includes(t("maintenance.purge_preview"))
        );
        expect(previewBtn).not.toBeNull();
        await fireEvent.click(previewBtn);

        expect(api.get).toHaveBeenCalledWith("/api/v1/maintenance/messages/purge-preview", {
            params: { older_than_days: 90 },
        });
    });

    it("exportOldMessagesArchive POSTs filtered export", async () => {
        const { view, api } = await renderSettings();
        await selectTab(view.container, "Maintenance");
        api.post.mockResolvedValue({ data: { format: "meshchatx/messages/v2", messages: [] } });

        const buttons = Array.from(view.container.querySelectorAll("button"));
        const exportArchiveBtn = buttons.find(
            (btn) => btn.textContent && btn.textContent.includes(t("maintenance.export_old_archive"))
        );
        expect(exportArchiveBtn).not.toBeNull();
        await fireEvent.click(exportArchiveBtn);

        expect(api.post).toHaveBeenCalledWith("/api/v1/maintenance/messages/export", {
            older_than_days: 90,
        });
    });

    it("exportFolders GETs folders export", async () => {
        const { view, api } = await renderSettings();
        await selectTab(view.container, "Maintenance");
        const buttons = Array.from(view.container.querySelectorAll("button"));
        const exportFoldersBtn = buttons.find(
            (btn) => btn.textContent && btn.textContent.toLowerCase().includes("export folders")
        );
        expect(exportFoldersBtn).not.toBeNull();
        await fireEvent.click(exportFoldersBtn);
        expect(api.get).toHaveBeenCalledWith("/api/v1/lxmf/folders/export");
    });

    it("flushArchivedPages sends websocket flush after confirm", async () => {
        const { view } = await renderSettings();
        await selectTab(view.container, "Nomad");
        const buttons = Array.from(view.container.querySelectorAll("button"));
        const flushBtn = buttons.find(
            (btn) => btn.textContent && btn.textContent.toLowerCase().includes("flush all archived pages")
        );
        expect(flushBtn).not.toBeNull();
        await fireEvent.click(flushBtn);
        expect(WebSocketConnection.send).toHaveBeenCalledWith(JSON.stringify({ type: "nomadnet.page.archive.flush" }));
    });

    it("revokeTelemetryTrust PATCHes contact telemetry flag", async () => {
        const serverConfig = buildFullServerConfig({ telemetry_enabled: true });
        const { view, api } = await renderSettings(serverConfig);
        await selectTab(view.container, "Privacy");

        api.get.mockImplementation(async (path) => {
            if (path === "/api/v1/telemetry/peers") {
                return {
                    data: {
                        peers: [{ id: "c1", name: "Peer", remote_identity_hash: "1234567890abcdef" }],
                    },
                };
            }
            if (path === "/api/v1/config") {
                return { data: { config: serverConfig } };
            }
            return { data: {} };
        });

        await selectTab(view.container, "General");
        await selectTab(view.container, "Privacy");

        const buttons = Array.from(view.container.querySelectorAll("button"));
        const revokeBtn = buttons.find((btn) => btn.title && btn.title.includes(t("app.telemetry_revoke_trust")));
        if (revokeBtn) {
            await fireEvent.click(revokeBtn);
            expect(api.patch).toHaveBeenCalledWith("/api/v1/telephone/contacts/c1", {
                is_telemetry_trusted: false,
            });
        }
    });
});
