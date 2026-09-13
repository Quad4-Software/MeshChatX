// SPDX-License-Identifier: 0BSD

export type NavBadgeSource = "unreadConversationsCount" | "relayChatUnreadCount" | "missedCallsCount";

export type NavTier = "primary" | "more";

export type NavGroup = "communicate" | "explore" | "network" | "app";

export interface NavEntry {
    id: string;
    route: { name: string };
    icon: string;
    labelKey: string;
    label?: string;
    badge?: { source: NavBadgeSource; pill?: boolean; cap?: number } | null;
    visibleWhen?: "rrcEnabled" | null;
    pluginId?: string | null;
    navTier?: NavTier;
    group?: NavGroup;
}

export const CORE_NAV_ENTRIES: NavEntry[] = [
    {
        id: "messages",
        route: { name: "messages" },
        icon: "message-text",
        labelKey: "app.messages",
        badge: { source: "unreadConversationsCount", pill: true, cap: 99 },
        navTier: "primary",
        group: "communicate",
    },
    {
        id: "call",
        route: { name: "call" },
        icon: "phone",
        labelKey: "app.audio_calls",
        badge: { source: "missedCallsCount", pill: true, cap: 99 },
        navTier: "primary",
        group: "communicate",
    },
    {
        id: "contacts",
        route: { name: "contacts" },
        icon: "account-multiple",
        labelKey: "app.contacts",
        navTier: "primary",
        group: "communicate",
    },
    {
        id: "relay-chat",
        route: { name: "relay-chat" },
        icon: "forum",
        labelKey: "app.relay_chat",
        badge: { source: "relayChatUnreadCount", pill: true, cap: 1000 },
        visibleWhen: "rrcEnabled",
        navTier: "primary",
        group: "communicate",
    },
    {
        id: "nomadnetwork",
        route: { name: "nomadnetwork" },
        icon: "earth",
        labelKey: "app.nomad_network",
        navTier: "primary",
        group: "explore",
    },
    {
        id: "map",
        route: { name: "map" },
        icon: "map",
        labelKey: "app.map",
        navTier: "primary",
        group: "explore",
    },
    {
        id: "network-visualiser",
        route: { name: "network-visualiser" },
        icon: "hub",
        labelKey: "app.network_visualiser",
        navTier: "primary",
        group: "explore",
    },
    {
        id: "interfaces",
        route: { name: "interfaces" },
        icon: "router",
        labelKey: "app.interfaces",
        navTier: "primary",
        group: "app",
    },
    {
        id: "tools",
        route: { name: "tools" },
        icon: "wrench",
        labelKey: "app.tools",
        navTier: "primary",
        group: "app",
    },
    {
        id: "settings",
        route: { name: "settings" },
        icon: "cog",
        labelKey: "app.settings",
        navTier: "primary",
        group: "app",
    },
    {
        id: "archives",
        route: { name: "archives" },
        icon: "archive",
        labelKey: "app.archives",
        navTier: "more",
        group: "explore",
    },
    {
        id: "blocked",
        route: { name: "blocked" },
        icon: "gavel",
        labelKey: "banishment.title",
        navTier: "more",
        group: "network",
    },
    {
        id: "identities",
        route: { name: "identities" },
        icon: "badge-account",
        labelKey: "app.identities",
        navTier: "more",
        group: "app",
    },
    {
        id: "about",
        route: { name: "about" },
        icon: "information",
        labelKey: "app.about",
        navTier: "more",
        group: "app",
    },
];
