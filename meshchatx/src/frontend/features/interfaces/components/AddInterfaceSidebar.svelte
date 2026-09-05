<!-- SPDX-License-Identifier: 0BSD -->

<script lang="ts">
    import MaterialDesignIcon from "../../../ui/svelte/MaterialDesignIcon.svelte";
    import { t } from "../../../js/i18n.js";
    import { parseRawConfig } from "../lib/addInterfaceState.js";
    import type { CommunityInterface } from "../lib/types.js";

    interface Props {
        isEditing?: boolean;
        communityInterfaces?: CommunityInterface[];
        communityFetchDone?: boolean;
        showCommunityPresets?: boolean;
        onquickapply?: (cfg: Record<string, any>) => void;
        onhidecommunitypresets?: () => void;
        onshowcommunitypresets?: () => void;
    }

    let {
        isEditing = false,
        communityInterfaces = [],
        communityFetchDone = false,
        showCommunityPresets = true,
        onquickapply,
        onhidecommunitypresets,
        onshowcommunitypresets,
    }: Props = $props();

    let rawConfigInput = $state("");
    let detectedConfigs: Record<string, any>[] = $state([]);

    function handleRawConfigInput(e: Event) {
        const val = (e.target as HTMLTextAreaElement).value;
        rawConfigInput = val;
        detectedConfigs = parseRawConfig(val);
        if (detectedConfigs.length === 1) {
            onquickapply?.(detectedConfigs[0]);
        }
    }

    function handleApplyDetected(cfg: Record<string, any>) {
        onquickapply?.(cfg);
    }
</script>

<aside
    class="w-full shrink-0 space-y-4 xl:w-96 xl:sticky xl:top-4 xl:self-start xl:max-h-[min(calc(100dvh-6rem),920px)] xl:overflow-y-auto xl:border-l border-gray-200/80 dark:border-zinc-800 xl:pl-8"
    aria-label={t("interfaces.add_interface_sidebar_a11y")}
>
    {#if !isEditing && showCommunityPresets && communityInterfaces.length > 0}
        <div class="glass-card p-0! overflow-hidden">
            <div
                class="bg-gray-50/50 dark:bg-zinc-800/50 p-4 border-b border-sem-border flex items-center justify-between gap-2"
            >
                <div class="min-w-0">
                    <h2 class="font-bold text-sem-fg flex items-center gap-2 text-sm">
                        <MaterialDesignIcon iconName="lightning-bolt" class="w-5 h-5 text-yellow-500" />
                        <span>{t("interfaces.community_quick_start")}</span>
                    </h2>
                    <p class="text-xs text-sem-fg-muted mt-0.5">
                        {t("interfaces.community_quick_start_hint")}
                    </p>
                </div>
                <div class="flex items-center gap-0.5 shrink-0">
                    <button
                        type="button"
                        class="text-gray-400 hover:text-gray-600 hover:text-sem-fg transition-colors p-1 shrink-0"
                        title={t("interfaces.community_quick_start_hide")}
                        onclick={onhidecommunitypresets}
                    >
                        <MaterialDesignIcon iconName="close" class="w-5 h-5" />
                    </button>
                </div>
            </div>

            <div class="divide-y divide-gray-100 dark:divide-zinc-800 max-h-[min(50vh,28rem)] overflow-y-auto">
                {#each communityInterfaces as communityIface (communityIface.name || communityIface.target_host)}
                    <div
                        class="flex p-3 sm:p-4 items-center gap-2 hover:bg-gray-50/30 dark:hover:bg-zinc-800/20 transition-colors"
                    >
                        <div class="min-w-0 flex-1">
                            <div class="font-bold text-sm text-sem-fg">
                                {communityIface.name}
                            </div>
                            <div
                                class="text-[10px] font-mono text-sem-fg-muted mt-0.5 flex flex-wrap items-center gap-2"
                            >
                                <MaterialDesignIcon iconName="server-network" class="w-3 h-3 shrink-0" />
                                {#if communityIface.type === "I2PInterface"}
                                    <span>{communityIface.target_host}</span>
                                {:else}
                                    <span>{communityIface.target_host}:{communityIface.target_port}</span>
                                {/if}
                                {#if communityIface.online === true}
                                    <span class="text-green-500 flex items-center gap-1">
                                        <span class="w-1.5 h-1.5 rounded-full bg-green-500 animate-pulse"></span>
                                        Online
                                    </span>
                                {:else if communityIface.online === false}
                                    <span class="text-red-500">Offline</span>
                                {/if}
                            </div>
                            {#if communityIface.description}
                                <div class="text-[10px] text-sem-fg-muted mt-1 italic line-clamp-2">
                                    {communityIface.description}
                                </div>
                            {/if}
                        </div>
                        <button
                            type="button"
                            class="primary-chip py-1.5! px-2! text-[10px]! shrink-0"
                            onclick={() => onquickapply?.(communityIface)}
                        >
                            {t("interfaces.community_use_preset")}
                        </button>
                    </div>
                {/each}
            </div>
        </div>
    {:else if !isEditing && !showCommunityPresets && communityInterfaces.length > 0}
        <div class="glass-card p-4 space-y-3">
            <p class="text-sm text-sem-fg-muted">
                {t("interfaces.community_presets_hidden_hint")}
            </p>
            <button type="button" class="primary-chip py-2! px-4! text-xs! w-full" onclick={onshowcommunitypresets}>
                {t("interfaces.community_presets_show_again")}
            </button>
        </div>
    {:else if !isEditing && showCommunityPresets && communityFetchDone && communityInterfaces.length === 0}
        <div class="glass-card p-4 text-sm text-sem-fg-muted">
            {t("interfaces.community_presets_empty")}
        </div>
    {/if}

    <div class="grid grid-cols-1 gap-4">
        <div
            class="glass-card flex items-center gap-4 bg-blue-50/30 dark:bg-blue-900/10 border-blue-100 dark:border-blue-900/30"
        >
            <div class="w-10 h-10 rounded-2xl bg-blue-500/10 flex items-center justify-center text-blue-500 shrink-0">
                <MaterialDesignIcon iconName="map-search-outline" class="w-6 h-6" />
            </div>
            <div class="flex-1 min-w-0">
                <h3 class="text-sm font-bold text-sem-fg">
                    {t("interfaces.find_more_nodes")}
                </h3>
                <div class="flex flex-wrap gap-2 mt-1">
                    <a
                        href="https://directory.rns.recipes/"
                        target="_blank"
                        rel="noopener noreferrer"
                        class="secondary-chip py-1! px-2! text-[9px]!">rns.recipes</a
                    >
                    <a
                        href="https://meshchatx.com/interfaces"
                        target="_blank"
                        rel="noopener noreferrer"
                        class="secondary-chip py-1! px-2! text-[9px]!">meshchatx.com</a
                    >
                    <a
                        href="https://rmap.world/"
                        target="_blank"
                        rel="noopener noreferrer"
                        class="secondary-chip py-1! px-2! text-[9px]!">rmap.world</a
                    >
                </div>
            </div>
        </div>

        <div
            class="glass-card flex flex-col gap-2 p-4! bg-emerald-50/20 dark:bg-emerald-900/5 border-emerald-100 dark:border-emerald-900/20"
        >
            <div class="flex items-center justify-between gap-2">
                <h3
                    class="text-xs font-bold text-emerald-600 dark:text-emerald-500 uppercase tracking-widest flex items-center gap-2"
                >
                    <MaterialDesignIcon iconName="import" class="w-4 h-4" />
                    <span>{t("interfaces.quick_import")}</span>
                </h3>
                <span class="text-[10px] text-gray-400 shrink-0">
                    {t("interfaces.quick_import_paste_hint")}
                </span>
            </div>
            <textarea
                value={rawConfigInput}
                placeholder={t("interfaces.quick_import_placeholder")}
                class="w-full h-20 bg-white/50 dark:bg-zinc-900/50 border border-emerald-100/50 dark:border-emerald-900/30 rounded-xl p-2 text-[10px] font-mono focus:ring-1 focus:ring-emerald-500 outline-hidden transition"
                oninput={handleRawConfigInput}></textarea>

            {#if detectedConfigs.length > 1}
                <div class="flex flex-wrap gap-2 mt-1">
                    {#each detectedConfigs as cfg, idx (cfg.name || idx)}
                        <button
                            type="button"
                            class="bg-emerald-500/10 hover:bg-emerald-500/20 border border-emerald-500/20 rounded-lg px-2 py-1 text-[9px] font-bold text-emerald-600 dark:text-emerald-400 transition"
                            onclick={() => handleApplyDetected(cfg)}
                        >
                            {t("interfaces.quick_import_apply", { name: cfg.name })}
                        </button>
                    {/each}
                </div>
            {/if}
        </div>
    </div>
</aside>
