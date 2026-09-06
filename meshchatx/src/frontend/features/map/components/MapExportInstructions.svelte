<!-- SPDX-License-Identifier: 0BSD -->

<script lang="ts">
    import { t } from "../../../js/i18n.js";
    import type { ExportRegionPreset } from "../lib/constants.js";

    interface Props {
        presets?: ExportRegionPreset[];
        onselectpreset?: (preset: ExportRegionPreset) => void;
    }

    let { presets = [], onselectpreset }: Props = $props();
</script>

<div class="absolute inset-x-0 top-0 mt-14 z-20 flex justify-center px-2 pointer-events-none">
    <div class="flex flex-col items-center gap-2 max-w-[min(100vw-2rem,36rem)] w-full pointer-events-auto">
        <div
            class="px-4 py-2 bg-blue-600 text-white rounded-full shadow-lg font-medium text-sm animate-bounce text-center"
        >
            {t("map.export_instructions")}
        </div>
        {#if presets && presets.length > 0}
            <div class="flex flex-wrap justify-center gap-2 pointer-events-auto">
                {#each presets as p (p.id)}
                    <button
                        type="button"
                        class="px-2 py-1 text-[10px] font-bold uppercase tracking-tight rounded-lg bg-white/95 dark:bg-zinc-900/95 border border-sem-border text-sem-fg shadow-xs hover:bg-sem-surface-muted"
                        onclick={() => onselectpreset?.(p)}
                    >
                        {t(`map.export_region_${p.id}`)}
                    </button>
                {/each}
            </div>
        {/if}
    </div>
</div>
