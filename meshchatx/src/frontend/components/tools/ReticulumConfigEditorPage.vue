<!-- SPDX-License-Identifier: 0BSD -->

<template>
    <div class="flex flex-col flex-1 overflow-hidden min-w-0 bg-slate-50 dark:bg-zinc-950">
        <div
            class="flex flex-wrap items-center justify-between gap-2 px-3 sm:px-4 py-2 border-b border-gray-200 dark:border-zinc-800 bg-slate-50/95 dark:bg-zinc-950/95 backdrop-blur-sm shrink-0 min-w-0"
        >
            <div class="flex items-center gap-2 sm:gap-3 min-w-0">
                <div class="bg-blue-100 dark:bg-blue-900/30 p-1.5 rounded-xl shrink-0">
                    <MaterialDesignIcon icon-name="file-cog" class="size-5 text-blue-600 dark:text-blue-400" />
                </div>
                <div class="flex flex-col min-w-0">
                    <h1
                        class="text-sm font-bold text-gray-900 dark:text-white uppercase tracking-wider truncate leading-tight"
                    >
                        {{ $t("tools.reticulum_config_editor.title") }}
                    </h1>
                    <span
                        v-if="configPath"
                        class="text-[10px] text-gray-500 dark:text-gray-400 truncate leading-tight"
                        :title="configPath"
                    >
                        {{ configPath }}
                    </span>
                </div>
            </div>
            <div class="flex items-center gap-2 flex-wrap">
                <button type="button" class="secondary-chip !py-1 !px-3" :disabled="loading" @click="loadConfig">
                    <MaterialDesignIcon icon-name="refresh" class="w-3.5 h-3.5" />
                    <span class="hidden sm:inline">{{ $t("tools.reticulum_config_editor.reload") }}</span>
                </button>
                <button
                    type="button"
                    class="secondary-chip !py-1 !px-3 !text-red-500 hover:!bg-red-50 dark:hover:!bg-red-900/20"
                    :disabled="loading || resetting"
                    @click="restoreDefaults"
                >
                    <MaterialDesignIcon icon-name="restore" class="w-3.5 h-3.5" />
                    <span class="hidden sm:inline">{{ $t("tools.reticulum_config_editor.restore_defaults") }}</span>
                </button>
                <button
                    type="button"
                    class="secondary-chip !py-1 !px-3"
                    :disabled="!isDirty || saving"
                    @click="discardChanges"
                >
                    <MaterialDesignIcon icon-name="undo" class="w-3.5 h-3.5" />
                    <span class="hidden sm:inline">{{ $t("tools.reticulum_config_editor.discard") }}</span>
                </button>
                <button
                    type="button"
                    class="primary-chip !py-1 !px-3"
                    :disabled="!isDirty || saving"
                    @click="saveConfig"
                >
                    <MaterialDesignIcon icon-name="content-save" class="w-3.5 h-3.5" />
                    <span class="hidden sm:inline">{{
                        saving ? $t("tools.reticulum_config_editor.saving") : $t("tools.reticulum_config_editor.save")
                    }}</span>
                </button>
            </div>
        </div>

        <div
            class="flex-1 overflow-y-auto overflow-x-hidden w-full px-3 sm:px-5 py-4 pb-[max(1rem,env(safe-area-inset-bottom))]"
        >
            <div class="space-y-4 w-full min-w-0 max-w-6xl mx-auto">
                <div
                    v-if="showRestartReminder"
                    class="bg-amber-600 text-white border border-amber-500/30 p-4 sm:rounded-xl flex flex-wrap gap-3 items-center"
                >
                    <div class="flex items-center gap-3">
                        <MaterialDesignIcon icon-name="alert" class="w-6 h-6" />
                        <div>
                            <div class="text-lg font-semibold">
                                {{ $t("tools.reticulum_config_editor.restart_required") }}
                            </div>
                            <div class="text-sm">
                                {{ $t("tools.reticulum_config_editor.restart_description") }}
                            </div>
                        </div>
                    </div>
                    <button
                        type="button"
                        class="ml-auto inline-flex items-center gap-2 rounded-full bg-white px-4 py-1.5 text-sm font-bold text-amber-600 hover:bg-white/90 transition shadow-sm disabled:opacity-50"
                        :disabled="reloadingRns"
                        :class="reloadingRns ? '' : 'animate-pulse motion-reduce:animate-none'"
                        @click="reloadRns"
                    >
                        <MaterialDesignIcon icon-name="restart" class="w-4 h-4" />
                        {{ reloadingRns ? $t("app.reloading_rns") : $t("tools.reticulum_config_editor.restart_now") }}
                    </button>
                </div>

                <div
                    class="rounded-xl border border-gray-200 dark:border-zinc-800 bg-white dark:bg-zinc-900 overflow-hidden"
                >
                    <div
                        class="flex flex-wrap items-center justify-between gap-2 px-3 py-2 border-b border-gray-200 dark:border-zinc-800 bg-gray-50 dark:bg-zinc-900/60 text-xs text-gray-600 dark:text-gray-300"
                    >
                        <span class="flex items-center gap-1.5">
                            <MaterialDesignIcon icon-name="information-outline" class="w-3.5 h-3.5" />
                            {{ $t("tools.reticulum_config_editor.info") }}
                        </span>
                        <span v-if="isDirty" class="text-amber-600 dark:text-amber-400 font-semibold">
                            {{ $t("tools.reticulum_config_editor.unsaved") }}
                        </span>
                    </div>
                    <textarea
                        ref="editorRef"
                        v-model="content"
                        spellcheck="false"
                        autocapitalize="off"
                        autocomplete="off"
                        autocorrect="off"
                        :placeholder="loading ? $t('tools.reticulum_config_editor.loading') : ''"
                        class="w-full bg-white dark:bg-zinc-900 text-gray-900 dark:text-white p-4 font-mono text-xs sm:text-sm resize-none focus:outline-none min-h-[420px] sm:min-h-[60vh]"
                        @keydown.tab.prevent="insertTab"
                    ></textarea>
                </div>
            </div>
        </div>
    </div>
</template>

<script>
import MaterialDesignIcon from "../MaterialDesignIcon.vue";
import ToastUtils from "../../js/ToastUtils";
import DialogUtils from "../../js/DialogUtils";
import GlobalState from "../../js/GlobalState";

export default {
    name: "ReticulumConfigEditorPage",
    components: {
        MaterialDesignIcon,
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
        };
    },
    computed: {
        isDirty() {
            return this.content !== this.originalContent;
        },
        showRestartReminder() {
            return this.hasSavedChanges || GlobalState.hasPendingInterfaceChanges;
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
                const response = await window.api.get("/api/v1/reticulum/config/raw");
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
                const response = await window.api.put("/api/v1/reticulum/config/raw", {
                    content: this.content,
                });
                this.originalContent = this.content;
                this.configPath = response.data.path || this.configPath;
                this.hasSavedChanges = true;
                GlobalState.hasPendingInterfaceChanges = true;
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
                const response = await window.api.post("/api/v1/reticulum/config/reset");
                this.content = response.data.content || "";
                this.originalContent = this.content;
                this.configPath = response.data.path || this.configPath;
                this.hasSavedChanges = true;
                GlobalState.hasPendingInterfaceChanges = true;
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
                const response = await window.api.post("/api/v1/reticulum/reload");
                ToastUtils.success(response.data.message || this.$t("tools.reticulum_config_editor.restart_done"));
                this.hasSavedChanges = false;
                GlobalState.hasPendingInterfaceChanges = false;
                if (GlobalState.modifiedInterfaceNames?.clear) {
                    GlobalState.modifiedInterfaceNames.clear();
                }
                await this.loadConfig();
            } catch (e) {
                ToastUtils.error(e.response?.data?.error || this.$t("tools.reticulum_config_editor.failed_restart"));
            } finally {
                ToastUtils.dismiss("rns-config-reload");
                this.reloadingRns = false;
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
