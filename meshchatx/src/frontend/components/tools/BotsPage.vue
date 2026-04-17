<!-- SPDX-License-Identifier: 0BSD -->

<template>
    <div class="flex flex-col flex-1 overflow-hidden min-w-0 bg-slate-50 dark:bg-zinc-950">
        <div
            class="flex-1 overflow-y-auto w-full px-3 sm:px-4 md:px-5 lg:px-8 py-4 sm:py-6 pb-[max(1.5rem,env(safe-area-inset-bottom))]"
        >
            <div class="space-y-8 w-full max-w-4xl mx-auto">
                <div class="space-y-2 border-b border-gray-200 dark:border-zinc-800 pb-6">
                    <div class="text-xs uppercase tracking-wide text-gray-500 dark:text-gray-400">
                        {{ $t("bots.bot_framework") }}
                    </div>
                    <div class="text-2xl font-semibold text-gray-900 dark:text-white">{{ $t("bots.title") }}</div>
                    <div class="text-sm text-gray-600 dark:text-gray-300">
                        {{ $t("bots.description") }}
                    </div>
                </div>

                <div class="space-y-6">
                    <div class="space-y-4">
                        <h3 class="text-lg font-semibold text-gray-900 dark:text-white">
                            {{ $t("bots.create_new_bot") }}
                        </h3>
                        <div class="grid grid-cols-1 sm:grid-cols-2 gap-3 sm:gap-4">
                            <div
                                v-for="template in templates"
                                :key="template.id"
                                class="relative rounded-lg border border-gray-200 dark:border-zinc-800 bg-white dark:bg-zinc-950 p-4 hover:border-blue-400 dark:hover:border-blue-600 transition cursor-pointer flex flex-col justify-between min-h-[140px] pr-12"
                                @click="selectTemplate(template)"
                            >
                                <div class="min-w-0">
                                    <div class="font-bold text-gray-900 dark:text-white">{{ template.name }}</div>
                                    <div class="text-sm text-gray-600 dark:text-gray-400 mt-1">
                                        {{ template.description }}
                                    </div>
                                </div>
                                <div
                                    class="absolute bottom-3 right-3 p-2 rounded-lg text-gray-400 hover:text-gray-700 dark:hover:text-gray-200 hover:bg-gray-100/80 dark:hover:bg-zinc-800/80 transition-colors pointer-events-none"
                                >
                                    <MaterialDesignIcon icon-name="chevron-right" class="size-6" />
                                </div>
                            </div>

                            <div
                                class="rounded-lg border border-dashed border-gray-300 dark:border-zinc-700 bg-gray-50/50 dark:bg-zinc-900/50 p-4 flex flex-col items-center justify-center min-h-[140px] opacity-70"
                            >
                                <div class="p-2 bg-gray-100 dark:bg-zinc-800 rounded-lg mb-2">
                                    <MaterialDesignIcon
                                        icon-name="plus"
                                        class="size-6 text-gray-400 dark:text-gray-500"
                                    />
                                </div>
                                <div class="text-sm font-medium text-gray-500 dark:text-gray-400 text-center">
                                    {{ $t("bots.more_bots_coming") }}
                                </div>
                            </div>
                        </div>
                    </div>

                    <div class="space-y-4">
                        <h3 class="text-lg font-semibold text-gray-900 dark:text-white">
                            {{ $t("bots.saved_bots") }}
                        </h3>
                        <div v-if="bots.length === 0" class="text-sm text-gray-500 italic">
                            {{ $t("bots.no_bots_running") }}
                        </div>
                        <div v-else class="space-y-2 sm:space-y-3">
                            <div
                                v-for="bot in bots"
                                :key="bot.id"
                                :class="[
                                    'relative rounded-lg border border-gray-200 dark:border-zinc-800 bg-white dark:bg-zinc-950 p-3 sm:p-4',
                                    editingBotId === bot.id ? 'pr-28 sm:pr-40' : 'pr-10 sm:pr-12',
                                ]"
                            >
                                <div
                                    class="absolute top-2 right-2 flex flex-wrap items-center justify-end gap-0.5 z-10 max-w-[min(100%,calc(100%-2rem))]"
                                >
                                    <button
                                        v-if="lxmfAddressFor(bot)"
                                        type="button"
                                        class="p-2 rounded-lg text-gray-500 dark:text-gray-400 hover:text-blue-600 dark:hover:text-blue-400 hover:bg-gray-100/80 dark:hover:bg-zinc-800/80 transition-colors"
                                        :title="$t('bots.chat_with_bot')"
                                        @click="openChatWithBot(bot)"
                                    >
                                        <MaterialDesignIcon icon-name="message-text" class="size-5" />
                                    </button>
                                    <button
                                        v-if="bot.running"
                                        type="button"
                                        class="p-2 rounded-lg text-gray-500 dark:text-gray-400 hover:text-amber-600 dark:hover:text-amber-400 hover:bg-gray-100/80 dark:hover:bg-zinc-800/80 transition-colors"
                                        :title="$t('bots.force_announce')"
                                        @click="forceAnnounce(bot)"
                                    >
                                        <MaterialDesignIcon icon-name="bullhorn" class="size-5" />
                                    </button>
                                    <button
                                        v-if="bot.running"
                                        type="button"
                                        class="p-2 rounded-lg text-gray-500 dark:text-gray-400 hover:text-blue-600 dark:hover:text-blue-400 hover:bg-gray-100/80 dark:hover:bg-zinc-800/80 transition-colors"
                                        :title="$t('bots.restart_bot')"
                                        @click="restartExisting(bot)"
                                    >
                                        <MaterialDesignIcon icon-name="refresh" class="size-5" />
                                    </button>
                                    <button
                                        v-if="bot.running"
                                        type="button"
                                        class="p-2 rounded-lg text-gray-500 dark:text-gray-400 hover:text-red-600 dark:hover:text-red-400 hover:bg-gray-100/80 dark:hover:bg-zinc-800/80 transition-colors"
                                        :title="$t('bots.stop_bot')"
                                        @click="stopBot(bot.id)"
                                    >
                                        <MaterialDesignIcon icon-name="stop" class="size-5" />
                                    </button>
                                    <button
                                        v-if="!bot.running"
                                        type="button"
                                        class="p-2 rounded-lg text-gray-500 dark:text-gray-400 hover:text-emerald-600 dark:hover:text-emerald-400 hover:bg-gray-100/80 dark:hover:bg-zinc-800/80 transition-colors"
                                        :title="$t('bots.start_bot')"
                                        @click="startExisting(bot)"
                                    >
                                        <MaterialDesignIcon icon-name="play" class="size-5" />
                                    </button>
                                    <button
                                        type="button"
                                        class="p-2 rounded-lg text-gray-500 dark:text-gray-400 hover:text-gray-900 dark:hover:text-white hover:bg-gray-100/80 dark:hover:bg-zinc-800/80 transition-colors"
                                        :title="$t('bots.export_identity')"
                                        @click="exportIdentity(bot.id)"
                                    >
                                        <MaterialDesignIcon icon-name="export" class="size-5" />
                                    </button>
                                    <button
                                        type="button"
                                        class="p-2 rounded-lg text-gray-500 dark:text-gray-400 hover:text-red-600 dark:hover:text-red-400 hover:bg-gray-100/80 dark:hover:bg-zinc-800/80 transition-colors"
                                        :title="$t('bots.delete_bot')"
                                        @click="deleteBot(bot.id)"
                                    >
                                        <MaterialDesignIcon icon-name="delete" class="size-5" />
                                    </button>
                                </div>

                                <div class="flex items-start gap-3 min-w-0">
                                    <div class="p-2 bg-blue-100 dark:bg-blue-900/30 rounded-lg shrink-0">
                                        <MaterialDesignIcon
                                            icon-name="robot"
                                            class="size-6 text-blue-600 dark:text-blue-400"
                                        />
                                    </div>
                                    <div class="min-w-0 flex-1 space-y-1.5 sm:pr-2">
                                        <div
                                            class="flex items-center gap-1 min-w-0"
                                            :class="
                                                editingBotId === bot.id
                                                    ? 'max-w-[min(100%,14rem)] sm:max-w-[16rem]'
                                                    : ''
                                            "
                                        >
                                            <template v-if="editingBotId === bot.id">
                                                <input
                                                    v-model="editingNameDraft"
                                                    type="text"
                                                    class="input-field text-xs py-1 h-8 px-2 min-w-0 flex-1 max-w-[10rem] sm:max-w-[12rem]"
                                                    maxlength="256"
                                                    @keydown.enter.prevent="saveBotName(bot)"
                                                    @keydown.escape="cancelEditName"
                                                />
                                                <button
                                                    type="button"
                                                    class="p-1 rounded-lg text-gray-500 hover:text-emerald-600 hover:bg-gray-100/80 dark:hover:bg-zinc-800/80 shrink-0"
                                                    :title="$t('common.save')"
                                                    @click="saveBotName(bot)"
                                                >
                                                    <MaterialDesignIcon icon-name="check" class="size-4" />
                                                </button>
                                                <button
                                                    type="button"
                                                    class="p-1 rounded-lg text-gray-500 hover:text-gray-900 dark:hover:text-white hover:bg-gray-100/80 dark:hover:bg-zinc-800/80 shrink-0"
                                                    :title="$t('common.cancel')"
                                                    @click="cancelEditName"
                                                >
                                                    <MaterialDesignIcon icon-name="close" class="size-4" />
                                                </button>
                                            </template>
                                            <template v-else>
                                                <span class="font-bold text-gray-900 dark:text-white truncate">{{
                                                    bot.name
                                                }}</span>
                                                <button
                                                    type="button"
                                                    class="p-1.5 rounded-lg text-gray-400 hover:text-gray-700 dark:hover:text-gray-200 hover:bg-gray-100/80 dark:hover:bg-zinc-800/80 shrink-0"
                                                    :title="$t('bots.edit_name')"
                                                    @click="startEditName(bot)"
                                                >
                                                    <MaterialDesignIcon icon-name="pencil" class="size-4" />
                                                </button>
                                            </template>
                                        </div>
                                        <div
                                            class="flex items-center gap-2 text-[11px] text-gray-600 dark:text-gray-300"
                                        >
                                            <span
                                                class="inline-block size-2 rounded-full shrink-0"
                                                :class="bot.running ? 'bg-emerald-500' : 'bg-gray-400 dark:bg-gray-500'"
                                            ></span>
                                            <span>{{
                                                bot.running ? $t("bots.status_running") : $t("bots.status_stopped")
                                            }}</span>
                                        </div>
                                        <div class="text-[11px] text-gray-500 dark:text-gray-400">
                                            <span class="font-semibold text-gray-600 dark:text-gray-300">{{
                                                $t("bots.lxmf_address")
                                            }}</span>
                                            <button
                                                v-if="lxmfAddressFor(bot)"
                                                type="button"
                                                class="font-mono break-all text-left text-gray-800 dark:text-gray-200 hover:underline"
                                                @click="copyLxmfAddress(bot)"
                                            >
                                                {{ lxmfAddressFor(bot) }}
                                            </button>
                                            <span v-else>{{ $t("bots.address_pending") }}</span>
                                        </div>
                                        <div class="text-[11px] text-gray-500 dark:text-gray-400">
                                            <span class="font-semibold text-gray-600 dark:text-gray-300">{{
                                                $t("bots.last_announce")
                                            }}</span>
                                            <span v-if="bot.last_announce_at" class="ml-1.5">{{
                                                formatRelativeSince(bot.last_announce_at)
                                            }}</span>
                                            <span v-else-if="lxmfAddressFor(bot)" class="ml-1.5">{{
                                                $t("bots.never_announced")
                                            }}</span>
                                            <span v-else class="ml-1.5">—</span>
                                        </div>
                                        <div class="text-[10px] text-gray-400">
                                            {{ bot.template_id || bot.template }}
                                        </div>
                                    </div>
                                </div>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        </div>

        <div
            v-if="selectedTemplate"
            class="fixed inset-0 z-[100] flex items-end sm:items-center justify-center p-0 sm:p-4 bg-black/50"
            @click.self="selectedTemplate = null"
        >
            <div
                class="w-full sm:max-w-md rounded-t-2xl sm:rounded-lg border border-gray-200 dark:border-zinc-800 bg-white dark:bg-zinc-950 p-4 sm:p-6 space-y-4 max-h-[90vh] overflow-y-auto"
            >
                <div class="flex justify-between items-start gap-2">
                    <h3 class="text-lg sm:text-xl font-bold text-gray-900 dark:text-white pr-2">
                        {{ $t("bots.start_bot") }}: {{ selectedTemplate.name }}
                    </h3>
                    <button
                        type="button"
                        class="p-2 rounded-lg text-gray-500 hover:text-gray-900 dark:hover:text-white hover:bg-gray-100/80 dark:hover:bg-zinc-800/80"
                        @click="selectedTemplate = null"
                    >
                        <MaterialDesignIcon icon-name="close" class="size-5" />
                    </button>
                </div>

                <div class="space-y-4">
                    <div>
                        <label class="glass-label">{{ $t("bots.bot_name") }}</label>
                        <input
                            v-model="newBotName"
                            type="text"
                            :placeholder="selectedTemplate.name"
                            class="input-field"
                        />
                    </div>

                    <div class="text-sm text-gray-600 dark:text-gray-400">
                        {{ selectedTemplate.description }}
                    </div>

                    <div class="flex justify-end gap-2 pt-2">
                        <button
                            type="button"
                            class="p-2 rounded-lg text-gray-500 hover:text-gray-900 dark:hover:text-white hover:bg-gray-100/80 dark:hover:bg-zinc-800/80"
                            @click="selectedTemplate = null"
                        >
                            <MaterialDesignIcon icon-name="close" class="size-6" />
                        </button>
                        <button
                            type="button"
                            class="p-2 rounded-lg text-gray-500 hover:text-emerald-600 hover:bg-gray-100/80 dark:hover:bg-zinc-800/80 disabled:opacity-40"
                            :disabled="isStarting"
                            @click="startBot"
                        >
                            <span
                                v-if="isStarting"
                                class="inline-block w-5 h-5 border-2 border-current border-t-transparent rounded-full animate-spin"
                            ></span>
                            <MaterialDesignIcon v-else icon-name="check" class="size-6" />
                        </button>
                    </div>
                </div>
            </div>
        </div>
    </div>
</template>

<script>
import ToastUtils from "../../js/ToastUtils";
import MaterialDesignIcon from "../MaterialDesignIcon.vue";

export default {
    name: "BotsPage",
    components: {
        MaterialDesignIcon,
    },
    data() {
        return {
            bots: [],
            templates: [],
            selectedTemplate: null,
            newBotName: "",
            isStarting: false,
            loading: true,
            refreshInterval: null,
            relativeTimerTick: 0,
            relativeTimerInterval: null,
            editingBotId: null,
            editingNameDraft: "",
        };
    },
    mounted() {
        this.getStatus();
        this.refreshInterval = setInterval(this.getStatus, 5000);
        this.relativeTimerInterval = setInterval(() => {
            this.relativeTimerTick += 1;
        }, 1000);
    },
    beforeUnmount() {
        if (this.refreshInterval) {
            clearInterval(this.refreshInterval);
        }
        if (this.relativeTimerInterval) {
            clearInterval(this.relativeTimerInterval);
        }
    },
    methods: {
        async getStatus() {
            try {
                const response = await window.api.get("/api/v1/bots/status");
                this.bots = response.data.status.bots || [];
                this.templates = response.data.templates;
                this.loading = false;
            } catch (e) {
                console.error(e);
            }
        },
        selectTemplate(template) {
            this.selectedTemplate = template;
            this.newBotName = template.name;
        },
        async startBot() {
            if (this.isStarting) return;
            this.isStarting = true;
            try {
                await window.api.post("/api/v1/bots/start", {
                    template_id: this.selectedTemplate.id,
                    name: this.newBotName,
                });
                ToastUtils.success(this.$t("bots.bot_started"));
                this.selectedTemplate = null;
                this.getStatus();
            } catch (e) {
                console.error(e);
                ToastUtils.error(e.response?.data?.message || this.$t("bots.failed_to_start"));
            } finally {
                this.isStarting = false;
            }
        },
        async stopBot(botId) {
            try {
                await window.api.post("/api/v1/bots/stop", { bot_id: botId });
                ToastUtils.success(this.$t("bots.bot_stopped"));
                this.getStatus();
            } catch (e) {
                console.error(e);
                ToastUtils.error(this.$t("bots.failed_to_stop"));
            }
        },
        async startExisting(bot) {
            try {
                await window.api.post("/api/v1/bots/start", {
                    bot_id: bot.id,
                    template_id: bot.template_id || bot.template,
                    name: bot.name,
                });
                ToastUtils.success(this.$t("bots.bot_started"));
                this.getStatus();
            } catch (e) {
                console.error(e);
                ToastUtils.error(e.response?.data?.message || this.$t("bots.failed_to_start"));
            }
        },
        async restartExisting(bot) {
            try {
                await window.api.post("/api/v1/bots/restart", { bot_id: bot.id });
                ToastUtils.success(this.$t("bots.bot_started"));
                this.getStatus();
            } catch (e) {
                console.error(e);
                ToastUtils.error(e.response?.data?.message || this.$t("bots.failed_to_start"));
            }
        },
        async deleteBot(botId) {
            if (!confirm(this.$t("common.delete_confirm"))) return;
            try {
                await window.api.post("/api/v1/bots/delete", { bot_id: botId });
                ToastUtils.success(this.$t("bots.bot_deleted"));
                if (this.editingBotId === botId) {
                    this.cancelEditName();
                }
                this.getStatus();
            } catch (e) {
                console.error(e);
                ToastUtils.error(this.$t("bots.failed_to_delete"));
            }
        },
        exportIdentity(botId) {
            window.open(`/api/v1/bots/export?bot_id=${botId}`, "_blank");
        },
        startEditName(bot) {
            this.editingBotId = bot.id;
            this.editingNameDraft = bot.name || "";
        },
        cancelEditName() {
            this.editingBotId = null;
            this.editingNameDraft = "";
        },
        async saveBotName(bot) {
            if (this.editingBotId !== bot.id) {
                return;
            }
            const name = (this.editingNameDraft || "").trim();
            if (!name) {
                ToastUtils.error(this.$t("bots.name_required"));
                return;
            }
            try {
                await window.api.patch("/api/v1/bots/update", {
                    bot_id: bot.id,
                    name,
                });
                ToastUtils.success(this.$t("bots.bot_renamed"));
                this.cancelEditName();
                this.getStatus();
            } catch (e) {
                console.error(e);
                ToastUtils.error(e.response?.data?.message || this.$t("bots.rename_failed"));
            }
        },
        async forceAnnounce(bot) {
            try {
                await window.api.post("/api/v1/bots/announce", { bot_id: bot.id });
                ToastUtils.success(this.$t("bots.announce_triggered"));
                this.getStatus();
            } catch (e) {
                console.error(e);
                ToastUtils.error(e.response?.data?.message || this.$t("bots.announce_failed"));
            }
        },
        lxmfAddressFor(bot) {
            const raw = bot.lxmf_address || bot.full_address;
            if (!raw || typeof raw !== "string") {
                return "";
            }
            const h = raw.trim().toLowerCase();
            return h.length === 32 && /^[0-9a-f]+$/.test(h) ? h : "";
        },
        openChatWithBot(bot) {
            const h = this.lxmfAddressFor(bot);
            if (!h) {
                return;
            }
            const routeName = this.$route?.meta?.isPopout ? "messages-popout" : "messages";
            this.$router.push({ name: routeName, params: { destinationHash: h } });
        },
        copyLxmfAddress(bot) {
            const h = this.lxmfAddressFor(bot);
            if (!h) {
                return;
            }
            navigator.clipboard.writeText(h);
            ToastUtils.success(this.$t("translator.copied_to_clipboard"));
        },
        formatRelativeSince(iso) {
            if (!iso) {
                return "";
            }
            let t;
            try {
                t = new Date(iso).getTime();
            } catch {
                return String(iso);
            }
            if (Number.isNaN(t)) {
                return String(iso);
            }
            const now = Date.now() + 0 * this.relativeTimerTick;
            let sec = Math.floor((now - t) / 1000);
            if (sec < 0) {
                sec = 0;
            }
            if (sec < 60) {
                return `${sec}s`;
            }
            const min = Math.floor(sec / 60);
            if (min < 60) {
                return min === 1 ? `${min}m` : `${min}m`;
            }
            const h = Math.floor(min / 60);
            if (h < 24) {
                return h === 1 ? `${h}h` : `${h}h`;
            }
            const d = Math.floor(h / 24);
            if (d < 30) {
                return d === 1 ? "1 day" : `${d} days`;
            }
            const mo = Math.floor(d / 30);
            if (d < 365) {
                return mo === 1 ? "1 month" : `${mo} months`;
            }
            const y = Math.floor(d / 365);
            return y === 1 ? "1 year" : `${y} years`;
        },
    },
};
</script>

<style scoped>
.glass-label {
    @apply block text-sm font-semibold text-gray-700 dark:text-gray-300 mb-1;
}
</style>
