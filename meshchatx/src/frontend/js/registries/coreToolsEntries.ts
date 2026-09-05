// SPDX-License-Identifier: 0BSD

/**
 * @typedef {Object} ToolEntry
 * @property {string} name
 * @property {{ name: string } | null} [route]
 * @property {string | null} [icon]
 * @property {string} iconBg
 * @property {string} titleKey
 * @property {string} descriptionKey
 * @property {string} [title]
 * @property {string} [description]
 * @property {boolean} [alpha]
 * @property {boolean} [beta]
 * @property {boolean} [comingSoon]
 * @property {string} [customClass]
 * @property {string} [image]
 * @property {string} [imageClass]
 * @property {string} [imageAlt]
 * @property {{ href: string, target: string, icon: string }} [extraAction]
 * @property {string | null} [pluginId]
 * @property {'diagnostics' | 'transfer' | 'messaging' | 'network' | 'other'} [group]
 */

/** @type {ToolEntry[]} */
export const CORE_TOOLS_ENTRIES = [
    {
        name: "ping",
        route: { name: "ping" },
        icon: "radar",
        iconBg: "tool-card__icon bg-blue-50 text-blue-500 dark:bg-blue-900/30 dark:text-blue-200",
        titleKey: "tools.ping.title",
        descriptionKey: "tools.ping.description",
        group: "diagnostics",
    },
    {
        name: "rnprobe",
        route: { name: "rnprobe" },
        icon: "radar",
        iconBg: "tool-card__icon bg-purple-50 text-purple-500 dark:bg-purple-900/30 dark:text-purple-200",
        titleKey: "tools.rnprobe.title",
        descriptionKey: "tools.rnprobe.description",
        group: "diagnostics",
    },
    {
        name: "rnstatus",
        route: { name: "rnstatus" },
        icon: "chart-line",
        iconBg: "tool-card__icon bg-orange-50 text-orange-500 dark:bg-orange-900/30 dark:text-orange-200",
        titleKey: "tools.rnstatus.title",
        descriptionKey: "tools.rnstatus.description",
        group: "diagnostics",
    },
    {
        name: "rnpath",
        route: { name: "rnpath" },
        icon: "route",
        iconBg: "tool-card__icon bg-indigo-50 text-indigo-500 dark:bg-indigo-900/30 dark:text-indigo-200",
        titleKey: "tools.rnpath.title",
        descriptionKey: "tools.rnpath.description",
        group: "diagnostics",
    },
    {
        name: "rnpath-trace",
        route: { name: "rnpath-trace" },
        icon: "map-marker-path",
        iconBg: "tool-card__icon bg-blue-50 text-blue-500 dark:bg-blue-900/30 dark:text-blue-200",
        titleKey: "tools.rnpath_trace.title",
        descriptionKey: "tools.rnpath_trace.description",
        group: "diagnostics",
    },
    {
        name: "rncp",
        route: { name: "rncp" },
        icon: "swap-horizontal",
        iconBg: "tool-card__icon bg-green-50 text-green-500 dark:bg-green-900/30 dark:text-green-200",
        titleKey: "tools.rncp.title",
        descriptionKey: "tools.rncp.description",
        group: "transfer",
    },
    {
        name: "rns-filesync",
        route: { name: "rns-filesync" },
        icon: "folder-sync",
        iconBg: "tool-card__icon bg-emerald-50 text-emerald-500 dark:bg-emerald-900/30 dark:text-emerald-200",
        titleKey: "tools.rns_filesync.title",
        descriptionKey: "tools.rns_filesync.description",
        alpha: true,
        group: "transfer",
    },
    {
        name: "rnsh",
        route: { name: "rnsh" },
        icon: "console-network-outline",
        iconBg: "tool-card__icon bg-indigo-50 text-indigo-600 dark:bg-indigo-900/30 dark:text-indigo-200",
        titleKey: "tools.rnsh.title",
        descriptionKey: "tools.rnsh.description",
        alpha: true,
        group: "network",
    },
    {
        name: "rnx",
        route: { name: "rnx" },
        icon: "console",
        iconBg: "tool-card__icon bg-teal-50 text-teal-600 dark:bg-teal-900/30 dark:text-teal-200",
        titleKey: "tools.rnx.title",
        descriptionKey: "tools.rnx.description",
        alpha: true,
        group: "network",
    },
    {
        name: "propagation-nodes",
        route: { name: "propagation-nodes" },
        icon: "mailbox",
        iconBg: "tool-card__icon bg-cyan-50 text-cyan-500 dark:bg-cyan-900/30 dark:text-cyan-200",
        titleKey: "tools.propagation_nodes.title",
        descriptionKey: "tools.propagation_nodes.description",
        group: "messaging",
    },
    {
        name: "forwarder",
        route: { name: "forwarder" },
        icon: "email-send-outline",
        iconBg: "tool-card__icon bg-rose-50 text-rose-500 dark:bg-rose-900/30 dark:text-rose-200",
        titleKey: "tools.forwarder.title",
        descriptionKey: "tools.forwarder.description",
        group: "messaging",
    },
    {
        name: "sieve-filters",
        route: { name: "sieve-filters" },
        icon: "filter-variant",
        iconBg: "tool-card__icon bg-violet-50 text-violet-600 dark:bg-violet-900/30 dark:text-violet-200",
        titleKey: "tools.sieve_filters.title",
        descriptionKey: "tools.sieve_filters.description",
        group: "messaging",
    },
    {
        name: "message-blocklist",
        route: { name: "message-blocklist" },
        icon: "shield-alert",
        iconBg: "tool-card__icon bg-rose-50 text-rose-600 dark:bg-rose-900/30 dark:text-rose-200",
        titleKey: "tools.message_blocklist.title",
        descriptionKey: "tools.message_blocklist.description",
        beta: true,
        group: "messaging",
    },
    {
        name: "bots",
        route: { name: "bots" },
        icon: "robot",
        iconBg: "tool-card__icon bg-blue-50 text-blue-500 dark:bg-blue-900/30 dark:text-blue-200",
        titleKey: "tools.bots.title",
        descriptionKey: "tools.bots.description",
        group: "other",
    },
    {
        name: "paper-message",
        route: { name: "paper-message" },
        icon: "qrcode",
        iconBg: "tool-card__icon bg-blue-50 text-blue-500 dark:bg-blue-900/30 dark:text-blue-200",
        titleKey: "tools.paper_message.title",
        descriptionKey: "tools.paper_message.description",
        group: "messaging",
    },
    {
        name: "translator",
        route: { name: "translator" },
        icon: "translate",
        iconBg: "tool-card__icon bg-indigo-50 text-indigo-500 dark:bg-indigo-900/30 dark:text-indigo-200",
        titleKey: "tools.translator.title",
        descriptionKey: "tools.translator.description",
        group: "messaging",
    },
    {
        name: "micron-editor",
        route: { name: "micron-editor" },
        icon: "code-tags",
        iconBg: "tool-card__icon bg-teal-50 text-teal-500 dark:bg-teal-900/30 dark:text-teal-200",
        titleKey: "tools.micron_editor.title",
        descriptionKey: "tools.micron_editor.description",
        group: "other",
    },
    {
        name: "documentation",
        route: { name: "documentation" },
        icon: "book-open-variant",
        iconBg: "tool-card__icon bg-cyan-50 text-cyan-500 dark:bg-cyan-900/30 dark:text-cyan-200",
        titleKey: "docs.title",
        descriptionKey: "docs.subtitle",
        group: "other",
    },
    {
        name: "repository-server",
        route: { name: "repository-server" },
        icon: "package-variant",
        iconBg: "tool-card__icon bg-sky-50 text-sky-600 dark:bg-sky-900/30 dark:text-sky-200",
        titleKey: "tools.repository_server.title",
        descriptionKey: "tools.repository_server.description",
        group: "network",
    },
    {
        name: "reticulum-config-editor",
        route: { name: "reticulum-config-editor" },
        icon: "file-cog",
        iconBg: "tool-card__icon bg-blue-50 text-blue-500 dark:bg-blue-900/30 dark:text-blue-200",
        titleKey: "tools.reticulum_config_editor.title",
        descriptionKey: "tools.reticulum_config_editor.description",
        group: "network",
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
        group: "network",
    },
    {
        name: "mesh-server",
        route: { name: "mesh-server" },
        icon: "server-network",
        iconBg: "tool-card__icon bg-amber-50 text-amber-500 dark:bg-amber-900/30 dark:text-amber-200",
        titleKey: "tools.mesh_server.title",
        descriptionKey: "tools.mesh_server.description",
        group: "network",
    },
    {
        name: "rns-tunnel",
        comingSoon: true,
        icon: "tunnel",
        iconBg: "tool-card__icon bg-indigo-50 text-indigo-500 dark:bg-indigo-900/30 dark:text-indigo-200",
        titleKey: "tools.rns_tunnel.title",
        descriptionKey: "tools.rns_tunnel.description",
        group: "network",
    },
    {
        name: "debug-logs",
        route: { name: "debug-logs" },
        icon: "console",
        iconBg: "tool-card__icon bg-zinc-100 text-zinc-500 dark:bg-zinc-800 dark:text-zinc-400",
        titleKey: "debug.title",
        descriptionKey: "debug.description",
        customClass: "bg-amber-50/50 dark:bg-transparent",
        group: "other",
    },
];
