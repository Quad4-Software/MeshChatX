<!-- SPDX-License-Identifier: 0BSD -->

<script lang="ts">
    import PluginSlotNode from "./PluginSlotNode.svelte";

    interface Props {
        descriptor?: any;
        pluginId: string;
        allowedWidgets?: string[];
        allowHtmlFrame?: boolean;
        uiError?: string;
        onaction?: (actionId: string) => void;
        oninput?: (payload: { id: string; value: any }) => void;
    }

    let {
        descriptor = null,
        pluginId,
        allowedWidgets = [],
        allowHtmlFrame = false,
        uiError = "",
        onaction,
        oninput,
    }: Props = $props();

    let nodes = $derived.by(() => {
        if (!descriptor) {
            return [];
        }
        if (descriptor.type === "column" && Array.isArray(descriptor.children)) {
            return descriptor.children;
        }
        return [descriptor];
    });
</script>

<div class="plugin-slot space-y-6">
    {#if uiError}
        <div class="rounded-lg border border-sem-danger/40 bg-sem-danger/10 px-3 py-2 text-sm text-sem-danger">
            {uiError}
        </div>
    {/if}
    {#each nodes as node, index (index)}
        <PluginSlotNode {node} {pluginId} {allowedWidgets} {allowHtmlFrame} {onaction} {oninput} />
    {/each}
</div>
