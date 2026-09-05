<!-- SPDX-License-Identifier: 0BSD -->

<script lang="ts">
    /**
     * Svelte wrapper around the not yet ported TutorialModal.vue.
     * Exposes the show / hide / isOpen surface the shell used to reach through
     * a Vue template ref. Replace with a native Svelte tutorial page later.
     */
    import { onDestroy, onMount } from "svelte";
    import TutorialModal from "../../../components/TutorialModal.vue";
    import { mountVueIsland } from "../../../shell/vueIsland.js";
    import type { VueIsland } from "../../../shell/vueIsland.js";

    interface Props {
        isPage?: boolean;
        openOnMount?: boolean;
    }

    let { isPage = false, openOnMount = false }: Props = $props();

    let rootEl: HTMLDivElement | undefined = $state();
    let island: VueIsland | null = null;

    onMount(() => {
        if (!rootEl) {
            return;
        }
        island = mountVueIsland(TutorialModal, rootEl, { isPage });
        if (openOnMount) {
            show();
        }
    });

    onDestroy(() => {
        island?.unmount();
        island = null;
    });

    export function show(): void {
        const vm = island?.vm;
        if (vm && typeof vm.show === "function") {
            void vm.show();
        }
    }

    export function hide(): void {
        const vm = island?.vm;
        if (vm) {
            vm.visible = false;
        }
    }

    export function isOpen(): boolean {
        return Boolean(island?.vm?.visible);
    }
</script>

<div bind:this={rootEl} class="contents"></div>
