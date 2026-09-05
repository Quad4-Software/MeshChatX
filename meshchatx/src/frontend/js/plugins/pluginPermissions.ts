// SPDX-License-Identifier: 0BSD

export function permissionLabel(
    permissionId: string,
    t: (key: string, values?: Record<string, unknown>) => string
): string {
    const key = `plugins.permissions.${String(permissionId).replaceAll(":", ".")}`;
    const translated = t(key);
    if (translated && translated !== key) {
        return translated;
    }
    return permissionId;
}

export function declaredPermissionIds(manifest: Record<string, any> | null | undefined): string[] {
    const permissions = manifest?.permissions || {};
    const ids: string[] = [];
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
    const ui = permissions.ui;
    if (ui === "sandboxed-html" || (Array.isArray(ui) && ui.includes("sandboxed-html"))) {
        ids.push("ui:sandboxed-html");
    }
    return [...new Set(ids)];
}

export function manifestPermissionSummary(
    manifest: Record<string, any> | null | undefined,
    t: (key: string, values?: Record<string, unknown>) => string = (key) => key
): string[] {
    const ids =
        Array.isArray(manifest?.declared_permissions) && manifest.declared_permissions.length
            ? manifest.declared_permissions
            : declaredPermissionIds(manifest);
    if (!ids.length) {
        return [t("plugins.permissions.none")];
    }
    return ids.map((id) => permissionLabel(id, t));
}
