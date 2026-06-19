<!-- SPDX-License-Identifier: 0BSD AND MIT -->

<template>
    <div class="flex flex-col flex-1 overflow-hidden min-w-0 bg-slate-50 dark:bg-zinc-950">
        <ToolsPageHeader
            icon="shield-alert"
            :title="$t('tools.message_blocklist.title')"
            :description="$t('tools.message_blocklist.description')"
            accent="rose"
        />
        <div class="flex-1 overflow-y-auto w-full pb-[max(1rem,env(safe-area-inset-bottom))]">
            <div class="p-3 sm:p-4 md:p-6 max-w-4xl mx-auto w-full space-y-4 min-w-0">
                <div
                    class="rounded-xl border border-amber-200 dark:border-amber-900/50 bg-amber-50 dark:bg-amber-950/30 px-4 py-3 flex items-start gap-3"
                >
                    <MaterialDesignIcon
                        icon-name="alert-circle-outline"
                        class="size-5 text-amber-600 dark:text-amber-400 shrink-0 mt-0.5"
                    />
                    <div class="min-w-0">
                        <div class="text-sm font-semibold text-amber-900 dark:text-amber-200">
                            {{ $t("tools.message_blocklist.beta_notice_title") }}
                        </div>
                        <p class="text-xs text-amber-800/90 dark:text-amber-300/90 mt-1 leading-relaxed">
                            {{ $t("tools.message_blocklist.beta_notice_body") }}
                        </p>
                    </div>
                </div>

                <div
                    class="rounded-xl border border-gray-200 dark:border-zinc-800 bg-white dark:bg-zinc-950 p-4 space-y-4"
                >
                    <label class="inline-flex items-center gap-3 cursor-pointer">
                        <input
                            v-model="enabled"
                            type="checkbox"
                            class="rounded-sm border-gray-300 size-4"
                            @change="onEnabledChange"
                        />
                        <span class="text-sm font-medium text-gray-900 dark:text-white">
                            {{ $t("tools.message_blocklist.enable_label") }}
                        </span>
                    </label>
                    <p class="text-xs text-gray-500 dark:text-gray-400">
                        {{ $t("tools.message_blocklist.enable_hint") }}
                    </p>
                </div>

                <div
                    class="rounded-xl border border-gray-200 dark:border-zinc-800 bg-white dark:bg-zinc-950 p-4 space-y-4"
                    :class="enabled ? '' : 'opacity-60'"
                >
                    <div class="flex flex-wrap items-center justify-between gap-2">
                        <h2 class="text-base font-semibold text-gray-900 dark:text-white">
                            {{ $t("tools.message_blocklist.entries_heading") }}
                        </h2>
                        <div class="flex flex-wrap items-center gap-2">
                            <button
                                type="button"
                                class="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-sm font-medium border border-gray-200 dark:border-zinc-700 text-gray-700 dark:text-gray-200 hover:bg-gray-50 dark:hover:bg-zinc-900 transition-colors"
                                @click="exportList"
                            >
                                <MaterialDesignIcon icon-name="export" class="size-4" />
                                {{ $t("tools.message_blocklist.export") }}
                            </button>
                            <button
                                type="button"
                                class="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-sm font-medium border border-gray-200 dark:border-zinc-700 text-gray-700 dark:text-gray-200 hover:bg-gray-50 dark:hover:bg-zinc-900 transition-colors"
                                @click="triggerImport"
                            >
                                <MaterialDesignIcon icon-name="import" class="size-4" />
                                {{ $t("tools.message_blocklist.import") }}
                            </button>
                            <input
                                ref="importFileInput"
                                type="file"
                                accept=".json,application/json"
                                class="hidden"
                                @change="onImportFile"
                            />
                            <button
                                type="button"
                                class="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-sm font-medium bg-rose-600 text-white hover:bg-rose-700 transition-colors"
                                @click="addEntry"
                            >
                                <MaterialDesignIcon icon-name="plus" class="size-4" />
                                {{ $t("tools.message_blocklist.add_entry") }}
                            </button>
                        </div>
                    </div>

                    <div class="grid grid-cols-1 sm:grid-cols-2 gap-3">
                        <div>
                            <label
                                class="block text-[10px] font-bold text-gray-400 dark:text-zinc-500 uppercase tracking-widest mb-1"
                                >{{ $t("tools.message_blocklist.scope_label") }}</label
                            >
                            <select
                                v-model="blocklist.scope"
                                class="w-full px-3 py-2 rounded-lg border border-gray-200 dark:border-zinc-700 bg-white dark:bg-zinc-900 text-sm text-gray-900 dark:text-white"
                            >
                                <option value="everyone">
                                    {{ $t("tools.message_blocklist.scope_everyone") }}
                                </option>
                                <option value="contacts">
                                    {{ $t("tools.message_blocklist.scope_contacts") }}
                                </option>
                                <option value="non_contacts">
                                    {{ $t("tools.message_blocklist.scope_non_contacts") }}
                                </option>
                            </select>
                        </div>
                        <div class="space-y-2">
                            <div
                                class="text-[10px] font-bold text-gray-400 dark:text-zinc-500 uppercase tracking-widest"
                            >
                                {{ $t("tools.message_blocklist.match_in_label") }}
                            </div>
                            <label class="inline-flex items-center gap-2 text-sm text-gray-700 dark:text-gray-200">
                                <input
                                    v-model="blocklist.match_message"
                                    type="checkbox"
                                    class="rounded-sm border-gray-300"
                                />
                                {{ $t("tools.message_blocklist.match_message") }}
                            </label>
                            <label class="inline-flex items-center gap-2 text-sm text-gray-700 dark:text-gray-200">
                                <input
                                    v-model="blocklist.match_peer_fields"
                                    type="checkbox"
                                    class="rounded-sm border-gray-300"
                                />
                                {{ $t("tools.message_blocklist.match_peer_fields") }}
                            </label>
                        </div>
                    </div>

                    <div
                        v-if="blocklist.entries.length === 0"
                        class="text-sm text-gray-500 dark:text-gray-400 py-6 text-center"
                    >
                        {{ $t("tools.message_blocklist.empty_entries") }}
                    </div>

                    <div v-else class="space-y-3">
                        <div
                            v-for="(entry, index) in blocklist.entries"
                            :key="entry.id"
                            class="rounded-lg border border-gray-200 dark:border-zinc-800 p-3 space-y-3 bg-gray-50/80 dark:bg-zinc-900/40"
                        >
                            <div class="flex flex-wrap items-center justify-between gap-2">
                                <label class="inline-flex items-center gap-2 text-sm text-gray-700 dark:text-gray-200">
                                    <input v-model="entry.enabled" type="checkbox" class="rounded-sm border-gray-300" />
                                    {{ $t("tools.message_blocklist.entry_enabled") }}
                                </label>
                                <div class="flex items-center gap-1">
                                    <button
                                        type="button"
                                        class="p-1.5 rounded-lg text-red-600 hover:bg-red-50 dark:hover:bg-red-950/40"
                                        :title="$t('tools.message_blocklist.remove_entry')"
                                        @click="removeEntry(index)"
                                    >
                                        <MaterialDesignIcon icon-name="delete-outline" class="size-5" />
                                    </button>
                                </div>
                            </div>
                            <div class="grid grid-cols-1 sm:grid-cols-[1fr_auto] gap-2">
                                <input
                                    v-model="entry.text"
                                    type="text"
                                    class="w-full px-3 py-2 rounded-lg border border-gray-200 dark:border-zinc-700 bg-white dark:bg-zinc-900 text-sm text-gray-900 dark:text-white font-mono"
                                    :placeholder="$t('tools.message_blocklist.entry_placeholder')"
                                />
                                <select
                                    v-model="entry.match_mode"
                                    class="px-3 py-2 rounded-lg border border-gray-200 dark:border-zinc-700 bg-white dark:bg-zinc-900 text-sm text-gray-900 dark:text-white"
                                >
                                    <option value="substring">
                                        {{ $t("tools.message_blocklist.match_mode_substring") }}
                                    </option>
                                    <option value="regex">
                                        {{ $t("tools.message_blocklist.match_mode_regex") }}
                                    </option>
                                </select>
                            </div>
                        </div>
                    </div>

                    <div class="flex flex-wrap items-center gap-2 pt-2">
                        <button
                            type="button"
                            class="inline-flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-medium bg-rose-600 text-white hover:bg-rose-700 disabled:opacity-50 transition-colors"
                            :disabled="isSaving"
                            @click="save"
                        >
                            <MaterialDesignIcon icon-name="content-save-outline" class="size-4" />
                            <span v-if="isSaving">{{ $t("tools.message_blocklist.saving") }}</span>
                            <span v-else>{{ $t("tools.message_blocklist.save") }}</span>
                        </button>
                        <button
                            type="button"
                            class="inline-flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-medium border border-gray-200 dark:border-zinc-700 text-gray-700 dark:text-gray-200 hover:bg-gray-50 dark:hover:bg-zinc-900 transition-colors"
                            @click="reload"
                        >
                            <MaterialDesignIcon icon-name="refresh" class="size-4" />
                            {{ $t("tools.message_blocklist.revert") }}
                        </button>
                    </div>
                </div>
            </div>
        </div>
    </div>
</template>

<script>
import MaterialDesignIcon from "../MaterialDesignIcon.vue";
import ToolsPageHeader from "./ToolsPageHeader.vue";
import ToastUtils from "../../js/ToastUtils";
import DownloadUtils from "../../js/DownloadUtils";
import DialogUtils from "../../js/DialogUtils";

function newEntryId() {
    return Math.random().toString(16).slice(2, 18);
}

export default {
    name: "MessageBlocklistPage",
    components: {
        MaterialDesignIcon,
        ToolsPageHeader,
    },
    data() {
        return {
            enabled: false,
            blocklist: {
                scope: "non_contacts",
                match_peer_fields: false,
                match_message: true,
                entries: [],
            },
            isSaving: false,
        };
    },
    async mounted() {
        await this.reload();
    },
    methods: {
        mapFromApi(raw) {
            const scope = raw.scope === "contacts" || raw.scope === "non_contacts" ? raw.scope : "everyone";
            const match_peer_fields = !!raw.match_peer_fields;
            const match_message = raw.match_message !== false;
            const entries = Array.isArray(raw.entries)
                ? raw.entries.map((e) => ({
                      id: e.id || newEntryId(),
                      enabled: e.enabled !== false,
                      text: e.text || "",
                      match_mode: e.match_mode === "regex" ? "regex" : "substring",
                  }))
                : [];
            return {
                scope,
                match_peer_fields,
                match_message: match_peer_fields || match_message ? match_message : true,
                entries,
            };
        },
        normalizeForSave() {
            const match_peer_fields = !!this.blocklist.match_peer_fields;
            const match_message = !!this.blocklist.match_message;
            const targets_ok = match_peer_fields || match_message;
            return {
                scope:
                    this.blocklist.scope === "contacts" || this.blocklist.scope === "non_contacts"
                        ? this.blocklist.scope
                        : "everyone",
                match_peer_fields: targets_ok ? match_peer_fields : false,
                match_message: targets_ok ? match_message : true,
                entries: (this.blocklist.entries || []).map((e) => ({
                    id: e.id,
                    enabled: !!e.enabled,
                    text: String(e.text || "").trim(),
                    match_mode: e.match_mode === "regex" ? "regex" : "substring",
                })),
            };
        },
        addEntry() {
            this.blocklist.entries.push({
                id: newEntryId(),
                enabled: true,
                text: "",
                match_mode: "substring",
            });
        },
        removeEntry(index) {
            this.blocklist.entries.splice(index, 1);
        },
        async reload() {
            try {
                const res = await window.api.get("/api/v1/lxmf/message-blocklist");
                this.enabled = !!res.data.enabled;
                this.blocklist = this.mapFromApi(res.data.blocklist || {});
            } catch (e) {
                console.error(e);
                ToastUtils.error(this.$t("tools.message_blocklist.load_failed"));
            }
        },
        async save() {
            this.isSaving = true;
            try {
                const payload = {
                    enabled: this.enabled,
                    blocklist: this.normalizeForSave(),
                };
                const res = await window.api.put("/api/v1/lxmf/message-blocklist", payload);
                this.enabled = !!res.data.enabled;
                this.blocklist = this.mapFromApi(res.data.blocklist || {});
                ToastUtils.success(this.$t("tools.message_blocklist.saved"));
            } catch (e) {
                const msg =
                    (e.response && e.response.data && e.response.data.message) ||
                    e.message ||
                    this.$t("tools.message_blocklist.save_failed");
                ToastUtils.error(msg);
            } finally {
                this.isSaving = false;
            }
        },
        async onEnabledChange() {
            try {
                await window.api.put("/api/v1/lxmf/message-blocklist", {
                    enabled: this.enabled,
                    blocklist: this.normalizeForSave(),
                });
                ToastUtils.success(
                    this.enabled
                        ? this.$t("tools.message_blocklist.enabled_toast")
                        : this.$t("tools.message_blocklist.disabled_toast")
                );
            } catch {
                this.enabled = !this.enabled;
                ToastUtils.error(this.$t("tools.message_blocklist.save_failed"));
            }
        },
        async exportList() {
            try {
                const res = await window.api.get("/api/v1/lxmf/message-blocklist/export");
                const blob = new Blob([JSON.stringify(res.data, null, 2)], {
                    type: "application/json",
                });
                await DownloadUtils.downloadFile("meshchatx_message_blocklist.json", blob);
                ToastUtils.success(this.$t("tools.message_blocklist.exported"));
            } catch (e) {
                console.error(e);
                ToastUtils.error(this.$t("tools.message_blocklist.export_failed"));
            }
        },
        triggerImport() {
            this.$refs.importFileInput?.click();
        },
        async onImportFile(event) {
            const file = event.target.files && event.target.files[0];
            event.target.value = "";
            if (!file) {
                return;
            }
            const merge = await DialogUtils.confirm(this.$t("tools.message_blocklist.import_merge_confirm"));
            try {
                const text = await file.text();
                const document = JSON.parse(text);
                const res = await window.api.post("/api/v1/lxmf/message-blocklist/import", {
                    document,
                    merge,
                });
                this.blocklist = this.mapFromApi(res.data.blocklist || {});
                ToastUtils.success(
                    merge
                        ? this.$t("tools.message_blocklist.imported_merge")
                        : this.$t("tools.message_blocklist.imported_replace")
                );
            } catch (e) {
                const msg =
                    (e.response && e.response.data && e.response.data.message) ||
                    e.message ||
                    this.$t("tools.message_blocklist.import_failed");
                ToastUtils.error(msg);
            }
        },
    },
};
</script>
