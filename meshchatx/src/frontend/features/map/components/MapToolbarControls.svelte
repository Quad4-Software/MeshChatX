<!-- SPDX-License-Identifier: 0BSD -->

<script lang="ts">
    import MaterialDesignIcon from "../../../ui/svelte/MaterialDesignIcon.svelte";
    import { t } from "../../../js/i18n.js";

    interface Props {
        discoveredVisible?: boolean;
        offlineEnabled?: boolean;
        compact?: boolean;
        ontogglediscovered?: () => void;
        ontoggleoffline?: (enabled: boolean) => void;
        ontogglemotools?: () => void;
        ontogglesettings?: () => void;
        onshare?: () => void;
    }

    let {
        discoveredVisible = false,
        offlineEnabled = false,
        compact = false,
        ontogglediscovered,
        ontoggleoffline,
        ontogglemotools,
        ontogglesettings,
        onshare,
    }: Props = $props();
</script>

<div
    class={compact
        ? "flex flex-wrap items-center gap-x-1.5 gap-y-1 min-w-0 justify-end"
        : "flex flex-wrap items-center gap-x-1.5 gap-y-2 px-3 py-2 sm:px-4 border-b border-sem-border bg-white/80 dark:bg-zinc-900/80 backdrop-blur-sm z-10 relative sm:justify-end min-w-0"}
>
    <div class="flex items-center bg-sem-surface-muted rounded-lg p-0.5 sm:p-1 min-w-0 max-w-full">
        <button
            type="button"
            class="p-1.5 sm:p-2 rounded-lg transition-colors shrink-0 cursor-pointer {discoveredVisible
                ? 'bg-white dark:bg-zinc-700 shadow-xs text-emerald-600 dark:text-emerald-400'
                : 'text-gray-500 dark:text-gray-300'}"
            title={discoveredVisible ? "Hide Discovered Interfaces" : "Show Discovered Interfaces"}
            onclick={ontogglediscovered}
        >
            <MaterialDesignIcon iconName="map-marker-radius" class="size-[18px] sm:size-5" />
        </button>
        <button
            type="button"
            class="px-2 py-1 text-xs sm:px-3 sm:text-sm font-medium rounded-md transition-all shrink-0 cursor-pointer {!offlineEnabled
                ? 'bg-white dark:bg-zinc-700 shadow-xs text-sem-accent'
                : 'text-gray-500 dark:text-gray-300'}"
            onclick={() => ontoggleoffline?.(false)}
        >
            {t("map.online_mode")}
        </button>
        <button
            type="button"
            class="px-2 py-1 text-xs sm:px-3 sm:text-sm font-medium rounded-md transition-all shrink-0 cursor-pointer {offlineEnabled
                ? 'bg-white dark:bg-zinc-700 shadow-xs text-sem-accent'
                : 'text-gray-500 dark:text-gray-300'}"
            onclick={() => ontoggleoffline?.(true)}
        >
            {t("map.offline_mode")}
        </button>
    </div>

    <button
        type="button"
        class="p-2 text-sem-fg-muted hover:bg-sem-surface-muted rounded-full transition-colors shrink-0 cursor-pointer"
        title={t("map.share_view")}
        onclick={onshare}
    >
        <MaterialDesignIcon iconName="share-variant" class="size-[18px] sm:size-5" />
    </button>
    <button
        type="button"
        class="p-2 text-sem-fg-muted hover:bg-sem-surface-muted rounded-full transition-colors shrink-0 cursor-pointer"
        title={t("map.side_panel")}
        onclick={ontogglemotools}
    >
        <MaterialDesignIcon iconName="layers-triple" class="size-[18px] sm:size-5" />
    </button>
    <button
        type="button"
        class="p-2 text-sem-fg-muted hover:bg-sem-surface-muted rounded-full transition-colors shrink-0 cursor-pointer"
        title={t("map.settings")}
        onclick={ontogglesettings}
    >
        <MaterialDesignIcon iconName="cog" class="size-[18px] sm:size-5" />
    </button>
</div>
