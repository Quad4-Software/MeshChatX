<!-- SPDX-License-Identifier: 0BSD -->

<script lang="ts">
    import { permissionLabel } from "../../../js/plugins/pluginPermissions.js";
    import { t } from "../../../js/i18n.js";

    interface Props {
        plugin: any;
        busyPluginId?: string | null;
        onenable?: (id: string) => void;
        ondisable?: (id: string) => void;
        onremove?: (plugin: any) => void;
    }

    let { plugin, busyPluginId = null, onenable, ondisable, onremove }: Props = $props();

    function permissionLines(p: any): string[] {
        const granted = p.granted_permissions || p.declared_permissions || [];
        if (!granted.length) {
            return [t("plugins.permissions.none")];
        }
        return granted.map((id: string) => permissionLabel(id, (key) => t(key)));
    }
</script>

<div class="rounded-lg border border-sem-border p-4 space-y-3">
    <div class="flex flex-wrap items-start justify-between gap-3">
        <div class="min-w-0 space-y-2">
            <div class="flex flex-wrap items-center gap-2">
                <h3 class="text-base font-semibold text-sem-fg">{plugin.name}</h3>
                <span
                    class="px-2 py-0.5 rounded-full text-[11px] font-semibold uppercase tracking-wide {plugin.enabled
                        ? 'bg-green-100 text-green-800 dark:bg-green-900/30 dark:text-green-200'
                        : 'bg-zinc-200 text-zinc-700 dark:bg-zinc-800 text-sem-fg-muted'}"
                >
                    {plugin.enabled ? t("plugins.settings.badge_enabled") : t("plugins.settings.badge_disabled")}
                </span>
                {#if plugin.has_frontend}
                    <span
                        class="px-2 py-0.5 rounded-full text-[11px] font-semibold uppercase tracking-wide bg-sky-100 text-sky-800 dark:bg-sky-900/30 dark:text-sky-200"
                    >
                        {t("plugins.settings.badge_frontend")}
                    </span>
                {/if}
                {#if plugin.has_backend && plugin.backend_type === "python"}
                    <span
                        class="px-2 py-0.5 rounded-full text-[11px] font-semibold uppercase tracking-wide bg-emerald-100 text-emerald-800 dark:bg-emerald-900/30 dark:text-emerald-200"
                    >
                        {t("plugins.settings.badge_python")}
                    </span>
                {:else if plugin.has_backend}
                    <span
                        class="px-2 py-0.5 rounded-full text-[11px] font-semibold uppercase tracking-wide bg-violet-100 text-violet-800 dark:bg-violet-900/30 dark:text-violet-200"
                    >
                        {t("plugins.settings.badge_wasm")}
                    </span>
                {/if}
                {#if plugin.requires_network_fetch}
                    <span
                        class="px-2 py-0.5 rounded-full text-[11px] font-semibold uppercase tracking-wide bg-amber-100 text-amber-800 dark:bg-amber-900/30 dark:text-amber-200"
                    >
                        {t("plugins.settings.badge_network")}
                    </span>
                {/if}
                {#if plugin.signature?.trusted}
                    <span
                        class="px-2 py-0.5 rounded-full text-[11px] font-semibold uppercase tracking-wide bg-green-100 text-green-800 dark:bg-green-900/30 dark:text-green-200"
                    >
                        {t("plugins.settings.badge_trusted")}
                    </span>
                {:else if plugin.signature?.valid}
                    <span
                        class="px-2 py-0.5 rounded-full text-[11px] font-semibold uppercase tracking-wide bg-sky-100 text-sky-800 dark:bg-sky-900/30 dark:text-sky-200"
                    >
                        {t("plugins.settings.badge_signed")}
                    </span>
                {:else if plugin.signature?.present && !plugin.signature?.valid}
                    <span
                        class="px-2 py-0.5 rounded-full text-[11px] font-semibold uppercase tracking-wide bg-red-100 text-red-800 dark:bg-red-900/30 dark:text-red-200"
                    >
                        {t("plugins.settings.badge_invalid_signature")}
                    </span>
                {/if}
                {#if plugin.tampered}
                    <span
                        class="px-2 py-0.5 rounded-full text-[11px] font-semibold uppercase tracking-wide bg-red-100 text-red-800 dark:bg-red-900/30 dark:text-red-200"
                    >
                        {t("plugins.settings.badge_tampered")}
                    </span>
                {/if}
            </div>
            <p class="text-sm text-sem-fg-muted">{plugin.description}</p>
            <p class="text-xs text-sem-fg-muted">{plugin.id} · v{plugin.version}</p>
        </div>
        <div class="flex flex-wrap gap-2">
            {#if !plugin.enabled}
                <button
                    type="button"
                    class="toolbar-label-chip border border-sem-action-primary bg-sem-action-primary text-white hover:bg-sem-action-primary-hover cursor-pointer"
                    disabled={busyPluginId === plugin.id}
                    onclick={() => onenable?.(plugin.id)}
                >
                    {t("plugins.settings.enable")}
                </button>
            {:else}
                <button
                    type="button"
                    class="toolbar-label-chip border border-sem-border bg-sem-surface-muted text-sem-fg cursor-pointer"
                    disabled={busyPluginId === plugin.id}
                    onclick={() => ondisable?.(plugin.id)}
                >
                    {t("plugins.settings.disable")}
                </button>
            {/if}
            <button
                type="button"
                class="toolbar-label-chip border border-red-300 text-red-600 dark:border-red-500/50 dark:text-red-400 cursor-pointer"
                disabled={busyPluginId === plugin.id}
                onclick={() => onremove?.(plugin)}
            >
                {t("plugins.settings.remove")}
            </button>
        </div>
    </div>
    {#if permissionLines(plugin).length}
        <div class="text-sm text-sem-fg">
            <p class="font-medium">{t("plugins.settings.permissions")}</p>
            <ul class="list-disc pl-5">
                {#each permissionLines(plugin) as line (line)}
                    <li>{line}</li>
                {/each}
            </ul>
        </div>
    {/if}
    {#if (plugin.network_endpoints || []).length}
        <div class="text-sm text-sem-fg space-y-1">
            <p class="font-medium">{t("plugins.settings.network_endpoints")}</p>
            <ul class="list-disc pl-5">
                {#each plugin.network_endpoints as endpoint (endpoint)}
                    <li class="font-mono text-xs break-all">
                        {endpoint}
                    </li>
                {/each}
            </ul>
        </div>
    {/if}
    {#if plugin.auto_disabled_reason}
        <p class="text-sm text-amber-700 dark:text-amber-300">
            {t("plugins.settings.auto_disabled", { reason: plugin.auto_disabled_reason })}
        </p>
    {/if}
</div>
