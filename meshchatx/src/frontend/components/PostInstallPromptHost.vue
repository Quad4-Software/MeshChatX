<!-- SPDX-License-Identifier: 0BSD -->

<template>
    <AppUpdatePrompt
        :model-value="visible"
        :title="resolvedTitle"
        :description="resolvedDescription"
        :primary-label="resolvedPrimaryLabel"
        :secondary-label="resolvedSecondaryLabel"
        :busy="busy"
        @update:model-value="onVisibleUpdate"
        @primary="onPrimary"
        @secondary="onSecondary"
    />
</template>

<script setup lang="ts">
import { computed, ref } from "vue";
import AppUpdatePrompt from "./AppUpdatePrompt.vue";
import { listPostInstallPromptsByPriority } from "../js/registries/postInstallPromptRegistry";
import { markPromptSeen, shouldShowPrompt } from "../js/postInstallPromptState.js";
import { useTranslateUi } from "../js/localeLoader.js";

const emit = defineEmits<{
    completed: [result: { id: string | undefined; revision: number | undefined }];
    dismissed: [];
}>();

const visible = ref(false);
const busy = ref(false);
const activeEntry = ref<Record<string, any> | null>(null);

const t = useTranslateUi();

const resolvedTitle = computed(() => {
    if (!activeEntry.value?.titleKey) {
        return "";
    }
    return t(activeEntry.value.titleKey);
});

const resolvedDescription = computed(() => {
    if (!activeEntry.value?.descriptionKey) {
        return "";
    }
    return t(activeEntry.value.descriptionKey);
});

const resolvedPrimaryLabel = computed(() => {
    const key = activeEntry.value?.primaryLabelKey || "common.continue";
    return t(key);
});

const resolvedSecondaryLabel = computed(() => {
    if (!activeEntry.value?.secondaryLabelKey) {
        return "";
    }
    return t(activeEntry.value.secondaryLabelKey);
});

/**
 * Find and show the next pending registry prompt.
 * @returns true if a prompt was opened
 */
async function showNext(): Promise<boolean> {
    if (visible.value) {
        return true;
    }
    const pending = await findNextPending();
    if (!pending) {
        return false;
    }
    activeEntry.value = pending;
    visible.value = true;
    return true;
}

async function findNextPending(): Promise<Record<string, any> | null> {
    for (const entry of listPostInstallPromptsByPriority()) {
        if (!shouldShowPrompt(entry.id, entry.revision)) {
            continue;
        }
        if (typeof entry.shouldShow === "function") {
            try {
                const ok = await entry.shouldShow();
                if (!ok) {
                    continue;
                }
            } catch (e) {
                console.error(`post-install prompt ${entry.id} shouldShow failed`, e);
                continue;
            }
        }
        return entry;
    }
    return null;
}

function hide() {
    visible.value = false;
    activeEntry.value = null;
    busy.value = false;
}

function onVisibleUpdate(val: boolean) {
    visible.value = val;
    if (!val) {
        emit("dismissed");
        activeEntry.value = null;
        busy.value = false;
    }
}

function dismissActive() {
    const entry = activeEntry.value;
    if (entry) {
        markPromptSeen(entry.id, entry.revision);
    }
    hide();
    emit("completed", { id: entry?.id, revision: entry?.revision });
}

async function runAction(kind: "primary" | "secondary") {
    if (busy.value || !activeEntry.value) {
        return;
    }
    if (kind === "secondary" && !activeEntry.value.secondaryLabelKey) {
        return;
    }
    busy.value = true;
    try {
        const entry = activeEntry.value;
        const handler = kind === "primary" ? entry.onPrimary : entry.onSecondary;
        const dismissFlag = kind === "primary" ? entry.dismissOnPrimary : entry.dismissOnSecondary;
        let keepOpen = false;
        if (typeof handler === "function") {
            const result = await handler({ entry });
            keepOpen = result === false;
        }
        if (keepOpen) {
            return;
        }
        if (dismissFlag !== false) {
            dismissActive();
        } else {
            hide();
            emit("completed", { id: entry.id, revision: entry.revision });
        }
    } catch (e) {
        console.error(`post-install prompt ${kind} action failed`, e);
    } finally {
        busy.value = false;
    }
}

function onPrimary() {
    return runAction("primary");
}

function onSecondary() {
    return runAction("secondary");
}

defineExpose({
    showNext,
    visible,
    busy,
    activeEntry,
    resolvedTitle,
    resolvedDescription,
    resolvedPrimaryLabel,
    resolvedSecondaryLabel,
    dismissActive,
    onVisibleUpdate,
    onPrimary,
    onSecondary,
});
</script>
