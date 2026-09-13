<!-- SPDX-License-Identifier: 0BSD -->

<script lang="ts">
    /**
     * Step 8. Closing screen. The modal only warns about the interface reload
     * when the wizard actually added one, the page always states it.
     */
    import MaterialDesignIcon from "../../../ui/svelte/MaterialDesignIcon.svelte";
    import { resolveTarget } from "../../../shell/hashRouter.js";
    import type { TutorialState } from "../lib/tutorialState.svelte.js";

    interface Props {
        state: TutorialState;
    }

    let { state }: Props = $props();

    const page = $derived(state.isPage);

    /** The docs feature may not be registered yet, so fall back to its path. */
    const documentationHref = $derived.by(() => {
        try {
            return `#${resolveTarget({ name: "documentation" })}`;
        } catch {
            return "#/documentation";
        }
    });
</script>

<div
    class="flex flex-col items-center text-center {page ? 'space-y-10 py-20' : 'space-y-8 py-10'}"
    data-tutorial-step="finish"
>
    <div
        class="{page
            ? 'w-48 h-48'
            : 'w-32 h-32'} bg-green-500/10 rounded-full flex items-center justify-center relative"
    >
        <MaterialDesignIcon iconName="check-decagram" class="{page ? 'size-[120px]' : 'size-20'} text-green-500" />
        <div class="absolute inset-0 bg-green-500/20 rounded-full animate-ping opacity-20"></div>
    </div>

    <div class={page ? "space-y-4" : "space-y-3"}>
        <h2 class="{page ? 'text-5xl' : 'text-3xl'} font-black text-sem-fg">
            {state.t("tutorial.ready")}
        </h2>
        <p class="text-sem-fg-muted mx-auto {page ? 'text-xl max-w-2xl' : 'text-lg max-w-md'}">
            {state.t(page ? "tutorial.ready_desc_page" : "tutorial.ready_desc")}
        </p>
    </div>

    {#if page}
        <div
            class="p-6 bg-amber-50 dark:bg-amber-900/20 rounded-3xl border border-amber-100 dark:border-amber-900/30 text-amber-700 dark:text-amber-400 flex gap-4 max-w-xl text-left"
        >
            <MaterialDesignIcon iconName="information-outline" class="size-8 shrink-0" />
            <div class="space-y-1">
                <div class="font-bold text-lg">{state.t("tutorial.restart_required")}</div>
                <div class="opacity-90">
                    {state.t("tutorial.restart_desc_page")}
                </div>
            </div>
        </div>
    {:else if state.interfaceAddedViaTutorial}
        <div
            class="p-4 bg-amber-50 dark:bg-amber-900/20 rounded-2xl border border-amber-100 dark:border-amber-900/30 text-amber-700 dark:text-amber-400 text-sm flex gap-3 max-w-md text-left"
        >
            <MaterialDesignIcon iconName="information-outline" class="shrink-0" />
            <span>{state.t("tutorial.docker_note")}</span>
        </div>
    {/if}

    <a
        href={documentationHref}
        class="{page
            ? 'text-base'
            : 'text-sm'} font-semibold text-blue-600 hover:text-blue-700 dark:text-blue-400 dark:hover:text-blue-300"
    >
        {state.t("tutorial.learn_more_docs")}
    </a>
</div>
