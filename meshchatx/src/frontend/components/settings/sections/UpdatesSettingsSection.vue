<!-- SPDX-License-Identifier: 0BSD -->

<template>
    <SettingsSectionBlock
        v-show="visible"
        eyebrow="Maintenance"
        :title="$t('updates.settings_title')"
        :description="$t('updates.settings_description')"
        body-class="space-y-4"
    >
        <div class="text-sm text-gray-600 dark:text-gray-400 space-y-1">
            <div>
                {{ $t("updates.current_version") }}: {{ status.current_version || "?" }}
                <span v-if="status.channel">({{ status.channel }})</span>
            </div>
            <div v-if="status.enabled === false" class="text-xs">
                {{ $t("updates.disabled_notice") }}
            </div>
        </div>

        <div v-if="checkResult" class="text-sm space-y-2">
            <div v-if="checkResult.error" class="text-red-500">
                {{ checkResult.error }}
            </div>
            <div v-else-if="checkResult.update_available">
                <span class="font-medium text-green-600 dark:text-green-400">
                    {{ $t("updates.available", { version: checkResult.manifest?.version }) }}
                </span>
            </div>
            <div v-else class="text-gray-600 dark:text-gray-400">
                {{ $t("updates.up_to_date") }}
            </div>
        </div>

        <div
            v-if="pending"
            class="rounded-xl border border-amber-300 dark:border-amber-700 bg-amber-50 dark:bg-amber-900/20 p-3 text-sm space-y-2"
        >
            <div class="font-medium">
                {{ $t("updates.pending_ready", { version: pending.version }) }}
            </div>
            <div class="text-xs text-gray-600 dark:text-gray-400 break-all">
                {{ pending.file }}
            </div>
            <div class="flex flex-wrap gap-2">
                <button
                    v-if="pending.apply && pending.apply.mode === 'relaunch'"
                    type="button"
                    class="px-3 py-1.5 rounded-lg bg-amber-500 text-white text-sm font-medium hover:bg-amber-600 disabled:opacity-50"
                    :disabled="busy"
                    @click="applyPending"
                >
                    {{ $t("updates.restart_to_apply") }}
                </button>
                <button
                    type="button"
                    class="px-3 py-1.5 rounded-lg border border-gray-300 dark:border-zinc-700 text-sm hover:border-gray-400 disabled:opacity-50"
                    :disabled="busy"
                    @click="showPendingInFolder"
                >
                    {{ $t("updates.show_file") }}
                </button>
                <button
                    type="button"
                    class="px-3 py-1.5 rounded-lg border border-gray-300 dark:border-zinc-700 text-sm hover:border-gray-400 disabled:opacity-50"
                    :disabled="busy"
                    @click="discard"
                >
                    {{ $t("updates.discard") }}
                </button>
            </div>
            <div
                v-if="pending.apply && pending.apply.mode === 'manual'"
                class="text-xs text-gray-600 dark:text-gray-400"
            >
                {{ pending.apply.instructions }}
            </div>
        </div>

        <div class="flex flex-wrap gap-2">
            <button
                type="button"
                class="px-3 py-1.5 rounded-lg bg-teal-600 text-white text-sm font-medium hover:bg-teal-700 disabled:opacity-50"
                :disabled="busy || status.enabled === false"
                @click="check"
            >
                {{ busyCheck ? $t("updates.checking") : $t("updates.check_now") }}
            </button>
            <button
                v-if="checkResult && checkResult.update_available && downloadable.length"
                type="button"
                class="px-3 py-1.5 rounded-lg bg-sem-action-success text-sem-action-success-text text-sm font-medium hover:bg-green-700 disabled:opacity-50"
                :disabled="busy"
                @click="download"
            >
                {{ busyDownload ? $t("updates.downloading") : $t("updates.download_apply") }}
            </button>
            <label
                class="px-3 py-1.5 rounded-lg border border-gray-300 dark:border-zinc-700 text-sm cursor-pointer hover:border-gray-400"
                :class="{ 'opacity-50 pointer-events-none': busy || status.enabled === false }"
            >
                {{ $t("updates.apply_file") }}
                <input type="file" class="hidden" :disabled="busy || status.enabled === false" @change="onFileChosen" />
            </label>
        </div>

        <div v-if="notice" class="text-sm text-gray-600 dark:text-gray-400">{{ notice }}</div>
        <div v-if="errorText" class="text-sm text-red-500">{{ errorText }}</div>
    </SettingsSectionBlock>
</template>

<script>
import SettingsSectionBlock from "../SettingsSectionBlock.vue";
import {
    applyUpdateFile,
    checkUpdate,
    discardUpdate,
    downloadUpdate,
    getPendingUpdate,
    getUpdateStatus,
} from "../../../js/api/update.js";
import ElectronUtils from "../../../js/ElectronUtils";

export default {
    name: "UpdatesSettingsSection",
    components: { SettingsSectionBlock },
    props: {
        visible: { type: Boolean, default: true },
    },
    data() {
        return {
            status: {},
            checkResult: null,
            pending: null,
            busyCheck: false,
            busyDownload: false,
            busyApply: false,
            notice: "",
            errorText: "",
        };
    },
    computed: {
        busy() {
            return this.busyCheck || this.busyDownload || this.busyApply;
        },
        downloadable() {
            // Prefer the platform-native package for this runtime:
            // Electron on Linux updates via AppImage swap, Android via APK,
            // self-hosted installs via wheel or pyz.
            const arts = (this.checkResult && this.checkResult.artifacts) || [];
            const pref = this.isElectron
                ? ["appimage", "exe", "dmg", "zip", "wheel", "pyz"]
                : ["apk", "wheel", "pyz", "zip"];
            return arts
                .filter((a) => pref.includes(a.kind))
                .sort((a, b) => pref.indexOf(a.kind) - pref.indexOf(b.kind));
        },
        isElectron() {
            return ElectronUtils.isElectron();
        },
    },
    async mounted() {
        await this.refresh();
    },
    methods: {
        async refresh() {
            try {
                const [status, pending] = await Promise.all([getUpdateStatus(), getPendingUpdate()]);
                this.status = status.data || {};
                this.pending = (pending.data && pending.data.pending) || null;
            } catch {
                this.status = {};
            }
        },
        async check() {
            this.busyCheck = true;
            this.errorText = "";
            try {
                const res = await checkUpdate();
                this.checkResult = res.data || null;
            } catch (e) {
                this.errorText = e?.response?.data?.error || this.$t("updates.check_failed");
            } finally {
                this.busyCheck = false;
            }
        },
        async download() {
            const entry = this.downloadable[0];
            if (!entry) {
                return;
            }
            this.busyDownload = true;
            this.errorText = "";
            this.notice = "";
            try {
                const res = await downloadUpdate({ file: entry.file });
                this.pending = (res.data && res.data.pending) || null;
                if (!this.pending) {
                    this.errorText = this.$t("updates.download_failed");
                }
            } catch (e) {
                this.errorText = e?.response?.data?.error || this.$t("updates.download_failed");
            } finally {
                this.busyDownload = false;
            }
        },
        async onFileChosen(event) {
            const file = event.target.files && event.target.files[0];
            event.target.value = "";
            if (!file) {
                return;
            }
            this.busyApply = true;
            this.errorText = "";
            this.notice = "";
            try {
                const res = await applyUpdateFile(file);
                this.pending = (res.data && res.data.pending) || null;
            } catch (e) {
                this.errorText = e?.response?.data?.error || this.$t("updates.file_rejected");
            } finally {
                this.busyApply = false;
            }
        },
        async applyPending() {
            if (!this.pending) {
                return;
            }
            this.busyApply = true;
            this.errorText = "";
            try {
                if (this.isElectron && window.electron && window.electron.applyUpdate) {
                    const result = await window.electron.applyUpdate();
                    if (!result || !result.applied) {
                        this.errorText = this.$t("updates.apply_failed");
                    }
                    // applied -> app relaunches
                } else {
                    this.notice = this.$t("updates.manual_install_notice");
                }
            } catch {
                this.errorText = this.$t("updates.apply_failed");
            } finally {
                this.busyApply = false;
            }
        },
        async showPendingInFolder() {
            if (this.pending && this.pending.path && window.electron && window.electron.showPathInFolder) {
                await window.electron.showPathInFolder(this.pending.path);
            }
        },
        async discard() {
            try {
                await discardUpdate();
            } finally {
                this.pending = null;
            }
        },
    },
};
</script>
