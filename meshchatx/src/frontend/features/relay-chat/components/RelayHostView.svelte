<!-- SPDX-License-Identifier: 0BSD -->

<script lang="ts">
    import MaterialDesignIcon from "../../../ui/svelte/MaterialDesignIcon.svelte";
    import { t } from "../../../js/i18n.js";
    import { formatUptime } from "../lib/relayFormatters.js";
    import type { RrcHostedHub } from "../lib/types.js";

    interface Props {
        hostedHub?: RrcHostedHub | null;
        isOperating?: boolean;
        oncreatehub?: () => void;
        ontogglestart?: () => void;
        onopenmoderation?: () => void;
        onopensettings?: () => void;
        oncopyhash?: (hash: string) => void;
    }

    let {
        hostedHub = null,
        isOperating = false,
        oncreatehub,
        ontogglestart,
        onopenmoderation,
        onopensettings,
        oncopyhash,
    }: Props = $props();
</script>

<div class="flex flex-1 flex-col overflow-y-auto bg-sem-canvas p-4 sm:p-6 text-sem-fg">
    <div class="mb-6 flex items-center justify-between">
        <div>
            <h2 class="text-lg font-bold">{t("relay_chat.host_view_title")}</h2>
            <p class="text-xs text-sem-fg-muted">{t("relay_chat.host_view_subtitle")}</p>
        </div>

        {#if !hostedHub}
            <button
                type="button"
                class="inline-flex items-center gap-1.5 px-4 py-2 rounded-xl bg-sem-action-primary text-sm font-semibold text-white hover:bg-sem-action-primary-hover transition-colors cursor-pointer"
                onclick={() => oncreatehub?.()}
            >
                <MaterialDesignIcon iconName="plus" class="size-4" />
                <span>{t("relay_chat.host_create_hub")}</span>
            </button>
        {/if}
    </div>

    {#if !hostedHub}
        <div class="flex flex-1 flex-col items-center justify-center p-8 text-center text-sem-fg-muted">
            <MaterialDesignIcon iconName="server-off" class="size-12 opacity-40 mb-2" />
            <div class="font-semibold text-base mb-1">{t("relay_chat.no_hosted_hub")}</div>
            <p class="text-xs max-w-sm mb-4">{t("relay_chat.no_hosted_hub_hint")}</p>
            <button
                type="button"
                class="inline-flex items-center gap-1.5 px-4 py-2 rounded-xl bg-sem-action-primary text-sm font-semibold text-white hover:bg-sem-action-primary-hover transition-colors cursor-pointer"
                onclick={() => oncreatehub?.()}
            >
                <MaterialDesignIcon iconName="plus" class="size-4" />
                <span>{t("relay_chat.host_create_hub")}</span>
            </button>
        </div>
    {:else}
        <div class="space-y-4 max-w-3xl">
            <div class="rounded-2xl border border-sem-border bg-sem-surface p-4 sm:p-6 shadow-sm">
                <div class="flex flex-wrap items-center justify-between gap-3 pb-4 border-b border-sem-border">
                    <div>
                        <div class="flex items-center gap-2">
                            <h3 class="text-base font-bold">{hostedHub.name}</h3>
                            <span
                                class="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-medium {hostedHub.running
                                    ? 'bg-emerald-500/15 text-emerald-600 dark:text-emerald-400'
                                    : 'bg-zinc-500/15 text-zinc-600 dark:text-zinc-400'}"
                            >
                                <span
                                    class="size-1.5 rounded-full {hostedHub.running ? 'bg-emerald-500' : 'bg-zinc-400'}"
                                ></span>
                                {hostedHub.running
                                    ? t("relay_chat.host_status_running")
                                    : t("relay_chat.host_status_stopped")}
                            </span>
                        </div>
                        <div class="flex items-center gap-2 mt-1">
                            <span class="font-mono text-xs text-sem-fg-muted truncate max-w-xs"
                                >{hostedHub.hub_hash}</span
                            >
                            <button
                                type="button"
                                class="p-1 rounded text-sem-fg-muted hover:text-sem-fg"
                                title={t("relay_chat.copy_hub_hash")}
                                onclick={() => oncopyhash?.(hostedHub.hub_hash)}
                            >
                                <MaterialDesignIcon iconName="content-copy" class="size-3.5" />
                            </button>
                        </div>
                    </div>

                    <div class="flex items-center gap-2">
                        <button
                            type="button"
                            class="inline-flex items-center gap-1.5 px-3 py-2 rounded-xl text-xs font-semibold text-white transition-colors cursor-pointer {hostedHub.running
                                ? 'bg-amber-600 hover:bg-amber-700'
                                : 'bg-emerald-600 hover:bg-emerald-700'}"
                            disabled={isOperating}
                            onclick={() => ontogglestart?.()}
                        >
                            <MaterialDesignIcon iconName={hostedHub.running ? "stop" : "play"} class="size-4" />
                            <span>{hostedHub.running ? t("relay_chat.host_stop") : t("relay_chat.host_start")}</span>
                        </button>

                        <button
                            type="button"
                            class="inline-flex items-center gap-1.5 px-3 py-2 rounded-xl border border-sem-border bg-sem-surface-muted text-xs font-semibold hover:bg-sem-surface-raised transition-colors cursor-pointer"
                            onclick={() => onopensettings?.()}
                        >
                            <MaterialDesignIcon iconName="cog" class="size-4" />
                            <span>{t("common.settings")}</span>
                        </button>
                    </div>
                </div>

                <div class="grid grid-cols-2 sm:grid-cols-4 gap-4 pt-4">
                    <div class="p-3 rounded-xl bg-sem-canvas border border-sem-border/60">
                        <div class="text-xs text-sem-fg-muted">{t("relay_chat.host_rooms_count")}</div>
                        <div class="text-lg font-bold mt-0.5">{hostedHub.rooms_count ?? 0}</div>
                    </div>
                    <div class="p-3 rounded-xl bg-sem-canvas border border-sem-border/60">
                        <div class="text-xs text-sem-fg-muted">{t("relay_chat.host_members_count")}</div>
                        <div class="text-lg font-bold mt-0.5">{hostedHub.members_count ?? 0}</div>
                    </div>
                    <div class="p-3 rounded-xl bg-sem-canvas border border-sem-border/60">
                        <div class="text-xs text-sem-fg-muted">{t("relay_chat.host_uptime")}</div>
                        <div class="text-lg font-bold mt-0.5">{formatUptime(hostedHub.uptime_seconds || 0)}</div>
                    </div>
                    <div class="p-3 rounded-xl bg-sem-canvas border border-sem-border/60">
                        <div class="text-xs text-sem-fg-muted">{t("relay_chat.host_announce_interval")}</div>
                        <div class="text-lg font-bold mt-0.5">
                            {Math.round((hostedHub.announce_interval || 900) / 60)}m
                        </div>
                    </div>
                </div>

                <div class="mt-6 pt-4 border-t border-sem-border flex justify-end">
                    <button
                        type="button"
                        class="inline-flex items-center gap-1.5 px-4 py-2 rounded-xl bg-sem-surface-muted border border-sem-border text-xs font-semibold hover:bg-sem-surface-raised transition-colors cursor-pointer"
                        onclick={() => onopenmoderation?.()}
                    >
                        <MaterialDesignIcon iconName="shield-account" class="size-4 text-sem-accent" />
                        <span>{t("relay_chat.open_host_moderation")}</span>
                    </button>
                </div>
            </div>
        </div>
    {/if}
</div>
