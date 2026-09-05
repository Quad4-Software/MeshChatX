<!-- SPDX-License-Identifier: 0BSD -->

<script lang="ts">
    import { t } from "../../../js/i18n.js";
    import MaterialDesignIcon from "../../../ui/svelte/MaterialDesignIcon.svelte";
    import LxmfUserIcon from "../../../ui/svelte/LxmfUserIcon.svelte";

    interface ConfigProps {
        lxmf_user_icon_name?: string;
        lxmf_user_icon_foreground_colour?: string;
        lxmf_user_icon_background_colour?: string;
        last_announced_at?: string | number | null;
        identity_hash?: string;
        lxmf_address_hash?: string;
        auto_announce_interval_seconds?: number;
    }

    interface Props {
        config: ConfigProps;
        displayName?: string;
        identityLabel: string;
        lastAnnouncedLabel?: string;
        isCollapsed?: boolean;

        onupdatedisplayname?: (val: string) => void;
        onsaveidentity?: () => void;
        onsendannounce?: () => void;
        onannounceintervalchange?: (val: number) => void;
        oncopyvalue?: (val: string, label: string) => void;
        onopenlxmfqr?: () => void;
        onnavigatetoidentities?: () => void;
    }

    let {
        config,
        displayName = "",
        identityLabel,
        lastAnnouncedLabel = "",
        isCollapsed = false,

        onupdatedisplayname,
        onsaveidentity,
        onsendannounce,
        onannounceintervalchange,
        oncopyvalue,
        onopenlxmfqr,
        onnavigatetoidentities,
    }: Props = $props();

    let isExpanded = $state(false);

    function onAccountChipClick(): void {
        if (isCollapsed) {
            if (onnavigatetoidentities) {
                onnavigatetoidentities();
            } else {
                window.location.hash = "#/settings/identities";
            }
            return;
        }
        isExpanded = !isExpanded;
    }
</script>

{#if config}
    <div class="bg-sem-surface border-t border-sem-border">
        <!-- svelte-ignore a11y_click_events_have_key_events -->
        <!-- svelte-ignore a11y_no_static_element_interactions -->
        <div
            class="cursor-pointer text-sem-fg-secondary"
            data-testid="sidebar-account-chip"
            onclick={onAccountChipClick}
        >
            <div class="flex items-center gap-1 {isCollapsed ? 'justify-center p-2' : 'p-3 pb-1'}">
                <a href="#/settings/profile-icon" class="shrink-0" onclick={(e) => e.stopPropagation()}>
                    <LxmfUserIcon
                        iconName={config.lxmf_user_icon_name}
                        iconForegroundColour={config.lxmf_user_icon_foreground_colour}
                        iconBackgroundColour={config.lxmf_user_icon_background_colour}
                        iconClass="size-8"
                    />
                </a>
                {#if !isCollapsed}
                    <button
                        type="button"
                        class="inline-flex size-8 items-center justify-center rounded-lg text-sem-fg-muted hover:bg-sem-surface-muted hover:text-sem-accent focus-ring-sem transition-colors shrink-0"
                        title={t("app.show_qr")}
                        aria-label={t("app.show_qr")}
                        onclick={(e) => {
                            e.stopPropagation();
                            onopenlxmfqr?.();
                        }}
                    >
                        <MaterialDesignIcon iconName="qrcode" class="size-5" />
                    </button>
                    <div class="min-w-0 flex-1">
                        <div class="truncate text-sm font-semibold text-sem-fg" title={identityLabel}>
                            {identityLabel}
                        </div>
                    </div>
                    <div class="flex shrink-0 items-center gap-0.5">
                        <button
                            type="button"
                            class="inline-flex size-8 items-center justify-center rounded-lg text-sem-fg-muted hover:bg-sem-surface-muted hover:text-sem-accent focus-ring-sem transition-colors"
                            title={t("app.announce_now")}
                            aria-label={t("app.announce_now")}
                            data-testid="sidebar-announce-radio"
                            onclick={(e) => {
                                e.stopPropagation();
                                onsendannounce?.();
                            }}
                        >
                            <MaterialDesignIcon iconName="radio" class="size-5" />
                        </button>
                        <MaterialDesignIcon
                            iconName={isExpanded ? "chevron-up" : "chevron-down"}
                            class="size-5 text-sem-fg-muted shrink-0"
                        />
                    </div>
                {/if}
            </div>
            {#if !isCollapsed}
                <div class="px-3 pb-2 text-[11px] leading-snug text-sem-fg-muted" data-testid="sidebar-last-announced">
                    {#if config.last_announced_at}
                        <span>{t("app.last_announced", { time: lastAnnouncedLabel })}</span>
                    {:else}
                        <span>{t("app.last_announced_never")}</span>
                    {/if}
                </div>
            {/if}
        </div>

        {#if isExpanded && !isCollapsed}
            <div class="divide-y divide-sem-border border-t border-sem-border text-sem-fg">
                <div class="p-2">
                    <input
                        value={displayName}
                        type="text"
                        data-testid="sidebar-display-name"
                        placeholder={t("app.display_name_placeholder")}
                        class="input-field w-full min-w-0"
                        oninput={(e) => onupdatedisplayname?.((e.target as HTMLInputElement).value)}
                        onkeydown={(e) => {
                            if (e.key === "Enter") {
                                e.preventDefault();
                                onsaveidentity?.();
                            }
                        }}
                        onblur={() => onsaveidentity?.()}
                    />
                </div>

                <div class="p-2 space-y-2 text-xs">
                    <div>
                        <div class="text-sem-fg-muted">{t("app.identity_hash")}</div>
                        <button
                            type="button"
                            class="mt-0.5 block w-full truncate text-left font-mono text-[11px] text-sem-fg-muted hover:text-blue-600 dark:hover:text-blue-400"
                            title={config.identity_hash}
                            onclick={() => oncopyvalue?.(config.identity_hash || "", t("app.identity_hash"))}
                        >
                            {config.identity_hash}
                        </button>
                    </div>
                    <div>
                        <div class="text-sem-fg-muted">{t("app.lxmf_address")}</div>
                        <button
                            type="button"
                            class="mt-0.5 block w-full truncate text-left font-mono text-[11px] text-sem-fg-muted hover:text-blue-600 dark:hover:text-blue-400"
                            title={config.lxmf_address_hash}
                            onclick={() => oncopyvalue?.(config.lxmf_address_hash || "", t("app.lxmf_address"))}
                        >
                            {config.lxmf_address_hash}
                        </button>
                    </div>
                </div>

                <div class="p-2">
                    <label for="sidebar-auto-announce-interval" class="block text-xs text-sem-fg-muted mb-1">
                        {t("app.announce_interval")}
                    </label>
                    <select
                        id="sidebar-auto-announce-interval"
                        value={config.auto_announce_interval_seconds}
                        class="bg-gray-50 border border-gray-300 text-gray-900 text-sm rounded-lg focus:ring-blue-500 focus:border-blue-500 block w-full p-2.5 dark:bg-zinc-800 dark:border-zinc-600 text-sem-fg dark:focus:ring-blue-400 dark:focus:border-blue-400"
                        onchange={(e) => onannounceintervalchange?.(Number((e.target as HTMLSelectElement).value))}
                    >
                        <option value={0}>{t("app.disabled")}</option>
                        <option value={900}>{t("app.announce_interval_15m")}</option>
                        <option value={1800}>{t("app.announce_interval_30m")}</option>
                        <option value={3600}>{t("app.announce_interval_1h")}</option>
                        <option value={10800}>{t("app.announce_interval_3h")}</option>
                        <option value={21600}>{t("app.announce_interval_6h")}</option>
                        <option value={43200}>{t("app.announce_interval_12h")}</option>
                        <option value={86400}>{t("app.announce_interval_24h")}</option>
                    </select>
                </div>

                <div class="p-2">
                    <a
                        href="#/settings/identities"
                        class="text-xs font-semibold text-blue-600 hover:text-blue-700 dark:text-blue-400 dark:hover:text-blue-300"
                    >
                        {t("app.manage_identities")}
                    </a>
                </div>
            </div>
        {/if}
    </div>
{/if}
