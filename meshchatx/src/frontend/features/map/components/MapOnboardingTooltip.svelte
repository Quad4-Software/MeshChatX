<!-- SPDX-License-Identifier: 0BSD -->

<script lang="ts">
    import MaterialDesignIcon from "../../../ui/svelte/MaterialDesignIcon.svelte";
    import { t } from "../../../js/i18n.js";

    interface Props {
        show?: boolean;
        style?: string;
        arrowPath?: string | null;
        isMobileScreen?: boolean;
        ondismiss?: () => void;
    }

    let { show = false, style = "", arrowPath = null, isMobileScreen = false, ondismiss }: Props = $props();
</script>

{#if show}
    <!-- svelte-ignore a11y_no_noninteractive_element_interactions, a11y_click_events_have_key_events -->
    <div
        class="fixed inset-0 z-100 pointer-events-none"
        onclick={() => ondismiss?.()}
        onkeydown={(e) => {
            if (e.key === "Escape") ondismiss?.();
        }}
        role="presentation"
    >
        <div class="absolute inset-0 bg-black/50 pointer-events-auto"></div>
        <!-- svelte-ignore a11y_no_noninteractive_element_interactions, a11y_click_events_have_key_events -->
        <div
            class="absolute bg-sem-surface rounded-xl shadow-2xl border border-sem-border p-4 pointer-events-auto max-w-xs sm:max-w-sm"
            {style}
            role="dialog"
            aria-modal="true"
            tabindex="-1"
            onclick={(e) => e.stopPropagation()}
            onkeydown={(e) => {
                if (e.key === "Escape") ondismiss?.();
            }}
        >
            <div class="flex items-start justify-between mb-2">
                <h3 class="font-semibold text-sem-fg text-sm">
                    {t("map.onboarding_title")}
                </h3>
                <button
                    type="button"
                    class="text-sem-fg-muted hover:text-sem-fg cursor-pointer"
                    onclick={() => ondismiss?.()}
                >
                    <MaterialDesignIcon iconName="close" class="size-4" />
                </button>
            </div>
            <p class="text-sm text-sem-fg-muted mb-3">
                {t("map.onboarding_text")}
            </p>
            <button
                type="button"
                class="w-full px-3 py-2 bg-blue-500 hover:bg-blue-600 text-white rounded-lg transition-colors text-sm font-medium cursor-pointer"
                onclick={() => ondismiss?.()}
            >
                {t("map.onboarding_got_it")}
            </button>
        </div>
        {#if arrowPath && !isMobileScreen}
            <svg class="absolute inset-0 w-full h-full pointer-events-none z-101">
                <path
                    d={arrowPath}
                    fill="none"
                    stroke="#3b82f6"
                    stroke-width="3"
                    stroke-dasharray="6 4"
                    class="animate-pulse"
                />
            </svg>
        {/if}
    </div>
{/if}
