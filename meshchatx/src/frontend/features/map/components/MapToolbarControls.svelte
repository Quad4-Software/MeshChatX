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
    <div class="flex items-center gap-0.5 bg-sem-surface-muted rounded-full p-0.5 min-w-0 max-w-full">
        <button
            type="button"
            class="inline-flex size-11 sm:size-8 shrink-0 items-center justify-center rounded-full transition-colors cursor-pointer {discoveredVisible
                ? 'bg-sem-surface-raised shadow-xs text-emerald-600 dark:text-emerald-400'
                : 'text-sem-fg-muted hover:text-sem-fg'}"
            title={discoveredVisible ? "Hide Discovered Interfaces" : "Show Discovered Interfaces"}
            onclick={ontogglediscovered}
        >
            <MaterialDesignIcon iconName="map-marker-radius" class="size-5" />
        </button>
        <button
            type="button"
            class="toolbar-label-chip shrink-0 cursor-pointer {offlineEnabled
                ? 'text-sem-fg-muted hover:text-sem-fg'
                : 'bg-sem-surface-raised shadow-xs text-sem-accent'}"
            onclick={() => ontoggleoffline?.(false)}
        >
            {t("map.online_mode")}
        </button>
        <button
            type="button"
            class="toolbar-label-chip shrink-0 cursor-pointer {!offlineEnabled
                ? 'text-sem-fg-muted hover:text-sem-fg'
                : 'bg-sem-surface-raised shadow-xs text-sem-accent'}"
            onclick={() => ontoggleoffline?.(true)}
        >
            {t("map.offline_mode")}
        </button>
    </div>

    <button type="button" class="toolbar-icon-btn cursor-pointer" title={t("map.share_view")} onclick={onshare}>
        <MaterialDesignIcon iconName="share-variant" class="size-5" />
    </button>
    <button type="button" class="toolbar-icon-btn cursor-pointer" title={t("map.side_panel")} onclick={ontogglemotools}>
        <MaterialDesignIcon iconName="layers-triple" class="size-5" />
    </button>
    <button type="button" class="toolbar-icon-btn cursor-pointer" title={t("map.settings")} onclick={ontogglesettings}>
        <MaterialDesignIcon iconName="cog" class="size-5" />
    </button>
</div>
