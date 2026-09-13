<!-- SPDX-License-Identifier: 0BSD -->

<script lang="ts">
    import type { TutorialState } from "../lib/tutorialState.svelte.js";

    interface Props {
        state: TutorialState;
    }

    let { state }: Props = $props();

    const steps = $derived(Array.from({ length: state.totalSteps }, (_, index) => index + 1));
</script>

<div class="w-full h-1.5 bg-sem-surface-muted overflow-hidden flex">
    {#each steps as step (step)}
        <div
            class="h-full transition-all duration-500 ease-out {state.currentStep >= step
                ? 'bg-blue-500'
                : 'bg-transparent'} {state.currentStep === step ? 'flex-2' : 'flex-1'}"
            style="border-right: {step < state.totalSteps ? '1px solid rgba(0,0,0,0.05)' : 'none'}"
        ></div>
    {/each}
</div>
