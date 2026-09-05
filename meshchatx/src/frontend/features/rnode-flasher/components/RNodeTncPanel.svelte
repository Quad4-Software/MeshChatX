<!-- SPDX-License-Identifier: 0BSD -->

<script lang="ts">
    import MaterialDesignIcon from "../../../ui/svelte/MaterialDesignIcon.svelte";
    import { t } from "../../../js/i18n.js";

    const BANDWIDTHS = [7800, 10400, 15600, 20800, 31250, 41700, 62500, 125000, 250000, 500000];
    const SPREADING_FACTORS = [7, 8, 9, 10, 11, 12];

    interface Props {
        frequency?: number;
        bandwidth?: number;
        txPower?: number;
        spreadingFactor?: number;
        onaction?: (actionId: string) => void;
    }

    let {
        frequency = $bindable(917375000),
        bandwidth = $bindable(250000),
        txPower = $bindable(22),
        spreadingFactor = $bindable(11),
        onaction,
    }: Props = $props();
</script>

<div class="border border-sem-border bg-sem-surface rounded-2xl shadow-xl overflow-hidden">
    <div class="px-4 sm:px-6 py-4 border-b border-sem-border flex items-center gap-2">
        <MaterialDesignIcon iconName="radio-tower" class="size-5 text-green-500" />
        <h3 class="font-bold text-sem-fg">
            {t("tools.rnode_flasher.configure_tnc")}
        </h3>
    </div>
    <div class="p-4 sm:p-6 space-y-4">
        <div class="grid grid-cols-2 gap-3">
            <div class="space-y-1">
                <label class="text-[10px] font-bold text-zinc-400 uppercase tracking-widest block" for="rnf-tnc-freq"
                    >{t("tools.rnode_flasher.frequency")}</label
                >
                <input
                    id="rnf-tnc-freq"
                    bind:value={frequency}
                    type="number"
                    class="w-full bg-gray-50 dark:bg-zinc-800 border border-sem-border text-sem-fg text-[12px] rounded-lg focus:ring-1 focus:ring-blue-500/50 focus:border-blue-500 px-3 py-2 transition-all"
                />
            </div>
            <div class="space-y-1">
                <label class="text-[10px] font-bold text-zinc-400 uppercase tracking-widest block" for="rnf-tnc-power"
                    >{t("tools.rnode_flasher.tx_power")}</label
                >
                <input
                    id="rnf-tnc-power"
                    bind:value={txPower}
                    type="number"
                    class="w-full bg-gray-50 dark:bg-zinc-800 border border-sem-border text-sem-fg text-[12px] rounded-lg focus:ring-1 focus:ring-blue-500/50 focus:border-blue-500 px-3 py-2 transition-all"
                />
            </div>
            <div class="space-y-1">
                <label class="text-[10px] font-bold text-zinc-400 uppercase tracking-widest block" for="rnf-tnc-bw"
                    >{t("tools.rnode_flasher.bandwidth")}</label
                >
                <select
                    id="rnf-tnc-bw"
                    bind:value={bandwidth}
                    class="w-full bg-gray-50 dark:bg-zinc-800 border border-sem-border text-sem-fg text-[12px] rounded-lg focus:ring-1 focus:ring-blue-500/50 focus:border-blue-500 px-3 py-2 transition-all"
                >
                    {#each BANDWIDTHS as bw (bw)}
                        <option value={bw}>{bw / 1000} KHz</option>
                    {/each}
                </select>
            </div>
            <div class="space-y-1">
                <label class="text-[10px] font-bold text-zinc-400 uppercase tracking-widest block" for="rnf-tnc-sf"
                    >{t("tools.rnode_flasher.spreading_factor")}</label
                >
                <select
                    id="rnf-tnc-sf"
                    bind:value={spreadingFactor}
                    class="w-full bg-gray-50 dark:bg-zinc-800 border border-sem-border text-sem-fg text-[12px] rounded-lg focus:ring-1 focus:ring-blue-500/50 focus:border-blue-500 px-3 py-2 transition-all"
                >
                    {#each SPREADING_FACTORS as sf (sf)}
                        <option value={sf}>
                            {sf}
                        </option>
                    {/each}
                </select>
            </div>
        </div>
        <div class="grid grid-cols-2 gap-2">
            <button
                type="button"
                class="inline-flex items-center justify-center gap-1.5 rounded-xl bg-green-600 hover:bg-green-700 px-3 py-2.5 text-[11px] font-bold text-white! border-none! transition-all active:scale-95 cursor-pointer"
                onclick={() => onaction?.("enable-tnc")}
            >
                {t("tools.rnode_flasher.enable")}
            </button>
            <button
                type="button"
                class="inline-flex items-center justify-center gap-1.5 rounded-xl bg-sem-surface-muted hover:bg-gray-200 dark:hover:bg-sem-surface-muted px-3 py-2.5 text-[11px] font-bold text-sem-fg-muted border border-sem-border transition-all active:scale-95 cursor-pointer"
                onclick={() => onaction?.("disable-tnc")}
            >
                {t("tools.rnode_flasher.disable")}
            </button>
        </div>
    </div>
</div>
