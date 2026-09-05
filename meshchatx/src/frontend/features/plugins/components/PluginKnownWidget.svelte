<!-- SPDX-License-Identifier: 0BSD -->

<script lang="ts">
    interface Props {
        node: any;
    }

    let { node }: Props = $props();
</script>

{#if node.name === "IssueStackView"}
    <pre
        class="overflow-auto rounded-lg border border-sem-border bg-sem-surface-muted p-3 font-mono text-xs text-sem-fg whitespace-pre-wrap break-all"
        style="max-height: {node.props?.maxHeight || '16rem'}">{node.props?.stack || ""}</pre>
{:else if node.name === "HashBadge"}
    <span
        class="inline-flex items-center gap-1.5 rounded-md border border-sem-border bg-sem-surface-muted px-2 py-0.5 font-mono text-xs text-sem-fg"
        title={node.props?.hash || ""}
    >
        {node.props?.label ? `${node.props.label} ` : ""}
        {node.props?.hash?.length >= 12
            ? `${node.props.hash.slice(0, 10)}…${node.props.hash.slice(-6)}`
            : node.props?.hash || "-"}
    </span>
{/if}
