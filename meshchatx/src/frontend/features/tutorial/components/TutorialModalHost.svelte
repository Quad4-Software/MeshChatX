<!-- SPDX-License-Identifier: 0BSD -->

<script lang="ts">
    /**
     * Shell-level tutorial modal. Keeps the show / hide / isOpen surface the
     * app shell binds to, and stays persistent so a half finished setup is not
     * dismissed by a stray backdrop click.
     */
    import { onDestroy, onMount } from "svelte";
    import Modal from "../../../ui/svelte/Modal.svelte";
    import TutorialProgressBar from "./TutorialProgressBar.svelte";
    import TutorialTopBar from "./TutorialTopBar.svelte";
    import TutorialSteps from "./TutorialSteps.svelte";
    import TutorialFooterNav from "./TutorialFooterNav.svelte";
    import { TutorialState } from "../lib/tutorialState.svelte.js";

    interface Props {
        openOnMount?: boolean;
    }

    let { openOnMount = false }: Props = $props();

    const state = new TutorialState("modal");

    function onResize(): void {
        state.onWindowResize();
    }

    onMount(() => {
        window.addEventListener("resize", onResize, { passive: true });
        if (openOnMount) {
            void state.show();
        }
    });

    onDestroy(() => {
        window.removeEventListener("resize", onResize);
        state.destroy();
    });

    export function show(): void {
        void state.show();
    }

    export function hide(): void {
        state.hide();
    }

    export function isOpen(): boolean {
        return state.isOpen();
    }
</script>

<Modal
    bind:open={state.visible}
    persistent
    showClose={false}
    maxWidth={state.dialogFullscreen ? "100%" : 800}
    panelClass="border-0 bg-sem-surface overflow-hidden relative {state.dialogFullscreen ? 'rounded-none' : ''}"
    bodyClass="flex min-h-0 flex-1 flex-col overflow-hidden p-0"
>
    <TutorialProgressBar {state} />
    <TutorialTopBar {state} />

    <div class="relative min-h-0 flex-1 overflow-y-auto overscroll-contain px-4 py-4 sm:px-6 sm:py-6 md:px-12 md:py-10">
        <TutorialSteps {state} />
    </div>

    {#snippet footer()}
        <TutorialFooterNav {state} />
    {/snippet}
</Modal>
