<!-- SPDX-License-Identifier: 0BSD -->

<script lang="ts">
    import LanguageSelector from "../../../ui/svelte/LanguageSelector.svelte";
    import MaterialDesignIcon from "../../../ui/svelte/MaterialDesignIcon.svelte";
    import type { TutorialState } from "../lib/tutorialState.svelte.js";

    interface Props {
        state: TutorialState;
    }

    let { state }: Props = $props();

    const isDark = $derived(state.theme === "dark");
</script>

<div class="shrink-0 flex items-center justify-end gap-1 px-3 py-1.5 sm:px-4">
    <LanguageSelector onlanguagechange={(code) => void state.onLanguageChange(code)} />
    <button
        type="button"
        class="rounded-full p-1.5 sm:p-2 text-sem-fg-muted hover:bg-sem-surface-muted transition-colors"
        title={isDark ? "Switch to light mode" : "Switch to dark mode"}
        onclick={() => void state.toggleTheme()}
    >
        <MaterialDesignIcon iconName={isDark ? "brightness-6" : "brightness-4"} class="w-5 h-5 sm:w-6 sm:h-6" />
    </button>
</div>
