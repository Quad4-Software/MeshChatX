<template>
    <div
        class="flex flex-col flex-1 overflow-hidden min-w-0 bg-gradient-to-br from-slate-50 via-slate-100 to-white dark:from-zinc-950 dark:via-zinc-900 dark:to-zinc-900"
    >
        <div class="overflow-y-auto space-y-4 p-4 md:p-6 max-w-5xl mx-auto w-full">
            <div class="glass-card space-y-3">
                <div class="text-xs uppercase tracking-wide text-gray-500 dark:text-gray-400">
                    {{ $t("tools.utilities") }}
                </div>
                <div class="text-2xl font-semibold text-gray-900 dark:text-white">{{ $t("tools.power_tools") }}</div>
                <div class="text-sm text-gray-600 dark:text-gray-300">
                    {{ $t("tools.diagnostics_description") }}
                </div>
            </div>

            <div class="grid gap-4 md:grid-cols-2">
                <RouterLink :to="{ name: 'ping' }" class="tool-card glass-card">
                    <div class="tool-card__icon bg-blue-50 text-blue-500 dark:bg-blue-900/30 dark:text-blue-200">
                        <MaterialDesignIcon icon-name="radar" class="w-6 h-6" />
                    </div>
                    <div class="flex-1">
                        <div class="tool-card__title">{{ $t("tools.ping.title") }}</div>
                        <div class="tool-card__description">
                            {{ $t("tools.ping.description") }}
                        </div>
                    </div>
                    <MaterialDesignIcon icon-name="chevron-right" class="tool-card__chevron" />
                </RouterLink>

                <RouterLink :to="{ name: 'rnprobe' }" class="tool-card glass-card">
                    <div
                        class="tool-card__icon bg-purple-50 text-purple-500 dark:bg-purple-900/30 dark:text-purple-200"
                    >
                        <MaterialDesignIcon icon-name="radar" class="w-6 h-6" />
                    </div>
                    <div class="flex-1">
                        <div class="tool-card__title">{{ $t("tools.rnprobe.title") }}</div>
                        <div class="tool-card__description">
                            {{ $t("tools.rnprobe.description") }}
                        </div>
                    </div>
                    <MaterialDesignIcon icon-name="chevron-right" class="tool-card__chevron" />
                </RouterLink>

                <RouterLink :to="{ name: 'rncp' }" class="tool-card glass-card">
                    <div class="tool-card__icon bg-green-50 text-green-500 dark:bg-green-900/30 dark:text-green-200">
                        <MaterialDesignIcon icon-name="swap-horizontal" class="w-6 h-6" />
                    </div>
                    <div class="flex-1">
                        <div class="tool-card__title">{{ $t("tools.rncp.title") }}</div>
                        <div class="tool-card__description">
                            {{ $t("tools.rncp.description") }}
                        </div>
                    </div>
                    <MaterialDesignIcon icon-name="chevron-right" class="tool-card__chevron" />
                </RouterLink>

                <RouterLink :to="{ name: 'rnstatus' }" class="tool-card glass-card">
                    <div
                        class="tool-card__icon bg-orange-50 text-orange-500 dark:bg-orange-900/30 dark:text-orange-200"
                    >
                        <MaterialDesignIcon icon-name="chart-line" class="w-6 h-6" />
                    </div>
                    <div class="flex-1">
                        <div class="tool-card__title">{{ $t("tools.rnstatus.title") }}</div>
                        <div class="tool-card__description">
                            {{ $t("tools.rnstatus.description") }}
                        </div>
                    </div>
                    <MaterialDesignIcon icon-name="chevron-right" class="tool-card__chevron" />
                </RouterLink>

                <RouterLink :to="{ name: 'translator' }" class="tool-card glass-card">
                    <div
                        class="tool-card__icon bg-indigo-50 text-indigo-500 dark:bg-indigo-900/30 dark:text-indigo-200"
                    >
                        <MaterialDesignIcon icon-name="translate" class="w-6 h-6" />
                    </div>
                    <div class="flex-1">
                        <div class="tool-card__title">{{ $t("tools.translator.title") }}</div>
                        <div class="tool-card__description">
                            {{ $t("tools.translator.description") }}
                        </div>
                    </div>
                    <MaterialDesignIcon icon-name="chevron-right" class="tool-card__chevron" />
                </RouterLink>

                <RouterLink :to="{ name: 'forwarder' }" class="tool-card glass-card">
                    <div class="tool-card__icon bg-rose-50 text-rose-500 dark:bg-rose-900/30 dark:text-rose-200">
                        <MaterialDesignIcon icon-name="email-send-outline" class="w-6 h-6" />
                    </div>
                    <div class="flex-1">
                        <div class="tool-card__title">{{ $t("tools.forwarder.title") }}</div>
                        <div class="tool-card__description">
                            {{ $t("tools.forwarder.description") }}
                        </div>
                    </div>
                    <MaterialDesignIcon icon-name="chevron-right" class="tool-card__chevron" />
                </RouterLink>

                <RouterLink :to="{ name: 'documentation' }" class="tool-card glass-card">
                    <div class="tool-card__icon bg-cyan-50 text-cyan-500 dark:bg-cyan-900/30 dark:text-cyan-200">
                        <MaterialDesignIcon icon-name="book-open-variant" class="w-6 h-6" />
                    </div>
                    <div class="flex-1">
                        <div class="tool-card__title">{{ $t("docs.title") }}</div>
                        <div class="tool-card__description">
                            {{ $t("docs.subtitle") }}
                        </div>
                    </div>
                    <MaterialDesignIcon icon-name="chevron-right" class="tool-card__chevron" />
                </RouterLink>

                <RouterLink :to="{ name: 'micron-editor' }" class="tool-card glass-card">
                    <div class="tool-card__icon bg-teal-50 text-teal-500 dark:bg-teal-900/30 dark:text-teal-200">
                        <MaterialDesignIcon icon-name="code-tags" class="w-6 h-6" />
                    </div>
                    <div class="flex-1">
                        <div class="tool-card__title">{{ $t("tools.micron_editor.title") }}</div>
                        <div class="tool-card__description">
                            {{ $t("tools.micron_editor.description") }}
                        </div>
                    </div>
                    <MaterialDesignIcon icon-name="chevron-right" class="tool-card__chevron" />
                </RouterLink>

                <RouterLink :to="{ name: 'paper-message' }" class="tool-card glass-card">
                    <div class="tool-card__icon bg-blue-50 text-blue-500 dark:bg-blue-900/30 dark:text-blue-200">
                        <MaterialDesignIcon icon-name="qrcode" class="w-6 h-6" />
                    </div>
                    <div class="flex-1">
                        <div class="tool-card__title">{{ $t("tools.paper_message.title") }}</div>
                        <div class="tool-card__description">
                            {{ $t("tools.paper_message.description") }}
                        </div>
                    </div>
                    <MaterialDesignIcon icon-name="chevron-right" class="tool-card__chevron" />
                </RouterLink>

                <RouterLink :to="{ name: 'rnode-flasher' }" class="tool-card glass-card">
                    <div
                        class="tool-card__icon bg-purple-50 text-purple-500 dark:bg-purple-900/30 dark:text-purple-200"
                    >
                        <img :src="rnodeLogoPath" class="w-8 h-8 rounded-full" alt="RNode" />
                    </div>
                    <div class="flex-1">
                        <div class="tool-card__title">{{ $t("tools.rnode_flasher.title") }}</div>
                        <div class="tool-card__description">
                            {{ $t("tools.rnode_flasher.description") }}
                        </div>
                    </div>
                    <div class="flex items-center gap-2">
                        <a
                            href="/rnode-flasher/index.html"
                            target="_blank"
                            class="p-2 hover:bg-gray-100 dark:hover:bg-zinc-800 rounded-lg transition-colors text-gray-400 hover:text-blue-500"
                            @click.stop
                        >
                            <MaterialDesignIcon icon-name="open-in-new" class="size-5" />
                        </a>
                        <MaterialDesignIcon icon-name="chevron-right" class="tool-card__chevron" />
                    </div>
                </RouterLink>

                <RouterLink :to="{ name: 'debug-logs' }" class="tool-card glass-card border-dashed border-2">
                    <div class="tool-card__icon bg-zinc-100 text-zinc-500 dark:bg-zinc-800 dark:text-zinc-400">
                        <MaterialDesignIcon icon-name="console" class="w-6 h-6" />
                    </div>
                    <div class="flex-1">
                        <div class="tool-card__title">Debug Logs</div>
                        <div class="tool-card__description">
                            View and export internal system logs for troubleshooting.
                        </div>
                    </div>
                    <MaterialDesignIcon icon-name="chevron-right" class="tool-card__chevron" />
                </RouterLink>
            </div>
        </div>
    </div>
</template>

<script>
import MaterialDesignIcon from "../MaterialDesignIcon.vue";
export default {
    name: "ToolsPage",
    components: {
        MaterialDesignIcon,
    },
    data() {
        return {
            rnodeLogoPath: "/rnode-flasher/reticulum_logo_512.png",
        };
    },
};
</script>

<style scoped>
.tool-card {
    @apply flex items-center gap-4 hover:border-blue-400 dark:hover:border-blue-500 transition cursor-pointer;
}
.tool-card__icon {
    @apply w-12 h-12 rounded-2xl flex items-center justify-center;
}
.tool-card__title {
    @apply text-lg font-semibold text-gray-900 dark:text-white;
}
.tool-card__description {
    @apply text-sm text-gray-600 dark:text-gray-300;
}
.tool-card__chevron {
    @apply w-5 h-5 text-gray-400;
}
</style>
