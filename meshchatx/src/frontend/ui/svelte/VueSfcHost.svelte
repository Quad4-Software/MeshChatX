<!-- SPDX-License-Identifier: 0BSD -->
<script lang="ts">
    /**
     * Mount a Vue SFC into a Svelte host (migration bridge).
     * Remove once the Vue target is fully ported to Svelte.
     */
    import { onMount, onDestroy } from "svelte";
    import { createApp, type App, type Component } from "vue";

    let {
        component,
        props = {},
        onEmit,
    }: {
        component: Component;
        props?: Record<string, unknown>;
        onEmit?: (event: string, ...args: unknown[]) => void;
    } = $props();

    let rootEl: HTMLDivElement | undefined = $state();
    let app: App | null = null;

    onMount(() => {
        if (!rootEl || !component) {
            return;
        }
        app = createApp(component, { ...props });
        if (onEmit && app) {
            app.config.globalProperties.$emit = (event: string, ...args: unknown[]) => {
                onEmit(event, ...args);
            };
        }
        app.mount(rootEl);
    });

    onDestroy(() => {
        if (app) {
            app.unmount();
            app = null;
        }
    });

    $effect(() => {
        // props updates: remount is heavy; Vue bridge is interim
        void props;
    });
</script>

<div bind:this={rootEl} class="contents"></div>
