<!-- SPDX-License-Identifier: 0BSD -->

<script lang="ts">
    interface Props {
        node: any;
        oninput?: (payload: { id: string; value: any }) => void;
    }

    let { node, oninput }: Props = $props();
</script>

{#if node.type === "input"}
    <div class="space-y-1.5">
        {#if node.label}
            <label class="block text-sm font-medium text-sem-fg" for={`rnf-node-${node.id}`}>
                {node.label}
            </label>
        {/if}
        {#if node.multiline}
            <textarea
                id={`rnf-node-${node.id}`}
                class="input-field min-h-[6rem]"
                placeholder={node.placeholder || ""}
                value={node.value || ""}
                oninput={(e) => oninput?.({ id: node.id, value: (e.target as HTMLTextAreaElement).value })}></textarea>
        {:else}
            <input
                id={`rnf-node-${node.id}`}
                class="input-field"
                type="text"
                placeholder={node.placeholder || ""}
                value={node.value || ""}
                oninput={(e) => oninput?.({ id: node.id, value: (e.target as HTMLInputElement).value })}
            />
        {/if}
    </div>
{:else if node.type === "number"}
    <div class="space-y-1.5">
        {#if node.label}
            <label class="block text-sm font-medium text-sem-fg" for={`rnf-node-${node.id}`}>
                {node.label}
            </label>
        {/if}
        <input
            id={`rnf-node-${node.id}`}
            class="input-field"
            type="number"
            placeholder={node.placeholder || ""}
            value={node.value ?? ""}
            min={node.min}
            max={node.max}
            step={node.step}
            oninput={(e) => oninput?.({ id: node.id, value: (e.target as HTMLInputElement).value })}
        />
    </div>
{/if}
