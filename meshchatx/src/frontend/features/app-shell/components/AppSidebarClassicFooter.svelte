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
    }: Props = $props();

    let isShowingMyIdentitySection = $state(true);
    let isShowingAnnounceSection = $state(true);
</script>

{#if config}
    <div>
        <div class="bg-sem-surface border-t border-sem-border">
            <!-- svelte-ignore a11y_click_events_have_key_events -->
            <!-- svelte-ignore a11y_no_static_element_interactions -->
            <div
                class="flex text-sem-fg cursor-pointer {isCollapsed ? 'justify-center p-2' : 'p-3'}"
                onclick={() => (isShowingMyIdentitySection = !isShowingMyIdentitySection)}
            >
                <div class={isCollapsed ? "shrink-0" : "my-auto mr-2 shrink-0"}>
                    <a href="#/profile/icon" onclick={(e) => e.stopPropagation()}>
                        <LxmfUserIcon
                            iconName={config.lxmf_user_icon_name}
                            iconForegroundColour={config.lxmf_user_icon_foreground_colour}
                            iconBackgroundColour={config.lxmf_user_icon_background_colour}
                            iconClass="size-7"
                        />
                    </a>
                </div>
                {#if !isCollapsed}
                    <div class="my-auto min-w-0 flex-1 text-sem-fg truncate" title={identityLabel}>
                        {identityLabel}
                    </div>
                {/if}
            </div>
            {#if isShowingMyIdentitySection && !isCollapsed}
                <div class="divide-y divide-sem-border text-sem-fg border-t border-sem-border">
                    <div class="p-2">
                        <input
                            value={displayName}
                            type="text"
                            data-testid="sidebar-display-name"
                            placeholder={t("app.display_name_placeholder")}
                            class="input-field w-full"
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
                    <div class="p-2 dark:border-zinc-900 overflow-hidden text-xs">
                        <div>{t("app.identity_hash")}</div>
                        <button
                            type="button"
                            class="text-[10px] text-sem-fg-muted truncate font-mono cursor-pointer text-left block w-full"
                            title={config.identity_hash}
                            onclick={() => oncopyvalue?.(config.identity_hash || "", t("app.identity_hash"))}
                        >
                            {config.identity_hash}
                        </button>
                    </div>
                    <div class="p-2 dark:border-zinc-900 overflow-hidden text-xs">
                        <div>{t("app.lxmf_address")}</div>
                        <div class="flex min-w-0 items-center gap-1">
                            <button
                                type="button"
                                class="min-w-0 flex-1 text-[10px] text-sem-fg-muted truncate font-mono cursor-pointer text-left"
                                title={config.lxmf_address_hash}
                                onclick={() => oncopyvalue?.(config.lxmf_address_hash || "", t("app.lxmf_address"))}
                            >
                                {config.lxmf_address_hash}
                            </button>
                            <button
                                type="button"
                                class="toolbar-icon-btn shrink-0"
                                title={t("app.show_qr")}
                                onclick={(e) => {
                                    e.stopPropagation();
                                    onopenlxmfqr?.();
                                }}
                            >
                                <MaterialDesignIcon iconName="qrcode" class="size-5" />
                            </button>
                        </div>
                    </div>
                </div>
            {/if}
        </div>

        <div class="bg-white border-t border-sem-border dark:bg-zinc-950">
            <!-- svelte-ignore a11y_click_events_have_key_events -->
            <!-- svelte-ignore a11y_no_static_element_interactions -->
            <div
                class="flex text-gray-700 cursor-pointer dark:text-white {isCollapsed ? 'justify-center p-2' : 'p-3'}"
                data-testid="sidebar-announce-header"
                onclick={() => (isShowingAnnounceSection = !isShowingAnnounceSection)}
            >
                <button
                    type="button"
                    class="flex shrink-0 items-center justify-center rounded-md border-0 bg-transparent p-0 text-inherit cursor-pointer {isCollapsed
                        ? ''
                        : 'my-auto mr-2'}"
                    title={t("app.announce_now")}
                    data-testid="sidebar-announce-radio"
                    onclick={(e) => {
                        e.stopPropagation();
                        onsendannounce?.();
                    }}
                >
                    <MaterialDesignIcon iconName="radio" class="size-6" />
                </button>
                {#if !isCollapsed}
                    <div class="my-auto truncate">
                        {t("app.announce")}
                    </div>
                    <div class="ml-auto shrink-0">
                        <button
                            type="button"
                            class="toolbar-label-chip border border-sem-border bg-sem-surface-muted text-sem-fg shadow-xs hover:border-sem-accent"
                            onclick={(e) => {
                                e.stopPropagation();
                                onsendannounce?.();
                            }}
                        >
                            {t("app.announce_now")}
                        </button>
                    </div>
                {/if}
            </div>
            {#if isShowingAnnounceSection && !isCollapsed}
                <div
                    class="divide-y divide-gray-200 text-gray-900 border-t border-gray-200 dark:divide-zinc-800 text-sem-fg dark:border-zinc-800"
                >
                    <div class="p-2 dark:border-zinc-800">
                        <select
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
                        <div
                            class="text-[10px] leading-snug text-gray-700 text-sem-fg mt-1"
                            data-testid="sidebar-last-announced"
                        >
                            {#if config.last_announced_at}
                                <span>{t("app.last_announced", { time: lastAnnouncedLabel })}</span>
                            {:else}
                                <span>{t("app.last_announced_never")}</span>
                            {/if}
                        </div>
                    </div>
                </div>
            {/if}
        </div>
    </div>
{/if}
