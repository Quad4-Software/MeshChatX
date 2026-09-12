<!-- SPDX-License-Identifier: 0BSD -->

<template>
    <div class="flex-1 overflow-y-auto custom-scrollbar p-3 sm:p-4">
        <div class="mx-auto w-full max-w-3xl space-y-4">
            <div class="flex flex-wrap items-start justify-between gap-3">
                <div>
                    <h2 class="text-lg font-semibold">{{ $t("relay_chat.bots_title") }}</h2>
                    <p class="text-sm text-sem-fg-muted">{{ $t("relay_chat.bots_subtitle") }}</p>
                </div>
                <div class="flex items-center gap-2">
                    <button
                        type="button"
                        :class="btnSecondary"
                        :title="$t('relay_chat.bots_manage_all')"
                        @click="$router.push({ name: 'bots' })"
                    >
                        <MaterialDesignIcon icon-name="cog" class="size-4" />
                        {{ $t("relay_chat.bots_manage_all") }}
                    </button>
                    <button type="button" :class="btnPrimary" @click="showCreate = !showCreate">
                        <MaterialDesignIcon icon-name="plus" class="size-4" />
                        {{ $t("relay_chat.bots_new") }}
                    </button>
                </div>
            </div>

            <!-- create form -->
            <div v-if="showCreate" class="rounded-xl border border-sem-border bg-sem-canvas p-4 space-y-3">
                <div class="grid gap-3 sm:grid-cols-2">
                    <label class="flex flex-col gap-1">
                        <span class="text-xs font-medium text-sem-fg-muted">{{ $t("bots.bot_name") }}</span>
                        <input v-model.trim="form.name" type="text" class="input-field" maxlength="48" />
                    </label>
                    <label class="flex flex-col gap-1">
                        <span class="text-xs font-medium text-sem-fg-muted">{{ $t("relay_chat.bots_form_nick") }}</span>
                        <input v-model.trim="form.nick" type="text" class="input-field" maxlength="32" />
                    </label>
                    <label class="flex flex-col gap-1 sm:col-span-2">
                        <span class="text-xs font-medium text-sem-fg-muted">{{ $t("relay_chat.bots_form_hub") }}</span>
                        <div class="flex gap-2">
                            <select v-model="form.hubPick" class="input-field min-w-0 flex-1">
                                <option value="">{{ $t("relay_chat.bots_form_hub_custom") }}</option>
                                <option v-for="h in knownHubs" :key="h.hash" :value="h.hash">
                                    {{ h.name || $t("relay_chat.bots_form_hub_custom") }} ({{ formatHash(h.hash) }})
                                </option>
                            </select>
                            <input
                                v-if="!form.hubPick"
                                v-model.trim="form.hubCustom"
                                type="text"
                                class="input-field min-w-0 flex-1 font-mono"
                                maxlength="64"
                                placeholder="<hub destination hash>"
                            />
                        </div>
                    </label>
                    <label class="flex flex-col gap-1 sm:col-span-2">
                        <span class="text-xs font-medium text-sem-fg-muted">{{
                            $t("relay_chat.bots_form_rooms")
                        }}</span>
                        <input
                            v-model.trim="form.roomsCsv"
                            type="text"
                            class="input-field"
                            placeholder="#general, #dev"
                        />
                        <span class="text-xs text-sem-fg-muted">{{ $t("relay_chat.bots_form_rooms_hint") }}</span>
                    </label>
                    <label class="flex items-center justify-between gap-2 sm:col-span-2">
                        <span class="text-sm">{{ $t("relay_chat.bots_form_mention_only") }}</span>
                        <Toggle v-model="form.mentionOnly" />
                    </label>
                    <label class="flex flex-col gap-1">
                        <span class="text-xs font-medium text-sem-fg-muted">{{
                            $t("relay_chat.bots_form_prefix")
                        }}</span>
                        <input v-model.trim="form.prefix" type="text" class="input-field" maxlength="4" />
                    </label>
                    <label class="flex flex-col gap-1">
                        <span class="text-xs font-medium text-sem-fg-muted">{{
                            $t("relay_chat.bots_form_cooldown")
                        }}</span>
                        <input v-model.number="form.rateSeconds" type="number" min="0" max="3600" class="input-field" />
                    </label>
                </div>
                <div class="flex items-center justify-end gap-2">
                    <button type="button" :class="btnSecondary" @click="resetCreate">
                        {{ $t("bots.cancel") }}
                    </button>
                    <button
                        type="button"
                        :class="btnPrimary"
                        :disabled="creating || !form.name || !effectiveHubHash"
                        @click="createBot"
                    >
                        <MaterialDesignIcon v-if="creating" icon-name="loading" class="size-4 animate-spin" />
                        {{ $t("relay_chat.bots_create") }}
                    </button>
                </div>
            </div>

            <!-- bot list -->
            <div v-if="botsLoading" class="flex justify-center py-8">
                <MaterialDesignIcon icon-name="loading" class="size-6 animate-spin text-sem-fg-muted" />
            </div>
            <div
                v-else-if="rrcBots.length === 0"
                class="flex flex-col items-center gap-2 rounded-xl border border-sem-border bg-sem-canvas p-8 text-center text-sm text-sem-fg-muted"
            >
                <MaterialDesignIcon icon-name="robot-off" class="size-10 opacity-40" />
                {{ $t("relay_chat.bots_none") }}
            </div>
            <div
                v-for="bot in rrcBots"
                v-else-if="rrcBots.length > 0"
                :key="bot.id"
                class="rounded-xl border border-sem-border bg-sem-canvas p-4 space-y-3"
            >
                <div class="flex flex-wrap items-start justify-between gap-3">
                    <div class="min-w-0 flex-1">
                        <div class="flex items-center gap-2">
                            <span
                                class="size-2 shrink-0 rounded-full"
                                :class="bot.running ? 'bg-sem-success' : 'bg-sem-fg-muted'"
                            ></span>
                            <span class="font-semibold truncate">{{ bot.name }}</span>
                            <span v-if="bot.rrc?.nick" class="text-xs text-sem-fg-muted">@{{ bot.rrc.nick }}</span>
                        </div>
                        <div class="mt-1 space-y-0.5 text-xs text-sem-fg-muted">
                            <div v-if="bot.rrc?.hub" class="font-mono truncate">
                                {{ $t("relay_chat.bots_hub") }}: {{ formatHash(bot.rrc.hub) }}
                            </div>
                            <div v-if="bot.rrc?.rooms?.length">
                                {{ $t("relay_chat.bots_rooms") }}:
                                {{ bot.rrc.rooms.map((r) => "#" + r.replace(/^#/, "")).join(", ") }}
                            </div>
                            <div v-if="bot.last_error" class="text-sem-danger break-all">{{ bot.last_error }}</div>
                        </div>
                    </div>
                    <div class="flex shrink-0 items-center gap-1.5">
                        <button
                            v-if="!bot.running"
                            type="button"
                            :class="[btnSecondary, 'px-2.5! py-1.5! text-xs!']"
                            @click="startBot(bot)"
                        >
                            <MaterialDesignIcon icon-name="play" class="size-4" />
                            {{ $t("relay_chat.host_start") }}
                        </button>
                        <button
                            v-else
                            type="button"
                            :class="[btnSecondary, 'px-2.5! py-1.5! text-xs!']"
                            @click="stopBot(bot)"
                        >
                            <MaterialDesignIcon icon-name="stop" class="size-4" />
                            {{ $t("relay_chat.host_stop") }}
                        </button>
                        <button
                            type="button"
                            :class="btnIcon"
                            :title="$t('bots.delete_bot')"
                            @click="confirmDelete(bot)"
                        >
                            <MaterialDesignIcon icon-name="delete" class="size-4" />
                        </button>
                    </div>
                </div>
            </div>
        </div>
    </div>
</template>

<script>
import MaterialDesignIcon from "../MaterialDesignIcon.vue";
import Toggle from "../forms/Toggle.vue";
import DialogUtils from "../../js/DialogUtils";
import ToastUtils from "../../js/ToastUtils";
import { apiPath } from "../../js/constants.js";

const BTN_PRIMARY =
    "inline-flex items-center justify-center gap-1.5 rounded-lg bg-sem-action-primary px-3 py-2 text-sm font-semibold text-white transition hover:bg-sem-action-primary-hover disabled:opacity-50";
const BTN_SECONDARY =
    "inline-flex items-center justify-center gap-1.5 rounded-lg border border-sem-border bg-sem-surface-raised px-3 py-2 text-sm font-medium text-sem-fg transition hover:bg-sem-surface-muted disabled:opacity-50";
const BTN_ICON =
    "inline-flex items-center justify-center rounded-lg p-2 text-sem-fg-muted transition hover:bg-sem-surface-muted hover:text-sem-fg";

const DEFAULT_FORM = () => ({
    name: "",
    nick: "",
    hubPick: "",
    hubCustom: "",
    roomsCsv: "#general",
    mentionOnly: true,
    prefix: "!",
    rateSeconds: 8,
});

export default {
    name: "RelayBotsPage",
    components: { MaterialDesignIcon, Toggle },
    props: {
        knownHubs: { type: Array, default: () => [] },
    },
    data() {
        return {
            btnPrimary: BTN_PRIMARY,
            btnSecondary: BTN_SECONDARY,
            btnIcon: BTN_ICON,
            botsLoading: false,
            bots: [],
            creating: false,
            showCreate: false,
            form: DEFAULT_FORM(),
            pollTimer: null,
        };
    },
    computed: {
        rrcBots() {
            return this.bots.filter((b) => (b.template_id || b.template) === "rrc");
        },
        effectiveHubHash() {
            return this.form.hubPick || this.form.hubCustom;
        },
    },
    mounted() {
        this.fetchBots();
        this.pollTimer = setInterval(() => this.fetchBots({ quiet: true }), 5000);
    },
    beforeUnmount() {
        if (this.pollTimer) clearInterval(this.pollTimer);
    },
    methods: {
        formatHash(h) {
            const s = String(h || "");
            return s.length > 20 ? `${s.slice(0, 10)}…${s.slice(-8)}` : s;
        },
        parseRooms(csv) {
            return String(csv || "")
                .split(",")
                .map((r) => r.trim().replace(/^#+/, ""))
                .filter(Boolean);
        },
        async fetchBots({ quiet = false } = {}) {
            if (!quiet) this.botsLoading = true;
            try {
                const res = await window.api.get(apiPath("/bots/status"));
                this.bots = res?.data?.status?.bots || [];
            } catch {
                if (!quiet) this.bots = [];
            } finally {
                this.botsLoading = false;
            }
        },
        resetCreate() {
            this.form = DEFAULT_FORM();
            this.showCreate = false;
        },
        async createBot() {
            this.creating = true;
            try {
                await window.api.post(apiPath("/bots/start"), {
                    template_id: "rrc",
                    name: this.form.name,
                    rrc: {
                        hub: this.effectiveHubHash,
                        rooms: this.parseRooms(this.form.roomsCsv),
                        nick: this.form.nick || this.form.name,
                        mention_only: this.form.mentionOnly,
                        prefix: this.form.prefix || "!",
                        rate_seconds: Math.max(0, Math.min(3600, Number(this.form.rateSeconds) || 8)),
                    },
                });
                ToastUtils.success(this.$t("bots.bot_started"));
                this.resetCreate();
                await this.fetchBots({ quiet: true });
            } catch (e) {
                ToastUtils.error(e?.response?.data?.message || this.$t("bots.failed_to_start"));
            } finally {
                this.creating = false;
            }
        },
        async startBot(bot) {
            try {
                await window.api.post(apiPath("/bots/start"), {
                    template_id: "rrc",
                    bot_id: bot.id,
                    name: bot.name,
                });
                ToastUtils.success(this.$t("bots.bot_started"));
            } catch (e) {
                ToastUtils.error(e?.response?.data?.message || this.$t("bots.failed_to_start"));
            }
            await this.fetchBots({ quiet: true });
        },
        async stopBot(bot) {
            try {
                await window.api.post(apiPath("/bots/stop"), { bot_id: bot.id });
                ToastUtils.success(this.$t("bots.bot_stopped"));
            } catch (e) {
                ToastUtils.error(e?.response?.data?.message || this.$t("bots.failed_to_stop"));
            }
            await this.fetchBots({ quiet: true });
        },
        async confirmDelete(bot) {
            const ok = await DialogUtils.confirm(this.$t("relay_chat.bots_delete_confirm", { name: bot.name }));
            if (!ok) return;
            try {
                await window.api.post(apiPath("/bots/delete"), { bot_id: bot.id });
                ToastUtils.success(this.$t("bots.bot_deleted"));
            } catch (e) {
                ToastUtils.error(e?.response?.data?.message || this.$t("bots.failed_to_delete"));
            }
            await this.fetchBots({ quiet: true });
        },
    },
};
</script>
