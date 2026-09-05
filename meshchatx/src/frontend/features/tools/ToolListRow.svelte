<!-- SPDX-License-Identifier: 0BSD AND MIT -->

<script>
    import MaterialDesignIcon from "../../ui/svelte/MaterialDesignIcon.svelte";
    import { t } from "../../js/i18n.js";

    /** @type {{ tool: Record<string, unknown> }} */
    let { tool } = $props();
</script>

<div class={String(tool.iconBg || "")}>
    {#if tool.icon}
        <MaterialDesignIcon iconName={String(tool.icon)} class="w-6 h-6" />
    {:else if tool.image}
        <img src={String(tool.image)} class={String(tool.imageClass || "")} alt={String(tool.imageAlt || "")} />
    {/if}
</div>
<div class="flex-1 min-w-0">
    <div class="flex items-center gap-2 flex-wrap">
        <div class="tool-card__title">{String(tool.title || "")}</div>
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
    <div class="tool-card__description">{String(tool.description || "")}</div>
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
                <MaterialDesignIcon iconName="chevron-right" class="tool-card__chevron" />
            </div>
        {:else}
            <MaterialDesignIcon iconName="chevron-right" class="tool-card__chevron" />
        {/if}
    </div>
{/if}

<style>
    .tool-card__title {
        font-size: 1rem;
        line-height: 1.5rem;
        font-weight: 600;
        color: var(--mc-fg, inherit);
    }
    @media (min-width: 640px) {
        .tool-card__title {
            font-size: 1.125rem;
            line-height: 1.75rem;
        }
    }
    .tool-card__description {
        font-size: 0.875rem;
        line-height: 1.25rem;
        color: var(--mc-fg-muted, #71717a);
        margin-top: 0.125rem;
        display: -webkit-box;
        -webkit-line-clamp: 2;
        line-clamp: 2;
        -webkit-box-orient: vertical;
        overflow: hidden;
    }
    @media (min-width: 640px) {
        .tool-card__description {
            display: block;
            -webkit-line-clamp: unset;
            line-clamp: unset;
            overflow: visible;
        }
    }
    :global(.tool-card__chevron) {
        width: 1.25rem;
        height: 1.25rem;
        color: #9ca3af;
        flex-shrink: 0;
    }
</style>
