<!-- SPDX-License-Identifier: 0BSD -->

<template>
    <SettingsSectionBlock
        v-show="visible"
        :title="$t('plugins.settings.title')"
        :description="$t('plugins.settings.description')"
    >
        <div class="space-y-4">
            <div
                class="rounded-xl border-2 border-dashed border-gray-300 dark:border-zinc-700 bg-gray-50 dark:bg-zinc-900/40 p-6 text-center transition-colors"
                :class="dragActive ? 'border-blue-500 bg-blue-50/60 dark:bg-blue-950/20' : ''"
                @dragenter.prevent="dragActive = true"
                @dragover.prevent="dragActive = true"
                @dragleave.prevent="dragActive = false"
                @drop.prevent="onDropArchive"
            >
                <p class="text-sm font-medium text-gray-800 dark:text-gray-200">
                    {{ $t("plugins.settings.drag_drop") }}
                </p>
                <p class="mt-1 text-xs text-gray-500 dark:text-gray-400">
                    {{ $t("plugins.settings.install_zip") }}
                </p>
                <label class="mt-4 inline-flex">
                    <input
                        ref="fileInput"
                        type="file"
                        accept=".zip,application/zip"
                        class="sr-only"
                        :disabled="installing"
                        @change="onInstallFile"
                    />
                    <span
                        class="px-4 py-2 rounded-md bg-blue-600 text-white text-sm cursor-pointer hover:bg-blue-700"
                        :class="installing ? 'opacity-60 pointer-events-none' : ''"
                    >
                        {{ installing ? $t("plugins.settings.installing") : $t("plugins.settings.choose_file") }}
                    </span>
                </label>
            </div>

            <div
                v-if="!plugins.length"
                class="rounded-lg border border-gray-200 dark:border-zinc-800 px-4 py-8 text-center text-sm text-gray-600 dark:text-gray-400"
            >
                {{ $t("plugins.settings.empty_state") }}
            </div>

            <div
                v-for="plugin in plugins"
                :key="plugin.id"
                class="rounded-lg border border-gray-200 dark:border-zinc-800 p-4 space-y-3"
            >
                <div class="flex flex-wrap items-start justify-between gap-3">
                    <div class="min-w-0 space-y-2">
                        <div class="flex flex-wrap items-center gap-2">
                            <h3 class="text-base font-semibold text-gray-900 dark:text-gray-100">{{ plugin.name }}</h3>
                            <span
                                class="px-2 py-0.5 rounded-full text-[11px] font-semibold uppercase tracking-wide"
                                :class="
                                    plugin.enabled
                                        ? 'bg-green-100 text-green-800 dark:bg-green-900/30 dark:text-green-200'
                                        : 'bg-zinc-200 text-zinc-700 dark:bg-zinc-800 dark:text-zinc-300'
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
                                v-if="plugin.has_backend"
                                class="px-2 py-0.5 rounded-full text-[11px] font-semibold uppercase tracking-wide bg-violet-100 text-violet-800 dark:bg-violet-900/30 dark:text-violet-200"
                            >
                                {{ $t("plugins.settings.badge_wasm") }}
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
                <p v-if="plugin.auto_disabled_reason" class="text-sm text-amber-700 dark:text-amber-300">
                    {{ $t("plugins.settings.auto_disabled", { reason: plugin.auto_disabled_reason }) }}
                </p>
            </div>
        </div>
    </SettingsSectionBlock>
</template>

<script>
import SettingsSectionBlock from "./SettingsSectionBlock.vue";
import ToastUtils from "../../js/ToastUtils";
import { manifestPermissionSummary } from "../../js/plugins/pluginManifest.js";
import { pluginHost } from "../../js/plugins/PluginHost.js";
import { onWsEvent, offWsEvent } from "../../js/registries/wsEventRegistry.js";

export default {
    name: "PluginsSettingsSection",
    components: { SettingsSectionBlock },
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
            busyPluginId: null,
        };
    },
    mounted() {
        void this.refresh();
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
            return manifestPermissionSummary(plugin.manifest || { permissions: plugin.permissions || {} });
        },
        async refresh() {
            const response = await window.api.get("/api/v1/plugins");
            this.plugins = response.data?.plugins || [];
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
        confirmRemove(plugin) {
            const prompt = this.$t("plugins.settings.confirm_remove", { name: plugin.name || plugin.id });
            if (!window.confirm(prompt)) {
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
        async installArchive(file) {
            if (!file) {
                return;
            }
            this.installing = true;
            try {
                const formData = new FormData();
                formData.append("archive", file);
                await window.api.post("/api/v1/plugins/install", formData);
                await this.refresh();
                ToastUtils.success(this.$t("plugins.settings.installed"));
            } catch (error) {
                ToastUtils.error(
                    this.$t("plugins.settings.install_failed", { reason: error?.message || String(error) })
                );
            } finally {
                this.installing = false;
                this.dragActive = false;
                if (this.$refs.fileInput) {
                    this.$refs.fileInput.value = "";
                }
            }
        },
        async onInstallFile(event) {
            const file = event.target.files?.[0];
            await this.installArchive(file);
        },
        async onDropArchive(event) {
            this.dragActive = false;
            const file = event.dataTransfer?.files?.[0];
            await this.installArchive(file);
        },
    },
};
</script>
