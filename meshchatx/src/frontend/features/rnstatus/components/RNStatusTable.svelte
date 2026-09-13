<!-- SPDX-License-Identifier: 0BSD -->

<script lang="ts">
    import MaterialDesignIcon from "../../../ui/svelte/MaterialDesignIcon.svelte";
    import EmptyState from "../../../ui/svelte/EmptyState.svelte";
    import { t } from "../../../js/i18n.js";
    import { buildInterfaceStatRows, copyText } from "../lib/statusFormat.js";
    import type { RNStatusInterface } from "../lib/types.js";

    interface Props {
        interfaces: RNStatusInterface[];
        isLoading?: boolean;
        reloadingRns?: boolean;
    }

    let { interfaces = [], isLoading = false, reloadingRns = false }: Props = $props();
</script>

{#if interfaces.length === 0 && !isLoading && !reloadingRns}
    <EmptyState icon="lan-disconnect" title={t("rnstatus.no_interfaces_found")} />
{:else}
    <div class="space-y-3">
        {#each interfaces as iface (iface.name)}
            <div class="rounded-xl border border-sem-border bg-sem-surface p-4 sm:p-5 space-y-4">
                <div class="flex flex-wrap items-start justify-between gap-3">
                    <div class="min-w-0 flex-1 space-y-1">
                        <div class="flex flex-wrap items-center gap-2">
                            <h3 class="wrap-break-word text-base font-semibold leading-snug text-sem-fg">
                                {iface.name}
                            </h3>
                            {#if iface.discovered}
                                <span
                                    class="inline-flex shrink-0 items-center rounded-md bg-amber-100 px-2 py-0.5 text-xs font-semibold text-amber-900 dark:bg-amber-900/45 dark:text-amber-100"
                                >
                                    {t("rnstatus.discovered")}
                                </span>
                            {/if}
                        </div>
                        {#if iface.type}
                            <div class="text-xs text-sem-fg-muted">
                                {iface.type}
                            </div>
                        {/if}
                    </div>
                    <span
                        class="shrink-0 rounded-full px-3 py-1 text-xs font-semibold {iface.status &&
                        String(iface.status).startsWith('Up')
                            ? 'bg-green-100 text-green-800 dark:bg-green-900/45 dark:text-green-100'
                            : 'bg-red-100 text-red-800 dark:bg-red-900/45 dark:text-red-100'}"
                    >
                        {iface.status}
                    </span>
                </div>

                {#if iface.i2p_b32}
                    <div class="address-card">
                        <div class="address-card__label">{t("rnstatus.i2p_address")}</div>
                        <div class="address-card__value monospace-field">{iface.i2p_b32}</div>
                        <button
                            type="button"
                            class="address-card__action focus-ring-sem"
                            onclick={() => copyText(iface.i2p_b32)}
                        >
                            <MaterialDesignIcon iconName="content-copy" class="w-3.5 h-3.5" />
                            {t("common.copy")}
                        </button>
                    </div>
                {/if}

                <div class="grid gap-x-6 gap-y-3 text-sm md:grid-cols-2 lg:grid-cols-3">
                    {#each buildInterfaceStatRows(iface) as row (`${iface.name}-${row.key}`)}
                        <div>
                            <div class="text-xs text-sem-fg-muted">{row.label}</div>
                            <div class="font-semibold tabular-nums text-sem-fg wrap-break-word">
                                {row.value}
                            </div>
                        </div>
                    {/each}
                </div>
            </div>
        {/each}
    </div>
{/if}
