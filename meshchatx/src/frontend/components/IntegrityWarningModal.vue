<!-- SPDX-License-Identifier: 0BSD -->

<template>
    <v-dialog v-model="visible" persistent max-width="500">
        <v-card color="warning" class="pa-4">
            <v-card-title class="headline text-white">
                <v-icon start icon="mdi-alert-decagram" class="mr-2"></v-icon>
                {{ $t("about.security_integrity") }}
            </v-card-title>

            <v-card-text class="text-white mt-2">
                <p v-if="integrity.backend && !integrity.backend.ok">
                    <strong>{{ $t("about.tampering_detected") }}</strong
                    ><br />
                    {{ $t("about.integrity_backend_error") }}
                </p>

                <p v-if="integrity.data && !integrity.data.ok" class="mt-2">
                    <strong>{{ $t("about.tampering_detected") }}</strong
                    ><br />
                    {{ $t("about.integrity_data_error") }}
                </p>

                <v-expansion-panels v-if="issues.length > 0" variant="inset" class="mt-4">
                    <v-expansion-panel :title="$t('about.technical_issues')" bg-color="warning-darken-1">
                        <v-expansion-panel-text>
                            <ul class="text-caption">
                                <li v-for="(issue, index) in issues" :key="index">{{ issue }}</li>
                            </ul>
                        </v-expansion-panel-text>
                    </v-expansion-panel>
                </v-expansion-panels>

                <p class="mt-4 text-caption">
                    {{ $t("about.integrity_warning_footer") }}
                </p>
            </v-card-text>

            <v-card-actions>
                <v-checkbox
                    v-model="dontShowAgain"
                    :label="$t('app.do_not_show_again')"
                    density="compact"
                    hide-details
                    class="text-white"
                ></v-checkbox>
                <v-spacer></v-spacer>
                <v-btn variant="text" color="white" @click="close"> {{ $t("common.continue") }} </v-btn>
                <v-btn
                    v-if="integrity.data && !integrity.data.ok"
                    variant="flat"
                    color="white"
                    class="text-warning font-bold"
                    @click="acknowledgeAndReset"
                >
                    {{ $t("common.acknowledge_reset") }}
                </v-btn>
            </v-card-actions>
        </v-card>
    </v-dialog>
</template>

<script>
import ToastUtils from "../js/ToastUtils";
export default {
    name: "IntegrityWarningModal",
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
                // Check if user has already dismissed this
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

<style scoped>
.text-white {
    color: white !important;
}
</style>
