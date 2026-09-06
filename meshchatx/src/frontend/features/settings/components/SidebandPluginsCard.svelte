<!-- SPDX-License-Identifier: 0BSD -->

<script lang="ts">
    import { t } from "../../../js/i18n.js";

    interface Props {
        sidebandConfig: {
            service_plugins_enabled: boolean;
            command_plugins_enabled: boolean;
            command_plugins_path: string;
        };
        sidebandPlugins: Array<{
            name: string;
            type: string;
            path: string;
            error?: string;
            security_findings?: Array<{ id: string; message: string }>;
        }>;
        sidebandBusy: boolean;
        onmastertoggle: () => void;
        onpickdirectory: () => void;
        onsave: () => void;
        onreload: () => void;
    }

    let {
        sidebandConfig = $bindable(),
        sidebandPlugins = [],
        sidebandBusy = false,
        onmastertoggle,
        onpickdirectory,
        onsave,
        onreload,
    }: Props = $props();
</script>

<section class="rounded-lg border border-amber-300 dark:border-amber-800 p-4 space-y-3">
    <div>
        <h3 class="text-sm font-semibold text-sem-fg">
            {t("plugins.sideband.title")}
        </h3>
        <p class="text-xs text-sem-fg-muted mt-1">
            {t("plugins.sideband.description")}
        </p>
    </div>
    <label class="flex items-start gap-2 text-sm text-sem-fg">
        <input
            bind:checked={sidebandConfig.service_plugins_enabled}
            type="checkbox"
            class="mt-1 rounded border-sem-border"
            onchange={onmastertoggle}
        />
        <span>{t("plugins.sideband.master_enable")}</span>
    </label>
    <label class="flex items-start gap-2 text-sm text-sem-fg">
        <input
            bind:checked={sidebandConfig.command_plugins_enabled}
            type="checkbox"
            class="mt-1 rounded border-sem-border"
            disabled={!sidebandConfig.service_plugins_enabled}
        />
        <span>{t("plugins.sideband.command_enable")}</span>
    </label>
    <div class="block text-sm text-sem-fg space-y-1">
        <span>{t("plugins.sideband.path")}</span>
        <div class="flex flex-col sm:flex-row gap-2">
            <input
                bind:value={sidebandConfig.command_plugins_path}
                type="text"
                class="w-full rounded-md border border-sem-border bg-sem-surface px-3 py-1.5 text-sm min-w-0"
                disabled={!sidebandConfig.service_plugins_enabled}
            />
            <button
                type="button"
                class="toolbar-label-chip border border-sem-border bg-sem-surface shrink-0 min-h-11 sm:min-h-8"
                disabled={!sidebandConfig.service_plugins_enabled || sidebandBusy}
                title={t("plugins.sideband.browse_title")}
                onclick={onpickdirectory}
            >
                {t("plugins.sideband.browse")}
            </button>
        </div>
    </div>
    <div class="flex flex-wrap gap-2">
        <button
            type="button"
            class="toolbar-label-chip border border-sem-action-primary bg-sem-action-primary text-white hover:bg-sem-action-primary-hover"
            disabled={sidebandBusy}
            onclick={onsave}
        >
            {t("plugins.sideband.save")}
        </button>
        <button
            type="button"
            class="toolbar-label-chip border border-sem-border bg-sem-surface"
            disabled={sidebandBusy}
            onclick={onreload}
        >
            {t("plugins.sideband.reload")}
        </button>
    </div>
    {#if sidebandPlugins.length}
        <div class="space-y-2">
            <p class="text-sm font-medium text-sem-fg">
                {t("plugins.sideband.loaded")}
            </p>
            <ul class="space-y-2">
                {#each sidebandPlugins as item (item.path)}
                    <li class="rounded-md border border-sem-border px-3 py-2 text-xs space-y-1">
                        <p class="font-medium text-sem-fg">
                            {item.name}
                            <span class="uppercase text-gray-500">({item.type})</span>
                        </p>
                        {#if item.error}
                            <p class="text-red-600 dark:text-red-400">{item.error}</p>
                        {/if}
                        {#if (item.security_findings || []).length}
                            <ul class="list-disc pl-4 text-sem-fg-muted">
                                {#each item.security_findings as finding (finding.id)}
                                    <li>{finding.message}</li>
                                {/each}
                            </ul>
                        {/if}
                    </li>
                {/each}
            </ul>
        </div>
    {/if}
</section>
