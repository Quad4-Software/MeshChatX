<!-- SPDX-License-Identifier: 0BSD -->

<script lang="ts">
    /**
     * Step 3. Pick how this install reaches the mesh. Every option is a local
     * interface choice, so the wizard stays usable with clearnet disabled.
     */
    import MaterialDesignIcon from "../../../ui/svelte/MaterialDesignIcon.svelte";
    import type { ConnectionMode, TutorialState } from "../lib/tutorialState.svelte.js";

    interface Props {
        state: TutorialState;
    }

    let { state }: Props = $props();

    const page = $derived(state.isPage);

    interface ModeCard {
        mode: Exclude<ConnectionMode, null>;
        icon: string;
        iconColor: string;
        surface: string;
        selected: string;
        idle: string;
        titleKey: string;
        descKey: string;
        spinner: boolean;
        run: () => void;
    }

    const modeCards: ModeCard[] = [
        {
            mode: "recommended",
            icon: "access-point-network",
            iconColor: "text-indigo-500",
            surface: "bg-indigo-500/5 dark:bg-indigo-500/10",
            selected: "border-indigo-500 ring-2 ring-indigo-500/30",
            idle: "border-indigo-500/20 hover:border-indigo-500",
            titleKey: "tutorial.mode_recommended_title",
            descKey: "tutorial.mode_recommended_desc",
            spinner: true,
            run: () => void state.useRecommendedMode(),
        },
        {
            mode: "discovery",
            icon: "radar",
            iconColor: "text-blue-500",
            surface: "bg-blue-500/5 dark:bg-blue-500/10",
            selected: "border-blue-500 ring-2 ring-blue-500/30",
            idle: "border-blue-500/20 hover:border-blue-500",
            titleKey: "tutorial.mode_discovery_title",
            descKey: "tutorial.mode_discovery_desc",
            spinner: true,
            run: () => void state.useDiscoveryMode(),
        },
        {
            mode: "local",
            icon: "lan",
            iconColor: "text-emerald-500",
            surface: "bg-emerald-500/5 dark:bg-emerald-500/10",
            selected: "border-emerald-500 ring-2 ring-emerald-500/30",
            idle: "border-emerald-500/20 hover:border-emerald-500",
            titleKey: "tutorial.mode_local_title",
            descKey: "tutorial.mode_local_desc",
            spinner: true,
            run: () => void state.useLocalMode(),
        },
        {
            mode: "manual",
            icon: "cog-outline",
            iconColor: "text-gray-500",
            surface: "bg-gray-100/50 dark:bg-zinc-800/40",
            selected: "border-gray-500 ring-2 ring-gray-500/30",
            idle: "border-gray-300 dark:border-zinc-700 hover:border-gray-500",
            titleKey: "tutorial.mode_manual_title",
            descKey: "tutorial.mode_manual_desc",
            spinner: false,
            run: () => state.useManualMode(),
        },
    ];
</script>

<div class={page ? "space-y-8 py-8" : "space-y-6"} data-tutorial-step="connect">
    <div class="text-center space-y-2">
        <h2 class="{page ? 'text-3xl font-black' : 'text-2xl font-bold'} text-sem-fg">
            {state.t("tutorial.connect")}
        </h2>
        <p class="text-sem-fg-muted {page ? 'text-lg max-w-2xl mx-auto' : 'text-base'}">
            {state.t(page ? "tutorial.connect_desc_page" : "tutorial.connect_desc")}
        </p>
    </div>

    <div
        class="grid grid-cols-1 {page ? 'md:grid-cols-2 gap-6 max-w-6xl mx-auto' : 'gap-4'} {state.connectionSetupBusy
            ? 'pointer-events-none opacity-70'
            : ''}"
    >
        {#each modeCards as card (card.mode)}
            <button
                type="button"
                class="text-left flex {page
                    ? 'flex-col gap-4 p-8 rounded-3xl hover:scale-[1.02] disabled:hover:scale-100'
                    : 'items-start gap-4 p-5 rounded-2xl'} {card.surface} border-2 transition-all disabled:cursor-not-allowed {state.connectionMode ===
                card.mode
                    ? card.selected
                    : card.idle}"
                disabled={state.connectionSetupBusy}
                onclick={card.run}
            >
                <MaterialDesignIcon iconName={card.icon} class="{page ? 'size-14' : 'size-10'} {card.iconColor}" />
                {#if page}
                    <div class="font-bold text-xl text-sem-fg">
                        {state.t(card.titleKey)}
                    </div>
                    <div class="text-sm text-sem-fg-muted">
                        {state.t(card.descKey)}
                    </div>
                {:else}
                    <div class="flex-1 min-w-0">
                        <div class="font-bold text-lg text-sem-fg">
                            {state.t(card.titleKey)}
                        </div>
                        <div class="text-sm text-sem-fg-muted mt-1">
                            {state.t(card.descKey)}
                        </div>
                    </div>
                {/if}
                {#if card.spinner && state.connectionSetupBusy}
                    <MaterialDesignIcon iconName="loading" class="size-5 animate-spin text-blue-500" />
                {/if}
            </button>
        {/each}
    </div>

    <p class="text-xs text-center text-sem-fg-muted">
        {state.t("tutorial.mode_change_later")}
    </p>
</div>
