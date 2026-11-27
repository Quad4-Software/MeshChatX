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
                        ? 'border-sem-accent bg-sem-info/15 dark:bg-sem-info/15'
                        : 'border-sem-border'
                "
            >
                <input v-model="selectedSetupMode" type="radio" class="mt-1" value="external" />
                <span>
                    <span class="font-medium text-sem-fg block">
                        {{ $t("android_storage.setup_external_title") }}
                    </span>
                    <span class="text-xs text-sem-fg-muted">
                        {{ $t("android_storage.setup_external_desc") }}
                    </span>
                </span>
            </label>
            <label
                class="flex items-start gap-3 p-3 rounded-xl border cursor-pointer transition-colors"
                :class="
                    selectedSetupMode === 'internal'
                        ? 'border-sem-accent bg-sem-info/15 dark:bg-sem-info/15'
                        : 'border-sem-border'
                "
            >
                <input v-model="selectedSetupMode" type="radio" class="mt-1" value="internal" />
                <span>
                    <span class="font-medium text-sem-fg block">
                        {{ $t("android_storage.setup_internal_title") }}
                    </span>
                    <span class="text-xs text-sem-fg-muted">
                        {{ $t("android_storage.setup_internal_desc") }}
                    </span>
                </span>
            </label>
        </div>
        <p v-if="status?.active_path" class="text-[10px] font-mono text-sem-fg-muted break-all">
            {{ status.active_path }}
        </p>
    </AppUpdatePrompt>
</template>

<script setup lang="ts">
import { computed, ref } from "vue";
import AppUpdatePrompt from "./AppUpdatePrompt.vue";
import AndroidStorageBridge from "../js/AndroidStorageBridge.js";
import ToastUtils from "../js/ToastUtils.js";
import { useTranslateUi } from "../js/localeLoader.js";

const props = withDefaults(
    defineProps<{
        variant?: string;
    }>(),
    {
        variant: "upgrade",
    }
);

const emit = defineEmits<{
    completed: [result: Record<string, any>];
    dismissed: [];
}>();

const t = useTranslateUi();

const visible = ref(false);
const busy = ref(false);
const status = ref<Record<string, any> | null>(null);
const selectedSetupMode = ref("external");

let storageBridge: any = null;

const setupMode = computed(() => props.variant === "setup");

const promptTitle = computed(() =>
    setupMode.value ? t("android_storage.setup_title") : t("android_storage.upgrade_title")
);

const promptDescription = computed(() =>
    setupMode.value ? t("android_storage.setup_desc") : t("android_storage.upgrade_desc")
);

const primaryLabel = computed(() =>
    setupMode.value ? t("android_storage.setup_continue") : t("android_storage.upgrade_copy")
);

const secondaryLabel = computed(() => (setupMode.value ? "" : t("android_storage.upgrade_stay_internal")));

function ensureStorageBridge() {
    if (!storageBridge) {
        storageBridge = new AndroidStorageBridge();
    }
    return storageBridge;
}

function refreshStatus() {
    status.value = ensureStorageBridge().getStatus();
    return status.value;
}

function shouldShowSetup() {
    const s = refreshStatus();
    return Boolean(s?.needs_setup_choice);
}

function shouldShowUpgrade() {
    const s = refreshStatus();
    return Boolean(s?.needs_upgrade_prompt);
}

function showSetup() {
    if (!shouldShowSetup()) {
        return false;
    }
    selectedSetupMode.value = "external";
    visible.value = true;
    return true;
}

function showUpgrade() {
    if (!shouldShowUpgrade()) {
        return false;
    }
    visible.value = true;
    return true;
}

function hide() {
    visible.value = false;
}

function onVisibleUpdate(val: boolean) {
    visible.value = val;
    if (!val) {
        emit("dismissed");
    }
}

async function onPrimary() {
    if (busy.value) {
        return;
    }
    busy.value = true;
    try {
        if (setupMode.value) {
            const mode = selectedSetupMode.value || "external";
            const result = ensureStorageBridge().applySetupChoice(mode, status.value);
            hide();
            emit("completed", { action: "setup", mode, restarted: result.restarted });
            if (result.restarted) {
                ToastUtils.success(t("android_storage.restart_to_apply"));
            }
            return;
        }
        if (!ensureStorageBridge().scheduleCopyToExternalAndRestart()) {
            ToastUtils.error(t("android_storage.failed"));
            return;
        }
        ToastUtils.success(t("android_storage.copy_restart_hint"));
        ensureStorageBridge().restartApp();
    } catch (e) {
        console.error(e);
        ToastUtils.error(t("android_storage.failed"));
    } finally {
        busy.value = false;
    }
}

async function onSecondary() {
    if (busy.value || setupMode.value) {
        return;
    }
    busy.value = true;
    try {
        if (!ensureStorageBridge().keepInternalAndDismiss()) {
            ToastUtils.error(t("android_storage.failed"));
            return;
        }
        hide();
        emit("completed", { action: "stay_internal" });
    } catch (e) {
        console.error(e);
        ToastUtils.error(t("android_storage.failed"));
    } finally {
        busy.value = false;
    }
}

defineExpose({ showSetup, showUpgrade, shouldShowSetup, shouldShowUpgrade, refreshStatus, visible });
</script>
