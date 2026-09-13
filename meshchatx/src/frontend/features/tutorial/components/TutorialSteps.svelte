<!-- SPDX-License-Identifier: 0BSD -->

<script lang="ts">
    /**
     * Renders the step that matches state.currentStep and owns the shared
     * button styling the step components and the footer reference by class.
     */
    import { fly } from "svelte/transition";
    import TutorialStepWelcome from "./TutorialStepWelcome.svelte";
    import TutorialStepIdentity from "./TutorialStepIdentity.svelte";
    import TutorialStepConnect from "./TutorialStepConnect.svelte";
    import TutorialStepBootstrap from "./TutorialStepBootstrap.svelte";
    import TutorialStepPropagation from "./TutorialStepPropagation.svelte";
    import TutorialStepLearn from "./TutorialStepLearn.svelte";
    import TutorialPrivacyStep from "./TutorialPrivacyStep.svelte";
    import TutorialStepFinish from "./TutorialStepFinish.svelte";
    import type { TutorialState } from "../lib/tutorialState.svelte.js";

    interface Props {
        state: TutorialState;
    }

    let { state }: Props = $props();

    const page = $derived(state.isPage);

    function reducedMotion(): boolean {
        if (typeof window === "undefined" || typeof window.matchMedia !== "function") {
            return false;
        }
        return window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    }

    const stepTransition = $derived(reducedMotion() ? { x: 0, duration: 0 } : { x: 30, duration: 400 });
</script>

{#key state.currentStep}
    <div in:fly={stepTransition}>
        {#if state.currentStep === 1}
            <TutorialStepWelcome {state} />
        {:else if state.currentStep === 2}
            <TutorialStepIdentity {state} />
        {:else if state.currentStep === 3}
            <TutorialStepConnect {state} />
        {:else if state.currentStep === 4}
            <TutorialStepBootstrap {state} />
        {:else if state.currentStep === 5}
            <TutorialStepPropagation {state} />
        {:else if state.currentStep === 6}
            <TutorialStepLearn {state} />
        {:else if state.currentStep === 7}
            <div class={page ? "space-y-6 py-8" : "space-y-4"}>
                <TutorialPrivacyStep />
            </div>
        {:else if state.currentStep === 8}
            <TutorialStepFinish {state} />
        {/if}
    </div>
{/key}

<style>
    :global(.tutorial-action-btn) {
        min-height: 2.75rem;
        padding: 0.625rem 1rem;
        border-radius: 0.75rem;
        font-size: 0.875rem;
        font-weight: 700;
        line-height: 1.1;
        display: inline-flex;
        align-items: center;
        justify-content: center;
        gap: 0.5rem;
        transition: all 0.15s ease;
    }

    :global(.tutorial-action-btn:disabled) {
        opacity: 0.6;
        cursor: not-allowed;
    }

    :global(.tutorial-action-btn-primary) {
        background: rgb(37 99 235);
        color: white;
    }

    :global(.tutorial-action-btn-primary:hover:not(:disabled)) {
        background: rgb(59 130 246);
    }

    :global(.tutorial-action-btn-secondary) {
        border: 1px solid rgb(209 213 219);
        background: white;
        color: rgb(55 65 81);
    }

    :global(.tutorial-action-btn-secondary:hover:not(:disabled)) {
        background: rgb(249 250 251);
    }

    :global(.tutorial-action-btn-success) {
        background: rgb(5 150 105);
        color: white;
    }

    :global(.tutorial-action-btn-success:hover:not(:disabled)) {
        background: rgb(16 185 129);
    }

    :global(.dark .tutorial-action-btn-secondary) {
        border-color: rgb(63 63 70);
        background: rgb(39 39 42);
        color: rgb(212 212 216);
    }

    :global(.dark .tutorial-action-btn-secondary:hover:not(:disabled)) {
        background: rgb(63 63 70);
    }
</style>
