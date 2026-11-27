<!-- SPDX-License-Identifier: 0BSD -->

<template>
    <AppUpdatePrompt
        v-model="visible"
        :title="titleText"
        :description="introText"
        :primary-label="$t('channel_prompt.dismiss')"
        :secondary-label="secondaryLabel"
        @primary="onDismiss"
        @secondary="onSecondary"
    >
        <div v-if="notes" class="rounded-md border border-sem-border bg-sem-canvas px-3 py-2 text-sem-fg">
            {{ notes }}
        </div>

        <div v-if="focusAreas.length" class="space-y-2">
            <div class="text-xs font-semibold uppercase tracking-wide text-sem-fg">
                {{ $t("channel_prompt.focus_title") }}
            </div>
            <ul class="list-disc space-y-1 pl-5 text-sem-fg-muted">
                <li v-for="(area, idx) in focusAreas" :key="`focus-${idx}`">{{ area }}</li>
            </ul>
        </div>

        <div class="space-y-2">
            <div class="text-xs font-semibold uppercase tracking-wide text-sem-fg">
                {{ $t("channel_prompt.bug_report_title") }}
            </div>
            <ol class="list-decimal space-y-1 pl-5 text-sem-fg-muted">
                <li v-for="(step, idx) in bugReportSteps" :key="`step-${idx}`">{{ step }}</li>
            </ol>
            <p
                v-if="reportTarget.value"
                class="break-all font-mono text-xs text-sem-fg-secondary"
                data-testid="channel-prompt-bug-url"
            >
                <span v-if="reportTarget.kind === 'lxmf'">{{ $t("channel_prompt.lxmf_label") }} </span>
                {{ reportTarget.value }}
            </p>
        </div>
    </AppUpdatePrompt>
</template>

<script setup lang="ts">
import { computed, ref } from "vue";
import AppUpdatePrompt from "./AppUpdatePrompt.vue";
import ToastUtils from "../js/ToastUtils";
import { apiPath } from "../js/constants";
import { translateUi } from "../js/localeLoader.js";
import {
    channelBugReportTarget,
    channelLabelKey,
    channelPromptSeenKey,
    normalizeReleaseChannel,
    shouldShowChannelPrompt,
} from "../js/releaseChannel.js";

const visible = ref(false);
const appInfo = ref<Record<string, any> | null>(null);

const channel = computed(() => normalizeReleaseChannel(appInfo.value?.build_channel));

const titleText = computed(() => {
    const label = translateUi(channelLabelKey(channel.value));
    return translateUi("channel_prompt.title", { channel: label });
});

const introText = computed(() => {
    const label = translateUi(channelLabelKey(channel.value));
    return translateUi("channel_prompt.intro", { channel: label });
});

const prompt = computed(() => {
    const p = appInfo.value?.channel_prompt;
    return p && typeof p === "object" ? p : {};
});

const notes = computed(() => (typeof prompt.value.notes === "string" ? prompt.value.notes.trim() : ""));

const focusAreas = computed(() =>
    Array.isArray(prompt.value.focus_areas) ? prompt.value.focus_areas.map((s: any) => String(s)).filter(Boolean) : []
);

const bugReportSteps = computed(() =>
    Array.isArray(prompt.value.bug_report_steps)
        ? prompt.value.bug_report_steps.map((s: any) => String(s)).filter(Boolean)
        : []
);

const reportTarget = computed(() => channelBugReportTarget(prompt.value));

const secondaryLabel = computed(() => {
    if (!reportTarget.value.value) {
        return "";
    }
    if (reportTarget.value.kind === "lxmf") {
        return translateUi("channel_prompt.copy_lxmf");
    }
    return translateUi("channel_prompt.copy_url");
});

function show(info: Record<string, any>) {
    if (!shouldShowChannelPrompt(info)) {
        return false;
    }
    appInfo.value = info;
    visible.value = true;
    return true;
}

async function onDismiss() {
    await markSeen();
    visible.value = false;
}

async function onSecondary() {
    if (!reportTarget.value.value) {
        return;
    }
    try {
        await navigator.clipboard.writeText(reportTarget.value.value);
        ToastUtils.success(
            reportTarget.value.kind === "lxmf"
                ? translateUi("channel_prompt.lxmf_copied")
                : translateUi("channel_prompt.url_copied")
        );
    } catch {
        ToastUtils.error(
            reportTarget.value.kind === "lxmf"
                ? translateUi("channel_prompt.lxmf_copy_failed")
                : translateUi("channel_prompt.url_copy_failed")
        );
    }
}

async function markSeen() {
    if (!appInfo.value) {
        return;
    }
    const key = channelPromptSeenKey(appInfo.value);
    try {
        await (window as any).api.post(apiPath("/app/channel-prompt/seen"), { key });
        if (appInfo.value) {
            appInfo.value.channel_prompt_seen = key;
        }
    } catch (e) {
        console.log(e);
    }
}

defineExpose({ show });
</script>
