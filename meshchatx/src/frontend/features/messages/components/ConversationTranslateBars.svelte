<!-- SPDX-License-Identifier: 0BSD -->

<script lang="ts">
    import MaterialDesignIcon from "../../../ui/svelte/MaterialDesignIcon.svelte";
    import { t } from "../../../js/i18n.js";

    type LangOption = { value: string; label: string };

    let {
        mode = "compose" as "compose" | "bubble",
        open = false,
        options = [] as LangOption[],
        value = $bindable(""),
        working = false,
        onconfirm,
        onclose,
        onoutside,
    }: {
        mode?: "compose" | "bubble";
        open?: boolean;
        options?: LangOption[];
        value?: string;
        working?: boolean;
        onconfirm?: () => void;
        onclose?: () => void;
        onoutside?: () => void;
    } = $props();

    let rootEl: HTMLDivElement | undefined = $state();

    $effect(() => {
        if (!open || mode !== "bubble") return;
        const onDoc = (event: MouseEvent) => {
            if (rootEl && !rootEl.contains(event.target as Node)) {
                onoutside?.();
            }
        };
        document.addEventListener("mousedown", onDoc, true);
        return () => document.removeEventListener("mousedown", onDoc, true);
    });
</script>

{#if open && mode === "compose"}
    <div
        class="mt-2 flex flex-wrap items-stretch sm:items-center gap-2 rounded-xl border border-indigo-200/60 dark:border-indigo-500/30 bg-indigo-50/80 dark:bg-indigo-950/25 px-2.5 py-2"
    >
        <MaterialDesignIcon
            iconName="translate"
            class="size-4 text-indigo-600 dark:text-indigo-400 shrink-0 self-center"
        />
        <label
            class="text-xs font-semibold text-indigo-900/90 dark:text-indigo-200/90 shrink-0 self-center"
            for="compose-translate-target"
        >
            {t("messages.translate_select_target")}
        </label>
        <select
            id="compose-translate-target"
            bind:value
            class="flex-1 min-w-0 min-h-[2.25rem] sm:min-h-0 text-sm rounded-lg border border-gray-200/90 dark:border-zinc-600 bg-sem-surface px-2.5 py-1.5 text-sem-fg"
            aria-label={t("messages.translate_select_target")}
        >
            {#each options as opt (`c-${opt.value}`)}
                <option value={opt.value}>{opt.label}</option>
            {/each}
        </select>
        <button
            type="button"
            class="primary-chip text-xs px-3.5 py-1.5 shrink-0"
            disabled={!options.length || working}
            onclick={() => onconfirm?.()}
        >
            {#if working}
                <span
                    class="inline-block w-3 h-3 border-2 border-white border-t-transparent rounded-full animate-spin align-[-0.1em] mr-1.5"
                ></span>
            {/if}
            {t("translator.translate")}
        </button>
        <button
            type="button"
            class="p-1.5 shrink-0 rounded-lg text-zinc-500 hover:bg-black/5 dark:hover:bg-white/10 self-center"
            title={t("common.close")}
            disabled={working}
            onclick={() => onclose?.()}
        >
            <MaterialDesignIcon iconName="close" class="size-4" />
        </button>
        {#if !options.length}
            <p class="w-full text-xs text-amber-700/90 dark:text-amber-300/90 -mt-0.5">
                {t("messages.translate_no_languages")}
            </p>
        {/if}
    </div>
{:else if open && mode === "bubble"}
    <div
        bind:this={rootEl}
        class="translate-bubble-bar fixed z-200 w-[min(calc(100%-1.25rem),24rem)] left-1/2 -translate-x-1/2 bottom-4 sm:bottom-5 pb-[max(0.25rem,env(safe-area-inset-bottom))] pointer-events-auto"
    >
        <div
            class="flex flex-col gap-2 rounded-2xl border border-indigo-200/60 dark:border-indigo-500/30 bg-white/95 dark:bg-zinc-900/95 backdrop-blur-md shadow-xl shadow-indigo-900/5 dark:shadow-black/30 px-3 py-2.5"
        >
            <div class="flex items-center gap-1.5 text-indigo-700/90 dark:text-indigo-300/90">
                <MaterialDesignIcon iconName="translate" class="size-4 shrink-0" />
                <span class="text-sm font-semibold leading-none">{t("messages.translate_select_target")}</span>
            </div>
            <div class="flex flex-wrap sm:flex-nowrap items-stretch gap-2">
                <select
                    bind:value
                    class="flex-1 min-w-0 min-h-[2.5rem] text-sm rounded-lg border border-gray-200/90 dark:border-zinc-600 bg-sem-surface/90 px-2.5 py-1.5 text-sem-fg"
                    aria-label={t("messages.translate_select_target")}
                >
                    {#each options as opt (`b-${opt.value}`)}
                        <option value={opt.value}>{opt.label}</option>
                    {/each}
                </select>
                <div class="flex items-center gap-1.5 w-full sm:w-auto justify-end sm:justify-start">
                    <button
                        type="button"
                        class="primary-chip text-xs px-3.5 py-2"
                        disabled={!options.length || working}
                        onclick={() => onconfirm?.()}
                    >
                        {#if working}
                            <span
                                class="inline-block w-3 h-3 border-2 border-white border-t-transparent rounded-full animate-spin align-[-0.1em] mr-1.5"
                            ></span>
                        {/if}
                        {t("translator.translate")}
                    </button>
                    <button
                        type="button"
                        class="p-2 rounded-lg text-zinc-500 hover:bg-black/5 dark:hover:bg-white/10"
                        title={t("common.close")}
                        disabled={working}
                        onclick={() => onclose?.()}
                    >
                        <MaterialDesignIcon iconName="close" class="size-4" />
                    </button>
                </div>
            </div>
            {#if !options.length}
                <p class="text-xs text-amber-700/90 dark:text-amber-300/90 -mt-0.5">
                    {t("messages.translate_no_languages")}
                </p>
            {/if}
        </div>
    </div>
{/if}
