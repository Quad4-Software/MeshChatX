<!-- SPDX-License-Identifier: 0BSD -->

<template>
    <div class="flex flex-col flex-1 overflow-hidden min-w-0 bg-sem-canvas">
        <ToolsPageHeader
            icon="file-cog"
            :title="$t('tools.reticulum_config_editor.title')"
            :description="$t('tools.reticulum_config_editor.description')"
            accent="blue"
        >
            <template #actions>
                <button type="button" class="secondary-chip py-1! px-3!" :disabled="loading" @click="loadConfig">
                    <MaterialDesignIcon icon-name="refresh" class="w-3.5 h-3.5" />
                    <span class="hidden sm:inline">{{ $t("tools.reticulum_config_editor.reload") }}</span>
                </button>
                <button
                    type="button"
                    class="secondary-chip py-1! px-3!"
                    :class="{ 'ring-1 ring-sem-accent/40': showVersions }"
                    :disabled="loading"
                    @click="toggleVersions"
                >
                    <MaterialDesignIcon icon-name="history" class="w-3.5 h-3.5" />
                    <span class="hidden sm:inline">{{ $t("tools.reticulum_config_editor.versions") }}</span>
                </button>
                <button
                    type="button"
                    class="secondary-chip py-1! px-3! text-sem-danger! hover:bg-sem-danger/10!"
                    :disabled="loading || resetting"
                    @click="restoreDefaults"
                >
                    <MaterialDesignIcon icon-name="restore" class="w-3.5 h-3.5" />
                    <span class="hidden sm:inline">{{ $t("tools.reticulum_config_editor.restore_defaults") }}</span>
                </button>
                <button
                    type="button"
                    class="secondary-chip py-1! px-3!"
                    :disabled="!isDirty || saving"
                    @click="discardChanges"
                >
                    <MaterialDesignIcon icon-name="undo" class="w-3.5 h-3.5" />
                    <span class="hidden sm:inline">{{ $t("tools.reticulum_config_editor.discard") }}</span>
                </button>
                <button
                    type="button"
                    class="primary-chip py-1! px-3!"
                    :disabled="!isDirty || saving"
                    @click="saveConfig"
                >
                    <MaterialDesignIcon icon-name="content-save" class="w-3.5 h-3.5" />
                    <span class="hidden sm:inline">{{
                        saving ? $t("tools.reticulum_config_editor.saving") : $t("tools.reticulum_config_editor.save")
                    }}</span>
                </button>
            </template>
        </ToolsPageHeader>

        <div
            class="flex-1 min-h-0 overflow-hidden w-full px-3 sm:px-5 py-4 pb-[max(1rem,env(safe-area-inset-bottom))] flex flex-col"
        >
            <div class="space-y-4 w-full min-w-0 max-w-6xl mx-auto flex-1 min-h-0 flex flex-col">
                <p v-if="configPath" class="text-xs text-sem-fg-muted font-mono truncate shrink-0" :title="configPath">
                    {{ configPath }}
                </p>
                <div
                    v-if="showRestartReminder"
                    class="bg-sem-warning/15 text-sem-fg border border-sem-warning/40 p-4 sm:rounded-xl flex flex-wrap gap-3 items-center shrink-0"
                >
                    <div class="flex items-center gap-3">
                        <MaterialDesignIcon icon-name="alert" class="w-6 h-6 text-sem-warning" />
                        <div>
                            <div class="text-lg font-semibold">
                                {{ $t("tools.reticulum_config_editor.restart_required") }}
                            </div>
                            <div class="text-sm text-sem-fg-secondary">
                                {{ $t("tools.reticulum_config_editor.restart_description") }}
                            </div>
                        </div>
                    </div>
                    <button
                        type="button"
                        class="ml-auto inline-flex items-center gap-2 rounded-full bg-sem-action-warning px-4 py-1.5 text-sm font-bold text-sem-action-warning-text hover:bg-sem-action-warning-hover transition shadow-xs disabled:opacity-50"
                        :disabled="reloadingRns"
                        :class="reloadingRns ? '' : 'animate-pulse motion-reduce:animate-none'"
                        @click="reloadRns"
                    >
                        <MaterialDesignIcon icon-name="restart" class="w-4 h-4" />
                        {{ reloadingRns ? $t("app.reloading_rns") : $t("tools.reticulum_config_editor.restart_now") }}
                    </button>
                </div>

                <div
                    v-if="showVersions"
                    class="rounded-xl border border-sem-border bg-sem-surface shrink-0 max-h-56 overflow-y-auto"
                >
                    <div
                        class="flex items-center gap-1.5 px-3 py-2 border-b border-sem-border bg-sem-surface-muted/60 text-xs font-semibold text-sem-fg-secondary"
                    >
                        <MaterialDesignIcon icon-name="history" class="w-3.5 h-3.5" />
                        {{ $t("tools.reticulum_config_editor.versions") }}
                    </div>
                    <div v-if="versionsLoading" class="px-3 py-3 text-xs text-sem-fg-muted">
                        {{ $t("tools.reticulum_config_editor.loading") }}
                    </div>
                    <div v-else-if="!versions.length" class="px-3 py-3 text-xs text-sem-fg-muted">
                        {{ $t("tools.reticulum_config_editor.versions_empty") }}
                    </div>
                    <ul v-else class="divide-y divide-sem-border">
                        <li
                            v-for="version in versions"
                            :key="version.id"
                            class="flex items-center gap-2 px-3 py-2 text-xs"
                        >
                            <div class="flex-1 min-w-0">
                                <div class="font-semibold text-sem-fg truncate">
                                    {{ formatVersionTime(version.created_at) }}
                                </div>
                                <div class="text-sem-fg-muted truncate">
                                    {{ version.label || version.id }}
                                </div>
                            </div>
                            <button
                                type="button"
                                class="secondary-chip py-1! px-2!"
                                :disabled="restoringVersionId != null"
                                @click="previewVersion(version)"
                            >
                                {{ $t("tools.reticulum_config_editor.preview") }}
                            </button>
                            <button
                                type="button"
                                class="secondary-chip py-1! px-2!"
                                :disabled="restoringVersionId != null"
                                @click="restoreVersion(version)"
                            >
                                <MaterialDesignIcon
                                    v-if="restoringVersionId === version.id"
                                    icon-name="loading"
                                    class="w-3.5 h-3.5 animate-spin"
                                />
                                {{ $t("tools.reticulum_config_editor.restore_version") }}
                            </button>
                        </li>
                    </ul>
                </div>

                <div
                    class="rounded-xl border border-sem-border bg-sem-surface overflow-hidden flex-1 min-h-0 flex flex-col"
                >
                    <div
                        class="flex flex-wrap items-center justify-between gap-2 px-3 py-2 border-b border-sem-border bg-sem-surface-muted/60 text-xs text-sem-fg-muted shrink-0"
                    >
                        <span class="flex items-center gap-1.5">
                            <MaterialDesignIcon icon-name="information-outline" class="w-3.5 h-3.5" />
                            {{ $t("tools.reticulum_config_editor.info") }}
                        </span>
                        <span v-if="isDirty" class="text-sem-warning font-semibold">
                            {{ $t("tools.reticulum_config_editor.unsaved") }}
                        </span>
                    </div>
                    <div class="relative flex-1 min-h-[12rem]">
                        <textarea
                            ref="editorRef"
                            v-model="content"
                            spellcheck="false"
                            autocapitalize="off"
                            autocomplete="off"
                            autocorrect="off"
                            :placeholder="loading ? $t('tools.reticulum_config_editor.loading') : ''"
                            class="absolute inset-0 w-full h-full bg-sem-surface text-sem-fg p-4 font-mono text-xs sm:text-sm resize-none focus:outline-hidden"
                            @keydown.tab.prevent="insertTab"
                        ></textarea>
                    </div>
                </div>
            </div>
        </div>
    </div>
</template>

<script>
import { useInterfaceChangesStore } from "../../js/stores/interfaceChangesStore.js";

import MaterialDesignIcon from "../MaterialDesignIcon.vue";
import ToastUtils from "../../js/ToastUtils";
import DialogUtils from "../../js/DialogUtils";
import ToolsPageHeader from "./ToolsPageHeader.vue";
import { apiPath } from "../../js/constants.js";

export default {
    name: "ReticulumConfigEditorPage",
    components: {
        MaterialDesignIcon,
        ToolsPageHeader,
    },
    beforeRouteLeave(to, from, next) {
        if (!this.isDirty) {
            next();
            return;
        }
        DialogUtils.confirm(this.$t("tools.reticulum_config_editor.confirm_leave")).then((ok) => {
            next(!!ok);
        });
    },
    data() {
        return {
            content: "",
            originalContent: "",
            configPath: "",
            loading: false,
            saving: false,
            resetting: false,
            reloadingRns: false,
            hasSavedChanges: false,
            showVersions: false,
            versions: [],
            versionsLoading: false,
            restoringVersionId: null,
        };
    },
    computed: {
        isDirty() {
            return this.content !== this.originalContent;
        },
        showRestartReminder() {
            return this.hasSavedChanges || useInterfaceChangesStore().hasPendingInterfaceChanges;
        },
    },
    async mounted() {
        await this.loadConfig();
    },
    methods: {
        async loadConfig() {
            if (this.loading) return;
            try {
                this.loading = true;
                const response = await window.api.get(apiPath("/reticulum/config/raw"));
                this.content = response.data.content || "";
                this.originalContent = this.content;
                this.configPath = response.data.path || "";
            } catch (e) {
                ToastUtils.error(e.response?.data?.error || this.$t("tools.reticulum_config_editor.failed_load"));
            } finally {
                this.loading = false;
            }
        },
        async saveConfig() {
            if (this.saving || !this.isDirty) return;
            try {
                this.saving = true;
                ToastUtils.loading(this.$t("tools.reticulum_config_editor.saving"), 0, "rns-config-save");
                const response = await window.api.put(apiPath("/reticulum/config/raw"), {
                    content: this.content,
                });
                this.originalContent = this.content;
                this.configPath = response.data.path || this.configPath;
                this.hasSavedChanges = true;
                useInterfaceChangesStore().hasPendingInterfaceChanges = true;
                ToastUtils.success(response.data.message || this.$t("tools.reticulum_config_editor.saved"));
            } catch (e) {
                ToastUtils.error(e.response?.data?.error || this.$t("tools.reticulum_config_editor.failed_save"));
            } finally {
                ToastUtils.dismiss("rns-config-save");
                this.saving = false;
            }
        },
        async restoreDefaults() {
            if (this.resetting) return;
            const confirmed = await DialogUtils.confirm(this.$t("tools.reticulum_config_editor.confirm_restore"));
            if (!confirmed) return;
            try {
                this.resetting = true;
                ToastUtils.loading(this.$t("tools.reticulum_config_editor.restoring"), 0, "rns-config-restore");
                const response = await window.api.post(apiPath("/reticulum/config/reset"));
                this.content = response.data.content || "";
                this.originalContent = this.content;
                this.configPath = response.data.path || this.configPath;
                this.hasSavedChanges = true;
                useInterfaceChangesStore().hasPendingInterfaceChanges = true;
                ToastUtils.success(response.data.message || this.$t("tools.reticulum_config_editor.restored"));
            } catch (e) {
                ToastUtils.error(e.response?.data?.error || this.$t("tools.reticulum_config_editor.failed_restore"));
            } finally {
                ToastUtils.dismiss("rns-config-restore");
                this.resetting = false;
            }
        },
        discardChanges() {
            if (!this.isDirty) return;
            this.content = this.originalContent;
        },
        async reloadRns() {
            if (this.reloadingRns) return;
            try {
                this.reloadingRns = true;
                ToastUtils.loading(this.$t("app.reloading_rns"), 0, "rns-config-reload");
                const response = await window.api.post(apiPath("/reticulum/reload"));
                ToastUtils.success(response.data.message || this.$t("tools.reticulum_config_editor.restart_done"));
                this.hasSavedChanges = false;
                useInterfaceChangesStore().hasPendingInterfaceChanges = false;
                if (useInterfaceChangesStore().modifiedInterfaceNames?.clear) {
                    useInterfaceChangesStore().modifiedInterfaceNames.clear();
                }
                await this.loadConfig();
            } catch (e) {
                ToastUtils.error(e.response?.data?.error || this.$t("tools.reticulum_config_editor.failed_restart"));
            } finally {
                ToastUtils.dismiss("rns-config-reload");
                this.reloadingRns = false;
            }
        },
        async toggleVersions() {
            this.showVersions = !this.showVersions;
            if (this.showVersions) {
                await this.loadVersions();
            }
        },
        async loadVersions() {
            if (this.versionsLoading) return;
            try {
                this.versionsLoading = true;
                const response = await window.api.get(apiPath("/reticulum/config/versions"));
                this.versions = Array.isArray(response.data?.versions) ? response.data.versions : [];
            } catch (e) {
                this.versions = [];
                ToastUtils.error(e.response?.data?.error || this.$t("tools.reticulum_config_editor.failed_versions"));
            } finally {
                this.versionsLoading = false;
            }
        },
        formatVersionTime(iso) {
            const date = new Date(iso);
            if (Number.isNaN(date.getTime())) {
                return iso || "";
            }
            return date.toLocaleString();
        },
        async previewVersion(version) {
            try {
                const response = await window.api.get(
                    apiPath(`/reticulum/config/versions/${encodeURIComponent(version.id)}`)
                );
                const content = response.data?.version?.content;
                if (typeof content === "string") {
                    this.content = content;
                }
            } catch (e) {
                ToastUtils.error(e.response?.data?.error || this.$t("tools.reticulum_config_editor.failed_versions"));
            }
        },
        async restoreVersion(version) {
            if (this.restoringVersionId != null) return;
            const confirmed = await DialogUtils.confirm(
                this.$t("tools.reticulum_config_editor.confirm_restore_version")
            );
            if (!confirmed) return;
            try {
                this.restoringVersionId = version.id;
                const response = await window.api.post(
                    apiPath(`/reticulum/config/versions/${encodeURIComponent(version.id)}/restore`)
                );
                this.content = response.data.content || "";
                this.originalContent = this.content;
                this.configPath = response.data.path || this.configPath;
                this.hasSavedChanges = true;
                useInterfaceChangesStore().hasPendingInterfaceChanges = true;
                ToastUtils.success(response.data.message || this.$t("tools.reticulum_config_editor.restored"));
                await this.loadVersions();
            } catch (e) {
                ToastUtils.error(e.response?.data?.error || this.$t("tools.reticulum_config_editor.failed_restore"));
            } finally {
                this.restoringVersionId = null;
            }
        },
        insertTab(event) {
            const target = event.target;
            const start = target.selectionStart;
            const end = target.selectionEnd;
            const before = this.content.substring(0, start);
            const after = this.content.substring(end);
            this.content = `${before}  ${after}`;
            this.$nextTick(() => {
                target.selectionStart = target.selectionEnd = start + 2;
            });
        },
    },
};
</script>
