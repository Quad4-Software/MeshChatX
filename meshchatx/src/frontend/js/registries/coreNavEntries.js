// SPDX-License-Identifier: 0BSD

/** @typedef {'unreadConversationsCount' | 'relayChatUnreadCount' | 'missedCallsCount'} NavBadgeSource */

/**
 * @typedef {Object} NavEntry
 * @property {string} id
 * @property {{ name: string }} route
 * @property {string} icon
 * @property {string} labelKey
 * @property {string} [label]
 * @property {{ source: NavBadgeSource, pill?: boolean, cap?: number } | null} [badge]
 * @property {'rrcEnabled' | null} [visibleWhen]
 * @property {string | null} [pluginId]
 */

/** @type {NavEntry[]} */
export const CORE_NAV_ENTRIES = [
    {
        id: "messages",
        route: { name: "messages" },
        icon: "message-text",
        labelKey: "app.messages",
        badge: { source: "unreadConversationsCount", pill: true, cap: 99 },
    },
    {
        id: "call",
        route: { name: "call" },
        icon: "phone",
        labelKey: "app.audio_calls",
        badge: { source: "missedCallsCount", pill: true, cap: 99 },
    },
    {
        id: "contacts",
        route: { name: "contacts" },
        icon: "account-multiple",
        labelKey: "app.contacts",
    },
    {
        id: "relay-chat",
        route: { name: "relay-chat" },
        icon: "forum",
        labelKey: "app.relay_chat",
        badge: { source: "relayChatUnreadCount", pill: true, cap: 1000 },
        visibleWhen: "rrcEnabled",
    },
    {
        id: "nomadnetwork",
        route: { name: "nomadnetwork" },
        icon: "earth",
        labelKey: "app.nomad_network",
    },
    {
        id: "map",
        route: { name: "map" },
        icon: "map",
        labelKey: "app.map",
    },
    {
        id: "archives",
        route: { name: "archives" },
        icon: "archive",
        labelKey: "app.archives",
    },
    {
        id: "tools",
        route: { name: "tools" },
        icon: "wrench",
        labelKey: "app.tools",
    },
    {
        id: "interfaces",
        route: { name: "interfaces" },
        icon: "router",
        labelKey: "app.interfaces",
    },
    {
        id: "network-visualiser",
        route: { name: "network-visualiser" },
        icon: "hub",
        labelKey: "app.network_visualiser",
    },
    {
        id: "blocked",
        route: { name: "blocked" },
        icon: "gavel",
        labelKey: "banishment.title",
    },
    {
        id: "settings",
        route: { name: "settings" },
        icon: "cog",
        labelKey: "app.settings",
    },
    {
        id: "identities",
        route: { name: "identities" },
        icon: "badge-account",
        labelKey: "app.identities",
    },
    {
        id: "about",
        route: { name: "about" },
        icon: "information",
        labelKey: "app.about",
    },
];
