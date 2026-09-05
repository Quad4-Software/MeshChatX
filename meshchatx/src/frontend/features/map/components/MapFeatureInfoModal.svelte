<!-- SPDX-License-Identifier: 0BSD -->

<script lang="ts">
    import MaterialDesignIcon from "../../../ui/svelte/MaterialDesignIcon.svelte";
    import DOMPurify from "dompurify";
    import { t } from "../../../js/i18n.js";
    import type { MapDrawFeatureInfo } from "../lib/types.js";

    interface Props {
        payload?: MapDrawFeatureInfo | null;
        canEdit?: boolean;
        onClose?: () => void;
        onSave?: (name: string, description: string) => void;
    }

    let { payload = null, canEdit = false, onClose, onSave }: Props = $props();

    let editing = $state(false);
    let editName = $state("");
    let editDescription = $state("");

    $effect(() => {
        if (payload) {
            editName = payload.name || "";
            editDescription = payload.description || "";
            editing = false;
        }
    });

    const descriptionSanitized = $derived.by(() => {
        if (!payload?.description || !payload.descriptionIsHtml) return "";
        return DOMPurify.sanitize(payload.description);
    });

    function splitTextWithLinks(text: string) {
        if (!text) return [];
        const urlRegex = /(https?:\/\/[^\s]+)/g;
        const parts: { kind: "text" | "link"; text: string; href?: string }[] = [];
        let lastIdx = 0;
        let match: RegExpExecArray | null;
        while ((match = urlRegex.exec(text)) !== null) {
            if (match.index > lastIdx) {
                parts.push({ kind: "text", text: text.substring(lastIdx, match.index) });
            }
            parts.push({ kind: "link", text: match[0], href: match[0] });
            lastIdx = match.index + match[0].length;
        }
        if (lastIdx < text.length) {
            parts.push({ kind: "text", text: text.substring(lastIdx) });
        }
        return parts;
    }

    function handleSave() {
        onSave?.(editName.trim(), editDescription.trim());
        editing = false;
    }
</script>

{#if payload}
    <div
        class="info-popup pointer-events-auto min-w-52 max-w-[min(22rem,calc(100vw-2rem))] max-h-[min(22rem,calc(100vh-6rem))] overflow-y-auto rounded-xl border border-sem-border bg-white/95 dark:bg-zinc-900/95 backdrop-blur-sm shadow-xl px-3 py-2.5 mb-2 text-sem-fg"
        role="dialog"
    >
        <div class="flex items-start justify-between gap-2 mb-1">
            {#if payload.iconSrc}
                <div class="flex justify-center shrink-0">
                    <img
                        src={payload.iconSrc}
                        alt=""
                        class="max-h-12 max-w-18 object-contain rounded-sm border border-sem-border bg-gray-50 dark:bg-zinc-800/50"
                    />
                </div>
            {/if}
            <div class="flex items-center gap-0.5 ml-auto shrink-0">
                {#if !editing && canEdit}
                    <button
                        type="button"
                        class="p-1 rounded-md text-sem-fg-muted hover:text-sem-fg hover:bg-sem-surface-muted cursor-pointer"
                        title={t("map.feature_edit")}
                        onclick={() => {
                            editing = true;
                        }}
                    >
                        <MaterialDesignIcon iconName="pencil" class="size-3.5" />
                    </button>
                {/if}
                <button
                    type="button"
                    class="p-1 rounded-md text-sem-fg-muted hover:text-sem-fg hover:bg-sem-surface-muted cursor-pointer"
                    title={t("common.close")}
                    onclick={() => onClose?.()}
                >
                    <MaterialDesignIcon iconName="close" class="size-3.5" />
                </button>
            </div>
        </div>

        {#if editing}
            <label
                class="block text-[10px] font-bold text-sem-fg-muted uppercase tracking-wider mb-0.5"
                for="feature-edit-name"
            >
                {t("map.feature_name")}
            </label>
            <input
                id="feature-edit-name"
                type="text"
                bind:value={editName}
                class="w-full mb-2 px-2 py-1.5 text-xs rounded-lg border border-sem-border bg-sem-surface text-sem-fg"
            />
            <label
                class="block text-[10px] font-bold text-sem-fg-muted uppercase tracking-wider mb-0.5"
                for="feature-edit-desc"
            >
                {t("map.feature_description")}
            </label>
            <textarea
                id="feature-edit-desc"
                bind:value={editDescription}
                rows="5"
                class="w-full mb-2 px-2 py-1.5 text-[11px] rounded-lg border border-sem-border bg-sem-surface text-sem-fg resize-y"
            ></textarea>
            <div class="flex justify-end gap-2">
                <button
                    type="button"
                    class="px-2 py-1 text-[10px] font-semibold rounded-lg text-sem-fg-muted hover:bg-sem-surface-muted cursor-pointer"
                    onclick={() => {
                        editing = false;
                    }}
                >
                    {t("common.cancel")}
                </button>
                <button
                    type="button"
                    class="px-2 py-1 text-[10px] font-semibold rounded-lg bg-blue-500 text-white hover:bg-blue-600 cursor-pointer"
                    onclick={handleSave}
                >
                    {t("common.save")}
                </button>
            </div>
        {:else}
            {#if payload.name}
                <div class="text-xs font-bold text-sem-fg leading-snug mb-1">
                    {payload.name}
                </div>
            {/if}
            {#if payload.description && !payload.descriptionIsHtml}
                <div class="text-[11px] text-sem-fg-muted whitespace-pre-wrap wrap-break-word leading-snug">
                    {#each splitTextWithLinks(payload.description) as part, idx (idx)}
                        {#if part.kind === "link"}
                            <a
                                href={part.href}
                                target="_blank"
                                rel="noopener noreferrer"
                                class="text-blue-500 underline break-all">{part.text}</a
                            >
                        {:else}
                            <span>{part.text}</span>
                        {/if}
                    {/each}
                </div>
            {:else if descriptionSanitized}
                <div class="text-[11px] text-sem-fg-muted leading-snug">
                    <!-- eslint-disable-next-line svelte/no-at-html-tags -->
                    {@html descriptionSanitized}
                </div>
            {/if}
            {#if payload.extended && payload.extended.length}
                <dl class="mt-2 space-y-1.5 border-t border-sem-border pt-2">
                    {#each payload.extended as row (row.key)}
                        <div class="grid grid-cols-[minmax(0,38%)_1fr] gap-x-2 gap-y-0.5 text-[10px] min-w-0">
                            <dt class="font-semibold text-sem-fg-muted wrap-break-word" title={row.key}>
                                {row.key}
                            </dt>
                            <dd class="text-sem-fg m-0 wrap-break-word min-w-0">
                                {#each splitTextWithLinks(row.value) as part, pIdx (pIdx)}
                                    {#if part.kind === "link"}
                                        <a
                                            href={part.href}
                                            target="_blank"
                                            rel="noopener noreferrer"
                                            class="text-blue-500 underline break-all">{part.text}</a
                                        >
                                    {:else}
                                        <span>{part.text}</span>
                                    {/if}
                                {/each}
                            </dd>
                        </div>
                    {/each}
                </dl>
            {/if}
        {/if}
    </div>
{/if}
