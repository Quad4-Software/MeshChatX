<!-- SPDX-License-Identifier: 0BSD -->

<script lang="ts">
    /**
     * Back / skip / continue bar. Steps 3 and 4 hide Continue because they
     * commit through their own buttons.
     */
    import type { TutorialState } from "../lib/tutorialState.svelte.js";

    interface Props {
        state: TutorialState;
    }

    let { state }: Props = $props();

    const page = $derived(state.isPage);
    const continueDisabled = $derived(
        state.tutorialNavBusy ||
            (state.currentStep === 2 && state.identityMode === "import" && !state.hasIdentityImportInput)
    );
</script>

<div
    class={page
        ? "flex justify-between items-center mt-12 border-t border-sem-border dark:border-zinc-900 pt-8"
        : "flex w-full shrink-0 justify-between border-t border-gray-100 bg-gray-50 px-4 py-4 pb-[max(1rem,env(safe-area-inset-bottom))] dark:border-zinc-900 dark:bg-zinc-950/50 sm:px-6 sm:py-6"}
>
    {#if state.currentStep > 1 && state.currentStep < state.totalSteps}
        <button
            type="button"
            class="tutorial-action-btn tutorial-action-btn-secondary"
            disabled={state.tutorialNavBusy}
            onclick={() => state.previousStep()}
        >
            {state.t("tutorial.back")}
        </button>
    {:else}
        <div></div>
    {/if}

    <div class="flex {page ? 'gap-4' : 'gap-3'}">
        {#if state.currentStep < state.totalSteps}
            <button
                type="button"
                class="tutorial-action-btn tutorial-action-btn-secondary"
                disabled={state.tutorialNavBusy}
                onclick={() => void state.skipTutorial()}
            >
                {state.t(page ? "tutorial.skip_setup" : "tutorial.skip")}
            </button>
        {/if}

        {#if state.showFooterContinue}
            <button
                type="button"
                class="tutorial-action-btn tutorial-action-btn-primary"
                disabled={continueDisabled}
                onclick={() => void state.handlePrimaryAction()}
            >
                {state.t(page ? "tutorial.continue" : "tutorial.next")}
            </button>
        {:else if state.currentStep === state.totalSteps}
            <button
                type="button"
                class="tutorial-action-btn tutorial-action-btn-success"
                disabled={state.finishingTutorial || state.tutorialNavBusy}
                onclick={() => void state.finishTutorial()}
            >
                {state.t("tutorial.finish_setup")}
            </button>
        {/if}
    </div>
</div>
