<template>
    <transition name="slide-down">
        <div
            v-if="isOpen"
            class="fixed inset-x-0 top-0 z-[200] flex items-start justify-center p-4 pointer-events-none"
        >
            <div
                v-click-outside="close"
                class="w-full max-w-2xl bg-white/95 dark:bg-zinc-900/95 backdrop-blur-md rounded-2xl shadow-2xl border border-gray-200 dark:border-zinc-800 overflow-hidden flex flex-col max-h-[70vh] pointer-events-auto mt-2 sm:mt-8"
            >
                <!-- search input -->
                <div class="relative flex items-center p-4 border-b border-gray-100 dark:border-zinc-800">
                    <MaterialDesignIcon icon-name="magnify" class="size-6 text-gray-400 mr-3" />
                    <input
                        ref="input"
                        v-model="query"
                        type="text"
                        class="w-full bg-transparent border-none focus:ring-0 text-gray-900 dark:text-white placeholder-gray-400 text-lg"
                        :placeholder="$t('command_palette.search_placeholder')"
                        @keydown.down.prevent="moveHighlight(1)"
                        @keydown.up.prevent="moveHighlight(-1)"
                        @keydown.enter="executeAction"
                        @keydown.esc="close"
                    />
                    <div class="flex items-center gap-1 ml-2">
                        <kbd
                            class="px-2 py-1 text-xs font-semibold text-gray-500 bg-gray-100 dark:bg-zinc-800 border border-gray-200 dark:border-zinc-700 rounded-lg shadow-sm"
                            >ESC</kbd
                        >
                    </div>
                </div>

                <!-- results -->
                <div class="flex-1 overflow-y-auto p-2 min-h-0">
                    <div v-if="filteredResults.length === 0" class="p-8 text-center text-gray-500 dark:text-gray-400">
                        {{ $t("command_palette.no_results", { query: query }) }}
                    </div>
                    <div v-else class="space-y-1">
                        <div v-for="(group, groupName) in groupedResults" :key="groupName">
                            <div class="px-3 py-2 text-[10px] font-bold text-gray-400 uppercase tracking-widest">
                                {{ $t(`command_palette.${groupName}`) }}
                            </div>
                            <button
                                v-for="result in group"
                                :key="result.id"
                                type="button"
                                class="w-full flex items-center gap-3 p-3 rounded-xl transition-all text-left group"
                                :class="[
                                    highlightedId === result.id
                                        ? 'bg-blue-50 dark:bg-blue-900/20 text-blue-600 dark:text-blue-400'
                                        : 'hover:bg-gray-50 dark:hover:bg-zinc-800/50 text-gray-700 dark:text-zinc-300',
                                ]"
                                @click="executeResult(result)"
                                @mousemove="highlightedId = result.id"
                            >
                                <div
                                    class="size-10 rounded-xl flex items-center justify-center shrink-0 border transition-colors"
                                    :class="[
                                        highlightedId === result.id
                                            ? 'bg-blue-100 dark:bg-blue-900/40 border-blue-200 dark:border-blue-800'
                                            : 'bg-gray-100 dark:bg-zinc-800 border-gray-200 dark:border-zinc-700',
                                    ]"
                                >
                                    <LxmfUserIcon
                                        v-if="result.type === 'contact' || result.type === 'peer'"
                                        :custom-image="result.type === 'contact' ? result.contact.custom_image : ''"
                                        :icon-name="result.icon"
                                        :icon-foreground-colour="result.iconForeground"
                                        :icon-background-colour="result.iconBackground"
                                        icon-class="size-5"
                                    />
                                    <MaterialDesignIcon v-else :icon-name="result.icon" class="size-5" />
                                </div>
                                <div class="min-w-0 flex-1">
                                    <div class="font-bold truncate">{{ result.title }}</div>
                                    <div class="text-xs opacity-60 truncate">{{ result.description }}</div>
                                </div>
                                <MaterialDesignIcon
                                    v-if="highlightedId === result.id"
                                    icon-name="arrow-right"
                                    class="size-4 animate-in slide-in-from-left-2"
                                />
                            </button>
                        </div>
                    </div>
                </div>

                <!-- footer -->
                <div
                    class="p-3 bg-gray-50/50 dark:bg-zinc-900/50 border-t border-gray-100 dark:border-zinc-800 flex justify-center gap-6 text-[10px] font-bold text-gray-400 uppercase tracking-widest"
                >
                    <div class="flex items-center gap-1.5">
                        <kbd
                            class="px-1.5 py-0.5 bg-white dark:bg-zinc-800 border border-gray-200 dark:border-zinc-700 rounded shadow-sm"
                            >↑↓</kbd
                        >
                        <span>{{ $t("command_palette.footer_navigate") }}</span>
                    </div>
                    <div class="flex items-center gap-1.5">
                        <kbd
                            class="px-1.5 py-0.5 bg-white dark:bg-zinc-800 border border-gray-200 dark:border-zinc-700 rounded shadow-sm"
                            >Enter</kbd
                        >
                        <span>{{ $t("command_palette.footer_select") }}</span>
                    </div>
                </div>
            </div>
        </div>
    </transition>
</template>

<script>
import MaterialDesignIcon from "./MaterialDesignIcon.vue";
import LxmfUserIcon from "./LxmfUserIcon.vue";

import GlobalEmitter from "../js/GlobalEmitter";
import ToastUtils from "../js/ToastUtils";

export default {
    name: "CommandPalette",
    components: { MaterialDesignIcon, LxmfUserIcon },
    data() {
        return {
            isOpen: false,
            query: "",
            highlightedId: null,
            peers: [],
            contacts: [],
            actions: [
                {
                    id: "nav-messages",
                    title: "nav_messages",
                    description: "nav_messages_desc",
                    icon: "message-text",
                    type: "navigation",
                    route: { name: "messages" },
                },
                {
                    id: "nav-nomad",
                    title: "nav_nomad",
                    description: "nav_nomad_desc",
                    icon: "earth",
                    type: "navigation",
                    route: { name: "nomadnetwork" },
                },
                {
                    id: "nav-map",
                    title: "nav_map",
                    description: "nav_map_desc",
                    icon: "map",
                    type: "navigation",
                    route: { name: "map" },
                },
                {
                    id: "nav-paper",
                    title: "nav_paper",
                    description: "nav_paper_desc",
                    icon: "qrcode",
                    type: "navigation",
                    route: { name: "paper-message" },
                },
                {
                    id: "nav-call",
                    title: "nav_call",
                    description: "nav_call_desc",
                    icon: "phone",
                    type: "navigation",
                    route: { name: "call" },
                },
                {
                    id: "nav-settings",
                    title: "nav_settings",
                    description: "nav_settings_desc",
                    icon: "cog",
                    type: "navigation",
                    route: { name: "settings" },
                },
                {
                    id: "nav-ping",
                    title: "nav_ping",
                    description: "nav_ping_desc",
                    icon: "radar",
                    type: "navigation",
                    route: { name: "ping" },
                },
                {
                    id: "nav-rnprobe",
                    title: "nav_rnprobe",
                    description: "nav_rnprobe_desc",
                    icon: "radar",
                    type: "navigation",
                    route: { name: "rnprobe" },
                },
                {
                    id: "nav-rncp",
                    title: "nav_rncp",
                    description: "nav_rncp_desc",
                    icon: "swap-horizontal",
                    type: "navigation",
                    route: { name: "rncp" },
                },
                {
                    id: "nav-rnstatus",
                    title: "nav_rnstatus",
                    description: "nav_rnstatus_desc",
                    icon: "chart-line",
                    type: "navigation",
                    route: { name: "rnstatus" },
                },
                {
                    id: "nav-rnpath",
                    title: "nav_rnpath",
                    description: "nav_rnpath_desc",
                    icon: "route",
                    type: "navigation",
                    route: { name: "rnpath" },
                },
                {
                    id: "nav-rnpath-trace",
                    title: "nav_rnpath_trace",
                    description: "nav_rnpath_trace_desc",
                    icon: "map-marker-path",
                    type: "navigation",
                    route: { name: "rnpath-trace" },
                },
                {
                    id: "nav-translator",
                    title: "nav_translator",
                    description: "nav_translator_desc",
                    icon: "translate",
                    type: "navigation",
                    route: { name: "translator" },
                },
                {
                    id: "nav-forwarder",
                    title: "nav_forwarder",
                    description: "nav_forwarder_desc",
                    icon: "email-send-outline",
                    type: "navigation",
                    route: { name: "forwarder" },
                },
                {
                    id: "nav-documentation",
                    title: "nav_documentation",
                    description: "nav_documentation_desc",
                    icon: "book-open-variant",
                    type: "navigation",
                    route: { name: "documentation" },
                },
                {
                    id: "nav-micron-editor",
                    title: "nav_micron_editor",
                    description: "nav_micron_editor_desc",
                    icon: "code-tags",
                    type: "navigation",
                    route: { name: "micron-editor" },
                },
                {
                    id: "nav-rnode-flasher",
                    title: "nav_rnode_flasher",
                    description: "nav_rnode_flasher_desc",
                    icon: "flash",
                    type: "navigation",
                    route: { name: "rnode-flasher" },
                },
                {
                    id: "nav-debug-logs",
                    title: "nav_debug_logs",
                    description: "nav_debug_logs_desc",
                    icon: "console",
                    type: "navigation",
                    route: { name: "debug-logs" },
                },
                {
                    id: "action-sync",
                    title: "action_sync",
                    description: "action_sync_desc",
                    icon: "refresh",
                    type: "action",
                    action: "sync",
                },
                {
                    id: "action-compose",
                    title: "action_compose",
                    description: "action_compose_desc",
                    icon: "email-plus",
                    type: "action",
                    action: "compose",
                },
                {
                    id: "action-orbit",
                    title: "action_orbit",
                    description: "action_orbit_desc",
                    icon: "orbit",
                    type: "action",
                    action: "toggle-orbit",
                },
                {
                    id: "action-bouncing-balls",
                    title: "action_bouncing_balls",
                    description: "action_bouncing_balls_desc",
                    icon: "bounce",
                    type: "action",
                    action: "toggle-bouncing-balls",
                },
                {
                    id: "action-getting-started",
                    title: "action_getting_started",
                    description: "action_getting_started_desc",
                    icon: "help-circle",
                    type: "action",
                    action: "show-tutorial",
                },
                {
                    id: "action-changelog",
                    title: "action_changelog",
                    description: "action_changelog_desc",
                    icon: "history",
                    type: "action",
                    action: "show-changelog",
                },
            ],
        };
    },
    computed: {
        allResults() {
            const results = this.actions.map((action) => ({
                ...action,
                title: this.$t(`command_palette.${action.title}`),
                description: this.$t(`command_palette.${action.description}`),
            }));

            // add peers
            if (Array.isArray(this.peers)) {
                for (const peer of this.peers) {
                    results.push({
                        id: `peer-${peer.destination_hash}`,
                        title: peer.custom_display_name ?? peer.display_name,
                        description: peer.destination_hash,
                        icon: peer.lxmf_user_icon?.icon_name ?? "account",
                        iconForeground: peer.lxmf_user_icon?.foreground_colour,
                        iconBackground: peer.lxmf_user_icon?.background_colour,
                        type: "peer",
                        peer: peer,
                    });
                }
            }

            // add contacts
            if (Array.isArray(this.contacts)) {
                for (const contact of this.contacts) {
                    results.push({
                        id: `contact-${contact.id}`,
                        title: contact.name,
                        description: this.$t("app.call") + ` ${contact.remote_identity_hash}`,
                        icon: "phone",
                        type: "contact",
                        contact: contact,
                    });
                }
            }

            return results;
        },
        filteredResults() {
            if (!this.query) return this.allResults.filter((r) => r.type === "navigation" || r.type === "action");
            const q = this.query.toLowerCase();
            return this.allResults.filter(
                (r) => r.title.toLowerCase().includes(q) || r.description.toLowerCase().includes(q)
            );
        },
        groupedResults() {
            const groups = {};
            for (const result of this.filteredResults) {
                const groupName =
                    result.type === "peer"
                        ? "group_recent"
                        : result.type === "contact"
                          ? "group_contacts"
                          : "group_actions";
                if (!groups[groupName]) groups[groupName] = [];
                groups[groupName].push(result);
            }
            return groups;
        },
    },
    watch: {
        filteredResults: {
            handler(newResults) {
                if (
                    newResults.length > 0 &&
                    (!this.highlightedId || !newResults.find((r) => r.id === this.highlightedId))
                ) {
                    this.highlightedId = newResults[0].id;
                }
            },
            immediate: true,
        },
    },
    mounted() {
        window.addEventListener("keydown", this.handleGlobalKeydown, true);
    },
    beforeUnmount() {
        window.removeEventListener("keydown", this.handleGlobalKeydown, true);
    },
    methods: {
        handleGlobalKeydown(e) {
            if ((e.metaKey || e.ctrlKey) && e.key === "k") {
                e.preventDefault();
                e.stopPropagation();
                this.toggle();
            }
        },
        async toggle() {
            if (this.isOpen) {
                this.close();
            } else {
                await this.open();
            }
        },
        async open() {
            this.query = "";
            this.isOpen = true;
            this.loadPeersAndContacts();
            this.$nextTick(() => {
                this.$refs.input?.focus();
            });
        },
        close() {
            this.isOpen = false;
        },
        async loadPeersAndContacts() {
            try {
                // fetch announces for "lxmf.delivery" aspect to get peers
                const peerResponse = await window.api.get(`/api/v1/announces`, {
                    params: { aspect: "lxmf.delivery", limit: 20 },
                });
                this.peers = peerResponse.data.announces;

                // fetch telephone contacts
                const contactResponse = await window.api.get("/api/v1/telephone/contacts");
                this.contacts =
                    contactResponse.data?.contacts ?? (Array.isArray(contactResponse.data) ? contactResponse.data : []);
            } catch (e) {
                console.error("Failed to load command palette data:", e);
            }
        },
        moveHighlight(step) {
            const index = this.filteredResults.findIndex((r) => r.id === this.highlightedId);
            let nextIndex = index + step;
            if (nextIndex < 0) nextIndex = this.filteredResults.length - 1;
            if (nextIndex >= this.filteredResults.length) nextIndex = 0;
            this.highlightedId = this.filteredResults[nextIndex].id;
        },
        executeAction() {
            const result = this.filteredResults.find((r) => r.id === this.highlightedId);
            if (result) this.executeResult(result);
        },
        executeResult(result) {
            this.close();
            if (result.type === "navigation") {
                this.$router.push(result.route);
            } else if (result.type === "peer") {
                this.$router.push({ name: "messages", params: { destinationHash: result.peer.destination_hash } });
            } else if (result.type === "contact") {
                this.dialContact(result.contact.remote_identity_hash);
            } else if (result.type === "action") {
                if (result.action === "sync") {
                    GlobalEmitter.emit("sync-propagation-node");
                } else if (result.action === "compose") {
                    this.$router.push({ name: "messages" });
                    this.$nextTick(() => {
                        const input = document.getElementById("compose-input");
                        input?.focus();
                    });
                } else if (result.action === "toggle-orbit") {
                    GlobalEmitter.emit("toggle-orbit");
                } else if (result.action === "toggle-bouncing-balls") {
                    GlobalEmitter.emit("toggle-bouncing-balls");
                } else if (result.action === "show-tutorial") {
                    GlobalEmitter.emit("show-tutorial");
                } else if (result.action === "show-changelog") {
                    GlobalEmitter.emit("show-changelog");
                }
            }
        },
        async dialContact(hash) {
            try {
                await window.api.get(`/api/v1/telephone/call/${hash}`);
                if (this.$route.name !== "call") {
                    this.$router.push({ name: "call" });
                }
            } catch (e) {
                ToastUtils.error(e.response?.data?.message || "Failed to initiate call");
            }
        },
    },
};
</script>

<style scoped>
.slide-down-enter-active,
.slide-down-leave-active {
    transition: all 0.3s cubic-bezier(0.16, 1, 0.3, 1);
}

.slide-down-enter-from,
.slide-down-leave-to {
    opacity: 0;
    transform: translateY(-20px) scale(0.98);
}

kbd {
    font-family: inherit;
}
</style>
