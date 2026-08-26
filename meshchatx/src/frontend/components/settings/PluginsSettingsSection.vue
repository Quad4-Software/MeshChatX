<!-- SPDX-License-Identifier: 0BSD -->

<template>
    <SettingsSectionBlock
        v-show="visible"
        :title="$t('plugins.settings.title')"
        :description="$t('plugins.settings.description')"
    >
        <div class="space-y-4">
            <div
                class="rounded-xl border-2 border-dashed border-gray-300 dark:border-zinc-700 bg-sem-surface-muted/40 p-6 text-center transition-colors"
                :class="dragActive ? 'border-blue-500 bg-blue-50/60 dark:bg-blue-950/20' : ''"
                @dragenter.prevent="dragActive = true"
                @dragover.prevent="dragActive = true"
                @dragleave.prevent="dragActive = false"
                @drop.prevent="onDropArchive"
            >
                <p class="text-sm font-medium text-gray-800 dark:text-gray-200">
                    {{ $t("plugins.settings.drag_drop") }}
                </p>
                <p class="mt-1 text-xs text-sem-fg-muted">
                    {{ $t("plugins.settings.install_zip") }}
                </p>
                <label class="mt-4 inline-flex">
                    <input
                        ref="fileInput"
                        type="file"
                        accept=".zip,.wasm,application/zip,application/wasm"
                        class="sr-only"
                        :disabled="installing || previewing"
                        @change="onInstallFile"
                    />
                    <span
                        class="px-4 py-2 rounded-md bg-blue-600 text-white text-sm cursor-pointer hover:bg-blue-700"
                        :class="installing || previewing ? 'opacity-60 pointer-events-none' : ''"
                    >
                        {{
                            installing || previewing
                                ? $t("plugins.settings.installing")
                                : $t("plugins.settings.choose_file")
                        }}
                    </span>
                </label>
            </div>

            <div
                v-if="!plugins.length"
                class="rounded-lg border border-sem-border px-4 py-8 text-center text-sm text-gray-600 dark:text-gray-400"
            >
                {{ $t("plugins.settings.empty_state") }}
            </div>

            <div v-for="plugin in plugins" :key="plugin.id" class="rounded-lg border border-sem-border p-4 space-y-3">
                <div class="flex flex-wrap items-start justify-between gap-3">
                    <div class="min-w-0 space-y-2">
                        <div class="flex flex-wrap items-center gap-2">
                            <h3 class="text-base font-semibold text-gray-900 dark:text-gray-100">{{ plugin.name }}</h3>
                            <span
                                class="px-2 py-0.5 rounded-full text-[11px] font-semibold uppercase tracking-wide"
                                :class="
                                    plugin.enabled
                                        ? 'bg-green-100 text-green-800 dark:bg-green-900/30 dark:text-green-200'
                                        : 'bg-zinc-200 text-zinc-700 dark:bg-zinc-800 text-sem-fg-muted'
                                "
                            >
                                {{
                                    plugin.enabled
                                        ? $t("plugins.settings.badge_enabled")
                                        : $t("plugins.settings.badge_disabled")
                                }}
                            </span>
                            <span
                                v-if="plugin.has_frontend"
                                class="px-2 py-0.5 rounded-full text-[11px] font-semibold uppercase tracking-wide bg-sky-100 text-sky-800 dark:bg-sky-900/30 dark:text-sky-200"
                            >
                                {{ $t("plugins.settings.badge_frontend") }}
                            </span>
                            <span
                                v-if="plugin.has_backend && plugin.backend_type === 'python'"
                                class="px-2 py-0.5 rounded-full text-[11px] font-semibold uppercase tracking-wide bg-emerald-100 text-emerald-800 dark:bg-emerald-900/30 dark:text-emerald-200"
                            >
                                {{ $t("plugins.settings.badge_python") }}
                            </span>
                            <span
                                v-else-if="plugin.has_backend"
                                class="px-2 py-0.5 rounded-full text-[11px] font-semibold uppercase tracking-wide bg-violet-100 text-violet-800 dark:bg-violet-900/30 dark:text-violet-200"
                            >
                                {{ $t("plugins.settings.badge_wasm") }}
                            </span>
                            <span
                                v-if="plugin.requires_network_fetch"
                                class="px-2 py-0.5 rounded-full text-[11px] font-semibold uppercase tracking-wide bg-amber-100 text-amber-800 dark:bg-amber-900/30 dark:text-amber-200"
                            >
                                {{ $t("plugins.settings.badge_network") }}
                            </span>
                            <span
                                v-if="plugin.signature?.trusted"
                                class="px-2 py-0.5 rounded-full text-[11px] font-semibold uppercase tracking-wide bg-green-100 text-green-800 dark:bg-green-900/30 dark:text-green-200"
                            >
                                {{ $t("plugins.settings.badge_trusted") }}
                            </span>
                            <span
                                v-else-if="plugin.signature?.valid"
                                class="px-2 py-0.5 rounded-full text-[11px] font-semibold uppercase tracking-wide bg-sky-100 text-sky-800 dark:bg-sky-900/30 dark:text-sky-200"
                            >
                                {{ $t("plugins.settings.badge_signed") }}
                            </span>
                            <span
                                v-else-if="plugin.signature?.present && !plugin.signature?.valid"
                                class="px-2 py-0.5 rounded-full text-[11px] font-semibold uppercase tracking-wide bg-red-100 text-red-800 dark:bg-red-900/30 dark:text-red-200"
                            >
                                {{ $t("plugins.settings.badge_invalid_signature") }}
                            </span>
                            <span
                                v-if="plugin.tampered"
                                class="px-2 py-0.5 rounded-full text-[11px] font-semibold uppercase tracking-wide bg-red-100 text-red-800 dark:bg-red-900/30 dark:text-red-200"
                            >
                                {{ $t("plugins.settings.badge_tampered") }}
                            </span>
                        </div>
                        <p class="text-sm text-gray-600 dark:text-gray-400">{{ plugin.description }}</p>
                        <p class="text-xs text-gray-500 dark:text-gray-500">{{ plugin.id }} · v{{ plugin.version }}</p>
                    </div>
                    <div class="flex flex-wrap gap-2">
                        <button
                            v-if="!plugin.enabled"
                            type="button"
                            class="px-3 py-1.5 rounded-md bg-blue-600 text-white text-sm"
                            :disabled="busyPluginId === plugin.id"
                            @click="enablePlugin(plugin.id)"
                        >
                            {{ $t("plugins.settings.enable") }}
                        </button>
                        <button
                            v-else
                            type="button"
                            class="px-3 py-1.5 rounded-md bg-zinc-600 text-white text-sm"
                            :disabled="busyPluginId === plugin.id"
                            @click="disablePlugin(plugin.id)"
                        >
                            {{ $t("plugins.settings.disable") }}
                        </button>
                        <button
                            type="button"
                            class="px-3 py-1.5 rounded-md border border-red-300 text-red-600 text-sm"
                            :disabled="busyPluginId === plugin.id"
                            @click="confirmRemove(plugin)"
                        >
                            {{ $t("plugins.settings.remove") }}
                        </button>
                    </div>
                </div>
                <div v-if="permissionLines(plugin).length" class="text-sm text-gray-700 dark:text-gray-300">
                    <p class="font-medium">{{ $t("plugins.settings.permissions") }}</p>
                    <ul class="list-disc pl-5">
                        <li v-for="line in permissionLines(plugin)" :key="line">{{ line }}</li>
                    </ul>
                </div>
                <div
                    v-if="(plugin.network_endpoints || []).length"
                    class="text-sm text-gray-700 dark:text-gray-300 space-y-1"
                >
                    <p class="font-medium">{{ $t("plugins.settings.network_endpoints") }}</p>
                    <ul class="list-disc pl-5">
                        <li
                            v-for="endpoint in plugin.network_endpoints"
                            :key="endpoint"
                            class="font-mono text-xs break-all"
                        >
                            {{ endpoint }}
                        </li>
                    </ul>
                </div>
                <p v-if="plugin.auto_disabled_reason" class="text-sm text-amber-700 dark:text-amber-300">
                    {{ $t("plugins.settings.auto_disabled", { reason: plugin.auto_disabled_reason }) }}
                </p>
            </div>

            <section class="rounded-lg border border-amber-300 dark:border-amber-800 p-4 space-y-3">
                <div>
                    <h3 class="text-sm font-semibold text-gray-900 dark:text-gray-100">
                        {{ $t("plugins.sideband.title") }}
                    </h3>
                    <p class="text-xs text-gray-600 dark:text-gray-400 mt-1">
                        {{ $t("plugins.sideband.description") }}
                    </p>
                </div>
                <label class="flex items-start gap-2 text-sm text-gray-800 dark:text-gray-200">
                    <input
                        v-model="sidebandConfig.service_plugins_enabled"
                        type="checkbox"
                        class="mt-1 rounded border-gray-300"
                        @change="onSidebandMasterToggle"
                    />
                    <span>{{ $t("plugins.sideband.master_enable") }}</span>
                </label>
                <label class="flex items-start gap-2 text-sm text-gray-800 dark:text-gray-200">
                    <input
                        v-model="sidebandConfig.command_plugins_enabled"
                        type="checkbox"
                        class="mt-1 rounded border-gray-300"
                        :disabled="!sidebandConfig.service_plugins_enabled"
                    />
                    <span>{{ $t("plugins.sideband.command_enable") }}</span>
                </label>
                <label class="block text-sm text-gray-800 dark:text-gray-200 space-y-1">
                    <span>{{ $t("plugins.sideband.path") }}</span>
                    <div class="flex flex-col sm:flex-row gap-2">
                        <input
                            v-model="sidebandConfig.command_plugins_path"
                            type="text"
                            class="w-full rounded-md border border-gray-300 dark:border-zinc-700 bg-sem-surface px-3 py-1.5 text-sm min-w-0"
                            :disabled="!sidebandConfig.service_plugins_enabled"
                        />
                        <button
                            type="button"
                            class="px-3 py-1.5 rounded-md border border-gray-300 dark:border-zinc-600 text-sm shrink-0 min-h-[44px]"
                            :disabled="!sidebandConfig.service_plugins_enabled || sidebandBusy"
                            :title="$t('plugins.sideband.browse_title')"
                            @click="pickSidebandPluginsDirectory"
                        >
                            {{ $t("plugins.sideband.browse") }}
                        </button>
                    </div>
                </label>
                <div class="flex flex-wrap gap-2">
                    <button
                        type="button"
                        class="px-3 py-1.5 rounded-md bg-blue-600 text-white text-sm"
                        :disabled="sidebandBusy"
                        @click="saveSidebandConfig"
                    >
                        {{ $t("plugins.sideband.save") }}
                    </button>
                    <button
                        type="button"
                        class="px-3 py-1.5 rounded-md border border-gray-300 dark:border-zinc-600 text-sm"
                        :disabled="sidebandBusy"
                        @click="reloadSideband"
                    >
                        {{ $t("plugins.sideband.reload") }}
                    </button>
                </div>
                <div v-if="sidebandPlugins.length" class="space-y-2">
                    <p class="text-sm font-medium text-gray-900 dark:text-gray-100">
                        {{ $t("plugins.sideband.loaded") }}
                    </p>
                    <ul class="space-y-2">
                        <li
                            v-for="item in sidebandPlugins"
                            :key="item.path"
                            class="rounded-md border border-sem-border px-3 py-2 text-xs space-y-1"
                        >
                            <p class="font-medium text-gray-800 dark:text-gray-200">
                                {{ item.name }}
                                <span class="uppercase text-gray-500">({{ item.type }})</span>
                            </p>
                            <p v-if="item.error" class="text-red-600 dark:text-red-400">{{ item.error }}</p>
                            <ul
                                v-if="(item.security_findings || []).length"
                                class="list-disc pl-4 text-gray-600 dark:text-gray-400"
                            >
                                <li v-for="finding in item.security_findings" :key="finding.id">
                                    {{ finding.message }}
                                </li>
                            </ul>
                        </li>
                    </ul>
                </div>
            </section>
        </div>

        <PluginInstallDialog
            :open="dialogOpen"
            :preview="installPreview"
            :confirming="installing"
            @cancel="cancelInstallPreview"
            @confirm="confirmInstallPreview"
        />
    </SettingsSectionBlock>
</template>

<script>
import SettingsSectionBlock from "./SettingsSectionBlock.vue";
import PluginInstallDialog from "./PluginInstallDialog.vue";
import ToastUtils from "../../js/ToastUtils";
import DialogUtils from "../../js/DialogUtils";
import ElectronUtils from "../../js/ElectronUtils";
import AndroidBridge from "../../js/rnode/AndroidBridge";
import { permissionLabel } from "../../js/plugins/pluginPermissions.js";
import { pluginHost } from "../../js/plugins/PluginHost.js";
import { onWsEvent, offWsEvent } from "../../js/registries/wsEventRegistry.js";

export default {
    name: "PluginsSettingsSection",
    components: { SettingsSectionBlock, PluginInstallDialog },
    props: {
        visible: {
            type: Boolean,
            default: true,
        },
    },
    data() {
        return {
            plugins: [],
            dragActive: false,
            installing: false,
            previewing: false,
            busyPluginId: null,
            dialogOpen: false,
            installPreview: null,
            pendingArchive: null,
            sidebandBusy: false,
            sidebandPlugins: [],
            sidebandConfig: {
                service_plugins_enabled: false,
                command_plugins_enabled: false,
                command_plugins_path: "",
            },
        };
    },
    mounted() {
        void this.refresh();
        void this.refreshSideband();
        this.onPluginDisabled = (payload) => {
            if (payload?.event === "plugin.disabled") {
                ToastUtils.warning(this.$t("plugins.settings.kill_switch", { reason: payload?.payload?.reason || "" }));
                pluginHost.unloadPlugin(payload?.plugin_id);
                void this.refresh();
            }
        };
        onWsEvent("plugin.event", this.onPluginDisabled);
    },
    beforeUnmount() {
        offWsEvent("plugin.event", this.onPluginDisabled);
    },
    methods: {
        currentLocale() {
            return this.$i18n?.locale?.value || this.$i18n?.locale || "en";
        },
        permissionLines(plugin) {
            const granted = plugin.granted_permissions || plugin.declared_permissions || [];
            if (!granted.length) {
                return [this.$t("plugins.permissions.none")];
            }
            return granted.map((id) => permissionLabel(id, (key) => this.$t(key)));
        },
        async refresh() {
            const response = await window.api.get("/api/v1/plugins");
            this.plugins = response.data?.plugins || [];
        },
        async refreshSideband() {
            const response = await window.api.get("/api/v1/sideband-plugins");
            const config = response.data?.config || {};
            this.sidebandConfig = {
                service_plugins_enabled: Boolean(config.service_plugins_enabled),
                command_plugins_enabled: Boolean(config.command_plugins_enabled),
                command_plugins_path: config.command_plugins_path || "",
            };
            this.sidebandPlugins = response.data?.plugins || [];
        },
        async onSidebandMasterToggle() {
            if (this.sidebandConfig.service_plugins_enabled) {
                const ok = await DialogUtils.confirm(this.$t("plugins.sideband.danger_confirm"));
                if (!ok) {
                    this.sidebandConfig.service_plugins_enabled = false;
                }
            }
        },
        async pickSidebandPluginsDirectory() {
            if (!this.sidebandConfig.service_plugins_enabled) {
                return;
            }
            const picked = await ElectronUtils.pickDirectory();
            if (picked) {
                this.sidebandConfig.command_plugins_path = picked;
                ToastUtils.success(this.$t("plugins.sideband.path_picked"));
                return;
            }
            if (ElectronUtils.isElectron()) {
                return;
            }
            const android = new AndroidBridge();
            let initial = this.sidebandConfig.command_plugins_path || "";
            if (android.isAvailable()) {
                const suggested = android.getSidebandPluginsDefaultPath();
                if (suggested && !initial) {
                    initial = suggested;
                }
            }
            const entered = await DialogUtils.prompt(
                initial
                    ? `${this.$t("plugins.sideband.path_prompt")}\n${initial}`
                    : this.$t("plugins.sideband.path_prompt")
            );
            if (entered != null && String(entered).trim()) {
                this.sidebandConfig.command_plugins_path = String(entered).trim();
                ToastUtils.success(this.$t("plugins.sideband.path_picked"));
            }
        },
        async saveSidebandConfig() {
            this.sidebandBusy = true;
            try {
                const response = await window.api.post("/api/v1/sideband-plugins/config", {
                    service_plugins_enabled: this.sidebandConfig.service_plugins_enabled,
                    command_plugins_enabled: this.sidebandConfig.command_plugins_enabled,
                    command_plugins_path: this.sidebandConfig.command_plugins_path || null,
                });
                this.sidebandPlugins = response.data?.plugins || [];
                ToastUtils.success(this.$t("plugins.sideband.saved"));
            } catch (error) {
                ToastUtils.error(
                    this.$t("plugins.settings.install_failed", { reason: error?.message || String(error) })
                );
            } finally {
                this.sidebandBusy = false;
            }
        },
        async reloadSideband() {
            this.sidebandBusy = true;
            try {
                const response = await window.api.post("/api/v1/sideband-plugins/reload");
                this.sidebandPlugins = response.data?.plugins || [];
                ToastUtils.success(this.$t("plugins.sideband.reloaded"));
            } catch (error) {
                ToastUtils.error(
                    this.$t("plugins.settings.install_failed", { reason: error?.message || String(error) })
                );
            } finally {
                this.sidebandBusy = false;
            }
        },
        async enablePlugin(pluginId) {
            this.busyPluginId = pluginId;
            try {
                await window.api.post(`/api/v1/plugins/${encodeURIComponent(pluginId)}/enable`);
                await pluginHost.loadEnabledPlugins(window.api, this.currentLocale());
                await this.refresh();
                ToastUtils.success(this.$t("plugins.settings.enabled"));
            } catch (error) {
                ToastUtils.error(
                    this.$t("plugins.settings.install_failed", { reason: error?.message || String(error) })
                );
                await this.refresh();
            } finally {
                this.busyPluginId = null;
            }
        },
        async disablePlugin(pluginId) {
            this.busyPluginId = pluginId;
            try {
                await window.api.post(`/api/v1/plugins/${encodeURIComponent(pluginId)}/disable`);
                pluginHost.unloadPlugin(pluginId);
                await this.refresh();
                ToastUtils.info(this.$t("plugins.settings.disabled"));
            } finally {
                this.busyPluginId = null;
            }
        },
        async confirmRemove(plugin) {
            const prompt = this.$t("plugins.settings.confirm_remove", { name: plugin.name || plugin.id });
            if (!(await DialogUtils.confirm(prompt))) {
                return;
            }
            void this.removePlugin(plugin.id);
        },
        async removePlugin(pluginId) {
            this.busyPluginId = pluginId;
            try {
                await window.api.delete(`/api/v1/plugins/${encodeURIComponent(pluginId)}`);
                pluginHost.unloadPlugin(pluginId);
                await this.refresh();
                ToastUtils.info(this.$t("plugins.settings.removed"));
            } finally {
                this.busyPluginId = null;
            }
        },
        async beginInstallPreview(file) {
            if (!file) {
                return;
            }
            this.previewing = true;
            this.pendingArchive = file;
            try {
                const formData = new FormData();
                formData.append("archive", file);
                const response = await window.api.post("/api/v1/plugins/preview", formData);
                this.installPreview = response.data;
                this.dialogOpen = true;
            } catch (error) {
                this.pendingArchive = null;
                this.installPreview = null;
                ToastUtils.error(
                    this.$t("plugins.settings.install_failed", { reason: error?.message || String(error) })
                );
            } finally {
                this.previewing = false;
                this.dragActive = false;
                if (this.$refs.fileInput) {
                    this.$refs.fileInput.value = "";
                }
            }
        },
        cancelInstallPreview() {
            this.dialogOpen = false;
            this.installPreview = null;
            this.pendingArchive = null;
        },
        async confirmInstallPreview({ grantedPermissions, trustPublisher, signer, signerName }) {
            if (!this.pendingArchive) {
                this.cancelInstallPreview();
                return;
            }
            this.installing = true;
            try {
                if (trustPublisher && signer) {
                    await window.api.post("/api/v1/plugins/trusted-publishers", {
                        identity: signer,
                        name: signerName || signer,
                    });
                }
                const formData = new FormData();
                formData.append("archive", this.pendingArchive);
                formData.append("granted_permissions", JSON.stringify(grantedPermissions || []));
                await window.api.post("/api/v1/plugins/install", formData);
                await this.refresh();
                ToastUtils.success(this.$t("plugins.settings.installed"));
                this.cancelInstallPreview();
            } catch (error) {
                ToastUtils.error(
                    this.$t("plugins.settings.install_failed", { reason: error?.message || String(error) })
                );
            } finally {
                this.installing = false;
            }
        },
        async onInstallFile(event) {
            const file = event.target.files?.[0];
            await this.beginInstallPreview(file);
        },
        async onDropArchive(event) {
            this.dragActive = false;
            const file = event.dataTransfer?.files?.[0];
            await this.beginInstallPreview(file);
        },
    },
};
</script>
