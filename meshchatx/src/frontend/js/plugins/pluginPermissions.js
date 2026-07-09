// SPDX-License-Identifier: 0BSD

/**
 * @param {string} permissionId
 * @param {(key: string, values?: Record<string, unknown>) => string} t
 * @returns {string}
 */
export function permissionLabel(permissionId, t) {
    const key = `plugins.permissions.${String(permissionId).replaceAll(":", ".")}`;
    const translated = t(key);
    if (translated && translated !== key) {
        return translated;
    }
    return permissionId;
}

/**
 * @param {Record<string, unknown> | null | undefined} manifest
 * @returns {string[]}
 */
export function declaredPermissionIds(manifest) {
    const permissions = manifest?.permissions || {};
    /** @type {string[]} */
    const ids = [];
    if (Array.isArray(permissions.hooks)) {
        for (const hook of permissions.hooks) {
            if (typeof hook === "string" && hook.trim()) {
                ids.push(`hooks:${hook.trim()}`);
            }
        }
    }
    if (Array.isArray(permissions.managers)) {
        for (const manager of permissions.managers) {
            if (typeof manager === "string" && manager.trim()) {
                ids.push(`managers:${manager.trim()}`);
            }
        }
    }
    if (typeof permissions.storage === "string" && permissions.storage && permissions.storage !== "none") {
        ids.push(`storage:${permissions.storage}`);
    }
    const network = permissions.network;
    if (network && network !== "none") {
        ids.push("network:fetch");
    }
    return [...new Set(ids)];
}

/**
 * @param {Record<string, unknown> | null | undefined} manifest
 * @param {(key: string, values?: Record<string, unknown>) => string} t
 * @returns {string[]}
 */
export function manifestPermissionSummary(manifest, t = (key) => key) {
    const ids =
        Array.isArray(manifest?.declared_permissions) && manifest.declared_permissions.length
            ? manifest.declared_permissions
            : declaredPermissionIds(manifest);
    if (!ids.length) {
        return [t("plugins.permissions.none")];
    }
    return ids.map((id) => permissionLabel(id, t));
}
