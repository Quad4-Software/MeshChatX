<!-- SPDX-License-Identifier: 0BSD -->

<script lang="ts">
    import MaterialDesignIcon from "../../../ui/svelte/MaterialDesignIcon.svelte";
    import { t } from "../../../js/i18n.js";
    import { formatUptime } from "../lib/relayFormatters.js";
    import { BTN_DANGER, BTN_ICON, BTN_PRIMARY, BTN_SECONDARY } from "../lib/constants.js";
    import type { RrcHostedHub } from "../lib/types.js";

    interface Props {
        serverHubs?: RrcHostedHub[];
        isHubAdded?: (destinationHash?: string | null) => boolean;
        uptimeFor?: (hub: RrcHostedHub) => number;
        formatHash?: (hash: string | null | undefined) => string;
        oncreatehub?: () => void;
        onjoinclient?: (hub: RrcHostedHub) => void;
        onleaveclient?: (hub: RrcHostedHub) => void;
        onshare?: (hub: RrcHostedHub) => void;
        onstart?: (hub: RrcHostedHub) => void;
        onstop?: (hub: RrcHostedHub) => void;
        onopensettings?: (hub: RrcHostedHub) => void;
        onannounce?: (hub: RrcHostedHub) => void;
        ondelete?: (hub: RrcHostedHub) => void;
        onmoderate?: (hub: RrcHostedHub) => void;
        oncopyhash?: (hash: string) => void;
    }

    let {
        serverHubs = [],
        isHubAdded = () => false,
        uptimeFor = (hub) => Number(hub?.uptime_seconds) || 0,
        formatHash = (h) => h || "-",
        oncreatehub,
        onjoinclient,
        onleaveclient,
        onshare,
        onstart,
        onstop,
        onopensettings,
        onannounce,
        ondelete,
        onmoderate,
        oncopyhash,
    }: Props = $props();
</script>

<div class="flex-1 overflow-y-auto custom-scrollbar p-3 sm:p-4">
    <div class="mx-auto w-full max-w-3xl space-y-4">
        <div class="flex flex-wrap items-start justify-between gap-3">
            <div>
                <h2 class="text-lg font-semibold">{t("relay_chat.host_title")}</h2>
                <p class="text-sm text-sem-fg-muted">{t("relay_chat.host_subtitle")}</p>
            </div>
            <button type="button" class={BTN_PRIMARY} onclick={() => oncreatehub?.()}>
                <MaterialDesignIcon iconName="plus" class="size-4" />
                {t("relay_chat.create_hub")}
            </button>
        </div>

        {#if serverHubs.length === 0}
            <div
                class="flex flex-col items-center gap-2 rounded-xl border border-sem-border bg-sem-canvas p-8 text-center text-sm text-sem-fg-muted"
            >
                <MaterialDesignIcon iconName="server-network-off" class="size-10 opacity-40" />
                {t("relay_chat.no_hosted_hubs")}
            </div>
        {/if}

        {#each serverHubs as hub (hub.id)}
            <div class="rounded-xl border border-sem-border bg-sem-canvas p-4 space-y-3">
                <div class="flex flex-wrap items-start justify-between gap-3">
                    <div class="min-w-0 flex-1">
                        <div class="flex items-center gap-2">
                            <span
                                class="size-2 shrink-0 rounded-full {hub.running
                                    ? 'bg-sem-success'
                                    : 'bg-sem-fg-muted'}"
                            ></span>
                            <span class="font-semibold truncate">{hub.name}</span>
                        </div>
                        <button
                            type="button"
                            class="mt-1 flex items-center gap-1.5 text-xs font-mono text-sem-fg-muted hover:text-sem-accent cursor-pointer"
                            title={t("relay_chat.copy_hash")}
                            onclick={() => hub.dest_hash && oncopyhash?.(hub.dest_hash)}
                        >
                            <MaterialDesignIcon iconName="content-copy" class="size-3.5" />
                            <span class="truncate">{formatHash(hub.dest_hash)}</span>
                        </button>
                    </div>
                    <div class="flex shrink-0 items-center gap-1.5">
                        {#if !isHubAdded(hub.dest_hash)}
                            <button
                                type="button"
                                class={BTN_ICON}
                                title={t("relay_chat.host_join_as_client")}
                                disabled={!hub.running || !hub.dest_hash}
                                onclick={() => onjoinclient?.(hub)}
                            >
                                <MaterialDesignIcon iconName="login" class="size-4" />
                            </button>
                        {:else}
                            <button
                                type="button"
                                class={BTN_ICON}
                                title={t("relay_chat.host_leave_as_client")}
                                onclick={() => onleaveclient?.(hub)}
                            >
                                <MaterialDesignIcon iconName="logout" class="size-4" />
                            </button>
                        {/if}
                        <button
                            type="button"
                            class={BTN_ICON}
                            title={t("relay_chat.share_hub")}
                            onclick={() => onshare?.(hub)}
                        >
                            <MaterialDesignIcon iconName="share-variant" class="size-4" />
                        </button>
                        {#if !hub.running}
                            <button
                                type="button"
                                class="{BTN_SECONDARY} px-2.5! py-1.5! text-xs!"
                                onclick={() => onstart?.(hub)}
                            >
                                <MaterialDesignIcon iconName="play" class="size-4" />
                                {t("relay_chat.host_start")}
                            </button>
                        {:else}
                            <button
                                type="button"
                                class="{BTN_SECONDARY} px-2.5! py-1.5! text-xs!"
                                onclick={() => onstop?.(hub)}
                            >
                                <MaterialDesignIcon iconName="stop" class="size-4" />
                                {t("relay_chat.host_stop")}
                            </button>
                        {/if}
                        <button
                            type="button"
                            class={BTN_ICON}
                            title={t("relay_chat.host_hub_settings")}
                            onclick={() => onopensettings?.(hub)}
                        >
                            <MaterialDesignIcon iconName="cog" class="size-4" />
                        </button>
                        <button
                            type="button"
                            class={BTN_ICON}
                            title={t("relay_chat.host_announce")}
                            disabled={!hub.running}
                            onclick={() => onannounce?.(hub)}
                        >
                            <MaterialDesignIcon iconName="bullhorn-outline" class="size-4" />
                        </button>
                        <button
                            type="button"
                            class={BTN_DANGER}
                            title={t("relay_chat.host_delete")}
                            onclick={() => ondelete?.(hub)}
                        >
                            <MaterialDesignIcon iconName="trash-can-outline" class="size-4" />
                        </button>
                    </div>
                </div>

                <div class="flex flex-wrap items-center gap-x-4 gap-y-1 text-xs text-sem-fg-muted">
                    <span class="inline-flex items-center gap-1">
                        <MaterialDesignIcon iconName="account-group" class="size-3.5" />
                        {hub.clients}
                        {t("relay_chat.host_users")}
                    </span>
                    <span class="inline-flex items-center gap-1">
                        <MaterialDesignIcon iconName="pound" class="size-3.5" />
                        {(hub.rooms || []).length}
                        {t("relay_chat.host_rooms")}
                    </span>
                    {#if hub.running}
                        <span class="inline-flex items-center gap-1">
                            <MaterialDesignIcon iconName="clock-outline" class="size-3.5" />
                            {t("relay_chat.host_moderation_uptime", { time: formatUptime(uptimeFor(hub)) })}
                        </span>
                    {/if}
                </div>

                <button type="button" class="{BTN_SECONDARY} w-full py-2! text-xs!" onclick={() => onmoderate?.(hub)}>
                    <MaterialDesignIcon iconName="shield-account" class="size-4" />
                    {t("relay_chat.host_moderate")}
                </button>
            </div>
        {/each}
    </div>
</div>
