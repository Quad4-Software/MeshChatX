// SPDX-License-Identifier: 0BSD

import { render, cleanup, screen, waitFor, fireEvent } from "@testing-library/svelte";
import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import PluginsSettingsSection from "@/features/settings/components/sections/PluginsSettingsSection.svelte";
import PluginItemCard from "@/features/settings/components/PluginItemCard.svelte";
import PluginPage from "@/features/plugins/PluginPage.svelte";
import DialogUtils from "@/js/DialogUtils";
import { registerFallbackMessages, registerTranslator } from "@/js/i18n.js";

vi.mock("@/js/ToastUtils", () => ({
    default: {
        success: vi.fn(),
        error: vi.fn(),
        info: vi.fn(),
        warning: vi.fn(),
    },
}));

vi.mock("@/js/DialogUtils", () => ({
    default: {
        confirm: vi.fn().mockResolvedValue(true),
        prompt: vi.fn(),
        alert: vi.fn(),
    },
}));

vi.mock("@/js/ElectronUtils", () => ({
    default: {
        isElectron: () => false,
        pickDirectory: vi.fn(),
    },
}));

vi.mock("@/js/registries/wsEventRegistry.js", () => ({
    onWsEvent: vi.fn(),
    offWsEvent: vi.fn(),
}));

const loadEnabledPlugins = vi.fn().mockResolvedValue(undefined);
const unloadPlugin = vi.fn();
const requestUiRefresh = vi.fn();
const getPluginUiCaps = vi.fn().mockReturnValue({ allowedWidgets: [], allowHtmlFrame: false });
const getLastDescriptor = vi.fn().mockReturnValue({
    type: "column",
    children: [{ type: "text", value: "Hello plugin" }],
});
const getLastUiError = vi.fn().mockReturnValue("");
const postAction = vi.fn();
const postInput = vi.fn();

vi.mock("@/js/plugins/PluginHost.js", () => ({
    pluginHost: {
        loadEnabledPlugins: (...args) => loadEnabledPlugins(...args),
        unloadPlugin: (...args) => unloadPlugin(...args),
        requestUiRefresh: (...args) => requestUiRefresh(...args),
        getPluginUiCaps: (...args) => getPluginUiCaps(...args),
        getLastDescriptor: (...args) => getLastDescriptor(...args),
        getLastUiError: (...args) => getLastUiError(...args),
        postAction: (...args) => postAction(...args),
        postInput: (...args) => postInput(...args),
    },
}));

describe("PluginItemCard.svelte", () => {
    beforeEach(() => {
        registerTranslator(null);
        registerFallbackMessages({
            plugins: {
                permissions: { none: "None" },
                settings: {
                    badge_enabled: "Enabled",
                    badge_disabled: "Disabled",
                    enable: "Enable",
                    disable: "Disable",
                    remove: "Remove",
                    permissions: "Permissions",
                    network_endpoints: "Endpoints",
                    auto_disabled: "Auto-disabled: {reason}",
                },
            },
        });
    });

    afterEach(() => {
        cleanup();
    });

    it("renders badges and fires enable/disable/remove", async () => {
        const onenable = vi.fn();
        const ondisable = vi.fn();
        const onremove = vi.fn();
        const plugin = {
            id: "com.example.demo",
            name: "Demo",
            description: "desc",
            version: "1.2.3",
            enabled: false,
            granted_permissions: [],
            network_endpoints: ["https://example.com"],
            auto_disabled_reason: "policy",
        };
        render(PluginItemCard, { props: { plugin, onenable, ondisable, onremove } });
        expect(screen.getByText("Demo")).toBeTruthy();
        expect(screen.getByText("Endpoints")).toBeTruthy();
        expect(screen.getByText("https://example.com")).toBeTruthy();
        expect(screen.getByText("Auto-disabled: policy")).toBeTruthy();
        await fireEvent.click(screen.getByText("Enable"));
        expect(onenable).toHaveBeenCalledWith("com.example.demo");
        plugin.enabled = true;
        cleanup();
        render(PluginItemCard, { props: { plugin, onenable, ondisable, onremove } });
        await fireEvent.click(screen.getByText("Disable"));
        expect(ondisable).toHaveBeenCalledWith("com.example.demo");
        await fireEvent.click(screen.getByText("Remove"));
        expect(onremove).toHaveBeenCalledWith(plugin);
    });
});

describe("PluginsSettingsSection.svelte", () => {
    let apiMock;

    beforeEach(() => {
        registerTranslator(null);
        registerFallbackMessages({
            plugins: {
                permissions: { none: "None" },
                settings: {
                    title: "Plugins",
                    description: "Manage plugins",
                    drag_drop: "Drop zip",
                    install_zip: "zip",
                    choose_file: "Choose",
                    installing: "Installing",
                    empty_state: "No plugins",
                    badge_enabled: "Enabled",
                    badge_disabled: "Disabled",
                    enable: "Enable",
                    disable: "Disable",
                    remove: "Remove",
                    enabled: "Plugin enabled",
                    disabled: "Plugin disabled",
                    removed: "Plugin removed",
                    confirm_remove: 'Remove plugin "{name}"? This deletes its files and stored data.',
                    permissions: "Permissions",
                    network_endpoints: "Endpoints",
                    auto_disabled: "Auto-disabled: {reason}",
                },
                sideband: {
                    title: "Sideband",
                    description: "Sideband plugins",
                    master_enable: "Master",
                    command_enable: "Commands",
                    path: "Path",
                    browse: "Browse",
                    browse_title: "Browse",
                    save: "Save",
                    reload: "Reload",
                    loaded: "Loaded",
                    config_saved: "Saved",
                    save_failed: "Save failed",
                },
            },
        });
        apiMock = {
            get: vi.fn(async (url) => {
                if (url === "/api/v1/plugins") {
                    return {
                        data: {
                            plugins: [
                                {
                                    id: "com.example.demo",
                                    name: "Demo",
                                    description: "d",
                                    version: "1.0.0",
                                    enabled: false,
                                    granted_permissions: [],
                                },
                            ],
                        },
                    };
                }
                if (url === "/api/v1/sideband-plugins") {
                    return {
                        data: {
                            config: {
                                service_plugins_enabled: false,
                                command_plugins_enabled: false,
                                command_plugins_path: "",
                            },
                            plugins: [],
                        },
                    };
                }
                return { data: {} };
            }),
            post: vi.fn().mockResolvedValue({ data: {} }),
            patch: vi.fn().mockResolvedValue({ data: {} }),
            delete: vi.fn().mockResolvedValue({ data: {} }),
        };
        window.api = apiMock;
        DialogUtils.confirm.mockResolvedValue(true);
        loadEnabledPlugins.mockClear();
        unloadPlugin.mockClear();
    });

    afterEach(() => {
        cleanup();
        delete window.api;
        vi.clearAllMocks();
    });

    it("lists plugins and enable posts then hot-loads host", async () => {
        render(PluginsSettingsSection);
        await waitFor(() => expect(screen.getByText("Demo")).toBeTruthy());
        await fireEvent.click(screen.getByText("Enable"));
        await waitFor(() => {
            expect(apiMock.post).toHaveBeenCalledWith("/api/v1/plugins/com.example.demo/enable");
            expect(loadEnabledPlugins).toHaveBeenCalled();
        });
    });

    it("sideband save posts config (not patch)", async () => {
        render(PluginsSettingsSection);
        await waitFor(() => expect(screen.getByText("Sideband")).toBeTruthy());
        await fireEvent.click(screen.getByText("Save"));
        await waitFor(() => {
            expect(apiMock.post).toHaveBeenCalledWith("/api/v1/sideband-plugins/config", {
                service_plugins_enabled: false,
                command_plugins_enabled: false,
                command_plugins_path: "",
            });
            expect(apiMock.patch).not.toHaveBeenCalledWith("/api/v1/sideband-plugins/config", expect.anything());
        });
    });

    it("remove confirm uses named confirm_remove key", async () => {
        render(PluginsSettingsSection);
        await waitFor(() => expect(screen.getByText("Demo")).toBeTruthy());
        await fireEvent.click(screen.getByText("Remove"));
        await waitFor(() => {
            expect(DialogUtils.confirm).toHaveBeenCalled();
            const prompt = DialogUtils.confirm.mock.calls[0][0];
            expect(prompt).toContain("Demo");
            expect(prompt).toMatch(/deletes its files/i);
        });
        await waitFor(() => {
            expect(apiMock.delete).toHaveBeenCalledWith("/api/v1/plugins/com.example.demo");
            expect(unloadPlugin).toHaveBeenCalledWith("com.example.demo");
        });
    });
});

describe("PluginPage.svelte", () => {
    beforeEach(() => {
        requestUiRefresh.mockClear();
        getLastDescriptor.mockClear();
    });

    afterEach(() => {
        cleanup();
    });

    it("renders descriptor text and requests UI refresh", async () => {
        render(PluginPage, { props: { pluginId: "com.example.demo" } });
        await waitFor(() => {
            expect(screen.getByText("Hello plugin")).toBeTruthy();
            expect(requestUiRefresh).toHaveBeenCalledWith("com.example.demo");
        });
    });
});
