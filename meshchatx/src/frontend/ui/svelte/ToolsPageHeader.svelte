<!-- SPDX-License-Identifier: 0BSD -->

<script>
    import MaterialDesignIcon from "./MaterialDesignIcon.svelte";
    import { t } from "../../js/i18n.js";

    const ACCENT = {
        blue: { wrap: "bg-blue-100 dark:bg-blue-900/30", icon: "text-sem-accent" },
        indigo: { wrap: "bg-indigo-100 dark:bg-indigo-900/30", icon: "text-indigo-600 dark:text-indigo-400" },
        teal: { wrap: "bg-teal-100 dark:bg-teal-900/30", icon: "text-teal-600 dark:text-teal-400" },
        purple: { wrap: "bg-purple-100 dark:bg-purple-900/30", icon: "text-purple-600 dark:text-purple-400" },
        green: { wrap: "bg-green-100 dark:bg-green-900/30", icon: "text-green-600 dark:text-green-400" },
        orange: { wrap: "bg-orange-100 dark:bg-orange-900/30", icon: "text-orange-600 dark:text-orange-400" },
        cyan: { wrap: "bg-cyan-100 dark:bg-cyan-900/30", icon: "text-cyan-600 dark:text-cyan-400" },
        rose: { wrap: "bg-rose-100 dark:bg-rose-900/30", icon: "text-rose-600 dark:text-rose-400" },
        violet: { wrap: "bg-violet-100 dark:bg-violet-900/30", icon: "text-violet-600 dark:text-violet-400" },
        amber: { wrap: "bg-amber-100 dark:bg-amber-900/30", icon: "text-amber-600 dark:text-amber-400" },
        sky: { wrap: "bg-sky-100 dark:bg-sky-900/30", icon: "text-sky-600 dark:text-sky-400" },
        red: { wrap: "bg-red-100 dark:bg-red-900/30", icon: "text-red-600 dark:text-red-400" },
        zinc: { wrap: "bg-zinc-100 dark:bg-zinc-800", icon: "text-zinc-600 text-sem-fg-muted" },
    };

    /**
     * @type {{
     *   icon: string,
     *   title: string,
     *   description?: string,
     *   eyebrow?: string,
     *   accent?: string,
     *   backTo?: string,
     *   backLabel?: string,
     *   children?: import('svelte').Snippet,
     * }}
     */
    let {
        icon,
        title,
        description = "",
        eyebrow = "",
        accent = "blue",
        backTo = "/tools",
        backLabel = "",
        children,
    } = $props();

    const palette = $derived(ACCENT[accent] || ACCENT.blue);
    const resolvedBackLabel = $derived(backLabel || t("app.tools"));
    const backHref = $derived(
        (() => {
            const raw = String(backTo || "/tools");
            if (raw.startsWith("#")) {
                return raw;
            }
            const path = raw.startsWith("/") ? raw : `/${raw}`;
            return `#${path}`;
        })()
    );
</script>

<div
    class="flex flex-wrap items-center gap-x-2 gap-y-2 pl-1.5 pr-3 sm:pl-2 sm:pr-4 md:pl-4 md:pr-6 py-3 sm:py-4 border-b border-sem-border bg-sem-canvas shrink-0 min-w-0"
>
    <a
        href={backHref}
        class="inline-flex items-center justify-center gap-0.5 sm:gap-1 rounded-lg pl-0 pr-1.5 sm:pr-2 py-2 min-h-9 min-w-9 sm:min-w-0 text-sm font-medium text-sem-fg-muted hover:bg-sem-surface-muted transition-colors shrink-0 order-first"
        aria-label={t("tools.back_to_tools")}
    >
        <MaterialDesignIcon iconName="chevron-left" />
        <span class="hidden sm:inline truncate max-w-[8rem]">{resolvedBackLabel}</span>
    </a>

    <div class="flex items-center gap-2 sm:gap-3 min-w-0 flex-1 basis-0">
        <div class="p-2 rounded-lg shrink-0 {palette.wrap}">
            <span class={palette.icon}>
                <MaterialDesignIcon iconName={icon} />
            </span>
        </div>
        <div class="min-w-0">
            {#if eyebrow}
                <p class="text-xs uppercase tracking-wide text-sem-fg-muted truncate">
                    {eyebrow}
                </p>
            {/if}
            <h1 class="text-lg sm:text-xl font-bold text-sem-fg truncate">
                {title}
            </h1>
            {#if description}
                <p class="text-xs sm:text-sm text-sem-fg-muted line-clamp-2 sm:line-clamp-none">
                    {description}
                </p>
            {/if}
        </div>
    </div>

    {#if children}
        <div class="flex items-center gap-2 shrink-0 ml-auto">
            {@render children()}
        </div>
    {/if}
</div>
