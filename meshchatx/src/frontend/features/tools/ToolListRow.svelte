<!-- SPDX-License-Identifier: 0BSD AND MIT -->

<script>
    import MaterialDesignIcon from "../../ui/svelte/MaterialDesignIcon.svelte";
    import { t } from "../../js/i18n.js";

    /** @type {{ tool: Record<string, unknown> }} */
    let { tool } = $props();

    const iconShellClass = $derived(
        [
            "w-11 h-11 sm:w-12 sm:h-12 rounded-xl flex items-center justify-center shrink-0",
            String(tool.iconBg || "")
                .replace(/\btool-card__icon\b/g, "")
                .trim(),
        ]
            .filter(Boolean)
            .join(" ")
    );
</script>

<div class={iconShellClass}>
    {#if tool.icon}
        <MaterialDesignIcon iconName={String(tool.icon)} class="size-6" />
    {:else if tool.image}
        <img src={String(tool.image)} class={String(tool.imageClass || "")} alt={String(tool.imageAlt || "")} />
    {/if}
</div>
<div class="flex-1 min-w-0">
    <div class="flex items-center gap-2 flex-wrap">
        <div class="text-base sm:text-lg font-semibold text-sem-fg">{String(tool.title || "")}</div>
        {#if tool.alpha}
            <span
                class="px-1.5 py-0.5 text-[10px] font-bold uppercase tracking-wider bg-violet-100 dark:bg-violet-900/30 text-violet-700 dark:text-violet-300 rounded-sm border border-violet-200 dark:border-violet-800"
            >
                {t("tools.alpha_badge")}
            </span>
        {/if}
        {#if tool.beta}
            <span
                class="px-1.5 py-0.5 text-[10px] font-bold uppercase tracking-wider bg-amber-100 dark:bg-amber-900/30 text-amber-700 dark:text-amber-300 rounded-sm border border-amber-200 dark:border-amber-800"
            >
                {t("tools.beta_badge")}
            </span>
        {/if}
        {#if tool.comingSoon}
            <span
                class="px-1.5 py-0.5 text-[10px] font-bold uppercase tracking-wider bg-sem-surface-muted text-sem-fg-muted rounded-sm border border-sem-border"
            >
                {t("tools.coming_soon_badge")}
            </span>
        {/if}
    </div>
    <div class="text-sm text-sem-fg-muted mt-0.5 line-clamp-2 sm:line-clamp-none">
        {String(tool.description || "")}
    </div>
</div>
{#if !tool.comingSoon}
    <div class="shrink-0 flex items-center gap-1">
        {#if tool.extraAction && typeof tool.extraAction === "object"}
            {@const action = tool.extraAction}
            <div class="flex items-center gap-2">
                <a
                    href={String(action.href || "#")}
                    target={action.target ? String(action.target) : undefined}
                    class="p-2 hover:bg-sem-surface-muted rounded-lg transition-colors text-gray-400 hover:text-blue-500"
                    onclick={(e) => e.stopPropagation()}
                >
                    <MaterialDesignIcon iconName={String(action.icon || "open-in-new")} class="size-5" />
                </a>
                <MaterialDesignIcon iconName="chevron-right" class="size-5 text-gray-400 shrink-0" />
            </div>
        {:else}
            <MaterialDesignIcon iconName="chevron-right" class="size-5 text-gray-400 shrink-0" />
        {/if}
    </div>
{/if}
