<!-- SPDX-License-Identifier: 0BSD -->

<script lang="ts">
    /**
     * Route page for /tutorial. Same wizard as the shell modal, laid out as a
     * full page and loading its lists on mount instead of waiting for show().
     */
    import { onDestroy, onMount } from "svelte";
    import { useEventListener } from "runed";
    import TutorialProgressBar from "./components/TutorialProgressBar.svelte";
    import TutorialTopBar from "./components/TutorialTopBar.svelte";
    import TutorialSteps from "./components/TutorialSteps.svelte";
    import TutorialFooterNav from "./components/TutorialFooterNav.svelte";
    import { TutorialState } from "./lib/tutorialState.svelte.js";

    const state = new TutorialState("page");

    function onResize(): void {
        state.onWindowResize();
    }

    useEventListener(window, "resize", onResize, { passive: true });

    onMount(() => {
        state.mountPage();
    });

    onDestroy(() => {
        state.destroy();
    });
</script>

<div class="flex flex-col h-full w-full min-w-0 bg-sem-surface overflow-hidden relative">
    <TutorialProgressBar {state} />
    <TutorialTopBar {state} />

    <div class="flex-1 overflow-y-auto px-6 md:px-12 py-6 md:py-10">
        <div class="w-full h-full flex flex-col">
            <TutorialSteps {state} />
        </div>
    </div>

    <!-- Navigation Buttons (Page Mode): pinned below the scroll area -->
    <div
        class="shrink-0 border-t border-sem-border bg-sem-surface-muted px-6 py-4 pb-[max(1rem,env(safe-area-inset-bottom))] dark:border-zinc-900 dark:bg-zinc-950/50 md:px-12"
    >
        <TutorialFooterNav {state} />
    </div>
</div>
