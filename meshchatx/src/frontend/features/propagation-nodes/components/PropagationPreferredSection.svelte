<!-- SPDX-License-Identifier: 0BSD -->

<script lang="ts">
    import MaterialDesignIcon from "../../../ui/svelte/MaterialDesignIcon.svelte";
    import { t } from "../../../js/i18n.js";
    import { formatDestinationHash, formatPathLabel } from "../lib/propagationFormat.js";
    import type { NodePathInfo, PropagationNodesConfig } from "../lib/types.js";

    interface Props {
        config: PropagationNodesConfig;
        preferredPath: NodePathInfo | null;
        manualHashDraft: string;
        isSavingPreferred: boolean;
        onCopyPreferredHash: () => void;
        onRequestPreferredPath: () => void;
        onClearPreferred: () => void;
        onManualHashPaste: (event: ClipboardEvent) => void;
        onPastePreferredHash: () => void;
        onSetPreferredFromDraft: () => void;
    }

    let {
        config,
        preferredPath,
        manualHashDraft = $bindable(),
        isSavingPreferred,
        onCopyPreferredHash,
        onRequestPreferredPath,
        onClearPreferred,
        onManualHashPaste,
        onPastePreferredHash,
        onSetPreferredFromDraft,
    }: Props = $props();
</script>

<div class="shrink-0 border-b border-sem-border px-3 py-1.5 space-y-1.5">
    <div class="flex items-center gap-2 min-w-0">
        <span class="text-xs font-medium text-sem-fg-muted shrink-0">
            {t("tools.propagation_nodes.preferred_heading")}
        </span>
        {#if config.lxmf_preferred_propagation_node_destination_hash}
            <span
                class="min-w-0 flex-1 truncate font-mono text-[11px] text-sem-fg-secondary"
                title={config.lxmf_preferred_propagation_node_destination_hash}
            >
                {formatDestinationHash(config.lxmf_preferred_propagation_node_destination_hash)}
            </span>
        {:else}
            <span class="min-w-0 flex-1 truncate text-[11px] text-sem-fg-muted">
                {t("tools.propagation_nodes.preferred_none_short")}
            </span>
        {/if}
        {#if config.lxmf_preferred_propagation_node_destination_hash}
            <div class="flex items-center gap-0.5 shrink-0">
                <button
                    type="button"
                    class="inline-flex size-7 items-center justify-center rounded-lg text-sem-fg-muted hover:bg-sem-surface-muted hover:text-sem-accent"
                    title={t("tools.propagation_nodes.copy_hash")}
                    onclick={onCopyPreferredHash}
                >
                    <MaterialDesignIcon iconName="content-copy" class="size-4" />
                </button>
                <button
                    type="button"
                    class="inline-flex size-7 items-center justify-center rounded-lg text-sem-fg-muted hover:bg-sem-surface-muted hover:text-sem-accent"
                    title={t("tools.propagation_nodes.find_path")}
                    onclick={onRequestPreferredPath}
                >
                    <MaterialDesignIcon iconName="map-marker-path" class="size-4" />
                </button>
                <button
                    type="button"
                    class="inline-flex size-7 items-center justify-center rounded-lg text-sem-fg-muted hover:bg-sem-surface-muted hover:text-red-600"
                    title={t("tools.propagation_nodes.clear_preferred")}
                    onclick={onClearPreferred}
                >
                    <MaterialDesignIcon iconName="close" class="size-4" />
                </button>
            </div>
        {/if}
    </div>

    {#if preferredPath}
        <div class="text-[11px] text-sem-fg-muted">
            {formatPathLabel(preferredPath)}
        </div>
    {/if}

    {#if config.lxmf_preferred_propagation_node_auto_select}
        <p class="text-[11px] text-amber-700 dark:text-amber-300">
            {t("tools.propagation_nodes.auto_select_on_notice")}
        </p>
    {/if}

    <div class="flex gap-1.5">
        <input
            bind:value={manualHashDraft}
            type="text"
            spellcheck="false"
            autocomplete="off"
            placeholder={t("tools.propagation_nodes.manual_placeholder")}
            title={t("tools.propagation_nodes.manual_hint")}
            class="input-field min-w-0 flex-1 py-1.5 font-mono text-xs"
            onkeydown={(e) => {
                if (e.key === "Enter") {
                    e.preventDefault();
                    onSetPreferredFromDraft();
                }
            }}
            onpaste={onManualHashPaste}
        />
        <button type="button" class="secondary-chip shrink-0 text-xs px-3 py-1.5" onclick={onPastePreferredHash}>
            {t("tools.propagation_nodes.paste_hash")}
        </button>
        <button
            type="button"
            class="primary-chip shrink-0 text-xs px-3 py-1.5"
            disabled={isSavingPreferred || !manualHashDraft}
            onclick={onSetPreferredFromDraft}
        >
            {t("tools.propagation_nodes.set_preferred")}
        </button>
    </div>
</div>
