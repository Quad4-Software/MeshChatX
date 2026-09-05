<!-- SPDX-License-Identifier: 0BSD -->

<script lang="ts">
    import { t } from "../../js/i18n.js";
    import MaterialDesignIcon from "./MaterialDesignIcon.svelte";

    interface Props {
        offset: number;
        limit: number;
        total: number;
        onPrev?: () => void;
        onNext?: () => void;
        class?: string;
    }

    let { offset, limit, total, onPrev, onNext, class: className = "" }: Props = $props();

    const showingFrom = $derived(total === 0 ? 0 : offset + 1);
    const showingTo = $derived(Math.min(offset + limit, total));
    const canPrev = $derived(offset > 0);
    const canNext = $derived(offset + limit < total);

    const containerClasses = $derived(
        ["px-4 py-3 flex items-center justify-between border-t border-sem-border bg-sem-surface-muted/50", className]
            .filter(Boolean)
            .join(" ")
    );
</script>

<div class={containerClasses}>
    <div class="flex-1 flex justify-between sm:hidden">
        <button
            type="button"
            class="secondary-chip px-3 py-1 text-xs disabled:opacity-50 focus-ring-sem"
            disabled={!canPrev}
            onclick={onPrev}
        >
            <MaterialDesignIcon iconName="chevron-left" class="w-4 h-4" />
            {t("common.previous")}
        </button>
        <button
            type="button"
            class="secondary-chip px-3 py-1 text-xs disabled:opacity-50 focus-ring-sem ml-3"
            disabled={!canNext}
            onclick={onNext}
        >
            {t("common.next")}
            <MaterialDesignIcon iconName="chevron-right" class="w-4 h-4" />
        </button>
    </div>
    <div class="hidden sm:flex-1 sm:flex sm:items-center sm:justify-between">
        <div>
            <p class="text-sm text-sem-fg-muted font-mono">
                {t("common.showing_range", { start: showingFrom, end: showingTo, total })}
            </p>
        </div>
        <div class="flex gap-2">
            <button
                type="button"
                class="secondary-chip px-3 py-1 text-xs disabled:opacity-50 focus-ring-sem"
                disabled={!canPrev}
                onclick={onPrev}
            >
                <MaterialDesignIcon iconName="chevron-left" class="w-4 h-4" />
                {t("common.previous")}
            </button>
            <button
                type="button"
                class="secondary-chip px-3 py-1 text-xs disabled:opacity-50 focus-ring-sem"
                disabled={!canNext}
                onclick={onNext}
            >
                {t("common.next")}
                <MaterialDesignIcon iconName="chevron-right" class="w-4 h-4" />
            </button>
        </div>
    </div>
</div>
