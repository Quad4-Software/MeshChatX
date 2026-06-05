<!-- SPDX-License-Identifier: 0BSD -->

<template>
    <AppUpdatePrompt
        :model-value="visible"
        :title="promptTitle"
        :description="promptDescription"
        :primary-label="primaryLabel"
        :secondary-label="secondaryLabel"
        :busy="busy"
        :busy-text="$t('android_storage.working')"
        :primary-disabled="setupMode && !selectedSetupMode"
        @update:model-value="onVisibleUpdate"
        @primary="onPrimary"
        @secondary="onSecondary"
    >
        <div v-if="setupMode" class="space-y-2 text-left">
            <label
                class="flex items-start gap-3 p-3 rounded-xl border cursor-pointer transition-colors"
                :class="
                    selectedSetupMode === 'external'
                        ? 'border-blue-500 bg-blue-50/80 dark:bg-blue-950/30'
                        : 'border-gray-200 dark:border-zinc-800'
                "
            >
                <input v-model="selectedSetupMode" type="radio" class="mt-1" value="external" />
                <span>
                    <span class="font-medium text-gray-900 dark:text-zinc-100 block">
                        {{ $t("android_storage.setup_external_title") }}
                    </span>
                    <span class="text-xs text-gray-600 dark:text-zinc-400">
                        {{ $t("android_storage.setup_external_desc") }}
                    </span>
                </span>
            </label>
            <label
                class="flex items-start gap-3 p-3 rounded-xl border cursor-pointer transition-colors"
                :class="
                    selectedSetupMode === 'internal'
                        ? 'border-blue-500 bg-blue-50/80 dark:bg-blue-950/30'
                        : 'border-gray-200 dark:border-zinc-800'
                "
            >
                <input v-model="selectedSetupMode" type="radio" class="mt-1" value="internal" />
                <span>
                    <span class="font-medium text-gray-900 dark:text-zinc-100 block">
                        {{ $t("android_storage.setup_internal_title") }}
                    </span>
                    <span class="text-xs text-gray-600 dark:text-zinc-400">
                        {{ $t("android_storage.setup_internal_desc") }}
                    </span>
                </span>
            </label>
        </div>
        <p v-if="status?.active_path" class="text-[10px] font-mono text-gray-500 dark:text-zinc-500 break-all">
            {{ status.active_path }}
        </p>
    </AppUpdatePrompt>
</template>

<script>
import AppUpdatePrompt from "./AppUpdatePrompt.vue";
import AndroidStorageBridge from "../js/AndroidStorageBridge.js";
import ToastUtils from "../js/ToastUtils.js";

export default {
    name: "AndroidStorageChoicePrompt",
    components: { AppUpdatePrompt },
    props: {
        variant: {
            type: String,
            default: "upgrade",
            validator: (v) => v === "setup" || v === "upgrade",
        },
    },
    emits: ["completed", "dismissed"],
    data() {
        return {
            visible: false,
            busy: false,
            status: null,
            selectedSetupMode: "external",
            storageBridge: null,
        };
    },
    computed: {
        setupMode() {
            return this.variant === "setup";
        },
        promptTitle() {
            return this.setupMode ? this.$t("android_storage.setup_title") : this.$t("android_storage.upgrade_title");
        },
        promptDescription() {
            return this.setupMode ? this.$t("android_storage.setup_desc") : this.$t("android_storage.upgrade_desc");
        },
        primaryLabel() {
            return this.setupMode ? this.$t("android_storage.setup_continue") : this.$t("android_storage.upgrade_copy");
        },
        secondaryLabel() {
            return this.setupMode ? "" : this.$t("android_storage.upgrade_stay_internal");
        },
    },
    created() {
        this.storageBridge = new AndroidStorageBridge();
    },
    methods: {
        ensureStorageBridge() {
            if (!this.storageBridge) {
                this.storageBridge = new AndroidStorageBridge();
            }
            return this.storageBridge;
        },
        refreshStatus() {
            this.status = this.ensureStorageBridge().getStatus();
            return this.status;
        },
        shouldShowSetup() {
            const s = this.refreshStatus();
            return Boolean(s?.needs_setup_choice);
        },
        shouldShowUpgrade() {
            const s = this.refreshStatus();
            return Boolean(s?.needs_upgrade_prompt);
        },
        showSetup() {
            if (!this.shouldShowSetup()) {
                return false;
            }
            this.selectedSetupMode = "external";
            this.visible = true;
            return true;
        },
        showUpgrade() {
            if (!this.shouldShowUpgrade()) {
                return false;
            }
            this.visible = true;
            return true;
        },
        hide() {
            this.visible = false;
        },
        onVisibleUpdate(val) {
            this.visible = val;
            if (!val) {
                this.$emit("dismissed");
            }
        },
        async onPrimary() {
            if (this.busy) {
                return;
            }
            this.busy = true;
            try {
                if (this.setupMode) {
                    const mode = this.selectedSetupMode || "external";
                    const result = this.ensureStorageBridge().applySetupChoice(mode, this.status);
                    this.hide();
                    this.$emit("completed", { action: "setup", mode, restarted: result.restarted });
                    if (result.restarted) {
                        ToastUtils.success(this.$t("android_storage.restart_to_apply"));
                    }
                    return;
                }
                if (!this.ensureStorageBridge().scheduleCopyToExternalAndRestart()) {
                    ToastUtils.error(this.$t("android_storage.failed"));
                    return;
                }
                ToastUtils.success(this.$t("android_storage.copy_restart_hint"));
                this.ensureStorageBridge().restartApp();
            } catch (e) {
                console.error(e);
                ToastUtils.error(this.$t("android_storage.failed"));
            } finally {
                this.busy = false;
            }
        },
        async onSecondary() {
            if (this.busy || this.setupMode) {
                return;
            }
            this.busy = true;
            try {
                if (!this.ensureStorageBridge().keepInternalAndDismiss()) {
                    ToastUtils.error(this.$t("android_storage.failed"));
                    return;
                }
                this.hide();
                this.$emit("completed", { action: "stay_internal" });
            } catch (e) {
                console.error(e);
                ToastUtils.error(this.$t("android_storage.failed"));
            } finally {
                this.busy = false;
            }
        },
    },
};
</script>
