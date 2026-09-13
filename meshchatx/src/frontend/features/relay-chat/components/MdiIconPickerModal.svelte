<!-- SPDX-License-Identifier: 0BSD -->

<script lang="ts">
    import MaterialDesignIcon from "../../../ui/svelte/MaterialDesignIcon.svelte";
    import { buildMdiIconNames } from "../../../js/mdiIconNames.js";
    import { t } from "../../../js/i18n.js";
    import { BTN_SECONDARY } from "../lib/constants.js";

    interface Props {
        open?: boolean;
        selectedIcon?: string | null;
        previewIconClass?: string;
        onclose?: () => void;
        onselect?: (icon: string | null) => void;
    }

    let {
        open = false,
        selectedIcon = null,
        previewIconClass = "text-sem-fg-secondary",
        onclose,
        onselect,
    }: Props = $props();

    let search = $state("");
    const maxSearchResults = 200;
    let iconNames = $state<string[]>([]);
    let searchInputEl: HTMLInputElement | null = $state(null);

    const searchedIconNames = $derived.by(() => {
        const q = search.trim().toLowerCase();
        const list = q ? iconNames.filter((name) => name.includes(q)) : iconNames;
        return list.slice(0, maxSearchResults);
    });

    $effect(() => {
        if (open) {
            search = "";
            if (iconNames.length === 0) {
                iconNames = buildMdiIconNames();
            }
            setTimeout(() => {
                searchInputEl?.focus();
            }, 0);
        }
    });

    function pick(iconName: string | null): void {
        onselect?.(iconName);
        onclose?.();
    }
</script>

{#if open}
    <div
        class="fixed inset-0 z-[60] flex items-center justify-center bg-black/50 p-4"
        role="presentation"
        onclick={(e) => {
            if (e.target === e.currentTarget) onclose?.();
        }}
    >
        <div
            class="flex w-full max-w-lg max-h-[min(36rem,90vh)] flex-col rounded-2xl border border-sem-border-card bg-sem-surface shadow-xl"
            role="dialog"
            aria-label={t("relay_chat.hub_icon_picker_title")}
        >
            <div class="flex items-center justify-between gap-2 border-b border-sem-border px-5 py-4">
                <h2 class="text-lg font-semibold">{t("relay_chat.hub_icon_picker_title")}</h2>
                <button
                    type="button"
                    class="rounded-lg p-1 text-sem-fg-muted hover:bg-sem-surface/60"
                    title={t("common.close")}
                    onclick={onclose}
                >
                    <MaterialDesignIcon iconName="close" class="size-5" />
                </button>
            </div>
            <div class="px-5 pt-3">
                <div class="relative">
                    <input
                        bind:this={searchInputEl}
                        bind:value={search}
                        type="text"
                        placeholder={t("relay_chat.hub_icon_search", { count: iconNames.length })}
                        class="input-field py-2.5! pr-10"
                    />
                    <MaterialDesignIcon
                        iconName="magnify"
                        class="pointer-events-none absolute right-3 top-1/2 size-5 -translate-y-1/2 text-sem-fg-muted"
                    />
                </div>
            </div>
            <div class="flex-1 overflow-y-auto custom-scrollbar px-5 py-3">
                <div class="grid grid-cols-4 sm:grid-cols-5 gap-2">
                    {#each searchedIconNames as iconName (iconName)}
                        <button
                            type="button"
                            class="flex flex-col items-center gap-1 rounded-lg border p-2 transition-colors hover:bg-sem-surface/60 {selectedIcon ===
                            iconName
                                ? 'border-sem-accent bg-sem-accent/10'
                                : 'border-sem-border'}"
                            title={iconName}
                            onclick={() => pick(iconName)}
                        >
                            <MaterialDesignIcon {iconName} class="size-7 {previewIconClass}" />
                            <span class="w-full truncate text-center text-[10px] text-sem-fg-muted">
                                {iconName}
                            </span>
                        </button>
                    {/each}
                </div>
                {#if searchedIconNames.length === 0}
                    <div class="py-8 text-center text-sm text-sem-fg-muted">
                        {t("relay_chat.hub_icon_no_results")}
                    </div>
                {:else if searchedIconNames.length >= maxSearchResults}
                    <div class="pt-2 text-center text-xs text-sem-fg-muted">
                        {t("relay_chat.hub_icon_search_limit", { count: maxSearchResults })}
                    </div>
                {/if}
            </div>
            <div class="flex justify-between gap-2 border-t border-sem-border px-5 py-3">
                <button type="button" class={BTN_SECONDARY} onclick={() => pick(null)}>
                    {t("relay_chat.hub_icon_reset_default")}
                </button>
                <button type="button" class={BTN_SECONDARY} onclick={onclose}>
                    {t("common.cancel")}
                </button>
            </div>
        </div>
    </div>
{/if}
