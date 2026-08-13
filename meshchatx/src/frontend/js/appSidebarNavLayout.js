// SPDX-License-Identifier: 0BSD

export const APP_SIDEBAR_NAV_LAYOUT_KEY = "meshchatx.sidebar.nav_layout";
export const DEFAULT_NAV_GROUP_ORDER = ["communicate", "explore", "app", "network"];
export const NAV_EDIT_HOLD_MS = 500;
export const NAV_EDIT_HOLD_MOVE_PX = 12;

const FORBIDDEN_IDS = new Set(["__proto__", "constructor", "prototype"]);

/**
 * @typedef {{ group: string, tier: "primary" | "more" }} NavPlacement
 * @typedef {{ version: number, groupOrder: string[], itemOrder: string[], placements: Record<string, NavPlacement> }} NavLayout
 */

/**
 * @param {string} key
 * @returns {unknown}
 */
function readJson(key) {
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

/**
 * @param {string} key
 * @param {unknown} value
 */
function writeJson(key, value) {
    try {
        if (typeof window === "undefined" || !window.localStorage) {
            return;
        }
        window.localStorage.setItem(key, JSON.stringify(value));
    } catch {
        // persistence is best-effort
    }
}

/**
 * @param {unknown} id
 * @returns {string}
 */
function cleanId(id) {
    if (typeof id !== "string") {
        return "";
    }
    const trimmed = id.trim();
    if (!trimmed || FORBIDDEN_IDS.has(trimmed)) {
        return "";
    }
    return trimmed;
}

/**
 * @param {unknown} raw
 * @returns {NavLayout | null}
 */
export function normalizeNavLayout(raw) {
    if (!raw || typeof raw !== "object" || Array.isArray(raw)) {
        return null;
    }
    const groupOrder = [];
    if (Array.isArray(raw.groupOrder)) {
        for (const value of raw.groupOrder) {
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
    const itemOrder = [];
    if (Array.isArray(raw.itemOrder)) {
        for (const value of raw.itemOrder) {
            const id = cleanId(value);
            if (id && !itemOrder.includes(id)) {
                itemOrder.push(id);
            }
        }
    }
    const placements = Object.create(null);
    const rawPlacements = raw.placements;
    if (rawPlacements && typeof rawPlacements === "object" && !Array.isArray(rawPlacements)) {
        for (const key of Object.keys(rawPlacements)) {
            const id = cleanId(key);
            const entry = rawPlacements[key];
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

/**
 * @returns {NavLayout | null}
 */
export function loadAppSidebarNavLayout() {
    return normalizeNavLayout(readJson(APP_SIDEBAR_NAV_LAYOUT_KEY));
}

/**
 * @param {NavLayout | null | undefined} layout
 */
export function saveAppSidebarNavLayout(layout) {
    const normalized = normalizeNavLayout(layout);
    if (!normalized) {
        return;
    }
    writeJson(APP_SIDEBAR_NAV_LAYOUT_KEY, normalized);
}

/**
 * @param {NavLayout | null | undefined} layout
 * @returns {NavLayout | null}
 */
export function cloneNavLayout(layout) {
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

/**
 * @param {{ id?: string, group?: string, navTier?: string }} item
 * @returns {NavPlacement}
 */
export function defaultNavPlacement(item) {
    return {
        group: item?.group || "app",
        tier: item?.navTier === "more" ? "more" : "primary",
    };
}

/**
 * @param {{ id: string, group?: string, navTier?: string }} item
 * @param {NavLayout | null | undefined} layout
 * @returns {NavPlacement}
 */
function placementFor(item, layout) {
    const saved = layout?.placements?.[item.id];
    if (saved && saved.group && saved.tier) {
        return saved;
    }
    return defaultNavPlacement(item);
}

/**
 * @param {Array<{ id: string, group?: string, navTier?: string }>} items
 * @param {NavLayout | null | undefined} layout
 * @returns {typeof items}
 */
export function orderItemsByLayout(items, layout) {
    const byId = new Map(items.map((item) => [item.id, item]));
    const ordered = [];
    const used = new Set();
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

/**
 * @param {Array<{ id: string, group?: string, navTier?: string }>} items
 * @param {NavLayout | null | undefined} layout
 * @param {{ includeEmptyGroups?: boolean }} [options]
 * @returns {{ primaryGroups: Array<{ id: string, items: typeof items }>, moreItems: typeof items }}
 */
export function applyNavLayout(items, layout, options = {}) {
    const includeEmptyGroups = options.includeEmptyGroups === true;
    const orderedItems = orderItemsByLayout(items, layout);
    const primaryByGroup = Object.create(null);
    const moreItems = [];
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
    const groupOrder = [];
    const seen = new Set();
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
    const primaryGroups = [];
    for (const groupId of groupOrder) {
        const groupItems = primaryByGroup[groupId] || [];
        if (groupItems.length > 0 || includeEmptyGroups) {
            primaryGroups.push({ id: groupId, items: groupItems });
        }
    }
    return { primaryGroups, moreItems };
}

/**
 * @param {Array<{ id: string, items: Array<{ id: string, group?: string }> }>} primaryGroups
 * @param {Array<{ id: string, group?: string }>} moreItems
 * @returns {NavLayout}
 */
export function captureNavLayout(primaryGroups, moreItems) {
    const groupOrder = [];
    const itemOrder = [];
    const placements = Object.create(null);
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

/**
 * @param {NavLayout} layout
 * @param {string} itemId
 * @param {NavPlacement} placement
 */
function ensurePlacement(layout, itemId, placement) {
    layout.placements[itemId] = {
        group: placement.group || "app",
        tier: placement.tier === "more" ? "more" : "primary",
    };
}

/**
 * @param {Array<{ id: string, group?: string, navTier?: string }>} items
 * @param {NavLayout | null | undefined} layout
 * @returns {NavLayout}
 */
function layoutFromItems(items, layout) {
    const view = applyNavLayout(items, layout);
    return captureNavLayout(view.primaryGroups, view.moreItems);
}

/**
 * @param {NavLayout} layout
 * @param {Array<{ id: string }>} items
 * @param {string} movingId
 * @param {number} insertAt
 */
function moveIdInItemOrder(layout, items, movingId, insertAt) {
    const ids = orderItemsByLayout(items, layout).map((item) => item.id);
    const without = ids.filter((id) => id !== movingId);
    const index = Math.max(0, Math.min(insertAt, without.length));
    without.splice(index, 0, movingId);
    layout.itemOrder = without;
}

/**
 * @param {NavLayout | null | undefined} layout
 * @param {Array<{ id: string, group?: string, navTier?: string }>} items
 * @returns {NavLayout}
 */
function layoutOrDefault(layout, items) {
    return cloneNavLayout(layout) || layoutFromItems(items || [], null);
}

/**
 * @param {NavLayout | null | undefined} layout
 * @param {string} itemId
 * @param {{ type: string, id?: string, position?: "before" | "after" }} target
 * @param {Array<{ id: string, group?: string, navTier?: string }>} items
 * @param {{ preservePlacement?: boolean }} [options]
 * @returns {NavLayout | null}
 */
export function moveNavItem(layout, itemId, target, items, options = {}) {
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

/**
 * @param {NavLayout | null | undefined} layout
 * @param {string} itemId
 * @param {number} delta
 * @param {Array<{ id: string, group?: string, navTier?: string }>} items
 * @param {{ preservePlacement?: boolean }} [options]
 * @returns {NavLayout | null}
 */
export function moveNavItemByOffset(layout, itemId, delta, items, options = {}) {
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

/**
 * @param {NavLayout | null | undefined} layout
 * @param {string} groupId
 * @param {string | null | undefined} beforeGroupId
 * @returns {NavLayout | null}
 */
export function moveNavGroup(layout, groupId, beforeGroupId) {
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
    const without = next.groupOrder.filter((id) => id !== movingId);
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

/**
 * @param {NavLayout | null | undefined} layout
 * @param {string} groupId
 * @param {number} delta
 * @returns {NavLayout | null}
 */
export function moveNavGroupByOffset(layout, groupId, delta) {
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
    const without = next.groupOrder.filter((id) => id !== movingId);
    without.splice(to, 0, movingId);
    next.groupOrder = without;
    return next;
}
