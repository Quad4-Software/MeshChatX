// SPDX-License-Identifier: 0BSD

import { render, fireEvent } from "@testing-library/svelte";
import { describe, expect, it, vi } from "vitest";
import SettingToggleRow from "../../meshchatx/src/frontend/features/settings/components/SettingToggleRow.svelte";
import StrangerProtectionSettingsSection from "../../meshchatx/src/frontend/features/settings/components/sections/StrangerProtectionSettingsSection.svelte";
import BanishmentSettingsSection from "../../meshchatx/src/frontend/features/settings/components/sections/BanishmentSettingsSection.svelte";
import TelephonySettingsSection from "../../meshchatx/src/frontend/features/settings/components/sections/TelephonySettingsSection.svelte";
import AppearanceSettingsSection from "../../meshchatx/src/frontend/features/settings/components/sections/AppearanceSettingsSection.svelte";
import BatterySettingsSection from "../../meshchatx/src/frontend/features/settings/components/sections/BatterySettingsSection.svelte";
import VisualiserSettingsSection from "../../meshchatx/src/frontend/features/settings/components/sections/VisualiserSettingsSection.svelte";
import BlockedSettingsSection from "../../meshchatx/src/frontend/features/settings/components/sections/BlockedSettingsSection.svelte";
import AndroidSettingsSection from "../../meshchatx/src/frontend/features/settings/components/sections/AndroidSettingsSection.svelte";
import ArchiverSettingsSection from "../../meshchatx/src/frontend/features/settings/components/sections/ArchiverSettingsSection.svelte";

describe("SettingToggleRow", () => {
    it("renders title and description and emits updates", async () => {
        const onchange = vi.fn();
        const { container } = render(SettingToggleRow, {
            props: {
                id: "probe-toggle",
                checked: false,
                title: "Probe title",
                description: "Probe description",
                hint: "Probe hint",
                onchange,
            },
        });
        expect(container.textContent).toContain("Probe title");
        expect(container.textContent).toContain("Probe description");
        expect(container.textContent).toContain("Probe hint");
        const input = container.querySelector("input[type='checkbox']");
        await fireEvent.click(input);
        expect(onchange).toHaveBeenCalledWith(true);
    });
});

describe("StrangerProtectionSettingsSection", () => {
    it("emits dedicated events for each stranger toggle", async () => {
        const onblockattachmentschange = vi.fn();
        const onblockallchange = vi.fn();
        const onunknownbannerchange = vi.fn();
        const onwarnlinkschange = vi.fn();
        const { container } = render(StrangerProtectionSettingsSection, {
            props: {
                visible: true,
                config: {
                    block_attachments_from_strangers: false,
                    block_all_from_strangers: false,
                    show_unknown_contact_banner: true,
                    warn_on_stranger_links: true,
                },
                onblockattachmentschange,
                onblockallchange,
                onunknownbannerchange,
                onwarnlinkschange,
            },
        });
        const inputs = container.querySelectorAll("input[type='checkbox']");
        expect(inputs).toHaveLength(4);
        await fireEvent.click(inputs[0]);
        await fireEvent.click(inputs[1]);
        await fireEvent.click(inputs[2]);
        await fireEvent.click(inputs[3]);
        expect(onblockattachmentschange).toHaveBeenCalledWith(true);
        expect(onblockallchange).toHaveBeenCalledWith(true);
        expect(onunknownbannerchange).toHaveBeenCalledWith(false);
        expect(onwarnlinkschange).toHaveBeenCalledWith(false);
    });
});

describe("BanishmentSettingsSection", () => {
    it("shows text and color controls only when enabled", async () => {
        const ontextchange = vi.fn();
        const { container, rerender } = render(BanishmentSettingsSection, {
            props: {
                visible: true,
                config: {
                    banished_effect_enabled: false,
                    banished_text: "gone",
                    banished_color: "#112233",
                },
            },
        });
        expect(container.querySelector("input[type='text']")).toBeNull();
        await rerender({
            config: {
                banished_effect_enabled: true,
                banished_text: "gone",
                banished_color: "#112233",
            },
            ontextchange,
        });
        expect(container.querySelector("input[type='text']")).not.toBeNull();
        expect(container.querySelector('input[type="color"]').classList.contains("color-fill-input")).toBe(true);
        const textInput = container.querySelector("input[type='text']");
        await fireEvent.input(textInput, { target: { value: "banished" } });
        expect(ontextchange).toHaveBeenCalledWith("banished");
    });
});

describe("TelephonySettingsSection", () => {
    it("emits enabled-change from the telephone toggle", async () => {
        const onenabledchange = vi.fn();
        const { container } = render(TelephonySettingsSection, {
            props: {
                visible: true,
                config: { telephone_enabled: true },
                onenabledchange,
            },
        });
        const input = container.querySelector("input[type='checkbox']");
        await fireEvent.click(input);
        expect(onenabledchange).toHaveBeenCalledWith(false);
    });
});

describe("AppearanceSettingsSection", () => {
    it("renders glass and split-view toggles as stacked setting rows", () => {
        const { container } = render(AppearanceSettingsSection, {
            props: {
                visible: true,
                config: {
                    theme: "dark",
                    messages_sidebar_position: "left",
                    app_sidebar_layout: "grouped",
                    message_font_size: 14,
                    message_icon_size: 28,
                    ui_transparency: 0,
                    ui_glass_enabled: true,
                    messages_multi_pane_enabled: true,
                    nomad_tabs_enabled: true,
                    rrc_enabled: true,
                    rrc_unread_badges_enabled: true,
                },
            },
        });
        const toggles = container.querySelectorAll("label.setting-toggle");
        expect(toggles.length).toBeGreaterThanOrEqual(4);
    });

    it("emits theme and field events without mutating config prop", async () => {
        const onupdatefield = vi.fn();
        const config = {
            theme: "light",
            messages_sidebar_position: "left",
            message_font_size: 14,
            message_icon_size: 28,
            ui_transparency: 0,
            ui_glass_enabled: true,
            messages_multi_pane_enabled: false,
            nomad_tabs_enabled: false,
            rrc_enabled: false,
            rrc_unread_badges_enabled: true,
            message_outbound_bubble_color: "#4f46e5",
            message_inbound_bubble_color: null,
            message_failed_bubble_color: "#ef4444",
            message_waiting_bubble_color: "#e5e7eb",
        };
        const { container } = render(AppearanceSettingsSection, {
            props: {
                visible: true,
                config,
                onupdatefield,
            },
        });
        expect(container.textContent).toContain("Appearance");
        const selects = container.querySelectorAll("select");
        await fireEvent.change(selects[0], { target: { value: "dark" } });
        expect(onupdatefield).toHaveBeenCalledWith({ key: "theme", value: "dark" });
    });
});

describe("BatterySettingsSection", () => {
    it("emits patch and apply events for battery controls", async () => {
        const onenabledchange = vi.fn();
        const batterySaver = {
            enabled: false,
            disableVisualiserDiscovery: false,
            hideOfflineInterfaces: false,
            maxVisualiserInterfaces: 0,
            visualiserReloadSeconds: 0,
            disableVisualiserLiveLayout: false,
            reduceBackgroundPolling: false,
            backgroundPollMultiplier: 2,
            reduceInterfacesDiscovery: false,
            interfacesStatsPollSeconds: 5,
            interfacesDiscoveryPollSeconds: 30,
            applyInterfaceBitrateLimits: false,
            interfaceBitrateLimits: {},
        };
        const { container } = render(BatterySettingsSection, {
            props: {
                visible: true,
                batterySaver,
                batteryInterfaceRows: [],
                batteryBitrateBusy: false,
                onenabledchange,
            },
        });
        expect(container.textContent).toContain("Battery saver");
        const toggle = container.querySelector("#settings-battery-saver-enabled");
        await fireEvent.click(toggle);
        expect(onenabledchange).toHaveBeenCalledWith(true);
    });
});

describe("VisualiserSettingsSection", () => {
    it("emits renderer, view mode, and visibility changes", async () => {
        const onrendererchange = vi.fn();
        const onviewmodechange = vi.fn();
        const onshowdisabledchange = vi.fn();
        const { container } = render(VisualiserSettingsSection, {
            props: {
                visible: true,
                renderer: "auto",
                viewMode: "flat",
                showDisabledInterfaces: false,
                showDiscoveredInterfaces: true,
                onrendererchange,
                onviewmodechange,
                onshowdisabledchange,
            },
        });
        expect(container.textContent).toContain("Network Visualiser");
        await fireEvent.change(container.querySelector("#settings-visualiser-renderer"), {
            target: { value: "webgl" },
        });
        expect(onrendererchange).toHaveBeenCalledWith("webgl");
        await fireEvent.change(container.querySelector("#settings-visualiser-view-mode"), {
            target: { value: "planet" },
        });
        expect(onviewmodechange).toHaveBeenCalledWith("planet");
        const toggle = container.querySelector("#settings-visualiser-offline");
        await fireEvent.click(toggle);
        expect(onshowdisabledchange).toHaveBeenCalledWith(true);
    });
});

describe("BlockedSettingsSection", () => {
    it("renders banished management link", () => {
        const { container } = render(BlockedSettingsSection, {
            props: { visible: true },
        });
        expect(container.textContent).toContain("Banished");
        expect(container.textContent).toContain("Manage Banished");
    });
});

describe("AndroidSettingsSection", () => {
    it("emits privacy updates, remote backend actions, and share-apk", async () => {
        const onupdateBlockScreenshots = vi.fn();
        const onupdateClearClipboardOnBackground = vi.fn();
        const onupdateRemoteBackendUrl = vi.fn();
        const onapplyRemoteBackend = vi.fn();
        const onshareApk = vi.fn();
        const { container } = render(AndroidSettingsSection, {
            props: {
                visible: true,
                androidShellPrivacy: {
                    blockScreenshots: false,
                    clearClipboardOnBackground: false,
                },
                remoteBackendUrl: "",
                effectiveBackendUrl: "https://127.0.0.1:8000",
                remoteBackendActive: false,
                onupdateBlockScreenshots,
                onupdateClearClipboardOnBackground,
                onupdateRemoteBackendUrl,
                onapplyRemoteBackend,
                onshareApk,
            },
        });
        expect(container.textContent).toContain("Device privacy");
        expect(container.textContent).toContain("Remote backend URL");
        const checkboxes = container.querySelectorAll('input[type="checkbox"]');
        expect(checkboxes).toHaveLength(2);
        await fireEvent.click(checkboxes[0]);
        await fireEvent.click(checkboxes[1]);
        expect(onupdateBlockScreenshots).toHaveBeenCalledWith(true);
        expect(onupdateClearClipboardOnBackground).toHaveBeenCalledWith(true);
        const urlInput = container.querySelector('input[type="url"]');
        await fireEvent.input(urlInput, { target: { value: "http://192.168.1.10:9337" } });
        expect(onupdateRemoteBackendUrl).toHaveBeenCalledWith("http://192.168.1.10:9337");
        const buttons = container.querySelectorAll("button");
        await fireEvent.click(buttons[0]);
        expect(onapplyRemoteBackend).toHaveBeenCalledTimes(1);
        await fireEvent.click(buttons[2]);
        expect(onshareApk).toHaveBeenCalledTimes(1);
    });
});

describe("ArchiverSettingsSection", () => {
    it("emits enabled-change, config-change, and flush", async () => {
        const onenabledchange = vi.fn();
        const onconfigchange = vi.fn();
        const onflush = vi.fn();
        const { container } = render(ArchiverSettingsSection, {
            props: {
                visible: true,
                config: {
                    page_archiver_enabled: false,
                    page_archiver_max_versions: 5,
                    archives_max_storage_gb: 2,
                },
                onenabledchange,
                onconfigchange,
                onflush,
            },
        });
        expect(container.textContent).toContain("Page Archiver");
        const toggle = container.querySelector("#page-archiver-enabled");
        await fireEvent.click(toggle);
        expect(onenabledchange).toHaveBeenCalledWith(true);
        const numberInputs = container.querySelectorAll('input[type="number"]');
        await fireEvent.input(numberInputs[0], { target: { value: "8" } });
        expect(onconfigchange).toHaveBeenCalledWith({ page_archiver_max_versions: 8 });
        const flushBtn = container.querySelector("button");
        await fireEvent.click(flushBtn);
        expect(onflush).toHaveBeenCalledTimes(1);
    });
});
