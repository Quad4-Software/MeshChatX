<!-- SPDX-License-Identifier: 0BSD -->

<template>
    <AppModal v-model="visible" :max-width="500" persistent panel-class="bg-sem-warning text-white">
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
                    class="rounded-lg bg-sem-surface px-4 py-2 text-sm font-bold text-sem-warning transition-colors hover:bg-sem-warning/15"
                    @click="acknowledgeAndReset"
                >
                    {{ $t("common.acknowledge_reset") }}
                </button>
            </div>
        </template>
    </AppModal>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from "vue";
import AppModal from "./AppModal.vue";
import MaterialDesignIcon from "./MaterialDesignIcon.vue";
import ToastUtils from "../js/ToastUtils";
import { apiPath, STORAGE_KEYS } from "../js/constants";
import { translateUi } from "../js/localeLoader.js";

const visible = ref(false);
const dontShowAgain = ref(false);
const integrity = ref<any>({
    backend: { ok: true, issues: [] },
    data: { ok: true, issues: [] },
});

const issues = computed(() => [...integrity.value.backend.issues, ...integrity.value.data.issues]);

onMounted(async () => {
    const desktop = (window as any).desktop;
    if (desktop && desktop.getIntegrityStatus) {
        integrity.value = await desktop.getIntegrityStatus();

        const isOk = integrity.value.backend.ok && integrity.value.data.ok;
        if (!isOk) {
            const dismissed = localStorage.getItem(STORAGE_KEYS.INTEGRITY_WARNING_DISMISSED);
            const appVersion = await desktop.appVersion();

            if (dismissed !== appVersion) {
                visible.value = true;
            }
        }
    }
});

async function close() {
    const desktop = (window as any).desktop;
    if (dontShowAgain.value && desktop) {
        const appVersion = await desktop.appVersion();
        localStorage.setItem(STORAGE_KEYS.INTEGRITY_WARNING_DISMISSED, appVersion);
    }
    visible.value = false;
}

async function acknowledgeAndReset() {
    try {
        await (window as any).api.post(apiPath("/app/integrity/acknowledge"));
        ToastUtils.success(translateUi("about.integrity_acknowledged_reset"));
        visible.value = false;
    } catch (e) {
        ToastUtils.error(translateUi("about.failed_acknowledge_integrity"));
        console.error(e);
    }
}
</script>
