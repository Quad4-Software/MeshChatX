<!-- SPDX-License-Identifier: 0BSD -->

<script lang="ts">
    import MaterialDesignIcon from "../../../ui/svelte/MaterialDesignIcon.svelte";
    import MapToolbarControls from "./MapToolbarControls.svelte";
    import { t } from "../../../js/i18n.js";

    interface Props {
        embedded?: boolean;
        tabTitle?: string;
        discoveredVisible?: boolean;
        offlineEnabled?: boolean;
        hideControls?: boolean;
        ontogglediscovered?: () => void;
        ontoggleoffline?: (enabled: boolean) => void;
        ontogglemotools?: () => void;
        ontogglesettings?: () => void;
        onshare?: () => void;
    }

    let {
        embedded = false,
        tabTitle = "",
        discoveredVisible = false,
        offlineEnabled = false,
        hideControls = false,
        ontogglediscovered,
        ontoggleoffline,
        ontogglemotools,
        ontogglesettings,
        onshare,
    }: Props = $props();
</script>

{#if !embedded}
    <div
        class="flex items-center gap-2 px-3 py-2 sm:px-4 border-b border-sem-border bg-white/80 dark:bg-zinc-900/80 backdrop-blur-sm z-10 relative"
    >
        <MaterialDesignIcon iconName="map" class="size-6 text-blue-500 dark:text-blue-400 shrink-0" />
        <h1 class="text-lg sm:text-xl font-black text-sem-fg truncate">
            {tabTitle || t("map.title")}
        </h1>
    </div>
{/if}

{#if !hideControls}
    <MapToolbarControls
        {discoveredVisible}
        {offlineEnabled}
        {ontogglediscovered}
        {ontoggleoffline}
        {ontogglemotools}
        {ontogglesettings}
        {onshare}
    />
{/if}
