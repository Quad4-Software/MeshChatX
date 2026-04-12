<template>
    <div class="flex flex-col flex-1 overflow-hidden min-w-0 bg-white dark:bg-zinc-950">
        <div class="flex-1 overflow-y-auto w-full">
            <div class="border-b border-gray-200 dark:border-zinc-800 px-4 py-4 md:px-6 md:py-5">
                <div class="flex flex-col gap-4 lg:flex-row lg:items-end lg:justify-between lg:gap-6">
                    <div class="space-y-2 min-w-0 flex-1">
                        <div class="text-xs uppercase tracking-wide text-gray-500 dark:text-gray-400">
                            {{ $t("tools.utilities") }}
                        </div>
                        <div class="text-2xl md:text-3xl font-black text-gray-900 dark:text-white tracking-tight">
                            {{ $t("tools.power_tools") }}
                        </div>
                        <div class="text-sm text-gray-600 dark:text-gray-300 leading-relaxed max-w-xl">
                            {{ $t("tools.diagnostics_description") }}
                        </div>
                    </div>

                    <div class="w-full lg:max-w-sm shrink-0">
                        <div class="relative group">
                            <div class="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
                                <MaterialDesignIcon
                                    icon-name="magnify"
                                    class="size-5 text-gray-400 group-focus-within:text-blue-500 transition-colors"
                                />
                            </div>
                            <input
                                v-model="searchQuery"
                                type="text"
                                :placeholder="$t('common.search')"
                                class="w-full pl-10 pr-10 py-3 bg-gray-50 dark:bg-zinc-900 border border-gray-200 dark:border-zinc-800 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500/40 focus:border-blue-500 text-gray-900 dark:text-white placeholder-gray-400 dark:placeholder-gray-500 text-sm"
                            />
                            <button
                                v-if="searchQuery"
                                class="absolute inset-y-0 right-0 pr-3 flex items-center text-gray-400 hover:text-gray-600 dark:hover:text-gray-200"
                                type="button"
                                @click="searchQuery = ''"
                            >
                                <MaterialDesignIcon icon-name="close-circle" class="size-5" />
                            </button>
                        </div>
                    </div>
                </div>
            </div>

            <div class="p-4 md:p-6 w-full max-w-6xl mx-auto">
                <div
                    class="rounded-lg border border-gray-200 dark:border-zinc-800 divide-y divide-gray-200 dark:divide-zinc-800 overflow-hidden bg-white dark:bg-zinc-950"
                >
                    <RouterLink
                        v-for="tool in filteredTools"
                        :key="tool.name"
                        :to="tool.comingSoon ? '' : tool.route"
                        :class="
                            [
                                'tool-row',
                                tool.customClass,
                                tool.comingSoon ? 'opacity-60 grayscale-[0.5] cursor-default' : '',
                            ].filter(Boolean)
                        "
                        @click="tool.comingSoon ? $event.preventDefault() : null"
                    >
                        <div :class="tool.iconBg">
                            <MaterialDesignIcon v-if="tool.icon" :icon-name="tool.icon" class="w-6 h-6" />
                            <img
                                v-else-if="tool.image"
                                :src="tool.image"
                                :class="tool.imageClass"
                                :alt="tool.imageAlt"
                            />
                        </div>
                        <div class="flex-1 min-w-0">
                            <div class="flex items-center gap-2 flex-wrap">
                                <div class="tool-card__title">{{ tool.title }}</div>
                                <span
                                    v-if="tool.comingSoon"
                                    class="px-1.5 py-0.5 text-[10px] font-bold uppercase tracking-wider bg-gray-100 dark:bg-zinc-800 text-gray-500 dark:text-gray-400 rounded border border-gray-200 dark:border-zinc-700"
                                >
                                    Soon
                                </span>
                            </div>
                            <div class="tool-card__description">
                                {{ tool.description }}
                            </div>
                        </div>
                        <div v-if="!tool.comingSoon" class="shrink-0 flex items-center gap-1">
                            <div v-if="tool.extraAction" class="flex items-center gap-2">
                                <a
                                    :href="tool.extraAction.href"
                                    :target="tool.extraAction.target"
                                    class="p-2 hover:bg-gray-100 dark:hover:bg-zinc-800 rounded-lg transition-colors text-gray-400 hover:text-blue-500"
                                    @click.stop
                                >
                                    <MaterialDesignIcon :icon-name="tool.extraAction.icon" class="size-5" />
                                </a>
                                <MaterialDesignIcon icon-name="chevron-right" class="tool-card__chevron" />
                            </div>
                            <MaterialDesignIcon v-else icon-name="chevron-right" class="tool-card__chevron" />
                        </div>
                    </RouterLink>
                </div>

                <div
                    v-if="filteredTools.length === 0"
                    class="mt-6 rounded-lg border border-dashed border-gray-300 dark:border-zinc-700 px-4 py-12 text-center"
                >
                    <MaterialDesignIcon icon-name="magnify" class="w-12 h-12 mx-auto mb-4 text-gray-400" />
                    <div class="text-gray-600 dark:text-gray-400">{{ $t("common.no_results") }}</div>
                </div>
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
            searchQuery: "",
            tools: [
                {
                    name: "ping",
                    route: { name: "ping" },
                    icon: "radar",
                    iconBg: "tool-card__icon bg-blue-50 text-blue-500 dark:bg-blue-900/30 dark:text-blue-200",
                    titleKey: "tools.ping.title",
                    descriptionKey: "tools.ping.description",
                },
                {
                    name: "rnprobe",
                    route: { name: "rnprobe" },
                    icon: "radar",
                    iconBg: "tool-card__icon bg-purple-50 text-purple-500 dark:bg-purple-900/30 dark:text-purple-200",
                    titleKey: "tools.rnprobe.title",
                    descriptionKey: "tools.rnprobe.description",
                },
                {
                    name: "rncp",
                    route: { name: "rncp" },
                    icon: "swap-horizontal",
                    iconBg: "tool-card__icon bg-green-50 text-green-500 dark:bg-green-900/30 dark:text-green-200",
                    titleKey: "tools.rncp.title",
                    descriptionKey: "tools.rncp.description",
                },
                {
                    name: "rnstatus",
                    route: { name: "rnstatus" },
                    icon: "chart-line",
                    iconBg: "tool-card__icon bg-orange-50 text-orange-500 dark:bg-orange-900/30 dark:text-orange-200",
                    titleKey: "tools.rnstatus.title",
                    descriptionKey: "tools.rnstatus.description",
                },
                {
                    name: "rnpath",
                    route: { name: "rnpath" },
                    icon: "route",
                    iconBg: "tool-card__icon bg-indigo-50 text-indigo-500 dark:bg-indigo-900/30 dark:text-indigo-200",
                    titleKey: "tools.rnpath.title",
                    descriptionKey: "tools.rnpath.description",
                },
                {
                    name: "rnpath-trace",
                    route: { name: "rnpath-trace" },
                    icon: "map-marker-path",
                    iconBg: "tool-card__icon bg-blue-50 text-blue-500 dark:bg-blue-900/30 dark:text-blue-200",
                    titleKey: "tools.rnpath_trace.title",
                    descriptionKey: "tools.rnpath_trace.description",
                },
                {
                    name: "translator",
                    route: { name: "translator" },
                    icon: "translate",
                    iconBg: "tool-card__icon bg-indigo-50 text-indigo-500 dark:bg-indigo-900/30 dark:text-indigo-200",
                    titleKey: "tools.translator.title",
                    descriptionKey: "tools.translator.description",
                },
                {
                    name: "bots",
                    route: { name: "bots" },
                    icon: "robot",
                    iconBg: "tool-card__icon bg-blue-50 text-blue-500 dark:bg-blue-900/30 dark:text-blue-200",
                    titleKey: "tools.bots.title",
                    descriptionKey: "tools.bots.description",
                },
                {
                    name: "forwarder",
                    route: { name: "forwarder" },
                    icon: "email-send-outline",
                    iconBg: "tool-card__icon bg-rose-50 text-rose-500 dark:bg-rose-900/30 dark:text-rose-200",
                    titleKey: "tools.forwarder.title",
                    descriptionKey: "tools.forwarder.description",
                },
                {
                    name: "documentation",
                    route: { name: "documentation" },
                    icon: "book-open-variant",
                    iconBg: "tool-card__icon bg-cyan-50 text-cyan-500 dark:bg-cyan-900/30 dark:text-cyan-200",
                    titleKey: "docs.title",
                    descriptionKey: "docs.subtitle",
                },
                {
                    name: "micron-editor",
                    route: { name: "micron-editor" },
                    icon: "code-tags",
                    iconBg: "tool-card__icon bg-teal-50 text-teal-500 dark:bg-teal-900/30 dark:text-teal-200",
                    titleKey: "tools.micron_editor.title",
                    descriptionKey: "tools.micron_editor.description",
                },
                {
                    name: "paper-message",
                    route: { name: "paper-message" },
                    icon: "qrcode",
                    iconBg: "tool-card__icon bg-blue-50 text-blue-500 dark:bg-blue-900/30 dark:text-blue-200",
                    titleKey: "tools.paper_message.title",
                    descriptionKey: "tools.paper_message.description",
                },
                {
                    name: "rnode-flasher",
                    route: { name: "rnode-flasher" },
                    icon: null,
                    image: "/rnode-flasher/reticulum_logo_512.png",
                    imageClass: "w-8 h-8 rounded-full",
                    imageAlt: "RNode",
                    iconBg: "tool-card__icon bg-purple-50 text-purple-500 dark:bg-purple-900/30 dark:text-purple-200",
                    titleKey: "tools.rnode_flasher.title",
                    descriptionKey: "tools.rnode_flasher.description",
                    extraAction: {
                        href: "/rnode-flasher/index.html",
                        target: "_blank",
                        icon: "open-in-new",
                    },
                },
                {
                    name: "mesh-server",
                    route: { name: "mesh-server" },
                    icon: "server-network",
                    iconBg: "tool-card__icon bg-amber-50 text-amber-500 dark:bg-amber-900/30 dark:text-amber-200",
                    titleKey: "tools.mesh_server.title",
                    descriptionKey: "tools.mesh_server.description",
                },
                {
                    name: "rns-tunnel",
                    comingSoon: true,
                    icon: "tunnel",
                    iconBg: "tool-card__icon bg-indigo-50 text-indigo-500 dark:bg-indigo-900/30 dark:text-indigo-200",
                    titleKey: "tools.rns_tunnel.title",
                    descriptionKey: "tools.rns_tunnel.description",
                },
                {
                    name: "rns-filesync",
                    comingSoon: true,
                    icon: "folder-sync",
                    iconBg: "tool-card__icon bg-emerald-50 text-emerald-500 dark:bg-emerald-900/30 dark:text-emerald-200",
                    titleKey: "tools.rns_filesync.title",
                    descriptionKey: "tools.rns_filesync.description",
                },
                {
                    name: "debug-logs",
                    route: { name: "debug-logs" },
                    icon: "console",
                    iconBg: "tool-card__icon bg-zinc-100 text-zinc-500 dark:bg-zinc-800 dark:text-zinc-400",
                    titleKey: null,
                    title: "Debug Logs",
                    descriptionKey: null,
                    description: "View and export internal system logs for troubleshooting.",
                    customClass: "bg-amber-50/40 dark:bg-amber-950/20",
                },
            ],
        };
    },
    computed: {
        filteredTools() {
            const toolsWithTranslations = this.tools.map((tool) => ({
                ...tool,
                title: tool.title || (tool.titleKey ? this.$t(tool.titleKey) : ""),
                description: tool.description || (tool.descriptionKey ? this.$t(tool.descriptionKey) : ""),
            }));

            if (!this.searchQuery.trim()) {
                return toolsWithTranslations;
            }

            const query = this.searchQuery.toLowerCase().trim();
            return toolsWithTranslations.filter((tool) => {
                return (
                    tool.title.toLowerCase().includes(query) ||
                    tool.description.toLowerCase().includes(query) ||
                    tool.name.toLowerCase().includes(query)
                );
            });
        },
    },
};
</script>

<style scoped>
.tool-row {
    @apply flex items-start sm:items-center gap-3 sm:gap-4 px-4 py-3.5 min-h-[4.25rem] transition-colors;
    @apply hover:bg-gray-50 dark:hover:bg-zinc-900/80 active:bg-gray-100 dark:active:bg-zinc-800/80;
}
.tool-card__icon {
    @apply w-11 h-11 sm:w-12 sm:h-12 rounded-xl flex items-center justify-center shrink-0;
}
.tool-card__title {
    @apply text-base sm:text-lg font-semibold text-gray-900 dark:text-white;
}
.tool-card__description {
    @apply text-sm text-gray-600 dark:text-gray-300 mt-0.5 line-clamp-2 sm:line-clamp-none;
}
.tool-card__chevron {
    @apply w-5 h-5 text-gray-400 shrink-0;
}
</style>
