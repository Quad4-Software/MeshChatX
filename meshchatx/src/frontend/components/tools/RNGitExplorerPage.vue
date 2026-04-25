<!-- SPDX-License-Identifier: 0BSD -->

<template>
    <div class="flex flex-col flex-1 h-full min-w-0 overflow-hidden bg-slate-50 dark:bg-zinc-950">
        <div class="bg-slate-50 dark:bg-zinc-950 border-b border-gray-200 dark:border-zinc-800 shadow-sm z-10">
            <div class="px-4 py-3 md:px-6 md:py-4 flex flex-wrap items-center justify-between gap-3 min-w-0">
                <div class="flex items-center gap-3 min-w-0">
                    <div class="p-2 bg-teal-100 dark:bg-teal-900/30 rounded-xl shrink-0">
                        <MaterialDesignIcon
                            icon-name="source-branch"
                            class="size-5 md:size-6 text-teal-600 dark:text-teal-300"
                        />
                    </div>
                    <div class="min-w-0">
                        <h1 class="text-lg md:text-xl font-bold text-gray-900 dark:text-white truncate">
                            {{ $t("tools.rngit_explorer.title") }}
                        </h1>
                        <p class="text-[10px] md:text-xs text-gray-500 dark:text-gray-400 truncate">
                            {{ $t("tools.rngit_explorer.description") }}
                        </p>
                    </div>
                </div>
                <RouterLink
                    to="/tools"
                    class="inline-flex items-center gap-2 text-sm text-teal-600 dark:text-teal-300 hover:underline shrink-0"
                >
                    <MaterialDesignIcon icon-name="arrow-left" class="size-4" />
                    {{ $t("rngit_explorer.back_tools") }}
                </RouterLink>
            </div>
        </div>

        <div class="flex-1 overflow-y-auto min-w-0">
            <div class="p-3 sm:p-4 md:p-6 max-w-5xl mx-auto space-y-4 pb-[max(1rem,env(safe-area-inset-bottom))]">
                <div
                    class="rounded-lg border border-gray-200 dark:border-zinc-800 bg-white dark:bg-zinc-950 p-4 space-y-2"
                >
                    <div class="flex flex-wrap items-center justify-between gap-2">
                        <h2 class="text-sm font-semibold text-gray-900 dark:text-white">
                            {{ $t("rngit_explorer.heard_heading") }}
                        </h2>
                        <button
                            type="button"
                            class="text-xs text-teal-600 dark:text-teal-400 hover:underline"
                            @click="loadHeardAnnounces"
                        >
                            {{ $t("rngit_explorer.refresh_heard") }}
                        </button>
                    </div>
                    <p class="text-xs text-gray-500 dark:text-zinc-500">
                        {{ $t("rngit_explorer.heard_hint") }}
                    </p>
                    <div v-if="heardLoading" class="text-xs text-gray-500 py-2">{{ $t("common.loading") }}</div>
                    <ul
                        v-else-if="heardAnnounces.length"
                        class="max-h-48 overflow-y-auto divide-y divide-gray-100 dark:divide-zinc-800 rounded-lg border border-gray-100 dark:border-zinc-800"
                    >
                        <li
                            v-for="h in heardAnnounces"
                            :key="h.destination_hash"
                            class="px-3 py-2 cursor-pointer hover:bg-gray-50 dark:hover:bg-zinc-900/80 text-sm"
                            :class="pickedHeardHash === h.destination_hash ? 'bg-teal-50/80 dark:bg-teal-950/30' : ''"
                            @click="applyHeardAnnounce(h)"
                        >
                            <div class="font-medium text-gray-900 dark:text-white truncate">
                                {{ heardNodeTitle(h) }}
                            </div>
                            <div class="font-mono text-[11px] text-gray-500 dark:text-zinc-400 truncate">
                                {{ h.destination_hash }}
                            </div>
                            <div class="text-[10px] text-gray-400 dark:text-zinc-500">
                                {{ $t("rngit_explorer.hops_label", { n: h.hops != null ? h.hops : "—" }) }}
                            </div>
                        </li>
                    </ul>
                    <p v-else class="text-xs text-gray-500 dark:text-zinc-500 py-1">
                        {{ $t("rngit_explorer.heard_empty") }}
                    </p>
                </div>

                <div
                    class="rounded-lg border border-gray-200 dark:border-zinc-800 bg-white dark:bg-zinc-950 p-4 space-y-3"
                >
                    <p class="text-xs text-gray-600 dark:text-zinc-400 leading-relaxed">
                        {{ $t("rngit_explorer.intro") }}
                    </p>
                    <div class="grid sm:grid-cols-2 gap-3">
                        <div>
                            <label class="glass-label">{{ $t("rngit_explorer.destination_hash") }}</label>
                            <input
                                v-model="destinationHash"
                                type="text"
                                autocomplete="off"
                                class="w-full rounded-lg border border-gray-200 dark:border-zinc-700 bg-white dark:bg-zinc-900 px-2 py-2 text-sm font-mono text-gray-900 dark:text-white"
                                :disabled="busy"
                            />
                        </div>
                        <div>
                            <label class="glass-label">{{ $t("rngit_explorer.group_name") }}</label>
                            <input
                                v-model="groupName"
                                type="text"
                                autocomplete="off"
                                class="w-full rounded-lg border border-gray-200 dark:border-zinc-700 bg-white dark:bg-zinc-900 px-2 py-2 text-sm font-mono text-gray-900 dark:text-white"
                                :disabled="busy"
                            />
                        </div>
                    </div>
                    <div>
                        <label class="glass-label">{{ $t("rngit_explorer.repo_names_label") }}</label>
                        <textarea
                            v-model="repoNamesText"
                            rows="6"
                            class="w-full rounded-lg border border-gray-200 dark:border-zinc-700 bg-white dark:bg-zinc-900 px-2 py-2 text-sm font-mono text-gray-900 dark:text-white"
                            :disabled="busy"
                            :placeholder="$t('rngit_explorer.repo_names_placeholder')"
                        />
                    </div>
                    <div class="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between sm:gap-4">
                        <label
                            class="inline-flex items-start gap-2 text-xs text-gray-600 dark:text-zinc-400 max-w-prose"
                        >
                            <input
                                v-model="forPush"
                                type="checkbox"
                                class="rounded border-gray-300 shrink-0 mt-0.5"
                                :disabled="busy"
                            />
                            <span>{{ $t("rngit_explorer.for_push") }}</span>
                        </label>
                        <button
                            type="button"
                            class="inline-flex items-center justify-center gap-2 px-4 py-2 rounded-lg bg-teal-600 hover:bg-teal-500 text-white text-sm font-medium disabled:opacity-50 shrink-0 self-start sm:self-auto"
                            :disabled="busy || !canProbe"
                            @click="runProbe"
                        >
                            <MaterialDesignIcon v-if="!busy" icon-name="radar" class="size-5" />
                            <MaterialDesignIcon v-else icon-name="loading" class="size-5 animate-spin" />
                            {{ $t("rngit_explorer.probe") }}
                        </button>
                    </div>
                </div>

                <div
                    v-if="results.length"
                    class="rounded-lg border border-gray-200 dark:border-zinc-800 overflow-hidden"
                >
                    <div
                        class="px-3 py-2 border-b border-gray-100 dark:border-zinc-800 text-xs font-semibold text-gray-600 dark:text-zinc-400"
                    >
                        {{ $t("rngit_explorer.results") }}
                    </div>
                    <ul class="divide-y divide-gray-100 dark:divide-zinc-800">
                        <li
                            v-for="row in results"
                            :key="row.repository"
                            class="px-3 py-2.5 cursor-pointer transition-colors text-sm"
                            :class="
                                selected && selected.repository === row.repository
                                    ? 'bg-teal-50 dark:bg-teal-950/40'
                                    : 'hover:bg-gray-50 dark:hover:bg-zinc-900/80'
                            "
                            @click="selectRow(row)"
                        >
                            <div class="flex items-center justify-between gap-2 min-w-0">
                                <span class="font-mono font-medium text-gray-900 dark:text-white truncate">{{
                                    row.repository
                                }}</span>
                                <span
                                    class="shrink-0 text-xs font-semibold uppercase"
                                    :class="
                                        row.reachable
                                            ? 'text-emerald-600 dark:text-emerald-400'
                                            : 'text-gray-400 dark:text-zinc-500'
                                    "
                                >
                                    {{
                                        row.reachable
                                            ? $t("rngit_explorer.reachable")
                                            : $t("rngit_explorer.unreachable")
                                    }}
                                </span>
                            </div>
                            <div
                                v-if="!row.reachable && row.error"
                                class="text-xs text-red-600 dark:text-red-400 mt-1 font-mono truncate"
                            >
                                {{ row.error }}
                            </div>
                        </li>
                    </ul>
                </div>

                <div
                    v-if="selected"
                    class="rounded-lg border border-gray-200 dark:border-zinc-800 bg-white dark:bg-zinc-950 p-4 space-y-3"
                >
                    <div class="text-sm font-semibold text-gray-900 dark:text-white">
                        {{ $t("rngit_explorer.detail_title", { repo: selected.repository }) }}
                    </div>
                    <div v-if="selected.reachable && selected.clone_command" class="space-y-2">
                        <div class="text-xs text-gray-500 dark:text-zinc-400">
                            {{ $t("rngit_explorer.clone_command") }}
                        </div>
                        <div class="flex flex-wrap gap-2 items-start">
                            <pre
                                class="flex-1 min-w-0 p-2 rounded bg-gray-100 dark:bg-zinc-900 text-xs font-mono text-gray-800 dark:text-zinc-200 overflow-x-auto whitespace-pre-wrap break-all"
                                >{{ selected.clone_command }}</pre
                            >
                            <button
                                type="button"
                                class="shrink-0 px-3 py-2 rounded-lg border border-gray-300 dark:border-zinc-600 text-sm text-gray-800 dark:text-zinc-200 hover:bg-gray-50 dark:hover:bg-zinc-800"
                                @click.stop="copyClone"
                            >
                                {{ $t("rngit_explorer.copy") }}
                            </button>
                        </div>
                    </div>
                    <div v-else class="text-xs text-gray-500 dark:text-zinc-400">
                        {{ $t("rngit_explorer.no_clone_hint") }}
                    </div>
                    <div v-if="selected.reachable && selected.refs_preview" class="space-y-1">
                        <div class="text-xs text-gray-500 dark:text-zinc-400">
                            {{ $t("rngit_explorer.refs_preview") }}
                            <span v-if="selected.refs_truncated" class="text-amber-600 dark:text-amber-400">{{
                                $t("rngit_explorer.truncated")
                            }}</span>
                        </div>
                        <pre
                            class="p-2 rounded bg-gray-100 dark:bg-zinc-900 text-xs font-mono text-gray-800 dark:text-zinc-200 max-h-48 overflow-y-auto whitespace-pre-wrap break-all"
                            >{{ selected.refs_preview }}</pre
                        >
                    </div>
                </div>
            </div>
        </div>
    </div>
</template>

<script>
import MaterialDesignIcon from "../MaterialDesignIcon.vue";
import ToastUtils from "../../js/ToastUtils";
import WebSocketConnection from "../../js/WebSocketConnection";

const RNGIT_ASPECT = "git.repositories";

export default {
    name: "RNGitExplorerPage",
    components: { MaterialDesignIcon },
    data() {
        return {
            heardAnnounces: [],
            heardLoading: false,
            pickedHeardHash: "",
            destinationHash: "",
            groupName: "",
            repoNamesText: "",
            forPush: false,
            busy: false,
            results: [],
            selected: null,
        };
    },
    computed: {
        normalizedDestinationHash() {
            return (this.destinationHash || "").trim().toLowerCase().replace(/:/g, "");
        },
        canProbe() {
            const h = this.normalizedDestinationHash;
            return (
                h.length === 32 &&
                /^[0-9a-f]+$/.test(h) &&
                (this.groupName || "").trim().length > 0 &&
                (this.repoNamesText || "").trim().length > 0
            );
        },
    },
    mounted() {
        WebSocketConnection.on("message", this.onSocketMessage);
        this.loadHeardAnnounces();
    },
    beforeUnmount() {
        WebSocketConnection.off("message", this.onSocketMessage);
    },
    methods: {
        onSocketMessage(event) {
            let json;
            try {
                json = JSON.parse(event.data);
            } catch {
                return;
            }
            if (json.type !== "announce" || !json.announce || json.announce.aspect !== RNGIT_ASPECT) {
                return;
            }
            const a = json.announce;
            const i = this.heardAnnounces.findIndex((x) => x.destination_hash === a.destination_hash);
            if (i >= 0) {
                this.heardAnnounces.splice(i, 1, a);
            } else {
                this.heardAnnounces.unshift(a);
            }
        },
        async loadHeardAnnounces() {
            this.heardLoading = true;
            try {
                const { data } = await window.api.get("/api/v1/announces", {
                    params: { aspect: RNGIT_ASPECT, limit: 200 },
                });
                this.heardAnnounces = Array.isArray(data.announces) ? data.announces : [];
            } catch (e) {
                ToastUtils.error(e.response?.data?.message || this.$t("rngit_explorer.heard_load_failed"));
            } finally {
                this.heardLoading = false;
            }
        },
        heardNodeTitle(h) {
            const custom = (h.custom_display_name || "").trim();
            if (custom) {
                return custom;
            }
            const d = (h.display_name || "").trim();
            if (d && d !== "Anonymous Peer") {
                return d;
            }
            const hex = (h.destination_hash || "").trim().toLowerCase();
            if (hex.length >= 8) {
                return this.$t("rngit_explorer.heard_title_short", { prefix: hex.slice(0, 8) });
            }
            return this.$t("rngit_explorer.unnamed_node");
        },
        applyHeardAnnounce(h) {
            this.pickedHeardHash = h.destination_hash || "";
            this.destinationHash = h.destination_hash || "";
        },
        selectRow(row) {
            this.selected = { ...row };
        },
        async copyClone() {
            if (!this.selected?.clone_command) {
                return;
            }
            try {
                await navigator.clipboard.writeText(this.selected.clone_command);
                ToastUtils.success(this.$t("rngit_explorer.copied"));
            } catch {
                ToastUtils.error(this.$t("rngit_explorer.copy_failed"));
            }
        },
        async runProbe() {
            if (!this.canProbe) {
                return;
            }
            this.busy = true;
            this.results = [];
            this.selected = null;
            ToastUtils.loading(this.$t("rngit_explorer.probing"), 0, "rngit-explorer-probe");
            try {
                const { data } = await window.api.post("/api/v1/rngit-tool/probe", {
                    destination_hash: this.normalizedDestinationHash,
                    group_name: (this.groupName || "").trim(),
                    repository_names_text: this.repoNamesText,
                    for_push: this.forPush,
                });
                if (data.ok && Array.isArray(data.results)) {
                    this.results = data.results;
                    const firstOk = data.results.find((r) => r.reachable);
                    this.selected = firstOk ? { ...firstOk } : data.results[0] ? { ...data.results[0] } : null;
                    ToastUtils.success(this.$t("rngit_explorer.probe_done"));
                } else {
                    ToastUtils.error(data.error || this.$t("rngit_explorer.probe_failed"));
                }
            } catch (e) {
                const d = e.response?.data;
                ToastUtils.error(d?.error || d?.message || this.$t("rngit_explorer.probe_failed"));
            } finally {
                ToastUtils.dismiss("rngit-explorer-probe");
                this.busy = false;
            }
        },
    },
};
</script>
