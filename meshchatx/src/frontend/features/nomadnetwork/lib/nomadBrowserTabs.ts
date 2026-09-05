// SPDX-License-Identifier: 0BSD

import LinkUtils from "../../../js/LinkUtils.js";
import { loadNomadTabs, saveNomadTabs } from "../../../js/browserLayoutStore.js";
import { DEFAULT_PAGE_PATH } from "./constants.js";
import type { NomadTab } from "./types.js";

let tabIdCounter = 1;

export function sanitizeNomadTabPath(path: string | null | undefined): string | null {
    if (typeof path !== "string" || path.length === 0) {
        return null;
    }
    if (LinkUtils.httpUrlHrefOrNull(path.trim())) {
        return null;
    }
    return path;
}

export function isExternalNomadTabPath(path: string | null | undefined): boolean {
    return typeof path === "string" && LinkUtils.httpUrlHrefOrNull(path.trim()) != null;
}

export function buildTabLayoutSignature(tabs: NomadTab[], activeTabId: number | null): string {
    const persistable = tabs.filter((tab) => !tab.private);
    const serialized = persistable
        .map((tab) => `${tab.destinationHash || ""}|${tab.path || ""}|${tab.title || ""}`)
        .join("\u241f");
    const activeIndex = persistable.findIndex((tab) => tab.id === activeTabId);
    return `${activeIndex}\u241e${serialized}`;
}

export function restoreTabsFromStorage(
    routeHash: string,
    routePath: string | null,
    forceNewTab = false
): { tabs: NomadTab[]; activeTabId: number; nextId: number } | null {
    const saved = loadNomadTabs();
    if (!saved || !Array.isArray(saved.tabs) || saved.tabs.length === 0) {
        return null;
    }

    let nextId = 1;
    const restoredTabs: NomadTab[] = saved.tabs
        .map((tab) => {
            const rawHash = typeof tab.destinationHash === "string" ? tab.destinationHash : "";
            const validHash = /^[0-9a-fA-F]{32}$/.test(rawHash) ? rawHash : "";
            const cleanPath = sanitizeNomadTabPath(tab.path);
            return {
                id: nextId++,
                destinationHash: validHash,
                initialPath: cleanPath,
                path: cleanPath,
                title: typeof tab.title === "string" ? tab.title : null,
                private: false,
            };
        })
        .filter((tab) => !isExternalNomadTabPath(tab.path));

    if (restoredTabs.length === 0) {
        return null;
    }

    const validIndex =
        Number.isInteger(saved.activeIndex) && saved.activeIndex >= 0 && saved.activeIndex < restoredTabs.length
            ? saved.activeIndex
            : 0;
    let activeTabId = restoredTabs[validIndex].id;

    if (routeHash) {
        if (forceNewTab) {
            const newId = nextId++;
            restoredTabs.push({
                id: newId,
                destinationHash: routeHash,
                initialPath: routePath,
                path: routePath,
                title: null,
                private: false,
            });
            activeTabId = newId;
        } else {
            const existing = restoredTabs.find((tab) => tab.destinationHash === routeHash);
            if (existing) {
                activeTabId = existing.id;
            } else {
                const newId = nextId++;
                restoredTabs.push({
                    id: newId,
                    destinationHash: routeHash,
                    initialPath: routePath,
                    path: routePath,
                    title: null,
                    private: false,
                });
                activeTabId = newId;
            }
        }
    }

    return { tabs: restoredTabs, activeTabId, nextId };
}

export function persistTabsToStorage(tabs: NomadTab[], activeTabId: number | null): void {
    const persistable = tabs.filter((tab) => !tab.private);
    if (persistable.length === 0) {
        saveNomadTabs({ tabs: [], activeIndex: 0 });
        return;
    }
    let activeIndex = persistable.findIndex((tab) => tab.id === activeTabId);
    if (activeIndex < 0) {
        activeIndex = 0;
    }
    saveNomadTabs({
        tabs: persistable.map((tab) => ({
            destinationHash: tab.destinationHash || "",
            path: sanitizeNomadTabPath(tab.path),
            title: tab.title || null,
        })),
        activeIndex,
    });
}

export function tabDisplayTitle(tab: NomadTab, fallbackNewTab: string, fallbackPrivateTab: string): string {
    if (tab.title) {
        return tab.title;
    }
    if (tab.destinationHash) {
        return tab.destinationHash.slice(0, 12);
    }
    return tab.private ? fallbackPrivateTab : fallbackNewTab;
}

export function calculateRelativeTabIndex(tabs: NomadTab[], activeTabId: number | null, offset: number): number {
    if (tabs.length < 2) {
        return -1;
    }
    const index = tabs.findIndex((tab) => tab.id === activeTabId);
    if (index === -1) {
        return -1;
    }
    return (index + offset + tabs.length) % tabs.length;
}

export function createNomadTab(
    destinationHash = "",
    path: string | null = DEFAULT_PAGE_PATH,
    isPrivate = false
): NomadTab {
    const cleanPath = sanitizeNomadTabPath(path) || DEFAULT_PAGE_PATH;
    return {
        id: ++tabIdCounter,
        destinationHash,
        initialPath: cleanPath,
        path: cleanPath,
        title: null,
        private: isPrivate,
    };
}

export function restoreNomadTabs(
    routeHash = "",
    routePath: string | null = null,
    forceNewTab = false
): { tabs: NomadTab[]; selectedTabId: number | null } {
    const restored = restoreTabsFromStorage(routeHash, routePath, forceNewTab);
    if (!restored) {
        return { tabs: [], selectedTabId: null };
    }
    if (restored.nextId > tabIdCounter) {
        tabIdCounter = restored.nextId;
    }
    return {
        tabs: restored.tabs,
        selectedTabId: restored.activeTabId,
    };
}

export function persistNomadTabs(tabs: NomadTab[], selectedTabId: number | null): void {
    persistTabsToStorage(tabs, selectedTabId);
}

export function closeNomadTab(
    tabs: NomadTab[],
    selectedTabId: number | null,
    tabIdToClose: number
): { tabs: NomadTab[]; selectedTabId: number | null } {
    const index = tabs.findIndex((tab) => tab.id === tabIdToClose);
    if (index === -1) {
        return { tabs, selectedTabId };
    }
    const nextTabs = tabs.filter((tab) => tab.id !== tabIdToClose);
    let nextSelectedTabId = selectedTabId;
    if (selectedTabId === tabIdToClose) {
        if (nextTabs.length === 0) {
            nextSelectedTabId = null;
        } else {
            const nextIndex = Math.min(index, nextTabs.length - 1);
            nextSelectedTabId = nextTabs[nextIndex].id;
        }
    }
    return { tabs: nextTabs, selectedTabId: nextSelectedTabId };
}

export function closeTabsToRight(
    tabs: NomadTab[],
    selectedTabId: number | null,
    tabId: number
): { tabs: NomadTab[]; selectedTabId: number | null } {
    const index = tabs.findIndex((tab) => tab.id === tabId);
    if (index === -1) {
        return { tabs, selectedTabId };
    }
    const nextTabs = tabs.slice(0, index + 1);
    let nextSelectedTabId = selectedTabId;
    if (!nextTabs.some((tab) => tab.id === selectedTabId)) {
        nextSelectedTabId = tabId;
    }
    return { tabs: nextTabs, selectedTabId: nextSelectedTabId };
}

export function closeOtherTabs(tabs: NomadTab[], tabId: number): { tabs: NomadTab[]; selectedTabId: number } {
    const target = tabs.find((tab) => tab.id === tabId);
    if (!target) {
        return { tabs, selectedTabId: tabs[0]?.id ?? 0 };
    }
    return { tabs: [target], selectedTabId: tabId };
}
