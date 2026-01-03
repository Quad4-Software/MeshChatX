<template>
    <v-dialog v-model="visible" persistent max-width="500">
        <v-card color="warning" class="pa-4">
            <v-card-title class="headline text-white">
                <v-icon start icon="mdi-alert-decagram" class="mr-2"></v-icon>
                Security Integrity Warning
            </v-card-title>

            <v-card-text class="text-white mt-2">
                <p v-if="integrity.backend && !integrity.backend.ok">
                    <strong>Backend Tampering Detected!</strong><br />
                    The application backend binary (unpacked from ASAR) appears to have been modified or replaced. This
                    could indicate a malicious actor trying to compromise your mesh communication.
                </p>

                <p v-if="integrity.data && !integrity.data.ok" class="mt-2">
                    <strong>Data Tampering Detected!</strong><br />
                    Your identities or database files appear to have been modified while the app was closed.
                </p>

                <v-expansion-panels v-if="issues.length > 0" variant="inset" class="mt-4">
                    <v-expansion-panel title="Technical Details" bg-color="warning-darken-1">
                        <v-expansion-panel-text>
                            <ul class="text-caption">
                                <li v-for="(issue, index) in issues" :key="index">{{ issue }}</li>
                            </ul>
                        </v-expansion-panel-text>
                    </v-expansion-panel>
                </v-expansion-panels>

                <p class="mt-4 text-caption">
                    Proceed with caution. If you did not manually update or modify these files, your installation may be
                    compromised.
                </p>
            </v-card-text>

            <v-card-actions>
                <v-checkbox
                    v-model="dontShowAgain"
                    label="I understand, do not show again for this version"
                    density="compact"
                    hide-details
                    class="text-white"
                ></v-checkbox>
                <v-spacer></v-spacer>
                <v-btn variant="text" color="white" @click="close"> Continue Anyway </v-btn>
                <v-btn
                    v-if="integrity.data && !integrity.data.ok"
                    variant="flat"
                    color="white"
                    class="text-warning font-bold"
                    @click="acknowledgeAndReset"
                >
                    Acknowledge & Reset
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
                await window.axios.post("/api/v1/app/integrity/acknowledge");
                ToastUtils.success("Integrity issues acknowledged and manifest reset");
                this.visible = false;
            } catch (e) {
                ToastUtils.error("Failed to acknowledge integrity issues");
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
