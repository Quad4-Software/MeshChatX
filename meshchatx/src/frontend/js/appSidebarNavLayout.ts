// SPDX-License-Identifier: 0BSD

export const APP_SIDEBAR_NAV_LAYOUT_KEY = "meshchatx.sidebar.nav_layout";
export const DEFAULT_NAV_GROUP_ORDER = ["communicate", "explore", "app", "network"];
export const NAV_EDIT_HOLD_MS = 500;
export const NAV_EDIT_HOLD_MOVE_PX = 12;

const FORBIDDEN_IDS = new Set(["__proto__", "constructor", "prototype"]);

export type NavPlacement = {
    group: string;
    tier: "primary" | "more";
};

export type NavLayout = {
    version: number;
    groupOrder: string[];
    itemOrder: string[];
    placements: Record<string, NavPlacement>;
};

export type NavItem = {
    id: string;
    group?: string;
    navTier?: string;
    [key: string]: unknown;
};

function readJson(key: string): unknown {
    try {
        if (typeof window === "undefined" || !window.localStorage) {
            return null;
        }
        const raw = window.localStorage.getItem(key);
        if (!raw) {
            return null;
        }
        return JSON.parse(raw);
    } catch {
        return null;
    }
}

function writeJson(key: string, value: unknown): void {
    try {
        if (typeof window === "undefined" || !window.localStorage) {
            return;
        }
        window.localStorage.setItem(key, JSON.stringify(value));
    } catch {
        // persistence is best-effort
    }
}

function cleanId(id: unknown): string {
    if (typeof id !== "string") {
        return "";
    }
    const trimmed = id.trim();
    if (!trimmed || FORBIDDEN_IDS.has(trimmed)) {
        return "";
    }
    return trimmed;
}

export function normalizeNavLayout(raw: unknown): NavLayout | null {
    if (!raw || typeof raw !== "object" || Array.isArray(raw)) {
        return null;
    }
    const rawObj = raw as Record<string, unknown>;
    const groupOrder: string[] = [];
    if (Array.isArray(rawObj.groupOrder)) {
        for (const value of rawObj.groupOrder) {
            const id = cleanId(value);
            if (id && !groupOrder.includes(id)) {
                groupOrder.push(id);
            }
        }
    }
    for (const id of DEFAULT_NAV_GROUP_ORDER) {
        if (!groupOrder.includes(id)) {
            groupOrder.push(id);
        }
    }
    const itemOrder: string[] = [];
    if (Array.isArray(rawObj.itemOrder)) {
        for (const value of rawObj.itemOrder) {
            const id = cleanId(value);
            if (id && !itemOrder.includes(id)) {
                itemOrder.push(id);
            }
        }
    }
    const placements: Record<string, NavPlacement> = Object.create(null);
    const rawPlacements = rawObj.placements;
    if (rawPlacements && typeof rawPlacements === "object" && !Array.isArray(rawPlacements)) {
        const placementsObj = rawPlacements as Record<string, unknown>;
        for (const key of Object.keys(placementsObj)) {
            const id = cleanId(key);
            const entry = placementsObj[key] as Record<string, unknown> | undefined;
            if (!id || !entry || typeof entry !== "object" || Array.isArray(entry)) {
                continue;
            }
            const group = cleanId(entry.group) || "app";
            placements[id] = {
                group,
                tier: entry.tier === "more" ? "more" : "primary",
            };
        }
    }
    return {
        version: 1,
        groupOrder,
        itemOrder,
        placements,
    };
}

export function loadAppSidebarNavLayout(): NavLayout | null {
    return normalizeNavLayout(readJson(APP_SIDEBAR_NAV_LAYOUT_KEY));
}

export function saveAppSidebarNavLayout(layout: NavLayout | null | undefined): void {
    const normalized = normalizeNavLayout(layout);
    if (!normalized) {
        return;
    }
    writeJson(APP_SIDEBAR_NAV_LAYOUT_KEY, normalized);
}

export function cloneNavLayout(layout: NavLayout | null | undefined): NavLayout | null {
    const normalized = normalizeNavLayout(layout);
    if (!normalized) {
        return null;
    }
    return {
        version: 1,
        groupOrder: [...normalized.groupOrder],
        itemOrder: [...normalized.itemOrder],
        placements: { ...normalized.placements },
    };
}

export function defaultNavPlacement(item?: { group?: string; navTier?: string } | null): NavPlacement {
    return {
        group: item?.group || "app",
        tier: item?.navTier === "more" ? "more" : "primary",
    };
}

function placementFor(
    item: { id: string; group?: string; navTier?: string },
    layout: NavLayout | null | undefined
): NavPlacement {
    const saved = layout?.placements?.[item.id];
    if (saved && saved.group && saved.tier) {
        return saved;
    }
    return defaultNavPlacement(item);
}

export function orderItemsByLayout<T extends { id: string }>(items: T[], layout?: NavLayout | null): T[] {
    const byId = new Map(items.map((item) => [item.id, item]));
    const ordered: T[] = [];
    const used = new Set<string>();
    const savedOrder = layout?.itemOrder || [];
    for (const id of savedOrder) {
        const item = byId.get(id);
        if (!item || used.has(id)) {
            continue;
        }
        ordered.push(item);
        used.add(id);
    }
    for (const item of items) {
        if (!used.has(item.id)) {
            ordered.push(item);
        }
    }
    return ordered;
}

export function applyNavLayout<T extends { id: string; group?: string; navTier?: string }>(
    items: T[],
    layout?: NavLayout | null,
    options: { includeEmptyGroups?: boolean } = {}
): { primaryGroups: Array<{ id: string; items: T[] }>; moreItems: T[] } {
    const includeEmptyGroups = options.includeEmptyGroups === true;
    const orderedItems = orderItemsByLayout(items, layout);
    const primaryByGroup: Record<string, T[]> = Object.create(null);
    const moreItems: T[] = [];
    for (const item of orderedItems) {
        const placement = placementFor(item, layout);
        if (placement.tier === "more") {
            moreItems.push(item);
            continue;
        }
        const groupId = placement.group || "app";
        if (!primaryByGroup[groupId]) {
            primaryByGroup[groupId] = [];
        }
        primaryByGroup[groupId].push(item);
    }
    const groupOrder: string[] = [];
    const seen = new Set<string>();
    const savedGroups = layout?.groupOrder?.length ? layout.groupOrder : DEFAULT_NAV_GROUP_ORDER;
    for (const groupId of savedGroups) {
        if (!groupId || seen.has(groupId)) {
            continue;
        }
        groupOrder.push(groupId);
        seen.add(groupId);
    }
    for (const groupId of DEFAULT_NAV_GROUP_ORDER) {
        if (!seen.has(groupId)) {
            groupOrder.push(groupId);
            seen.add(groupId);
        }
    }
    for (const groupId of Object.keys(primaryByGroup)) {
        if (!seen.has(groupId)) {
            groupOrder.push(groupId);
            seen.add(groupId);
        }
    }
    const primaryGroups: Array<{ id: string; items: T[] }> = [];
    for (const groupId of groupOrder) {
        const groupItems = primaryByGroup[groupId] || [];
        if (groupItems.length > 0 || includeEmptyGroups) {
            primaryGroups.push({ id: groupId, items: groupItems });
        }
    }
    return { primaryGroups, moreItems };
}

export function captureNavLayout<T extends { id: string; group?: string }>(
    primaryGroups: Array<{ id: string; items?: T[] }>,
    moreItems?: T[]
): NavLayout {
    const groupOrder: string[] = [];
    const itemOrder: string[] = [];
    const placements: Record<string, NavPlacement> = Object.create(null);
    for (const group of primaryGroups || []) {
        const groupId = cleanId(group?.id);
        if (!groupId || groupOrder.includes(groupId)) {
            continue;
        }
        groupOrder.push(groupId);
        for (const item of group.items || []) {
            const itemId = cleanId(item?.id);
            if (!itemId || itemOrder.includes(itemId)) {
                continue;
            }
            itemOrder.push(itemId);
            placements[itemId] = { group: groupId, tier: "primary" };
        }
    }
    for (const id of DEFAULT_NAV_GROUP_ORDER) {
        if (!groupOrder.includes(id)) {
            groupOrder.push(id);
        }
    }
    for (const item of moreItems || []) {
        const itemId = cleanId(item?.id);
        if (!itemId || itemOrder.includes(itemId)) {
            continue;
        }
        itemOrder.push(itemId);
        placements[itemId] = {
            group: item.group || "app",
            tier: "more",
        };
    }
    return {
        version: 1,
        groupOrder,
        itemOrder,
        placements,
    };
}

function ensurePlacement(layout: NavLayout, itemId: string, placement: NavPlacement): void {
    layout.placements[itemId] = {
        group: placement.group || "app",
        tier: placement.tier === "more" ? "more" : "primary",
    };
}

function layoutFromItems<T extends { id: string; group?: string; navTier?: string }>(
    items: T[],
    layout?: NavLayout | null
): NavLayout {
    const view = applyNavLayout(items, layout);
    return captureNavLayout(view.primaryGroups, view.moreItems);
}

function moveIdInItemOrder<T extends { id: string }>(
    layout: NavLayout,
    items: T[],
    movingId: string,
    insertAt: number
): void {
    const ids = orderItemsByLayout(items, layout).map((item) => item.id);
    const without = ids.filter((id) => id !== movingId);
    const index = Math.max(0, Math.min(insertAt, without.length));
    without.splice(index, 0, movingId);
    layout.itemOrder = without;
}

function layoutOrDefault<T extends { id: string; group?: string; navTier?: string }>(
    layout: NavLayout | null | undefined,
    items: T[]
): NavLayout {
    return cloneNavLayout(layout) || layoutFromItems(items || [], null);
}

export function moveNavItem<T extends { id: string; group?: string; navTier?: string }>(
    layout: NavLayout | null | undefined,
    itemId: string,
    target: { type: string; id?: string; position?: "before" | "after" },
    items: T[],
    options: { preservePlacement?: boolean } = {}
): NavLayout | null {
    const next = layoutOrDefault(layout, items);
    const movingId = cleanId(itemId);
    if (!movingId || !target || typeof target !== "object") {
        return next;
    }
    const preservePlacement = options.preservePlacement === true;
    const byId = new Map((items || []).map((item) => [item.id, item]));
    const movingItem = byId.get(movingId);
    if (!movingItem) {
        return next;
    }
    if (!next.placements[movingId]) {
        ensurePlacement(next, movingId, defaultNavPlacement(movingItem));
    }
    const orderedIds = () => orderItemsByLayout(items, next).map((item) => item.id);

    if (target.type === "item") {
        const targetId = cleanId(target.id);
        if (!targetId || targetId === movingId) {
            return next;
        }
        const targetItem = byId.get(targetId);
        if (!targetItem) {
            return next;
        }
        if (!preservePlacement) {
            ensurePlacement(next, movingId, placementFor(targetItem, next));
        }
        const ids = orderedIds();
        const without = ids.filter((id) => id !== movingId);
        let insertAt = without.indexOf(targetId);
        if (insertAt < 0) {
            insertAt = without.length;
        } else if (target.position === "after") {
            insertAt += 1;
        }
        without.splice(insertAt, 0, movingId);
        next.itemOrder = without;
        return next;
    }

    if (target.type === "group" || target.type === "group-start" || target.type === "group-end") {
        const groupId = cleanId(target.id) || "app";
        if (!preservePlacement) {
            ensurePlacement(next, movingId, { group: groupId, tier: "primary" });
        }
        const view = applyNavLayout(items, next, { includeEmptyGroups: true });
        const groupItems = (view.primaryGroups.find((entry) => entry.id === groupId)?.items || []).filter(
            (item) => item.id !== movingId
        );
        if (target.type === "group-end" && groupItems.length > 0) {
            const lastId = groupItems[groupItems.length - 1].id;
            const ids = orderedIds().filter((id) => id !== movingId);
            const insertAt = ids.indexOf(lastId);
            moveIdInItemOrder(next, items, movingId, insertAt < 0 ? ids.length : insertAt + 1);
            return next;
        }
        if (groupItems.length > 0) {
            const firstId = groupItems[0].id;
            const ids = orderedIds().filter((id) => id !== movingId);
            const insertAt = ids.indexOf(firstId);
            moveIdInItemOrder(next, items, movingId, insertAt < 0 ? 0 : insertAt);
            return next;
        }
        const firstMore = view.moreItems.find((item) => item.id !== movingId);
        const ids = orderedIds().filter((id) => id !== movingId);
        const insertAt = firstMore ? ids.indexOf(firstMore.id) : ids.length;
        moveIdInItemOrder(next, items, movingId, insertAt < 0 ? ids.length : insertAt);
        return next;
    }

    if (target.type === "more" || target.type === "more-start" || target.type === "more-end") {
        if (!preservePlacement) {
            const current = next.placements[movingId] || defaultNavPlacement(movingItem);
            ensurePlacement(next, movingId, { group: current.group, tier: "more" });
        }
        const view = applyNavLayout(items, next);
        const moreItems = view.moreItems.filter((item) => item.id !== movingId);
        const ids = orderedIds().filter((id) => id !== movingId);
        if (target.type === "more-end" && moreItems.length > 0) {
            const lastId = moreItems[moreItems.length - 1].id;
            const insertAt = ids.indexOf(lastId);
            moveIdInItemOrder(next, items, movingId, insertAt < 0 ? ids.length : insertAt + 1);
            return next;
        }
        if (moreItems.length > 0) {
            const insertAt = ids.indexOf(moreItems[0].id);
            moveIdInItemOrder(next, items, movingId, insertAt < 0 ? ids.length : insertAt);
            return next;
        }
        moveIdInItemOrder(next, items, movingId, ids.length);
        return next;
    }
    return next;
}

export function moveNavItemByOffset<T extends { id: string; group?: string; navTier?: string }>(
    layout: NavLayout | null | undefined,
    itemId: string,
    delta: number,
    items: T[],
    options: { preservePlacement?: boolean } = {}
): NavLayout | null {
    const movingId = cleanId(itemId);
    const step = delta > 0 ? 1 : delta < 0 ? -1 : 0;
    if (!movingId || step === 0) {
        return cloneNavLayout(layout);
    }
    const preservePlacement = options.preservePlacement === true;
    const view = applyNavLayout(items, layout, { includeEmptyGroups: false });
    const sequence = preservePlacement
        ? orderItemsByLayout(items, layout)
        : [...view.primaryGroups.flatMap((group) => group.items), ...view.moreItems];
    const from = sequence.findIndex((item) => item.id === movingId);
    const to = from + step;
    if (from < 0 || to < 0 || to >= sequence.length) {
        return cloneNavLayout(layout) || captureNavLayout(view.primaryGroups, view.moreItems);
    }
    const target = sequence[to];
    return moveNavItem(
        layout,
        movingId,
        { type: "item", id: target.id, position: step > 0 ? "after" : "before" },
        items,
        options
    );
}

export function moveNavGroup(
    layout: NavLayout | null | undefined,
    groupId: string,
    beforeGroupId?: string | null
): NavLayout | null {
    const next = cloneNavLayout(layout);
    if (!next) {
        return next;
    }
    const movingId = cleanId(groupId);
    if (!movingId) {
        return next;
    }
    if (!next.groupOrder.includes(movingId)) {
        next.groupOrder.push(movingId);
    }
    const without: string[] = next.groupOrder.filter((id) => id !== movingId);
    const beforeId = cleanId(beforeGroupId);
    if (!beforeId) {
        without.push(movingId);
        next.groupOrder = without;
        return next;
    }
    const insertAt = without.indexOf(beforeId);
    if (insertAt < 0) {
        without.push(movingId);
    } else {
        without.splice(insertAt, 0, movingId);
    }
    next.groupOrder = without;
    return next;
}

export function moveNavGroupByOffset(
    layout: NavLayout | null | undefined,
    groupId: string,
    delta: number
): NavLayout | null {
    const next = cloneNavLayout(layout);
    if (!next) {
        return next;
    }
    const movingId = cleanId(groupId);
    const step = delta > 0 ? 1 : delta < 0 ? -1 : 0;
    if (!movingId || step === 0) {
        return next;
    }
    const from = next.groupOrder.indexOf(movingId);
    if (from < 0) {
        return next;
    }
    const to = from + step;
    if (to < 0 || to >= next.groupOrder.length) {
        return next;
    }
    const without: string[] = next.groupOrder.filter((id) => id !== movingId);
    without.splice(to, 0, movingId);
    next.groupOrder = without;
    return next;
}
