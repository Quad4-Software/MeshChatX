<!-- SPDX-License-Identifier: 0BSD -->

<script lang="ts">
    import PluginHtmlFrame from "./PluginHtmlFrame.svelte";
    import PluginKnownWidget from "./PluginKnownWidget.svelte";
    import PluginSlotFields from "./PluginSlotFields.svelte";
    import PluginSlotNode from "./PluginSlotNode.svelte";
    import { sanitizePluginAssetSrc } from "../../../js/plugins/pluginUiDescriptor.js";
    import {
        pluginSlotActionButtonClass,
        pluginSlotBadgeClass,
        pluginSlotRowClass,
        pluginSlotSelectOptions,
        pluginSlotTableColumns,
        pluginSlotTableRows,
        pluginSlotTextClass,
    } from "../lib/pluginSlotNodeUi.js";

    interface Props {
        node: any;
        pluginId?: string;
        allowedWidgets?: string[];
        allowHtmlFrame?: boolean;
        onaction?: (actionId: string) => void;
        oninput?: (payload: { id: string; value: any }) => void;
    }

    let { node, pluginId = "", allowedWidgets = [], allowHtmlFrame = false, onaction, oninput }: Props = $props();

    let textClass = $derived(pluginSlotTextClass(node?.variant));
    let buttonClass = $derived(pluginSlotActionButtonClass(node || {}));
    let rowClass = $derived(pluginSlotRowClass(node?.variant));
    let badgeClass = $derived(pluginSlotBadgeClass(node?.variant));
    let selectOptions = $derived(pluginSlotSelectOptions(node?.options));
    let progressPercent = $derived.by(() => {
        const value = Number(node?.value);
        const max = Number(node?.max);
        const pct = Number.isFinite(value) ? (max > 0 ? (value / max) * 100 : value) : 0;
        return Math.max(0, Math.min(100, pct));
    });
    let codeStyle = $derived(node?.maxHeight ? `max-height: ${node.maxHeight}` : "max-height: 16rem");
    let safeImageSrc = $derived.by(() => {
        if (!pluginId || !node?.src) {
            return "";
        }
        return sanitizePluginAssetSrc(pluginId, node.src) || "";
    });
    let tabItems = $derived(
        (node?.tabs || []).map((tab: any) => ({
            id: String(tab.id || ""),
            label: String(tab.label || tab.id || ""),
        }))
    );
    let activeTabId = $derived(String(node?.active || tabItems[0]?.id || ""));
    let activeTabChildren = $derived.by(() => {
        const panels = node?.panels || [];
        const match = panels.find((p: any) => String(p.id) === activeTabId);
        if (match && Array.isArray(match.children)) {
            return match.children;
        }
        if (match && match.type) {
            return [match];
        }
        return [];
    });
    let tableColumns = $derived(pluginSlotTableColumns(node?.columns));
    let tableRows = $derived(pluginSlotTableRows(node?.rows));
    let isKnownWidget = $derived(node?.type === "widget" && allowedWidgets.includes(node.name));
</script>

{#if !node}
    <!-- empty -->
{:else if node.type === "text"}
    <p class={textClass}>
        {node.value}
    </p>
{:else if node.type === "input" || node.type === "number"}
    <PluginSlotFields {node} {oninput} />
{:else if node.type === "select"}
    <div class="space-y-1.5">
        {#if node.label}
            <label class="block text-sm font-medium text-sem-fg" for={`rnf-node-${node.id}`}>
                {node.label}
            </label>
        {/if}
        <select
            id={`rnf-node-${node.id}`}
            class="input-field"
            value={node.value || ""}
            onchange={(e) => oninput?.({ id: node.id, value: (e.target as HTMLSelectElement).value })}
        >
            {#if node.placeholder}
                <option value="" disabled>
                    {node.placeholder}
                </option>
            {/if}
            {#each selectOptions as opt (opt.value)}
                <option value={opt.value}>
                    {opt.label}
                </option>
            {/each}
        </select>
    </div>
{:else if node.type === "checkbox"}
    <label class="flex items-start gap-2.5 text-sm text-sem-fg cursor-pointer">
        <input
            class="mt-0.5 rounded border-sem-border text-sem-accent focus:ring-sem-focus/40"
            type="checkbox"
            checked={Boolean(node.checked)}
            onchange={(e) =>
                oninput?.({
                    id: node.id,
                    value: (e.target as HTMLInputElement).checked ? "1" : "0",
                })}
        />
        <span>{node.label}</span>
    </label>
{:else if node.type === "button"}
    <button type="button" class={buttonClass} onclick={() => onaction?.(node.id)}>
        {node.label}
    </button>
{:else if node.type === "badge"}
    <span
        class="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium whitespace-nowrap {badgeClass}"
    >
        {node.label}
    </span>
{:else if node.type === "progress"}
    <div class="space-y-1">
        {#if node.label}
            <div class="text-xs text-sem-fg-muted">{node.label}</div>
        {/if}
        <div class="h-2 w-full overflow-hidden rounded-full bg-sem-surface-muted">
            <div
                class="h-full rounded-full bg-sem-action-primary transition-all"
                style="width: {progressPercent}%"
            ></div>
        </div>
    </div>
{:else if node.type === "separator"}
    <hr class="border-0 border-t border-sem-border" />
{:else if node.type === "empty"}
    <div class="rounded-lg border border-dashed border-sem-border px-4 py-8 text-center text-sm text-sem-fg-muted">
        {node.value || node.label || ""}
    </div>
{:else if node.type === "code"}
    <pre
        class="overflow-auto rounded-lg border border-sem-border bg-sem-surface-muted p-3 font-mono text-xs text-sem-fg whitespace-pre-wrap break-all"
        style={codeStyle}>{node.value || ""}</pre>
{:else if node.type === "image" && safeImageSrc}
    <img src={safeImageSrc} alt={node.alt || ""} class="max-w-full rounded-lg border border-sem-border" />
{:else if node.type === "actions"}
    <div class="flex flex-wrap items-center gap-2">
        {#each node.items || [] as action (action.id)}
            <button type="button" class={pluginSlotActionButtonClass(action)} onclick={() => onaction?.(action.id)}>
                {action.label}
            </button>
        {/each}
    </div>
{:else if node.type === "tabs"}
    <div class="space-y-4">
        <div class="flex flex-wrap gap-2 border-b border-sem-border pb-2">
            {#each tabItems as tab (tab.id)}
                <button
                    type="button"
                    class="px-3 py-1.5 rounded-lg text-sm font-medium transition-colors cursor-pointer {tab.id ===
                    activeTabId
                        ? 'bg-sem-action-primary text-white'
                        : 'text-sem-fg-muted hover:bg-sem-surface-muted'}"
                    onclick={() => onaction?.(`tab:${tab.id}`)}
                >
                    {tab.label}
                </button>
            {/each}
        </div>
        {#each activeTabChildren as child, index (index)}
            <PluginSlotNode node={child} {pluginId} {allowedWidgets} {allowHtmlFrame} {onaction} {oninput} />
        {/each}
    </div>
{:else if node.type === "table"}
    <div class="overflow-x-auto rounded-lg border border-sem-border">
        <table class="min-w-full text-sm text-sem-fg">
            <thead class="bg-sem-surface-muted text-left text-xs uppercase tracking-wide text-sem-fg-muted">
                <tr>
                    {#each tableColumns as col, ci (ci)}
                        <th class="px-3 py-2 font-medium">
                            {col}
                        </th>
                    {/each}
                </tr>
            </thead>
            <tbody class="divide-y divide-sem-border bg-sem-surface">
                {#each tableRows as row, ri (ri)}
                    <tr>
                        {#each row as cell, ci (ci)}
                            <td class="px-3 py-2 align-top">
                                {#if cell && typeof cell === "object" && "type" in (cell as Record<string, any>)}
                                    <PluginSlotNode
                                        node={cell}
                                        {pluginId}
                                        {allowedWidgets}
                                        {allowHtmlFrame}
                                        {onaction}
                                        {oninput}
                                    />
                                {:else}
                                    <span>{cell}</span>
                                {/if}
                            </td>
                        {/each}
                    </tr>
                {/each}
            </tbody>
        </table>
        {#if !tableRows.length}
            <p class="px-4 py-6 text-center text-sm text-sem-fg-muted">
                {node.emptyText || ""}
            </p>
        {/if}
    </div>
{:else if node.type === "section"}
    <div class="rounded-xl border border-sem-border bg-sem-surface-muted/70 p-4 sm:p-5 space-y-4">
        {#if node.title || node.description}
            <div class="space-y-1">
                {#if node.title}
                    <h2 class="text-base font-semibold text-sem-fg">
                        {node.title}
                    </h2>
                {/if}
                {#if node.description}
                    <p class="text-sm text-sem-fg-muted">
                        {node.description}
                    </p>
                {/if}
            </div>
        {/if}
        {#each node.children || [] as child, index (index)}
            <PluginSlotNode node={child} {pluginId} {allowedWidgets} {allowHtmlFrame} {onaction} {oninput} />
        {/each}
    </div>
{:else if node.type === "list"}
    <div class="space-y-2">
        {#if (node.items || []).length && node.variant === "cards"}
            <div class="rounded-lg border border-sem-border overflow-hidden divide-y divide-sem-border bg-sem-surface">
                {#each node.items || [] as item, index (index)}
                    <PluginSlotNode node={item} {pluginId} {allowedWidgets} {allowHtmlFrame} {onaction} {oninput} />
                {/each}
            </div>
        {:else}
            {#each node.items || [] as item, index (index)}
                <PluginSlotNode node={item} {pluginId} {allowedWidgets} {allowHtmlFrame} {onaction} {oninput} />
            {/each}
        {/if}
        {#if !(node.items || []).length}
            <p
                class="rounded-lg border border-dashed border-sem-border px-4 py-8 text-center text-sm text-sem-fg-muted"
            >
                {node.emptyText || ""}
            </p>
        {/if}
    </div>
{:else if node.type === "row"}
    <div class={rowClass}>
        {#each node.children || [] as child, index (index)}
            <PluginSlotNode node={child} {pluginId} {allowedWidgets} {allowHtmlFrame} {onaction} {oninput} />
        {/each}
    </div>
{:else if node.type === "column"}
    <div class="space-y-4">
        {#each node.children || [] as child, index (index)}
            <PluginSlotNode node={child} {pluginId} {allowedWidgets} {allowHtmlFrame} {onaction} {oninput} />
        {/each}
    </div>
{:else if node.type === "widget" && isKnownWidget}
    <PluginKnownWidget {node} />
{:else if node.type === "html-frame" && allowHtmlFrame}
    <PluginHtmlFrame
        {pluginId}
        frameId={node.id || ""}
        src={safeImageSrc}
        srcdoc={node.srcdoc || ""}
        title={node.title || ""}
        minHeight={node.minHeight || "12rem"}
        onframeAction={(actionId) => onaction?.(actionId)}
    />
{:else if node.type}
    <div class="rounded-lg border border-sem-border bg-sem-surface-muted px-3 py-2 text-sm text-sem-danger">
        Unknown or disallowed UI node: {node.type}
    </div>
{/if}
