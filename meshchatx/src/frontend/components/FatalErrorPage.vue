<!-- SPDX-License-Identifier: 0BSD -->

<template>
    <div
        class="fatal-error-page flex min-h-dvh w-full flex-col items-center justify-center px-4 py-8"
        :class="embedded ? 'relative min-h-0 bg-transparent' : 'fixed inset-0 z-[500] bg-sem-canvas'"
        role="alertdialog"
        aria-modal="true"
        :aria-labelledby="headingId"
        :aria-describedby="messageId"
    >
        <div class="modal-panel w-full max-w-lg p-6 sm:p-8">
            <div class="flex items-start gap-4">
                <div
                    class="flex size-12 shrink-0 items-center justify-center rounded-2xl"
                    :class="
                        kind === 'backend' ? 'bg-sem-warning/15 text-sem-warning' : 'bg-sem-danger/15 text-sem-danger'
                    "
                >
                    <MaterialDesignIcon
                        :icon-name="kind === 'backend' ? 'server-off' : 'alert-circle-outline'"
                        class="size-7"
                    />
                </div>
                <div class="min-w-0 flex-1 space-y-2">
                    <h1 :id="headingId" class="text-xl font-bold text-sem-fg">
                        {{ resolvedTitle }}
                    </h1>
                    <p :id="messageId" class="text-sm leading-relaxed text-sem-fg-muted">
                        {{ error.message }}
                    </p>
                </div>
            </div>

            <details v-if="hasDetails" class="mt-5 rounded-xl border border-sem-border bg-sem-surface-muted">
                <summary class="cursor-pointer px-4 py-3 text-sm font-semibold text-sem-fg">
                    {{ $t("app.error_details_heading") }}
                </summary>
                <pre
                    class="max-h-48 overflow-auto border-t border-sem-border px-4 py-3 text-xs leading-relaxed text-sem-fg-secondary whitespace-pre-wrap wrap-break-word"
                    >{{ detailBody }}</pre>
            </details>

            <div class="mt-6 flex flex-wrap items-center gap-2">
                <button type="button" class="primary-chip" @click="onReload">
                    <MaterialDesignIcon icon-name="refresh" class="size-4" />
                    {{ $t("app.error_reload_page") }}
                </button>
                <button type="button" class="secondary-chip" @click="onReportLocal">
                    <MaterialDesignIcon icon-name="bug-outline" class="size-4" />
                    {{ reportLabel }}
                </button>
                <button type="button" class="secondary-chip" @click="onCopy">
                    <MaterialDesignIcon icon-name="content-copy" class="size-4" />
                    {{ copyLabel }}
                </button>
            </div>
        </div>
    </div>
</template>

<script>
import MaterialDesignIcon from "./MaterialDesignIcon.vue";
import ToastUtils from "../js/ToastUtils.js";
import { copyTextToClipboard } from "../js/clipboardUtils.js";
import { formatFatalErrorReport, recordFatalErrorLocally } from "../js/fatalErrorState.js";

export default {
    name: "FatalErrorPage",
    components: {
        MaterialDesignIcon,
    },
    props: {
        error: {
            type: Object,
            required: true,
        },
        embedded: {
            type: Boolean,
            default: false,
        },
    },
    data() {
        return {
            copyLabel: "",
            reportLabel: "",
            headingId: `fatal-error-title-${Math.random().toString(36).slice(2, 9)}`,
            messageId: `fatal-error-message-${Math.random().toString(36).slice(2, 9)}`,
        };
    },
    computed: {
        kind() {
            return this.error?.kind === "backend" ? "backend" : "frontend";
        },
        resolvedTitle() {
            if (this.error?.title) {
                return this.error.title;
            }
            return this.kind === "backend" ? this.$t("app.error_backend_title") : this.$t("app.error_frontend_title");
        },
        hasDetails() {
            return Boolean(this.detailBody);
        },
        detailBody() {
            return [this.error?.details, this.error?.context, this.error?.stack].filter(Boolean).join("\n\n");
        },
    },
    created() {
        this.copyLabel = this.$t("app.error_copy_details");
        this.reportLabel = this.$t("app.error_report_locally");
    },
    methods: {
        onReload() {
            window.location.reload();
        },
        async onReportLocal() {
            const result = await recordFatalErrorLocally(this.error);
            if (result?.ok) {
                ToastUtils.success(this.$t("app.error_report_saved"));
                this.reportLabel = this.$t("app.error_report_saved");
                try {
                    this.$router?.push?.({ name: "plugin-mcx-bugs" });
                } catch {
                    window.location.hash = "#/plugins/com.meshchatx.mcx-bugs";
                }
            } else {
                ToastUtils.error(this.$t("app.error_report_failed"));
            }
        },
        async onCopy() {
            const report = formatFatalErrorReport(this.error);
            const ok = await copyTextToClipboard(report);
            if (ok) {
                ToastUtils.success(this.$t("common.copied"));
                this.copyLabel = this.$t("common.copied");
                window.setTimeout(() => {
                    this.copyLabel = this.$t("app.error_copy_details");
                }, 1800);
            } else {
                ToastUtils.error(this.$t("common.failed_to_copy"));
            }
        },
    },
};
</script>
