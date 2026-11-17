<!-- SPDX-License-Identifier: 0BSD -->

<template>
    <SettingsSectionBlock
        v-show="visible"
        eyebrow="Maintenance"
        :title="$t('updates.settings_title')"
        :description="$t('updates.settings_description')"
        body-class="space-y-4"
    >
        <div class="text-sm text-sem-fg-muted space-y-1">
            <div>
                {{ $t("updates.current_version") }}: {{ status.current_version || "?" }}
                <span v-if="status.channel">({{ status.channel }})</span>
            </div>
            <div v-if="lastCheckLine" class="text-xs">{{ lastCheckLine }}</div>
        </div>

        <div class="rounded-xl border border-sem-border p-3 space-y-2">
            <div class="text-sm font-medium">{{ $t("updates.disclosure_title") }}</div>
            <div class="text-xs text-sem-fg-muted space-y-1">
                <div v-for="m in disclosureMirrors" :key="m.url" class="break-all">{{ m.name }}: {{ m.url }}</div>
                <div>{{ $t("updates.disclosure_rns") }}: {{ disclosure.rns_destination || "meshchatx.update" }}</div>
                <div v-if="disclosure.signer_hashes && disclosure.signer_hashes.length">
                    {{ $t("updates.disclosure_signers") }}:
                    <span class="font-mono">{{ disclosure.signer_hashes.join(", ") }}</span>
                </div>
                <div>{{ disclosure.note }}</div>
            </div>
        </div>

        <label class="setting-toggle">
            <div>
                <div class="text-sm font-medium">{{ $t("updates.enable") }}</div>
                <div class="text-xs text-sem-fg-muted">{{ $t("updates.enable_desc") }}</div>
            </div>
            <input type="checkbox" :checked="!!settings.enabled" :disabled="busy" @change="onEnabledToggle" />
        </label>

        <template v-if="settings.enabled">
            <div class="grid gap-3 sm:grid-cols-2">
                <label class="block text-sm">
                    <span class="text-sem-fg-muted">{{ $t("updates.transport") }}</span>
                    <select
                        class="mt-1 w-full rounded-lg border border-sem-border bg-sem-surface px-2 py-1.5 text-sm"
                        :value="settings.transport"
                        :disabled="busy"
                        @change="savePatch({ transport: $event.target.value })"
                    >
                        <option value="auto">{{ $t("updates.transport_auto") }}</option>
                        <option value="clearnet">{{ $t("updates.transport_clearnet") }}</option>
                        <option value="rns">{{ $t("updates.transport_rns") }}</option>
                    </select>
                </label>
                <label class="block text-sm">
                    <span class="text-sem-fg-muted">{{ $t("updates.channel") }}</span>
                    <select
                        class="mt-1 w-full rounded-lg border border-sem-border bg-sem-surface px-2 py-1.5 text-sm"
                        :value="settings.channel || status.channel"
                        :disabled="busy"
                        @change="savePatch({ channel: $event.target.value })"
                    >
                        <option value="stable">stable</option>
                        <option value="beta">beta</option>
                        <option value="testing">testing</option>
                    </select>
                </label>
                <label class="block text-sm">
                    <span class="text-sem-fg-muted">{{ $t("updates.apply_policy") }}</span>
                    <select
                        class="mt-1 w-full rounded-lg border border-sem-border bg-sem-surface px-2 py-1.5 text-sm"
                        :value="settings.apply_policy"
                        :disabled="busy"
                        @change="savePatch({ apply_policy: $event.target.value })"
                    >
                        <option value="manual">{{ $t("updates.apply_manual") }}</option>
                        <option value="on_restart">{{ $t("updates.apply_on_restart") }}</option>
                    </select>
                </label>
                <label class="block text-sm">
                    <span class="text-sem-fg-muted">{{ $t("updates.max_download_mb") }}</span>
                    <input
                        type="number"
                        min="1"
                        max="8192"
                        class="mt-1 w-full rounded-lg border border-sem-border bg-sem-surface px-2 py-1.5 text-sm"
                        :value="settings.max_download_mb"
                        :disabled="busy"
                        @change="savePatch({ max_download_mb: Number($event.target.value) })"
                    />
                </label>
                <label class="block text-sm">
                    <span class="text-sem-fg-muted">{{ $t("updates.check_interval_hours") }}</span>
                    <input
                        type="number"
                        min="6"
                        max="720"
                        step="0.5"
                        class="mt-1 w-full rounded-lg border border-sem-border bg-sem-surface px-2 py-1.5 text-sm"
                        :value="settings.check_interval_hours"
                        :disabled="busy"
                        @change="savePatch({ check_interval_hours: Number($event.target.value) })"
                    />
                </label>
                <label class="block text-sm">
                    <span class="text-sem-fg-muted">{{ $t("updates.rns_rate_kbps") }}</span>
                    <input
                        type="number"
                        min="8"
                        max="10240"
                        class="mt-1 w-full rounded-lg border border-sem-border bg-sem-surface px-2 py-1.5 text-sm"
                        :value="settings.rns_rate_kbps"
                        :disabled="busy"
                        @change="savePatch({ rns_rate_kbps: Number($event.target.value) })"
                    />
                </label>
                <label class="block text-sm">
                    <span class="text-sem-fg-muted">{{ $t("updates.slow_link_kbps") }}</span>
                    <input
                        type="number"
                        min="1"
                        max="100000"
                        class="mt-1 w-full rounded-lg border border-sem-border bg-sem-surface px-2 py-1.5 text-sm"
                        :value="settings.slow_link_kbps"
                        :disabled="busy"
                        @change="savePatch({ slow_link_kbps: Number($event.target.value) })"
                    />
                </label>
            </div>

            <label class="setting-toggle">
                <div>
                    <div class="text-sm font-medium">{{ $t("updates.auto_check") }}</div>
                    <div class="text-xs text-sem-fg-muted">{{ $t("updates.auto_check_desc") }}</div>
                </div>
                <input
                    type="checkbox"
                    :checked="!!settings.auto_check"
                    :disabled="busy"
                    @change="savePatch({ auto_check: $event.target.checked })"
                />
            </label>
            <label class="setting-toggle">
                <div>
                    <div class="text-sm font-medium">{{ $t("updates.auto_download") }}</div>
                    <div class="text-xs text-sem-fg-muted">{{ $t("updates.auto_download_desc") }}</div>
                </div>
                <input
                    type="checkbox"
                    :checked="!!settings.auto_download"
                    :disabled="busy"
                    @change="savePatch({ auto_download: $event.target.checked })"
                />
            </label>
            <label class="setting-toggle">
                <div>
                    <div class="text-sm font-medium">{{ $t("updates.peer_relay") }}</div>
                    <div class="text-xs text-sem-fg-muted">{{ $t("updates.peer_relay_desc") }}</div>
                </div>
                <input
                    type="checkbox"
                    :checked="!!settings.peer_relay"
                    :disabled="busy"
                    @change="savePatch({ peer_relay: $event.target.checked })"
                />
            </label>

            <div class="space-y-2">
                <label class="block text-sm">
                    <span class="text-sem-fg-muted">{{ $t("updates.custom_mirrors") }}</span>
                    <textarea
                        class="mt-1 w-full rounded-lg border border-sem-border bg-sem-surface px-2 py-1.5 text-sm font-mono"
                        rows="3"
                        :value="mirrorsText"
                        :disabled="busy"
                        :placeholder="$t('updates.custom_mirrors_hint')"
                        @change="onMirrorsChange"
                    ></textarea>
                </label>
                <label class="block text-sm">
                    <span class="text-sem-fg-muted">{{ $t("updates.signer_hashes") }}</span>
                    <textarea
                        class="mt-1 w-full rounded-lg border border-sem-border bg-sem-surface px-2 py-1.5 text-sm font-mono"
                        rows="2"
                        :value="signersText"
                        :disabled="busy"
                        :placeholder="$t('updates.signer_hashes_hint')"
                        @change="onSignersChange"
                    ></textarea>
                </label>
                <label class="block text-sm">
                    <span class="text-sem-fg-muted">{{ $t("updates.rns_seeds") }}</span>
                    <textarea
                        class="mt-1 w-full rounded-lg border border-sem-border bg-sem-surface px-2 py-1.5 text-sm font-mono"
                        rows="2"
                        :value="seedsText"
                        :disabled="busy"
                        :placeholder="$t('updates.rns_seeds_hint')"
                        @change="onSeedsChange"
                    ></textarea>
                </label>
                <div class="text-xs text-sem-fg-muted">{{ $t("updates.mirrors_signers_note") }}</div>
            </div>
        </template>

        <div v-if="checkResult" class="text-sm space-y-2">
            <div v-if="checkResult.error" class="text-sem-danger">{{ checkResult.error }}</div>
            <div v-else-if="checkResult.update" class="space-y-2">
                <span class="font-medium text-sem-success">
                    {{ $t("updates.available", { version: checkResult.update.version }) }}
                </span>
                <div class="text-xs text-sem-fg-muted break-all">{{ checkResult.update.artifact.name }}</div>
                <button
                    type="button"
                    class="px-3 py-1.5 rounded-lg bg-sem-success text-white text-sm font-medium hover:opacity-90 disabled:opacity-50"
                    :disabled="busy || !settings.enabled"
                    @click="download"
                >
                    {{ downloading ? $t("updates.downloading") : $t("updates.download_apply") }}
                </button>
            </div>
            <div v-else class="text-sem-fg-muted">{{ $t("updates.up_to_date") }}</div>
        </div>

        <div v-if="progress && progress.phase && progress.phase !== 'idle'" class="text-xs text-sem-fg-muted">
            {{ progress.phase }}
            <template v-if="progress.size">
                ({{ fmtBytes(progress.downloaded || 0) }} / {{ fmtBytes(progress.size) }})</template
            >
            <template v-if="progress.reused"
                >, {{ $t("updates.bytes_reused", { count: fmtBytes(progress.reused) }) }}</template
            >
        </div>

        <div v-if="pending" class="rounded-xl border border-sem-warning bg-sem-warning/15 p-3 text-sm space-y-2">
            <div class="font-medium">
                {{ $t("updates.pending_ready", { version: pendingVersion }) }}
            </div>
            <div class="text-xs text-sem-fg-muted break-all">
                <div v-for="a in pending.artifacts || []" :key="a.file">{{ a.file }}</div>
            </div>
            <div v-if="pending.apply_policy === 'on_restart'" class="text-xs text-sem-fg-muted">
                {{ $t("updates.pending_on_restart") }}
            </div>
            <div class="flex flex-wrap gap-2">
                <button
                    v-if="canApplyPending"
                    type="button"
                    class="px-3 py-1.5 rounded-lg bg-sem-warning text-white text-sm font-medium hover:opacity-90 disabled:opacity-50"
                    :disabled="busy"
                    @click="applyPending"
                >
                    {{ $t("updates.restart_to_apply") }}
                </button>
                <button
                    type="button"
                    class="px-3 py-1.5 rounded-lg border border-sem-border text-sm hover:opacity-80 disabled:opacity-50"
                    :disabled="busy"
                    @click="showPendingInFolder"
                >
                    {{ $t("updates.show_file") }}
                </button>
                <button
                    type="button"
                    class="px-3 py-1.5 rounded-lg border border-sem-border text-sm hover:opacity-80 disabled:opacity-50"
                    :disabled="busy"
                    @click="discard"
                >
                    {{ $t("updates.discard") }}
                </button>
            </div>
            <div v-if="pendingManualNote" class="text-xs text-sem-fg-muted">
                {{ pendingManualNote }}
            </div>
        </div>

        <div class="flex flex-wrap gap-2">
            <button
                type="button"
                class="px-3 py-1.5 rounded-lg bg-sem-accent text-white text-sm font-medium hover:opacity-90 disabled:opacity-50"
                :disabled="busy || !settings.enabled"
                @click="check"
            >
                {{ busyCheck ? $t("updates.checking") : $t("updates.check_now") }}
            </button>
            <label
                class="px-3 py-1.5 rounded-lg border border-sem-border text-sm cursor-pointer hover:opacity-80"
                :class="{ 'opacity-50 pointer-events-none': busy || !settings.enabled }"
            >
                {{ $t("updates.apply_file") }}
                <input type="file" class="hidden" :disabled="busy || !settings.enabled" @change="onFileChosen" />
            </label>
        </div>

        <div v-if="notice" class="text-sm text-sem-fg-muted">{{ notice }}</div>
        <div v-if="errorText" class="text-sm text-sem-danger">{{ errorText }}</div>
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
    getUpdateProgress,
    getUpdateStatus,
    updateSettings,
} from "../../../js/api/update.js";
import DesktopUtils from "../../../js/DesktopUtils";

export default {
    name: "UpdatesSettingsSection",
    components: { SettingsSectionBlock },
    props: {
        visible: { type: Boolean, default: true },
    },
    data() {
        return {
            status: {},
            settings: {},
            disclosure: {},
            checkResult: null,
            pending: null,
            progress: null,
            busyCheck: false,
            busyDownload: false,
            busyApply: false,
            busySettings: false,
            notice: "",
            errorText: "",
            mirrorsText: "",
            signersText: "",
            seedsText: "",
            progressTimer: null,
        };
    },
    computed: {
        busy() {
            return this.busyCheck || this.busyDownload || this.busyApply || this.busySettings;
        },
        downloading() {
            return this.busyDownload;
        },
        disclosureMirrors() {
            return (this.disclosure && this.disclosure.mirrors) || [];
        },
        lastCheckLine() {
            const lc = this.status.last_check;
            if (!lc) return "";
            const parts = [this.$t("updates.last_check"), lc.at, lc.result];
            if (lc.version) parts.push(lc.version);
            if (lc.detail) parts.push(lc.detail);
            return parts.filter(Boolean).join(" - ");
        },
        pendingVersion() {
            const arts = (this.pending && this.pending.artifacts) || [];
            return arts.length ? arts[0].version || "" : "";
        },
        canApplyPending() {
            return DesktopUtils.isDesktop() && !!window.desktop && typeof window.desktop.applyUpdate === "function";
        },
        pendingManualNote() {
            const arts = (this.pending && this.pending.artifacts) || [];
            const a = arts[0];
            if (a && a.apply && a.apply.mode === "manual") {
                return a.apply.instructions || this.$t("updates.manual_install_notice");
            }
            return "";
        },
    },
    async mounted() {
        await this.refresh();
    },
    beforeUnmount() {
        this.stopProgressPolling();
    },
    methods: {
        async refresh() {
            try {
                const [status, pending] = await Promise.all([getUpdateStatus(), getPendingUpdate()]);
                const s = status.data || {};
                this.status = s;
                this.settings = s.settings || {};
                this.disclosure = s.disclosure || {};
                this.pending = (pending.data && pending.data.pending) || null;
                this.syncTexts();
            } catch {
                this.status = {};
                this.settings = {};
            }
        },
        syncTexts() {
            this.mirrorsText = (this.settings.custom_mirrors || []).join("\n");
            this.signersText = (this.settings.signer_hashes || []).join("\n");
            this.seedsText = (this.settings.rns_seeds || []).join("\n");
        },
        async savePatch(patch) {
            this.busySettings = true;
            this.errorText = "";
            try {
                const res = await updateSettings(patch);
                const s = (res && res.data) || {};
                this.status = s;
                this.settings = s.settings || {};
                this.disclosure = s.disclosure || {};
                this.syncTexts();
            } catch (e) {
                this.errorText = this.errMsg(e) || this.$t("updates.settings_failed");
            } finally {
                this.busySettings = false;
            }
        },
        async onEnabledToggle(event) {
            const enabled = !!event.target.checked;
            await this.savePatch({ enabled });
        },
        linesToList(text) {
            return String(text || "")
                .split("\n")
                .map((l) => l.trim())
                .filter(Boolean);
        },
        async onMirrorsChange(event) {
            this.mirrorsText = event.target.value;
            await this.savePatch({ custom_mirrors: this.linesToList(this.mirrorsText) });
        },
        async onSignersChange(event) {
            this.signersText = event.target.value;
            await this.savePatch({ signer_hashes: this.linesToList(this.signersText) });
        },
        async onSeedsChange(event) {
            this.seedsText = event.target.value;
            await this.savePatch({ rns_seeds: this.linesToList(this.seedsText) });
        },
        async check() {
            this.busyCheck = true;
            this.errorText = "";
            this.notice = "";
            try {
                const res = await checkUpdate({});
                this.checkResult = (res && res.data) || null;
                if (this.checkResult && this.checkResult.status === "update_available") {
                    this.notice = "";
                } else if (this.checkResult && this.checkResult.status === "up_to_date") {
                    this.notice = this.$t("updates.up_to_date");
                } else if (this.checkResult && this.checkResult.error) {
                    this.errorText = this.checkResult.error;
                }
                await this.refresh();
            } catch (e) {
                this.errorText = this.errMsg(e) || this.$t("updates.check_failed");
            } finally {
                this.busyCheck = false;
            }
        },
        async download() {
            this.busyDownload = true;
            this.errorText = "";
            this.startProgressPolling();
            try {
                const artifact = this.checkResult && this.checkResult.update && this.checkResult.update.artifact;
                const res = await downloadUpdate(artifact ? { artifact } : {});
                const d = (res && res.data) || {};
                if (d.status === "staged") {
                    this.notice = this.$t("updates.staged_notice");
                    this.checkResult = null;
                } else {
                    this.errorText = d.detail || this.$t("updates.download_failed");
                }
                await this.refresh();
            } catch (e) {
                this.errorText = this.errMsg(e) || this.$t("updates.download_failed");
            } finally {
                this.busyDownload = false;
                this.stopProgressPolling();
                await this.refresh();
            }
        },
        startProgressPolling() {
            this.stopProgressPolling();
            this.progressTimer = setInterval(async () => {
                try {
                    const res = await getUpdateProgress();
                    this.progress = (res && res.data) || null;
                } catch {
                    /* ignore */
                }
            }, 800);
        },
        stopProgressPolling() {
            if (this.progressTimer) {
                clearInterval(this.progressTimer);
                this.progressTimer = null;
            }
        },
        async onFileChosen(event) {
            const file = event.target.files && event.target.files[0];
            event.target.value = "";
            if (!file) return;
            this.busyApply = true;
            this.errorText = "";
            try {
                const res = await applyUpdateFile(file);
                const d = (res && res.data) || {};
                if (d.status === "staged") {
                    this.notice = this.$t("updates.staged_notice");
                } else {
                    this.errorText = this.$t("updates.file_rejected");
                }
                await this.refresh();
            } catch (e) {
                this.errorText = this.errMsg(e) || this.$t("updates.file_rejected");
            } finally {
                this.busyApply = false;
            }
        },
        async applyPending() {
            this.busyApply = true;
            try {
                if (window.desktop && typeof window.desktop.applyUpdate === "function") {
                    await window.desktop.applyUpdate();
                }
            } catch (e) {
                this.errorText = this.errMsg(e) || this.$t("updates.apply_failed");
            } finally {
                this.busyApply = false;
            }
        },
        async showPendingInFolder() {
            const arts = (this.pending && this.pending.artifacts) || [];
            const a = arts[0];
            if (!a) return;
            const dir = (await DesktopUtils.pendingUpdateDir) ? DesktopUtils.pendingUpdateDir() : null;
            if (dir) {
                DesktopUtils.showPathInFolder(dir);
            } else if (a.file) {
                DesktopUtils.copyTextToClipboard(a.file).catch(() => {});
                this.notice = a.file;
            }
        },
        async discard() {
            this.busyApply = true;
            try {
                await discardUpdate();
                this.pending = null;
                this.checkResult = null;
            } catch (e) {
                this.errorText = this.errMsg(e) || this.$t("updates.apply_failed");
            } finally {
                this.busyApply = false;
                await this.refresh();
            }
        },
        fmtBytes(n) {
            n = Number(n) || 0;
            if (n >= 1024 * 1024) return (n / (1024 * 1024)).toFixed(1) + " MB";
            if (n >= 1024) return (n / 1024).toFixed(1) + " KB";
            return n + " B";
        },
        errMsg(e) {
            const d = e && e.response && e.response.data;
            if (d && typeof d === "object" && d.error) return d.error;
            if (d && typeof d === "string") return d;
            return (e && e.message) || "";
        },
    },
};
</script>
