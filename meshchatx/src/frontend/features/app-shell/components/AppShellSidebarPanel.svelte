<!-- SPDX-License-Identifier: 0BSD -->

<script lang="ts">
    /**
     * Sidebar column: collapse and nav edit controls, the grouped or classic
     * nav, the identity footer, and the version link.
     */
    import { t } from "../../../js/i18n.js";
    import MaterialDesignIcon from "../../../ui/svelte/MaterialDesignIcon.svelte";
    import LanguageSelector from "../../../ui/svelte/LanguageSelector.svelte";
    import AppSidebarNav from "./AppSidebarNav.svelte";
    import AppSidebarClassicNav from "./AppSidebarClassicNav.svelte";
    import AppSidebarAccountFooter from "./AppSidebarAccountFooter.svelte";
    import AppSidebarClassicFooter from "./AppSidebarClassicFooter.svelte";
    import type { AppShellState } from "../lib/appShellState.svelte.js";
    import { toggleTheme, onLanguageChange } from "../lib/appShellConfig.js";
    import {
        copyValue,
        flushIdentitySave,
        onAnnounceIntervalChange,
        onDisplayNameUpdate,
        openLxmfQr,
        sendAnnounce,
    } from "../lib/appShellIdentity.js";
    import { navigate } from "../../../shell/hashRouter.js";
    import {
        enterSidebarNavEdit,
        onMoreNavToggle,
        onSidebarNavReorder,
        saveSidebarNavLayout,
        toggleSidebarCollapsed,
    } from "../lib/appShellNav.js";

    interface Props {
        shell: AppShellState;
    }

    let { shell }: Props = $props();

    const tr = $derived.by(() => {
        void shell.localeVersion;
        return (key: string, values?: Record<string, unknown>) => t(key, values);
    });
</script>

<div
    class="absolute inset-y-0 left-0 z-70 transform transition-all duration-300 ease-in-out sm:relative sm:inset-auto sm:z-0 sm:flex sm:translate-x-0 {shell.isSidebarOpen
        ? 'translate-x-0'
        : '-translate-x-full'} {shell.isSidebarCollapsed ? 'w-14' : 'w-80 md:max-lg:w-64 lg:w-80'}"
>
    <div class="flex h-full w-full flex-col overflow-y-auto border-r border-sem-border bg-sem-canvas">
        <!-- toggle row for desktop (h-10 aligns with Messages/Nomad collapse rows) -->
        <div
            class="h-10 shrink-0 items-center gap-1 border-b border-sem-border px-2 {shell.isSidebarNavEditing &&
            !shell.isSidebarCollapsed
                ? 'flex'
                : 'hidden sm:flex'} {shell.isSidebarCollapsed ? 'justify-center' : 'justify-end'}"
        >
            {#if shell.isSidebarNavEditing && !shell.isSidebarCollapsed}
                <button
                    type="button"
                    class="p-1.5 rounded-lg text-sem-fg-muted hover:bg-sem-surface-muted transition-colors"
                    data-testid="sidebar-nav-layout-save"
                    title={tr("common.save")}
                    aria-label={tr("common.save")}
                    onclick={() => saveSidebarNavLayout(shell)}
                >
                    <MaterialDesignIcon iconName="content-save" class="size-5" />
                </button>
            {/if}
            <button
                type="button"
                class="p-1.5 rounded-lg text-sem-fg-muted hover:bg-sem-surface-muted transition-colors hidden sm:inline-flex"
                onclick={() => toggleSidebarCollapsed(shell)}
            >
                <MaterialDesignIcon
                    iconName={shell.isSidebarCollapsed ? "chevron-right" : "chevron-left"}
                    class="size-5"
                />
            </button>
        </div>

        <!-- mobile-only quick settings row (theme + language) -->
        <div class="sm:hidden flex items-center justify-between gap-2 px-3 py-2 border-b border-sem-border">
            <button
                type="button"
                class="flex items-center gap-2 flex-1 rounded-lg px-2 py-1.5 text-sm font-medium text-sem-fg hover:bg-sem-surface-muted transition-colors"
                title={shell.themeToggleTitle}
                onclick={() => void toggleTheme(shell)}
            >
                <MaterialDesignIcon iconName={shell.themeToggleIcon} class="w-5 h-5 shrink-0" />
                <span class="truncate">{shell.themeToggleTitle}</span>
            </button>
            <LanguageSelector onlanguagechange={(code) => void onLanguageChange(shell, code)} />
        </div>

        {#if shell.useGroupedAppSidebar}
            <AppSidebarNav
                primaryNavGroups={shell.primaryNavGroups}
                moreNavItems={shell.moreNavItems}
                isCollapsed={shell.isSidebarCollapsed}
                isEditing={shell.isSidebarNavEditing}
                isShowingMoreNav={shell.isShowingMoreNav}
                unreadConversationsCount={shell.global.unreadConversationsCount}
                relayChatUnreadCount={shell.global.relayChatUnreadCount}
                missedCallsCount={shell.global.missedCallsCount}
                activeRouteName={shell.routeName}
                onmoretoggle={() => onMoreNavToggle(shell)}
                oneditstart={() => enterSidebarNavEdit(shell)}
                onnavreorder={(op) => onSidebarNavReorder(shell, op)}
            />
        {:else}
            <AppSidebarClassicNav
                navItems={shell.visibleNavItems}
                isCollapsed={shell.isSidebarCollapsed}
                isEditing={shell.isSidebarNavEditing}
                unreadConversationsCount={shell.global.unreadConversationsCount}
                relayChatUnreadCount={shell.global.relayChatUnreadCount}
                missedCallsCount={shell.global.missedCallsCount}
                activeRouteName={shell.routeName}
                oneditstart={() => enterSidebarNavEdit(shell)}
                onnavreorder={(op) => onSidebarNavReorder(shell, op)}
            />
        {/if}

        <div>
            {#if shell.config && shell.useGroupedAppSidebar}
                <AppSidebarAccountFooter
                    config={shell.config}
                    displayName={shell.displayName}
                    identityLabel={shell.identitySidebarLabel}
                    lastAnnouncedLabel={shell.lastAnnouncedSidebarLabel}
                    isCollapsed={shell.isSidebarCollapsed}
                    onupdatedisplayname={(value) => onDisplayNameUpdate(shell, value)}
                    onsaveidentity={() => flushIdentitySave(shell)}
                    onsendannounce={() => void sendAnnounce(shell)}
                    onannounceintervalchange={(seconds) => void onAnnounceIntervalChange(shell, seconds)}
                    oncopyvalue={(value, label) => void copyValue(shell, value, label)}
                    onopenlxmfqr={() => void openLxmfQr(shell)}
                    onnavigatetoidentities={() => void navigate({ name: "identities" })}
                />
            {:else if shell.config}
                <AppSidebarClassicFooter
                    config={shell.config}
                    displayName={shell.displayName}
                    identityLabel={shell.identitySidebarLabel}
                    lastAnnouncedLabel={shell.lastAnnouncedSidebarLabel}
                    isCollapsed={shell.isSidebarCollapsed}
                    onupdatedisplayname={(value) => onDisplayNameUpdate(shell, value)}
                    onsaveidentity={() => flushIdentitySave(shell)}
                    onsendannounce={() => void sendAnnounce(shell)}
                    onannounceintervalchange={(seconds) => void onAnnounceIntervalChange(shell, seconds)}
                    oncopyvalue={(value, label) => void copyValue(shell, value, label)}
                    onopenlxmfqr={() => void openLxmfQr(shell)}
                />
            {/if}

            {#if shell.appInfo?.version}
                <div class="shrink-0 border-t border-sem-border bg-sem-canvas">
                    <a
                        href="#/about"
                        class="flex items-center gap-2 py-2 text-[10px] font-mono text-gray-500 transition-colors hover:text-gray-700 text-sem-fg-muted dark:hover:text-zinc-300 {shell.isSidebarCollapsed
                            ? 'justify-center px-0'
                            : 'justify-start px-3'}"
                        data-testid="sidebar-app-version"
                        title={shell.sidebarVersionTitle}
                    >
                        {#if shell.isSidebarCollapsed}
                            <MaterialDesignIcon iconName="information-outline" class="size-4" />
                        {:else}
                            <span>{shell.sidebarVersionLabel}</span>
                            {#if shell.sidebarChannelLabel}
                                <span
                                    class="inline-flex h-4 items-center rounded-xs px-1.5 text-[9px] font-black uppercase tracking-tighter {shell.sidebarChannelBadgeClass}"
                                    data-testid="sidebar-channel-badge"
                                >
                                    {shell.sidebarChannelLabel}
                                </span>
                            {/if}
                        {/if}
                    </a>
                </div>
            {/if}
        </div>
    </div>
</div>
