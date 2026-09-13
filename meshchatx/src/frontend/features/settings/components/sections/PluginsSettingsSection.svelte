<!-- SPDX-License-Identifier: 0BSD -->

<script lang="ts">
    import { onMount, onDestroy } from "svelte";
    import SettingsSectionBlock from "../SettingsSectionBlock.svelte";
    import PluginInstallDialog from "../PluginInstallDialog.svelte";
    import SidebandPluginsCard from "../SidebandPluginsCard.svelte";
    import PluginItemCard from "../PluginItemCard.svelte";
    import ToastUtils from "../../../../js/ToastUtils.js";
    import DialogUtils from "../../../../js/DialogUtils.js";
    import ElectronUtils from "../../../../js/ElectronUtils.js";
    import AndroidBridge from "../../../../js/rnode/AndroidBridge.js";
    import { pluginHost } from "../../../../js/plugins/PluginHost.js";
    import { onWsEvent, offWsEvent } from "../../../../js/registries/wsEventRegistry.js";
    import { t } from "../../../../js/i18n.js";
    import { getCurrentUiLocale } from "../../../../js/localeLoader.js";

    interface Props {
        visible?: boolean;
    }

    let { visible = true }: Props = $props();

    let plugins = $state<any[]>([]);
    let dragActive = $state(false);
    let installing = $state(false);
    let previewing = $state(false);
    let busyPluginId = $state<string | null>(null);
    let dialogOpen = $state(false);
    let installPreview = $state<any>(null);
    let pendingArchive = $state<File | null>(null);
    let sidebandBusy = $state(false);
    let sidebandPlugins = $state<any[]>([]);
    let sidebandConfig = $state({
        service_plugins_enabled: false,
        command_plugins_enabled: false,
        command_plugins_path: "",
    });
    let fileInputEl: HTMLInputElement | undefined = $state();

    let onPluginDisabledHandler: ((payload: any) => void) | null = null;

    onMount(() => {
        void refresh();
        void refreshSideband();
        onPluginDisabledHandler = (payload: any) => {
            if (payload?.event === "plugin.disabled") {
                ToastUtils.warning(t("plugins.settings.kill_switch", { reason: payload?.payload?.reason || "" }));
                pluginHost.unloadPlugin(payload?.plugin_id);
                void refresh();
            }
        };
        onWsEvent("plugin.event", onPluginDisabledHandler);
    });

    onDestroy(() => {
        if (onPluginDisabledHandler) {
            offWsEvent("plugin.event", onPluginDisabledHandler);
        }
    });

    async function refresh() {
        if (!window.api?.get) return;
        try {
            const response = await window.api.get("/api/v1/plugins");
            plugins = response.data?.plugins || [];
        } catch (e) {
            console.error(e);
        }
    }

    async function refreshSideband() {
        if (!window.api?.get) return;
        try {
            const response = await window.api.get("/api/v1/sideband-plugins");
            const config = response.data?.config || {};
            sidebandConfig = {
                service_plugins_enabled: Boolean(config.service_plugins_enabled),
                command_plugins_enabled: Boolean(config.command_plugins_enabled),
                command_plugins_path: config.command_plugins_path || "",
            };
            sidebandPlugins = response.data?.plugins || [];
        } catch (e) {
            console.error(e);
        }
    }

    async function onSidebandMasterToggle() {
        if (sidebandConfig.service_plugins_enabled) {
            const ok = await DialogUtils.confirm(t("plugins.sideband.danger_confirm"));
            if (!ok) {
                sidebandConfig.service_plugins_enabled = false;
            }
        }
    }

    async function pickSidebandPluginsDirectory() {
        if (!sidebandConfig.service_plugins_enabled) return;
        const picked = await ElectronUtils.pickDirectory();
        if (picked) {
            sidebandConfig.command_plugins_path = picked;
            ToastUtils.success(t("plugins.sideband.path_picked"));
            return;
        }
        if (ElectronUtils.isElectron()) return;

        const android = new AndroidBridge();
        let initial = sidebandConfig.command_plugins_path || "";
        if (android.isAvailable()) {
            const suggested = android.getSidebandPluginsDefaultPath();
            if (suggested && !initial) {
                initial = suggested;
            }
        }
        const entered = await DialogUtils.prompt(t("plugins.sideband.path_prompt"), initial);
        if (entered != null) {
            sidebandConfig.command_plugins_path = entered.trim();
        }
    }

    async function saveSidebandConfig() {
        sidebandBusy = true;
        try {
            await window.api.post("/api/v1/sideband-plugins/config", {
                service_plugins_enabled: sidebandConfig.service_plugins_enabled,
                command_plugins_enabled: sidebandConfig.command_plugins_enabled,
                command_plugins_path: sidebandConfig.command_plugins_path,
            });
            ToastUtils.success(t("plugins.sideband.config_saved"));
            await refreshSideband();
        } catch (e) {
            console.error(e);
            ToastUtils.error(t("plugins.sideband.save_failed"));
        } finally {
            sidebandBusy = false;
        }
    }

    async function reloadSideband() {
        sidebandBusy = true;
        try {
            await window.api.post("/api/v1/sideband-plugins/reload");
            ToastUtils.success(t("plugins.sideband.reloaded"));
            await refreshSideband();
        } catch (e) {
            console.error(e);
            ToastUtils.error(t("plugins.sideband.reload_failed"));
        } finally {
            sidebandBusy = false;
        }
    }

    async function enablePlugin(pluginId: string) {
        busyPluginId = pluginId;
        try {
            await window.api.post(`/api/v1/plugins/${encodeURIComponent(pluginId)}/enable`);
            await pluginHost.loadEnabledPlugins(window.api, getCurrentUiLocale());
            await refresh();
            ToastUtils.success(t("plugins.settings.enabled"));
        } catch (error: any) {
            ToastUtils.error(t("plugins.settings.enable_failed", { reason: error?.message || String(error) }));
        } finally {
            busyPluginId = null;
        }
    }

    async function disablePlugin(pluginId: string) {
        busyPluginId = pluginId;
        try {
            await window.api.post(`/api/v1/plugins/${encodeURIComponent(pluginId)}/disable`);
            pluginHost.unloadPlugin(pluginId);
            await refresh();
            ToastUtils.info(t("plugins.settings.disabled"));
        } catch (error: any) {
            ToastUtils.error(t("plugins.settings.disable_failed", { reason: error?.message || String(error) }));
        } finally {
            busyPluginId = null;
        }
    }

    async function confirmRemove(plugin: any) {
        const ok = await DialogUtils.confirm(t("plugins.settings.confirm_remove", { name: plugin.name || plugin.id }));
        if (ok) {
            await removePlugin(plugin.id);
        }
    }

    async function removePlugin(pluginId: string) {
        busyPluginId = pluginId;
        try {
            await window.api.delete(`/api/v1/plugins/${encodeURIComponent(pluginId)}`);
            pluginHost.unloadPlugin(pluginId);
            await refresh();
            ToastUtils.info(t("plugins.settings.removed"));
        } finally {
            busyPluginId = null;
        }
    }

    async function beginInstallPreview(file?: File | null) {
        if (!file) return;
        previewing = true;
        pendingArchive = file;
        try {
            const formData = new FormData();
            formData.append("archive", file);
            const response = await window.api.post("/api/v1/plugins/preview", formData);
            installPreview = response.data;
            dialogOpen = true;
        } catch (error: any) {
            pendingArchive = null;
            installPreview = null;
            ToastUtils.error(t("plugins.settings.install_failed", { reason: error?.message || String(error) }));
        } finally {
            previewing = false;
            dragActive = false;
            if (fileInputEl) fileInputEl.value = "";
        }
    }

    function cancelInstallPreview() {
        dialogOpen = false;
        installPreview = null;
        pendingArchive = null;
    }

    async function confirmInstallPreview(data: {
        grantedPermissions: string[];
        trustPublisher: boolean;
        signer: string;
        signerName: string;
    }) {
        if (!pendingArchive) {
            cancelInstallPreview();
            return;
        }
        installing = true;
        try {
            if (data.trustPublisher && data.signer) {
                await window.api.post("/api/v1/plugins/trusted-publishers", {
                    identity: data.signer,
                    name: data.signerName || data.signer,
                });
            }
            const formData = new FormData();
            formData.append("archive", pendingArchive);
            formData.append("granted_permissions", JSON.stringify(data.grantedPermissions || []));
            await window.api.post("/api/v1/plugins/install", formData);
            await refresh();
            ToastUtils.success(t("plugins.settings.installed"));
            cancelInstallPreview();
        } catch (error: any) {
            ToastUtils.error(t("plugins.settings.install_failed", { reason: error?.message || String(error) }));
        } finally {
            installing = false;
        }
    }
</script>

<SettingsSectionBlock
    show={visible}
    title={t("plugins.settings.title")}
    description={t("plugins.settings.description")}
>
    <div class="space-y-4">
        <div
            class="rounded-xl border-2 border-dashed border-sem-border bg-sem-surface-muted/40 p-6 text-center transition-colors {dragActive
                ? 'border-blue-500 bg-blue-50/60 dark:bg-blue-950/20'
                : ''}"
            role="region"
            aria-label={t("plugins.settings.drag_drop")}
            ondragenter={(e) => {
                e.preventDefault();
                dragActive = true;
            }}
            ondragover={(e) => {
                e.preventDefault();
                dragActive = true;
            }}
            ondragleave={(e) => {
                e.preventDefault();
                dragActive = false;
            }}
            ondrop={(e) => {
                e.preventDefault();
                dragActive = false;
                const file = e.dataTransfer?.files?.[0];
                void beginInstallPreview(file);
            }}
        >
            <p class="text-sm font-medium text-sem-fg">
                {t("plugins.settings.drag_drop")}
            </p>
            <p class="mt-1 text-xs text-sem-fg-muted">
                {t("plugins.settings.install_zip")}
            </p>
            <label class="mt-4 inline-flex">
                <input
                    bind:this={fileInputEl}
                    type="file"
                    accept=".zip,.wasm,application/zip,application/wasm"
                    class="sr-only"
                    disabled={installing || previewing}
                    onchange={(e) => {
                        const file = (e.target as HTMLInputElement).files?.[0];
                        void beginInstallPreview(file);
                    }}
                />
                <span
                    class="px-4 py-2 rounded-md bg-blue-600 text-white text-sm cursor-pointer hover:bg-blue-700 {installing ||
                    previewing
                        ? 'opacity-60 pointer-events-none'
                        : ''}"
                >
                    {installing || previewing ? t("plugins.settings.installing") : t("plugins.settings.choose_file")}
                </span>
            </label>
        </div>

        {#if !plugins.length}
            <div class="rounded-lg border border-sem-border px-4 py-8 text-center text-sm text-sem-fg-muted">
                {t("plugins.settings.empty_state")}
            </div>
        {/if}

        {#each plugins as plugin (plugin.id)}
            <PluginItemCard
                {plugin}
                {busyPluginId}
                onenable={enablePlugin}
                ondisable={disablePlugin}
                onremove={confirmRemove}
            />
        {/each}

        <SidebandPluginsCard
            bind:sidebandConfig
            {sidebandPlugins}
            {sidebandBusy}
            onmastertoggle={onSidebandMasterToggle}
            onpickdirectory={pickSidebandPluginsDirectory}
            onsave={saveSidebandConfig}
            onreload={reloadSideband}
        />
    </div>

    <PluginInstallDialog
        open={dialogOpen}
        preview={installPreview}
        confirming={installing}
        oncancel={cancelInstallPreview}
        onconfirm={confirmInstallPreview}
    />
</SettingsSectionBlock>
