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

<script>
import AppUpdatePrompt from "./AppUpdatePrompt.vue";
import ToastUtils from "../js/ToastUtils";
import {
    channelBugReportTarget,
    channelLabelKey,
    channelPromptSeenKey,
    normalizeReleaseChannel,
    shouldShowChannelPrompt,
} from "../js/releaseChannel.js";

export default {
    name: "ChannelPromptModal",
    components: {
        AppUpdatePrompt,
    },
    data() {
        return {
            visible: false,
            appInfo: null,
        };
    },
    computed: {
        channel() {
            return normalizeReleaseChannel(this.appInfo?.build_channel);
        },
        titleText() {
            const label = this.$t(channelLabelKey(this.channel));
            return this.$t("channel_prompt.title", { channel: label });
        },
        introText() {
            const label = this.$t(channelLabelKey(this.channel));
            return this.$t("channel_prompt.intro", { channel: label });
        },
        prompt() {
            const p = this.appInfo?.channel_prompt;
            return p && typeof p === "object" ? p : {};
        },
        notes() {
            return typeof this.prompt.notes === "string" ? this.prompt.notes.trim() : "";
        },
        focusAreas() {
            return Array.isArray(this.prompt.focus_areas)
                ? this.prompt.focus_areas.map((s) => String(s)).filter(Boolean)
                : [];
        },
        bugReportSteps() {
            return Array.isArray(this.prompt.bug_report_steps)
                ? this.prompt.bug_report_steps.map((s) => String(s)).filter(Boolean)
                : [];
        },
        reportTarget() {
            return channelBugReportTarget(this.prompt);
        },
        secondaryLabel() {
            if (!this.reportTarget.value) {
                return "";
            }
            if (this.reportTarget.kind === "lxmf") {
                return this.$t("channel_prompt.copy_lxmf");
            }
            return this.$t("channel_prompt.copy_url");
        },
    },
    methods: {
        show(appInfo) {
            if (!shouldShowChannelPrompt(appInfo)) {
                return false;
            }
            this.appInfo = appInfo;
            this.visible = true;
            return true;
        },
        async onDismiss() {
            await this.markSeen();
            this.visible = false;
        },
        async onSecondary() {
            if (!this.reportTarget.value) {
                return;
            }
            try {
                await navigator.clipboard.writeText(this.reportTarget.value);
                ToastUtils.success(
                    this.reportTarget.kind === "lxmf"
                        ? this.$t("channel_prompt.lxmf_copied")
                        : this.$t("channel_prompt.url_copied")
                );
            } catch {
                ToastUtils.error(
                    this.reportTarget.kind === "lxmf"
                        ? this.$t("channel_prompt.lxmf_copy_failed")
                        : this.$t("channel_prompt.url_copy_failed")
                );
            }
        },
        async markSeen() {
            if (!this.appInfo) {
                return;
            }
            const key = channelPromptSeenKey(this.appInfo);
            try {
                await window.api.post("/api/v1/app/channel-prompt/seen", { key });
                if (this.appInfo) {
                    this.appInfo.channel_prompt_seen = key;
                }
            } catch (e) {
                console.log(e);
            }
        },
    },
};
</script>
