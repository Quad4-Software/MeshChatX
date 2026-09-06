<!-- SPDX-License-Identifier: 0BSD -->

<script lang="ts">
    /**
     * Shell header: brand, theme and language controls, sync and compose
     * actions, and the relay, call, and inbound badges.
     */
    import { t } from "../../../js/i18n.js";
    import logoUrl from "../../../assets/images/logo.png";
    import MaterialDesignIcon from "../../../ui/svelte/MaterialDesignIcon.svelte";
    import LanguageSelector from "../../../ui/svelte/LanguageSelector.svelte";
    import { navigate } from "../../../shell/hashRouter.js";
    import type { AppShellState } from "../lib/appShellState.svelte.js";
    import { composeNewMessage, onAppNameClick } from "../lib/appShellCommands.js";
    import { onLanguageChange, toggleTheme } from "../lib/appShellConfig.js";
    import { openCommandPalette } from "../lib/appShellNav.js";
    import { cancelInboundDeliveries, syncPropagationNode } from "../lib/appShellPropagation.js";

    interface Props {
        shell: AppShellState;
        middleEl?: HTMLDivElement;
    }

    let { shell, middleEl = undefined }: Props = $props();

    const tr = $derived.by(() => {
        void shell.localeVersion;
        return (key: string, values?: Record<string, unknown>) => t(key, values);
    });
</script>

<div
    class="z-100 flex shrink-0 bg-sem-canvas border-sem-border border-b min-h-12 sm:min-h-14 shadow-xs pt-[env(safe-area-inset-top,0px)]"
>
    <div
        class="flex w-full min-h-12 sm:min-h-14 items-center gap-0 overflow-x-auto no-scrollbar pl-2 pr-2 sm:ps-0 sm:pe-3"
    >
        <button
            type="button"
            class="sm:hidden shrink-0 mr-2 inline-flex min-h-[44px] min-w-[44px] items-center justify-center text-sem-fg-muted hover:text-sem-fg"
            onclick={() => (shell.isSidebarOpen = !shell.isSidebarOpen)}
        >
            <MaterialDesignIcon iconName={shell.isSidebarOpen ? "close" : "menu"} class="size-6" />
        </button>
        <div class="flex min-w-0 flex-1 items-center gap-2 sm:flex-initial sm:gap-3">
            <div class="hidden shrink-0 justify-start sm:flex sm:w-12 sm:justify-center">
                <button
                    type="button"
                    class="flex h-10 w-10 cursor-pointer items-center justify-center overflow-hidden rounded-xl sm:h-12 sm:w-12"
                    onclick={() => onAppNameClick(shell, middleEl)}
                >
                    <img class="h-9 w-9 max-h-full max-w-full object-contain sm:h-11 sm:w-11" src={logoUrl} alt="" />
                </button>
            </div>
            <div class="hidden min-w-0 leading-tight sm:block">
                <button
                    type="button"
                    class="block text-left font-semibold cursor-pointer text-sem-fg hover:text-sem-accent transition-colors tracking-tight text-base"
                    onclick={() => onAppNameClick(shell, middleEl)}
                >
                    {tr("app.name")}
                </button>
                <div class="text-xs text-sem-fg-muted">
                    {tr("app.tagline")}
                </div>
            </div>
        </div>
        <div class="flex ml-auto shrink-0 items-center mr-0 sm:mr-2 space-x-1 sm:space-x-2">
            <button
                type="button"
                class="relative hidden sm:inline-flex size-8 shrink-0 items-center justify-center rounded-full bg-sem-surface-muted text-sem-fg-muted transition-colors hover:bg-sem-surface-raised"
                title={shell.themeToggleTitle}
                onclick={() => void toggleTheme(shell)}
            >
                <MaterialDesignIcon iconName={shell.themeToggleIcon} class="size-5" />
            </button>
            <LanguageSelector class="hidden sm:block" onlanguagechange={(code) => void onLanguageChange(shell, code)} />
            <button
                type="button"
                class="hidden sm:inline-flex size-8 shrink-0 items-center justify-center rounded-full bg-sem-surface-muted text-sem-fg-muted transition-colors hover:bg-sem-surface-raised"
                title={tr("command_palette.open_hint")}
                aria-label={tr("command_palette.open_hint")}
                data-testid="header-command-palette"
                onclick={() => openCommandPalette(shell)}
            >
                <MaterialDesignIcon iconName="magnify" class="size-5" />
            </button>
            {#if shell.rrcEnabled}
                <button
                    type="button"
                    class="relative inline-flex size-11 sm:size-8 shrink-0 items-center justify-center rounded-full bg-sem-surface-muted text-sem-fg-muted transition-colors hover:bg-sem-surface-raised"
                    title={tr("app.relay_chat")}
                    aria-label={tr("app.relay_chat")}
                    data-testid="header-relay-chat"
                    onclick={() => void navigate({ name: "relay-chat" })}
                >
                    <MaterialDesignIcon iconName="forum" class="size-5" />
                    {#if shell.global.relayChatUnreadCount > 0}
                        <span
                            class="absolute -top-0.5 -right-0.5 inline-flex h-4 min-w-4 items-center justify-center rounded-full bg-red-500 px-1 text-[10px] font-bold leading-none text-white"
                        >
                            {shell.global.relayChatUnreadCount > 99 ? "99+" : shell.global.relayChatUnreadCount}
                        </span>
                    {/if}
                </button>
            {/if}
            <button
                type="button"
                class="relative inline-flex size-11 sm:size-8 shrink-0 items-center justify-center rounded-full bg-sem-surface-muted text-sem-fg-muted transition-colors hover:bg-sem-surface-raised"
                title={tr("app.audio_calls")}
                aria-label={tr("app.audio_calls")}
                data-testid="header-telephone"
                onclick={() => void navigate({ name: "call" })}
            >
                <MaterialDesignIcon iconName="phone" class="size-5" />
                {#if shell.global.missedCallsCount > 0}
                    <span
                        class="absolute -top-0.5 -right-0.5 inline-flex h-4 min-w-4 items-center justify-center rounded-full bg-red-500 px-1 text-[10px] font-bold leading-none text-white"
                    >
                        {shell.global.missedCallsCount > 99 ? "99+" : shell.global.missedCallsCount}
                    </span>
                {/if}
            </button>
            <button
                type="button"
                class="sm:hidden inline-flex size-11 shrink-0 items-center justify-center rounded-full bg-sem-surface-muted text-sem-fg-muted transition-colors hover:bg-sem-surface-raised"
                title={shell.isSyncingPropagationNode ? tr("app.syncing") : tr("app.sync_messages")}
                onclick={() => void syncPropagationNode(shell)}
            >
                <MaterialDesignIcon
                    iconName="refresh"
                    class="size-5 {shell.isSyncingPropagationNode ? 'animate-spin' : ''}"
                />
            </button>
            {#if shell.inboundDeliveryCount > 0}
                <button
                    type="button"
                    class="sm:hidden inline-flex size-11 shrink-0 items-center justify-center rounded-full bg-amber-50 text-amber-700 transition-colors hover:bg-amber-100 dark:bg-amber-900/20 dark:text-amber-300 dark:hover:bg-amber-900/40"
                    title={tr("app.cancel_inbound_deliveries")}
                    onclick={() => void cancelInboundDeliveries(shell)}
                >
                    <MaterialDesignIcon iconName="close-circle-outline" class="size-5" />
                </button>
            {/if}
            <button
                type="button"
                class="hidden sm:inline-flex rounded-full"
                onclick={() => void syncPropagationNode(shell)}
            >
                <span
                    class="inline-flex min-h-8 items-center gap-1 rounded-full border border-sem-border bg-sem-surface-raised px-2.5 py-1 text-sem-fg leading-none shadow-xs transition hover:border-sem-accent"
                >
                    <MaterialDesignIcon
                        iconName="refresh"
                        class="size-5 shrink-0 {shell.isSyncingPropagationNode ? 'animate-spin' : ''}"
                    />
                    <span class="text-sm font-medium leading-none">
                        {shell.isSyncingPropagationNode ? tr("app.syncing") : tr("app.sync_messages")}
                    </span>
                </span>
            </button>
            {#if shell.inboundDeliveryCount > 0}
                <button
                    type="button"
                    class="hidden sm:inline-flex rounded-full"
                    onclick={() => void cancelInboundDeliveries(shell)}
                >
                    <span
                        class="inline-flex min-h-8 items-center gap-1 rounded-full border border-amber-200 bg-amber-50 px-2.5 py-1 text-amber-800 leading-none shadow-xs transition hover:border-amber-400 dark:border-amber-800/60 dark:bg-amber-900/20 dark:text-amber-200 dark:hover:border-amber-500/60"
                    >
                        <MaterialDesignIcon iconName="close-circle-outline" class="size-5 shrink-0" />
                        <span class="text-sm font-medium leading-none">
                            {tr("app.cancel_inbound_deliveries_count", {
                                count: shell.inboundDeliveryCount,
                            })}
                        </span>
                    </span>
                </button>
            {/if}
            <button
                type="button"
                class="inline-flex min-h-11 min-w-11 sm:min-h-0 sm:min-w-0 items-center justify-center rounded-full"
                title={tr("app.compose")}
                aria-label={tr("app.compose")}
                data-testid="header-compose"
                onclick={() => void composeNewMessage(shell)}
            >
                <span
                    class="inline-flex min-h-8 items-center gap-1 rounded-full border border-sem-action-primary bg-sem-action-primary px-2.5 py-1 text-white leading-none shadow-xs transition hover:bg-sem-action-primary-hover"
                >
                    <MaterialDesignIcon iconName="email" class="size-5 shrink-0" />
                    <span class="hidden sm:inline text-sm font-medium leading-none">
                        {tr("app.compose")}
                    </span>
                </span>
            </button>
        </div>
    </div>
</div>
