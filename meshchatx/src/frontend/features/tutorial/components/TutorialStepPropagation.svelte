<!-- SPDX-License-Identifier: 0BSD -->

<script lang="ts">
    /**
     * Step 5. Offer automatic propagation node selection. Skipping is a first
     * class choice because store-and-forward is optional on a direct link.
     */
    import MaterialDesignIcon from "../../../ui/svelte/MaterialDesignIcon.svelte";
    import type { TutorialState } from "../lib/tutorialState.svelte.js";

    interface Props {
        state: TutorialState;
    }

    let { state }: Props = $props();

    const page = $derived(state.isPage);
</script>

<div class={page ? "space-y-8 py-12" : "space-y-6"} data-tutorial-step="propagation">
    <div class="text-center {page ? 'space-y-4' : 'space-y-2'}">
        <h2 class="{page ? 'text-4xl' : 'text-2xl'} font-black text-sem-fg">
            {state.t("tutorial.propagation")}
        </h2>
        <p class="text-sem-fg-muted {page ? 'text-xl max-w-2xl mx-auto' : 'text-base'}">
            {state.t("tutorial.propagation_desc")}
        </p>
    </div>

    <div class="flex flex-col items-center {page ? 'gap-10 py-12' : 'gap-6 py-4'}">
        <div
            class="bg-blue-500/10 dark:bg-blue-500/20 text-center border border-blue-500/20 {page
                ? 'p-12 rounded-[3rem] space-y-8 max-w-2xl shadow-2xl'
                : 'p-6 rounded-4xl space-y-4 max-w-md'}"
        >
            <MaterialDesignIcon iconName="server-network" class="{page ? 'size-20' : 'size-12'} text-blue-500" />
            <div class="{page ? 'text-3xl font-black' : 'text-lg font-bold'} text-sem-fg">
                {state.t("tutorial.propagation_question")}
            </div>
            <p class="{page ? 'text-xl' : 'text-sm'} text-sem-fg-muted">
                {state.t("tutorial.propagation_auto")}
            </p>
            <div class="flex flex-col {page ? 'gap-4 pt-4' : 'gap-3 pt-2'}">
                <button
                    type="button"
                    class="tutorial-action-btn tutorial-action-btn-primary {page ? '' : 'w-full'}"
                    disabled={state.savingPropagation}
                    onclick={() => void state.enableAutoPropagation()}
                >
                    {#if state.savingPropagation}
                        <MaterialDesignIcon
                            iconName="loading"
                            class="{page ? 'size-6' : 'size-5'} animate-spin text-blue-500"
                        />
                    {/if}
                    {state.t("tutorial.propagation_enable_auto")}
                </button>
                <button
                    type="button"
                    class="tutorial-action-btn tutorial-action-btn-secondary {page ? '' : 'w-full'}"
                    onclick={() => state.nextStep()}
                >
                    {state.t("tutorial.propagation_skip_auto")}
                </button>
            </div>
            <div class="{page ? 'mt-8 pt-8 border-t-2' : 'mt-6 pt-6 border-t'} border-sem-border">
                <div class="{page ? 'text-xl mb-2' : 'text-sm mb-1'} font-bold text-sem-fg">
                    {state.t("tutorial.propagation_manual")}
                </div>
                <p class="{page ? 'text-base' : 'text-xs'} text-sem-fg-muted">
                    {state.t("tutorial.propagation_manual_desc")}
                </p>
            </div>
        </div>
    </div>
</div>
