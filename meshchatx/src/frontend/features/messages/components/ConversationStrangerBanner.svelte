<!-- SPDX-License-Identifier: 0BSD AND MIT -->

<script lang="ts">
    import MaterialDesignIcon from "../../../ui/svelte/MaterialDesignIcon.svelte";
    import { t } from "../../../js/i18n.js";

    let {
        onadd,
        ondismiss,
    }: {
        onadd?: () => void;
        ondismiss?: () => void;
    } = $props();
</script>

<div
    class="mx-3 mt-2 mb-0 px-3 py-1.5 bg-amber-50 dark:bg-amber-900/20 border border-amber-300 dark:border-amber-700 rounded-lg flex flex-row items-center gap-2 text-sm"
>
    <div class="flex items-center gap-2 min-w-0 flex-1">
        <MaterialDesignIcon
            iconName="alert-circle-outline"
            class="w-4 h-4 text-amber-600 dark:text-amber-400 shrink-0"
        />
        <span class="min-w-0 flex-1 truncate text-amber-900 dark:text-amber-200 whitespace-nowrap">
            {t("messages.stranger_banner_text")}
        </span>
    </div>
    <div class="flex items-center gap-2 shrink-0">
        <button
            type="button"
            class="px-2 py-1 text-xs font-medium rounded-md bg-amber-600 hover:bg-amber-700 text-white transition-colors whitespace-nowrap"
            onclick={() => onadd?.()}
        >
            {t("messages.add_to_contacts")}
        </button>
        <button
            type="button"
            class="px-2 py-1 text-xs text-amber-600 dark:text-amber-400 hover:text-amber-800 dark:hover:text-amber-200 transition-colors whitespace-nowrap"
            onclick={() => ondismiss?.()}
        >
            {t("messages.dismiss")}
        </button>
    </div>
</div>
