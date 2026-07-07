<!-- SPDX-License-Identifier: 0BSD -->

<template>
    <SettingsSectionBlock
        v-show="visible"
        :title="$t('plugins.settings.title')"
        :description="$t('plugins.settings.description')"
    >
        <div class="space-y-4">
            <div
                v-for="plugin in plugins"
                :key="plugin.id"
                class="rounded-lg border border-gray-200 dark:border-zinc-800 p-4 space-y-3"
            >
                <div class="flex flex-wrap items-start justify-between gap-3">
                    <div>
                        <h3 class="text-base font-semibold text-gray-900 dark:text-gray-100">{{ plugin.name }}</h3>
                        <p class="text-sm text-gray-600 dark:text-gray-400">{{ plugin.description }}</p>
                        <p class="text-xs text-gray-500 dark:text-gray-500 mt-1">{{ plugin.id }} · v{{ plugin.version }}</p>
                    </div>
                    <div class="flex gap-2">
                        <button
                            v-if="!plugin.enabled"
                            type="button"
                            class="px-3 py-1.5 rounded-md bg-blue-600 text-white text-sm"
                            @click="enablePlugin(plugin.id)"
                        >
                            {{ $t("plugins.settings.enable") }}
                        </button>
                        <button
                            v-else
                            type="button"
                            class="px-3 py-1.5 rounded-md bg-zinc-600 text-white text-sm"
                            @click="disablePlugin(plugin.id)"
                        >
                            {{ $t("plugins.settings.disable") }}
                        </button>
                        <button
                            type="button"
                            class="px-3 py-1.5 rounded-md border border-red-300 text-red-600 text-sm"
                            @click="removePlugin(plugin.id)"
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
            <label class="block">
                <span class="text-sm font-medium text-gray-700 dark:text-gray-300">{{ $t("plugins.settings.install_zip") }}</span>
                <input type="file" accept=".zip,application/zip" class="mt-1 block w-full text-sm" @change="onInstallFile" />
            </label>
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
        };
    },
    mounted() {
        void this.refresh();
        this.onPluginDisabled = (payload) => {
            if (payload?.event === "plugin.disabled") {
                ToastUtils.warning(this.$t("plugins.settings.kill_switch", { reason: payload?.payload?.reason || "" }));
                void this.refresh();
            }
        };
        onWsEvent("plugin.event", this.onPluginDisabled);
    },
    beforeUnmount() {
        offWsEvent("plugin.event", this.onPluginDisabled);
    },
    methods: {
        permissionLines(plugin) {
            return manifestPermissionSummary(plugin.manifest || { permissions: plugin.permissions || {} });
        },
        async refresh() {
            const response = await window.api.get("/api/v1/plugins");
            this.plugins = response.data?.plugins || [];
        },
        async enablePlugin(pluginId) {
            await window.api.post(`/api/v1/plugins/${encodeURIComponent(pluginId)}/enable`);
            await pluginHost.loadEnabledPlugins(window.api, (key) => this.$t(key));
            await this.refresh();
            ToastUtils.success(this.$t("plugins.settings.enabled"));
        },
        async disablePlugin(pluginId) {
            await window.api.post(`/api/v1/plugins/${encodeURIComponent(pluginId)}/disable`);
            pluginHost.unloadPlugin(pluginId);
            await this.refresh();
            ToastUtils.info(this.$t("plugins.settings.disabled"));
        },
        async removePlugin(pluginId) {
            await window.api.delete(`/api/v1/plugins/${encodeURIComponent(pluginId)}`);
            pluginHost.unloadPlugin(pluginId);
            await this.refresh();
            ToastUtils.info(this.$t("plugins.settings.removed"));
        },
        async onInstallFile(event) {
            const file = event.target.files?.[0];
            if (!file) {
                return;
            }
            const formData = new FormData();
            formData.append("archive", file);
            await window.api.post("/api/v1/plugins/install", formData);
            await this.refresh();
            ToastUtils.success(this.$t("plugins.settings.installed"));
            event.target.value = "";
        },
    },
};
</script>
