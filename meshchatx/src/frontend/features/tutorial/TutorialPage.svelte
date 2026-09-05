<!-- SPDX-License-Identifier: 0BSD -->

<script lang="ts">
    /**
     * Route page for /tutorial. Same wizard as the shell modal, laid out as a
     * full page and loading its lists on mount instead of waiting for show().
     */
    import { onDestroy, onMount } from "svelte";
    import TutorialProgressBar from "./components/TutorialProgressBar.svelte";
    import TutorialTopBar from "./components/TutorialTopBar.svelte";
    import TutorialSteps from "./components/TutorialSteps.svelte";
    import TutorialFooterNav from "./components/TutorialFooterNav.svelte";
    import { TutorialState } from "./lib/tutorialState.svelte.js";

    const state = new TutorialState("page");

    function onResize(): void {
        state.onWindowResize();
    }

    onMount(() => {
        window.addEventListener("resize", onResize, { passive: true });
        state.mountPage();
    });

    onDestroy(() => {
        window.removeEventListener("resize", onResize);
        state.destroy();
    });
</script>

<div class="flex flex-col h-full w-full min-w-0 bg-sem-surface overflow-hidden relative">
    <TutorialProgressBar {state} />
    <TutorialTopBar {state} />

    <div class="flex-1 overflow-y-auto px-6 md:px-12 py-6 md:py-10">
        <div class="w-full h-full flex flex-col justify-between">
            <TutorialSteps {state} />
            <TutorialFooterNav {state} />
        </div>
    </div>
</div>
