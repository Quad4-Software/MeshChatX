<template>
    <div
        class="flex flex-col flex-1 overflow-hidden min-w-0 bg-gradient-to-br from-slate-50 via-slate-100 to-white dark:from-zinc-950 dark:via-zinc-900 dark:to-zinc-900"
    >
        <div class="flex-1 overflow-y-auto w-full px-4 md:px-8 py-6">
            <div class="space-y-4 w-full max-w-4xl mx-auto">
                <div class="glass-card space-y-5">
                    <div class="space-y-2">
                        <div class="text-xs uppercase tracking-wide text-gray-500 dark:text-gray-400">
                            {{ $t("bots.bot_framework") }}
                        </div>
                        <div class="text-2xl font-semibold text-gray-900 dark:text-white">{{ $t("bots.title") }}</div>
                        <div class="text-sm text-gray-600 dark:text-gray-300">
                            {{ $t("bots.description") }}
                        </div>
                    </div>

                    <div class="space-y-6">
                        <!-- Create New Bot -->
                        <div class="space-y-4">
                            <h3 class="text-lg font-semibold text-gray-900 dark:text-white">
                                {{ $t("bots.create_new_bot") }}
                            </h3>
                            <div class="grid sm:grid-cols-2 gap-4">
                                <div
                                    v-for="template in templates"
                                    :key="template.id"
                                    class="glass-card !p-4 hover:border-blue-400 transition cursor-pointer flex flex-col justify-between"
                                    @click="selectTemplate(template)"
                                >
                                    <div>
                                        <div class="font-bold text-gray-900 dark:text-white">{{ template.name }}</div>
                                        <div class="text-sm text-gray-600 dark:text-gray-400 mt-1">
                                            {{ template.description }}
                                        </div>
                                    </div>
                                    <button
                                        class="primary-chip w-full mt-4 py-2"
                                        @click.stop="selectTemplate(template)"
                                    >
                                        {{ $t("bots.select") }}
                                    </button>
                                </div>

                                <!-- More bots coming soon -->
                                <div
                                    class="glass-card !p-4 border-dashed border-2 border-gray-200 dark:border-zinc-800 flex flex-col items-center justify-center opacity-60"
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

                        <!-- Saved Bots -->
                        <div class="space-y-4">
                            <h3 class="text-lg font-semibold text-gray-900 dark:text-white">
                                {{ $t("bots.saved_bots") }}
                            </h3>
                            <div v-if="bots.length === 0" class="text-sm text-gray-500 italic">
                                {{ $t("bots.no_bots_running") }}
                            </div>
                            <div v-else class="space-y-3">
                                <div
                                    v-for="bot in bots"
                                    :key="bot.id"
                                    class="glass-card !p-4 flex items-center justify-between"
                                >
                                    <div class="flex items-center gap-3">
                                        <div class="p-2 bg-blue-100 dark:bg-blue-900/30 rounded-lg">
                                            <MaterialDesignIcon
                                                icon-name="robot"
                                                class="size-6 text-blue-600 dark:text-blue-400"
                                            />
                                        </div>
                                        <div>
                                            <div class="font-bold text-gray-900 dark:text-white">{{ bot.name }}</div>
                                            <div class="text-xs font-mono text-gray-500">
                                                {{ bot.address || runningMap[bot.id]?.address || "Not running" }}
                                            </div>
                                            <div class="text-[10px] text-gray-400">
                                                {{ bot.template_id || bot.template }}
                                            </div>
                                            <div v-if="bot.storage_dir" class="text-[10px] text-gray-400">
                                                {{ bot.storage_dir }}
                                            </div>
                                        </div>
                                    </div>
                                    <div class="flex items-center gap-2">
                                        <template v-if="runningMap[bot.id]">
                                            <button
                                                class="p-2 text-red-500 hover:bg-red-50 dark:hover:bg-red-900/20 rounded-lg transition-colors"
                                                :title="$t('bots.stop_bot')"
                                                @click="stopBot(bot.id)"
                                            >
                                                <MaterialDesignIcon icon-name="stop" class="size-5" />
                                            </button>
                                            <button
                                                class="p-2 text-blue-500 hover:bg-blue-50 dark:hover:bg-blue-900/20 rounded-lg transition-colors"
                                                :title="$t('bots.restart_bot')"
                                                @click="restartExisting(bot)"
                                            >
                                                <MaterialDesignIcon icon-name="refresh" class="size-5" />
                                            </button>
                                        </template>
                                        <template v-else>
                                            <button class="primary-chip px-3 py-1 text-xs" @click="startExisting(bot)">
                                                {{ $t("bots.start_bot") }}
                                            </button>
                                        </template>
                                        <button
                                            class="p-2 text-gray-500 hover:bg-gray-50 dark:hover:bg-zinc-800 rounded-lg transition-colors"
                                            :title="$t('bots.export_identity')"
                                            @click="exportIdentity(bot.id)"
                                        >
                                            <MaterialDesignIcon icon-name="export" class="size-5" />
                                        </button>
                                        <button
                                            class="p-2 text-red-500 hover:bg-red-50 dark:hover:bg-red-900/20 rounded-lg transition-colors"
                                            :title="$t('bots.delete_bot')"
                                            @click="deleteBot(bot.id)"
                                        >
                                            <MaterialDesignIcon icon-name="delete" class="size-5" />
                                        </button>
                                    </div>
                                </div>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        </div>

        <!-- Start Bot Modal -->
        <div
            v-if="selectedTemplate"
            class="fixed inset-0 z-[100] flex items-center justify-center p-4 bg-black/50 backdrop-blur-sm"
            @click.self="selectedTemplate = null"
        >
            <div class="glass-card max-w-md w-full space-y-4">
                <div class="flex justify-between items-center">
                    <h3 class="text-xl font-bold text-gray-900 dark:text-white">
                        {{ $t("bots.start_bot") }}: {{ selectedTemplate.name }}
                    </h3>
                    <button
                        class="p-1 hover:bg-gray-100 dark:hover:bg-zinc-800 rounded-lg"
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

                    <div class="flex gap-3 justify-end pt-2">
                        <button class="secondary-chip px-6 py-2" @click="selectedTemplate = null">
                            {{ $t("bots.cancel") }}
                        </button>
                        <button class="primary-chip px-6 py-2" :disabled="isStarting" @click="startBot">
                            <span
                                v-if="isStarting"
                                class="inline-block w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin mr-2"
                            ></span>
                            {{ $t("bots.start_bot") }}
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
            runningBots: [],
            selectedTemplate: null,
            newBotName: "",
            isStarting: false,
            loading: true,
            refreshInterval: null,
        };
    },
    computed: {
        runningMap() {
            const map = {};
            this.runningBots.forEach((b) => {
                map[b.id] = b;
            });
            return map;
        },
    },
    mounted() {
        this.getStatus();
        this.refreshInterval = setInterval(this.getStatus, 5000);
    },
    beforeUnmount() {
        if (this.refreshInterval) {
            clearInterval(this.refreshInterval);
        }
    },
    methods: {
        async getStatus() {
            try {
                const response = await window.api.get("/api/v1/bots/status");
                this.bots = response.data.status.bots || [];
                this.runningBots = response.data.status.running_bots;
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
                this.getStatus();
            } catch (e) {
                console.error(e);
                ToastUtils.error(this.$t("bots.failed_to_delete"));
            }
        },
        exportIdentity(botId) {
            window.open(`/api/v1/bots/export?bot_id=${botId}`, "_blank");
        },
        copyToClipboard(text) {
            navigator.clipboard.writeText(text);
            ToastUtils.success(this.$t("translator.copied_to_clipboard"));
        },
    },
};
</script>

<style scoped>
.glass-label {
    @apply block text-sm font-semibold text-gray-700 dark:text-gray-300 mb-1;
}
</style>
