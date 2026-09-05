<!-- SPDX-License-Identifier: 0BSD -->

<script lang="ts">
    interface Props {
        targetId: string;
        enabled?: boolean;
        children?: import("svelte").Snippet;
    }

    let { targetId, enabled = true, children }: Props = $props();

    let mountEl = $state<HTMLDivElement | null>(null);

    $effect(() => {
        if (!enabled || !mountEl) return;
        const target = document.getElementById(targetId);
        if (!target) return;
        target.appendChild(mountEl);
        return () => {
            if (mountEl?.parentElement === target) {
                mountEl.remove();
            }
        };
    });
</script>

<div bind:this={mountEl} class="flex flex-wrap items-center gap-x-1.5 gap-y-1 min-w-0 justify-end">
    {@render children?.()}
</div>
