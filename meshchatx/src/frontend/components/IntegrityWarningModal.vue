<!-- SPDX-License-Identifier: 0BSD -->

<template>
    <AppModal v-model="visible" :max-width="500" persistent panel-class="bg-amber-500 text-white">
        <template #header>
            <MaterialDesignIcon icon-name="alert-decagram" class="size-6 shrink-0" />
            <h2 class="min-w-0 flex-1 text-lg font-semibold">{{ $t("about.security_integrity") }}</h2>
        </template>

        <div class="space-y-3 px-4 py-4 sm:px-5">
            <p v-if="integrity.backend && !integrity.backend.ok">
                <strong>{{ $t("about.tampering_detected") }}</strong
                ><br />
                {{ $t("about.integrity_backend_error") }}
            </p>

            <p v-if="integrity.data && !integrity.data.ok">
                <strong>{{ $t("about.tampering_detected") }}</strong
                ><br />
                {{ $t("about.integrity_data_error") }}
            </p>

            <details v-if="issues.length > 0" class="rounded-lg bg-amber-600/40 p-3">
                <summary class="cursor-pointer text-sm font-medium">{{ $t("about.technical_issues") }}</summary>
                <ul class="mt-2 list-disc pl-5 text-xs">
                    <li v-for="(issue, index) in issues" :key="index">{{ issue }}</li>
                </ul>
            </details>

            <p class="text-xs opacity-90">{{ $t("about.integrity_warning_footer") }}</p>
        </div>

        <template #actions>
            <div class="flex w-full flex-wrap items-center gap-3">
                <label class="flex items-center gap-2 text-sm">
                    <input
                        v-model="dontShowAgain"
                        type="checkbox"
                        class="rounded-sm border-white/40 bg-transparent text-white focus:ring-white/50"
                    />
                    <span>{{ $t("app.do_not_show_again") }}</span>
                </label>
                <div class="flex-1" />
                <button
                    type="button"
                    class="rounded-lg px-4 py-2 text-sm font-medium text-white transition-colors hover:bg-white/10"
                    @click="close"
                >
                    {{ $t("common.continue") }}
                </button>
                <button
                    v-if="integrity.data && !integrity.data.ok"
                    type="button"
                    class="rounded-lg bg-white px-4 py-2 text-sm font-bold text-amber-600 transition-colors hover:bg-amber-50"
                    @click="acknowledgeAndReset"
                >
                    {{ $t("common.acknowledge_reset") }}
                </button>
            </div>
        </template>
    </AppModal>
</template>

<script>
import AppModal from "./AppModal.vue";
import MaterialDesignIcon from "./MaterialDesignIcon.vue";
import ToastUtils from "../js/ToastUtils";

export default {
    name: "IntegrityWarningModal",
    components: {
        AppModal,
        MaterialDesignIcon,
    },
    data() {
        return {
            visible: false,
            dontShowAgain: false,
            integrity: {
                backend: { ok: true, issues: [] },
                data: { ok: true, issues: [] },
            },
        };
    },
    computed: {
        issues() {
            return [...this.integrity.backend.issues, ...this.integrity.data.issues];
        },
    },
    async mounted() {
        if (window.electron && window.electron.getIntegrityStatus) {
            this.integrity = await window.electron.getIntegrityStatus();

            const isOk = this.integrity.backend.ok && this.integrity.data.ok;
            if (!isOk) {
                const dismissed = localStorage.getItem("integrity_warning_dismissed");
                const appVersion = await window.electron.appVersion();

                if (dismissed !== appVersion) {
                    this.visible = true;
                }
            }
        }
    },
    methods: {
        async close() {
            if (this.dontShowAgain && window.electron) {
                const appVersion = await window.electron.appVersion();
                localStorage.setItem("integrity_warning_dismissed", appVersion);
            }
            this.visible = false;
        },
        async acknowledgeAndReset() {
            try {
                await window.api.post("/api/v1/app/integrity/acknowledge");
                ToastUtils.success(this.$t("about.integrity_acknowledged_reset"));
                this.visible = false;
            } catch (e) {
                ToastUtils.error(this.$t("about.failed_acknowledge_integrity"));
                console.error(e);
            }
        },
    },
};
</script>
