<!-- SPDX-License-Identifier: 0BSD -->

<script lang="ts">
    import { onDestroy } from "svelte";
    import MaterialDesignIcon from "../../../ui/svelte/MaterialDesignIcon.svelte";
    import { t } from "../../../js/i18n.js";
    import { hubDisplayName } from "../lib/relayFormatters.js";
    import type { RrcHub } from "../lib/types.js";

    interface Props {
        selectedHub?: RrcHub | null;
        selectedRoom?: string | null;
        isPopoutMode?: boolean;
        showMembers?: boolean;
        showSearch?: boolean;
        smUp?: boolean;
        memberCount?: number;
        onback?: () => void;
        ontogglemembers?: () => void;
        ontogglesearch?: () => void;
        onopenchatprefs?: () => void;
        onpopout?: () => void;
        onleaveroom?: () => void;
        onclearmessages?: () => void;
    }

    let {
        selectedHub = null,
        selectedRoom = null,
        isPopoutMode = false,
        showMembers = false,
        showSearch = false,
        smUp = false,
        memberCount = 0,
        onback,
        ontogglemembers,
        ontogglesearch,
        onopenchatprefs,
        onpopout,
        onleaveroom,
        onclearmessages,
    }: Props = $props();

    const BTN_ICON =
        "inline-flex items-center justify-center rounded-lg border border-sem-border bg-sem-canvas p-2 text-sem-fg transition hover:bg-sem-surface/60 disabled:opacity-50 disabled:cursor-not-allowed";
    const BTN_DANGER =
        "inline-flex items-center justify-center rounded-lg border border-sem-border bg-sem-canvas p-2 text-sem-fg transition hover:border-sem-danger hover:text-sem-danger hover:bg-sem-danger/10 disabled:opacity-50 disabled:cursor-not-allowed";

    let overflowOpen = $state(false);
    let overflowRoot = $state<HTMLDivElement | null>(null);

    function onWindowClick(event: MouseEvent) {
        if (!overflowOpen) {
            return;
        }
        const target = event.target as Node | null;
        if (overflowRoot && target && !overflowRoot.contains(target)) {
            overflowOpen = false;
        }
    }

    $effect(() => {
        if (overflowOpen) {
            window.addEventListener("click", onWindowClick, true);
            return () => window.removeEventListener("click", onWindowClick, true);
        }
    });

    onDestroy(() => {
        window.removeEventListener("click", onWindowClick, true);
    });
</script>

<div
    class="flex items-center justify-between gap-3 px-2 py-2.5 border-b border-sem-border bg-sem-canvas sm:px-3 shrink-0"
>
    <div class="flex min-w-0 items-center gap-2">
        {#if !isPopoutMode}
            <button
                type="button"
                class="md:hidden rounded-lg p-1.5 text-sem-fg-muted hover:bg-sem-surface/60 cursor-pointer"
                title={t("relay_chat.back")}
                onclick={() => onback?.()}
            >
                <MaterialDesignIcon iconName="arrow-left" class="size-5" />
            </button>
        {/if}
        <MaterialDesignIcon iconName="pound" class="size-5 shrink-0 text-sem-accent" />
        <div class="min-w-0">
            <div class="font-semibold truncate leading-tight">{selectedRoom}</div>
            {#if selectedHub}
                <div
                    class="text-xs text-sem-fg-muted truncate"
                    title={selectedHub.motd
                        ? `${hubDisplayName(selectedHub)} - ${selectedHub.motd}`
                        : hubDisplayName(selectedHub)}
                >
                    {hubDisplayName(selectedHub)}{#if selectedHub.motd}
                        · {selectedHub.motd}{/if}
                </div>
            {/if}
        </div>
    </div>
    <div class="flex items-center gap-1.5 shrink-0">
        <button
            type="button"
            title={showMembers ? t("relay_chat.hide_members") : t("relay_chat.show_members")}
            class="inline-flex items-center gap-1 rounded-lg border px-2 py-1.5 text-sm font-medium transition cursor-pointer {showMembers
                ? 'border-sem-action-primary bg-sem-action-primary/15 text-sem-accent'
                : 'border-sem-border bg-sem-canvas text-sem-fg hover:bg-sem-surface/60'}"
            onclick={() => ontogglemembers?.()}
        >
            <MaterialDesignIcon iconName="account-group" class="size-5" />
            <span class="text-xs font-semibold">{memberCount}</span>
        </button>
        <div class="hidden md:contents">
            <button
                type="button"
                class={BTN_ICON}
                title={t("relay_chat.search_messages")}
                onclick={() => ontogglesearch?.()}
            >
                <MaterialDesignIcon iconName="magnify" class="size-5" />
            </button>
            <button
                type="button"
                class={BTN_ICON}
                title={t("relay_chat.chat_prefs")}
                onclick={() => onopenchatprefs?.()}
            >
                <MaterialDesignIcon iconName="tune-variant" class="size-5" />
            </button>
            {#if smUp && !isPopoutMode}
                <button
                    type="button"
                    data-testid="relay-popout"
                    class={BTN_ICON}
                    title={t("relay_chat.popout_channel")}
                    onclick={() => onpopout?.()}
                >
                    <MaterialDesignIcon iconName="open-in-new" class="size-5" />
                </button>
            {/if}
            <button
                type="button"
                class={BTN_ICON}
                title={t("relay_chat.clear_messages")}
                onclick={() => onclearmessages?.()}
            >
                <MaterialDesignIcon iconName="broom" class="size-5" />
            </button>
            <button type="button" class={BTN_DANGER} title={t("relay_chat.leave_room")} onclick={() => onleaveroom?.()}>
                <MaterialDesignIcon iconName="exit-to-app" class="size-5" />
            </button>
        </div>
        <div class="relative md:hidden shrink-0" bind:this={overflowRoot}>
            <button
                type="button"
                class={BTN_ICON}
                title={t("messages.more_actions")}
                aria-label={t("messages.more_actions")}
                onclick={() => {
                    overflowOpen = !overflowOpen;
                }}
            >
                <MaterialDesignIcon iconName="dots-horizontal" class="size-5" />
            </button>
            {#if overflowOpen}
                <div class="absolute right-0 top-full mt-1 z-50 min-w-44">
                    <div
                        class="dropdown-caret pointer-events-none absolute -top-[4px] right-3 border-t border-l border-sem-border"
                        aria-hidden="true"
                    ></div>
                    <div class="bg-sem-surface border border-sem-border rounded-xl shadow-xl py-1 text-sem-fg">
                        <button
                            type="button"
                            class="flex w-full items-center gap-2 px-3 py-2 text-left text-sm hover:bg-sem-surface-muted cursor-pointer"
                            onclick={() => {
                                overflowOpen = false;
                                ontogglesearch?.();
                            }}
                        >
                            <MaterialDesignIcon iconName="magnify" class="size-5" />
                            <span>{t("relay_chat.search_messages")}</span>
                        </button>
                        <button
                            type="button"
                            class="flex w-full items-center gap-2 px-3 py-2 text-left text-sm hover:bg-sem-surface-muted cursor-pointer"
                            onclick={() => {
                                overflowOpen = false;
                                onopenchatprefs?.();
                            }}
                        >
                            <MaterialDesignIcon iconName="tune-variant" class="size-5" />
                            <span>{t("relay_chat.chat_prefs")}</span>
                        </button>
                        <button
                            type="button"
                            class="flex w-full items-center gap-2 px-3 py-2 text-left text-sm hover:bg-sem-surface-muted cursor-pointer"
                            onclick={() => {
                                overflowOpen = false;
                                onclearmessages?.();
                            }}
                        >
                            <MaterialDesignIcon iconName="broom" class="size-5" />
                            <span>{t("relay_chat.clear_messages")}</span>
                        </button>
                        <button
                            type="button"
                            class="flex w-full items-center gap-2 px-3 py-2 text-left text-sm hover:bg-sem-surface-muted cursor-pointer"
                            onclick={() => {
                                overflowOpen = false;
                                onleaveroom?.();
                            }}
                        >
                            <MaterialDesignIcon iconName="exit-to-app" class="size-5" />
                            <span>{t("relay_chat.leave_room")}</span>
                        </button>
                    </div>
                </div>
            {/if}
        </div>
    </div>
</div>
