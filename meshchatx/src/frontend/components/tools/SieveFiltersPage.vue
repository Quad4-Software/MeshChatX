<!-- SPDX-License-Identifier: 0BSD AND MIT -->

<template>
    <div class="flex flex-col flex-1 overflow-hidden min-w-0 bg-slate-50 dark:bg-zinc-950">
        <ToolsPageHeader
            icon="filter-variant"
            :title="$t('tools.sieve_filters.title')"
            :description="$t('tools.sieve_filters.description')"
            accent="violet"
        />
        <div class="flex-1 overflow-y-auto w-full pb-[max(1rem,env(safe-area-inset-bottom))]">
            <div class="p-3 sm:p-4 md:p-6 max-w-6xl mx-auto w-full space-y-4 min-w-0">
                <div class="grid grid-cols-1 xl:grid-cols-2 gap-4 items-start">
                    <div class="space-y-4 min-w-0 order-2 xl:order-1">
                        <div
                            class="rounded-xl border border-gray-200 dark:border-zinc-800 bg-white dark:bg-zinc-950 p-4 space-y-3"
                        >
                            <div class="flex items-center justify-between gap-2">
                                <h2 class="text-base font-semibold text-gray-900 dark:text-white">
                                    {{ $t("tools.sieve_filters.rules_heading") }}
                                </h2>
                                <button
                                    type="button"
                                    class="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-sm font-medium bg-violet-600 text-white hover:bg-violet-700 transition-colors"
                                    @click="addRule"
                                >
                                    <MaterialDesignIcon icon-name="plus" class="size-4" />
                                    {{ $t("tools.sieve_filters.add_rule") }}
                                </button>
                            </div>
                            <p class="text-xs text-gray-500 dark:text-gray-400">
                                {{ $t("tools.sieve_filters.order_hint") }}
                            </p>

                            <div
                                v-if="filters.length === 0"
                                class="text-sm text-gray-500 dark:text-gray-400 py-6 text-center"
                            >
                                {{ $t("tools.sieve_filters.empty_rules") }}
                            </div>

                            <div v-else class="space-y-3">
                                <div
                                    v-for="(rule, index) in filters"
                                    :key="rule.id"
                                    class="rounded-lg border border-gray-200 dark:border-zinc-800 p-3 space-y-3 bg-gray-50/80 dark:bg-zinc-900/40"
                                >
                                    <div class="flex flex-wrap items-center justify-between gap-2">
                                        <label
                                            class="inline-flex items-center gap-2 text-sm text-gray-700 dark:text-gray-200"
                                        >
                                            <input
                                                v-model="rule.enabled"
                                                type="checkbox"
                                                class="rounded-sm border-gray-300"
                                            />
                                            {{ $t("tools.sieve_filters.enabled") }}
                                        </label>
                                        <div class="flex items-center gap-1">
                                            <button
                                                type="button"
                                                class="p-1.5 rounded-lg text-gray-500 hover:bg-gray-200 dark:hover:bg-zinc-800"
                                                :title="$t('tools.sieve_filters.move_up')"
                                                :disabled="index === 0"
                                                @click="moveRule(index, -1)"
                                            >
                                                <MaterialDesignIcon icon-name="chevron-up" class="size-5" />
                                            </button>
                                            <button
                                                type="button"
                                                class="p-1.5 rounded-lg text-gray-500 hover:bg-gray-200 dark:hover:bg-zinc-800"
                                                :title="$t('tools.sieve_filters.move_down')"
                                                :disabled="index === filters.length - 1"
                                                @click="moveRule(index, 1)"
                                            >
                                                <MaterialDesignIcon icon-name="chevron-down" class="size-5" />
                                            </button>
                                            <button
                                                type="button"
                                                class="p-1.5 rounded-lg text-red-600 hover:bg-red-50 dark:hover:bg-red-950/40"
                                                :title="$t('tools.sieve_filters.remove_rule')"
                                                @click="removeRule(index)"
                                            >
                                                <MaterialDesignIcon icon-name="delete-outline" class="size-5" />
                                            </button>
                                        </div>
                                    </div>
                                    <div>
                                        <label
                                            class="block text-[10px] font-bold text-gray-400 dark:text-zinc-500 uppercase tracking-widest mb-1"
                                            >{{ $t("tools.sieve_filters.terms_label") }}</label
                                        >
                                        <textarea
                                            :value="termsText(rule)"
                                            rows="3"
                                            class="w-full px-3 py-2 rounded-lg border border-gray-200 dark:border-zinc-700 bg-white dark:bg-zinc-900 text-sm text-gray-900 dark:text-white font-mono"
                                            :placeholder="$t('tools.sieve_filters.terms_placeholder')"
                                            @input="onTermsInput(rule, $event)"
                                        />
                                    </div>
                                    <div>
                                        <label
                                            class="block text-[10px] font-bold text-gray-400 dark:text-zinc-500 uppercase tracking-widest mb-1"
                                            >{{ $t("tools.sieve_filters.scope_label") }}</label
                                        >
                                        <select
                                            v-model="rule.scope"
                                            class="w-full px-3 py-2 rounded-lg border border-gray-200 dark:border-zinc-700 bg-white dark:bg-zinc-900 text-sm text-gray-900 dark:text-white"
                                        >
                                            <option value="everyone">
                                                {{ $t("tools.sieve_filters.scope_everyone") }}
                                            </option>
                                            <option value="contacts">
                                                {{ $t("tools.sieve_filters.scope_contacts") }}
                                            </option>
                                            <option value="non_contacts">
                                                {{ $t("tools.sieve_filters.scope_non_contacts") }}
                                            </option>
                                        </select>
                                    </div>
                                    <div class="space-y-2">
                                        <div
                                            class="text-[10px] font-bold text-gray-400 dark:text-zinc-500 uppercase tracking-widest"
                                        >
                                            {{ $t("tools.sieve_filters.match_targets_label") }}
                                        </div>
                                        <label class="flex items-center gap-2 text-sm text-gray-700 dark:text-gray-200">
                                            <input
                                                v-model="rule.match_peer_fields"
                                                type="checkbox"
                                                class="rounded-sm border-gray-300"
                                                @change="onMatchTargetsChange(rule)"
                                            />
                                            {{ $t("tools.sieve_filters.match_peer_fields") }}
                                        </label>
                                        <label class="flex items-center gap-2 text-sm text-gray-700 dark:text-gray-200">
                                            <input
                                                v-model="rule.match_message"
                                                type="checkbox"
                                                class="rounded-sm border-gray-300"
                                                @change="onMatchTargetsChange(rule)"
                                            />
                                            {{ $t("tools.sieve_filters.match_message") }}
                                        </label>
                                        <p class="text-xs text-gray-500 dark:text-gray-400">
                                            {{ $t("tools.sieve_filters.match_targets_hint") }}
                                        </p>
                                    </div>
                                    <div>
                                        <label
                                            class="block text-[10px] font-bold text-gray-400 dark:text-zinc-500 uppercase tracking-widest mb-1"
                                            >{{ $t("tools.sieve_filters.match_mode_label") }}</label
                                        >
                                        <select
                                            v-model="rule.match_mode"
                                            class="w-full px-3 py-2 rounded-lg border border-gray-200 dark:border-zinc-700 bg-white dark:bg-zinc-900 text-sm text-gray-900 dark:text-white"
                                        >
                                            <option value="substring">
                                                {{ $t("tools.sieve_filters.match_mode_substring") }}
                                            </option>
                                            <option value="regex">
                                                {{ $t("tools.sieve_filters.match_mode_regex") }}
                                            </option>
                                        </select>
                                    </div>
                                    <div class="grid grid-cols-1 sm:grid-cols-2 gap-3">
                                        <div>
                                            <label
                                                class="block text-[10px] font-bold text-gray-400 dark:text-zinc-500 uppercase tracking-widest mb-1"
                                                >{{ $t("tools.sieve_filters.action_label") }}</label
                                            >
                                            <select
                                                v-model="rule.action"
                                                class="w-full px-3 py-2 rounded-lg border border-gray-200 dark:border-zinc-700 bg-white dark:bg-zinc-900 text-sm text-gray-900 dark:text-white"
                                                @change="onActionChange(rule)"
                                            >
                                                <option value="hide">
                                                    {{ $t("tools.sieve_filters.action_hide") }}
                                                </option>
                                                <option value="ignore">
                                                    {{ $t("tools.sieve_filters.action_ignore") }}
                                                </option>
                                                <option value="folder">
                                                    {{ $t("tools.sieve_filters.action_folder") }}
                                                </option>
                                                <option value="banish">
                                                    {{ $t("tools.sieve_filters.action_banish") }}
                                                </option>
                                            </select>
                                        </div>
                                        <div v-if="rule.action === 'folder'">
                                            <label
                                                class="block text-[10px] font-bold text-gray-400 dark:text-zinc-500 uppercase tracking-widest mb-1"
                                                >{{ $t("tools.sieve_filters.folder_label") }}</label
                                            >
                                            <select
                                                v-model.number="rule.folder_id"
                                                class="w-full px-3 py-2 rounded-lg border border-gray-200 dark:border-zinc-700 bg-white dark:bg-zinc-900 text-sm text-gray-900 dark:text-white"
                                            >
                                                <option v-for="f in folders" :key="f.id" :value="f.id">
                                                    {{ f.name }}
                                                </option>
                                            </select>
                                        </div>
                                    </div>
                                </div>
                            </div>

                            <div class="flex flex-wrap gap-2 pt-2">
                                <button
                                    type="button"
                                    class="inline-flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-medium bg-gray-900 text-white dark:bg-zinc-100 dark:text-zinc-900 hover:opacity-90"
                                    :disabled="isSaving"
                                    @click="save"
                                >
                                    <MaterialDesignIcon
                                        v-if="!isSaving"
                                        icon-name="content-save-outline"
                                        class="size-4"
                                    />
                                    <span v-if="isSaving">{{ $t("tools.sieve_filters.saving") }}</span>
                                    <span v-else>{{ $t("tools.sieve_filters.save") }}</span>
                                </button>
                                <button
                                    type="button"
                                    class="inline-flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-medium border border-gray-300 dark:border-zinc-600 text-gray-800 dark:text-gray-200 hover:bg-gray-100 dark:hover:bg-zinc-800"
                                    :disabled="isSaving"
                                    @click="reload"
                                >
                                    <MaterialDesignIcon icon-name="restore" class="size-4" />
                                    {{ $t("tools.sieve_filters.revert") }}
                                </button>
                            </div>
                        </div>
                    </div>

                    <div class="min-w-0 order-1 xl:order-2 space-y-2">
                        <h2 class="text-base font-semibold text-gray-900 dark:text-white px-1">
                            {{ $t("tools.sieve_filters.flow_heading") }}
                        </h2>
                        <SieveFlowNetwork :filters="filters" :folders="folders" :labels="flowLabels" />
                    </div>
                </div>
            </div>
        </div>
    </div>
</template>

<script>
import MaterialDesignIcon from "../MaterialDesignIcon.vue";
import SieveFlowNetwork from "./internal/SieveFlowNetwork.vue";
import ToastUtils from "../../js/ToastUtils";
import ToolsPageHeader from "./ToolsPageHeader.vue";

function newRuleId() {
    if (typeof crypto !== "undefined" && crypto.randomUUID) {
        return crypto.randomUUID();
    }
    return `r-${Date.now()}-${Math.random().toString(16).slice(2)}`;
}

export default {
    name: "SieveFiltersPage",
    components: {
        MaterialDesignIcon,
        SieveFlowNetwork,
        ToolsPageHeader,
    },
    data() {
        return {
            filters: [],
            folders: [],
            isSaving: false,
        };
    },
    computed: {
        flowLabels() {
            return {
                sourceNode: this.$t("tools.sieve_filters.flow_source"),
                sourceHint: this.$t("tools.sieve_filters.flow_source_hint"),
                rulePrefix: this.$t("tools.sieve_filters.flow_if"),
                hide: this.$t("tools.sieve_filters.flow_hide"),
                ignore: this.$t("tools.sieve_filters.action_ignore"),
                banish: this.$t("tools.sieve_filters.flow_banish"),
                folder: this.$t("tools.sieve_filters.flow_folder"),
                noRules: this.$t("tools.sieve_filters.flow_no_rules"),
                graphScopeEveryone: this.$t("tools.sieve_filters.graph_scope_everyone"),
                graphScopeContacts: this.$t("tools.sieve_filters.graph_scope_contacts"),
                graphScopeNonContacts: this.$t("tools.sieve_filters.graph_scope_non_contacts"),
                graphMatchPeer: this.$t("tools.sieve_filters.graph_match_peer"),
                graphMatchMessage: this.$t("tools.sieve_filters.graph_match_message"),
                graphMatchModeSubstring: this.$t("tools.sieve_filters.graph_match_mode_substring"),
                graphMatchModeRegex: this.$t("tools.sieve_filters.graph_match_mode_regex"),
            };
        },
    },
    mounted() {
        this.reload();
    },
    methods: {
        termsText(rule) {
            return (rule.terms || []).join("\n");
        },
        onTermsInput(rule, e) {
            const raw = (e.target && e.target.value) || "";
            rule.terms = raw
                .split(/[\n,]+/)
                .map((s) => s.trim())
                .filter(Boolean);
        },
        onActionChange(rule) {
            if (rule.action === "folder" && this.folders.length && (rule.folder_id == null || rule.folder_id === "")) {
                rule.folder_id = this.folders[0].id;
            }
            if (rule.action !== "folder") {
                rule.folder_id = null;
            }
        },
        onMatchTargetsChange(rule) {
            if (!rule.match_peer_fields && !rule.match_message) {
                rule.match_peer_fields = true;
            }
        },
        mapRuleFromApi(r) {
            let action = r.action || "ignore";
            if (action === "block") {
                action = "hide";
            }
            return {
                id: r.id || newRuleId(),
                enabled: r.enabled !== false,
                scope: r.scope === "contacts" || r.scope === "non_contacts" ? r.scope : "everyone",
                terms: Array.isArray(r.terms) ? [...r.terms] : [],
                action,
                folder_id: r.folder_id ?? null,
                match_peer_fields: r.match_peer_fields !== false,
                match_message: !!r.match_message,
                match_mode: r.match_mode === "regex" ? "regex" : "substring",
            };
        },
        addRule() {
            const base = {
                id: newRuleId(),
                enabled: true,
                scope: "everyone",
                terms: [],
                action: "ignore",
                folder_id: this.folders.length ? this.folders[0].id : null,
                match_peer_fields: true,
                match_message: false,
                match_mode: "substring",
            };
            this.filters.push(base);
        },
        removeRule(index) {
            this.filters.splice(index, 1);
        },
        moveRule(index, delta) {
            const j = index + delta;
            if (j < 0 || j >= this.filters.length) {
                return;
            }
            const copy = this.filters.slice();
            const t = copy[index];
            copy[index] = copy[j];
            copy[j] = t;
            this.filters = copy;
        },
        normalizeForSave() {
            return this.filters.map((r) => {
                const scope = r.scope === "contacts" || r.scope === "non_contacts" ? r.scope : "everyone";
                const match_peer_fields = r.match_peer_fields !== false;
                const match_message = !!r.match_message;
                const targets_ok = match_peer_fields || match_message;
                return {
                    id: r.id,
                    enabled: !!r.enabled,
                    scope,
                    terms: Array.isArray(r.terms) ? r.terms : [],
                    action: r.action === "block" ? "hide" : r.action,
                    folder_id: r.action === "folder" ? r.folder_id : null,
                    match_peer_fields: targets_ok ? match_peer_fields : true,
                    match_message: targets_ok ? match_message : false,
                    match_mode: r.match_mode === "regex" ? "regex" : "substring",
                };
            });
        },
        async reload() {
            try {
                const [fRes, foldersRes] = await Promise.all([
                    window.api.get("/api/v1/lxmf/sieve-filters"),
                    window.api.get("/api/v1/lxmf/folders"),
                ]);
                const raw = fRes.data.filters || [];
                this.filters = raw.map((r) => this.mapRuleFromApi(r));
                this.folders = foldersRes.data || [];
                this.onActionChangeForAll();
            } catch (e) {
                console.error(e);
                ToastUtils.error(this.$t("tools.sieve_filters.load_failed"));
            }
        },
        onActionChangeForAll() {
            this.filters.forEach((r) => this.onActionChange(r));
        },
        async save() {
            this.isSaving = true;
            try {
                const payload = { filters: this.normalizeForSave() };
                const res = await window.api.put("/api/v1/lxmf/sieve-filters", payload);
                this.filters = (res.data.filters || []).map((r) => this.mapRuleFromApi(r));
                ToastUtils.success(this.$t("tools.sieve_filters.saved"));
            } catch (e) {
                const msg =
                    (e.response && e.response.data && e.response.data.message) ||
                    e.message ||
                    this.$t("tools.sieve_filters.save_failed");
                ToastUtils.error(msg);
            } finally {
                this.isSaving = false;
            }
        },
    },
};
</script>
