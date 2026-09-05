<!-- SPDX-License-Identifier: 0BSD -->

<script lang="ts">
    import MaterialDesignIcon from "../../../ui/svelte/MaterialDesignIcon.svelte";
    import { t } from "../../../js/i18n.js";

    interface ExtendedRow {
        key: string;
        value: string;
    }

    interface DrawFeaturePayload {
        iconSrc?: string | null;
        name?: string | null;
        description?: string | null;
        descriptionIsHtml?: boolean;
        extended?: ExtendedRow[];
    }

    interface Props {
        payload?: DrawFeaturePayload | null;
        editing?: boolean;
        canEdit?: boolean;
        editName?: string;
        editDescription?: string;
        descriptionSanitized?: string;
        isMobileScreen?: boolean;
        onstartedit?: () => void;
        oncanceledit?: () => void;
        onsaveedit?: () => void;
        onclose?: () => void;
        onupdatename?: (name: string) => void;
        onupdatedescription?: (desc: string) => void;
    }

    let {
        payload = null,
        editing = false,
        canEdit = false,
        editName = $bindable(""),
        editDescription = $bindable(""),
        descriptionSanitized = "",
        isMobileScreen = false,
        onstartedit,
        oncanceledit,
        onsaveedit,
        onclose,
        onupdatename,
        onupdatedescription,
    }: Props = $props();

    function splitTextWithLinks(
        text: string | null | undefined
    ): { kind: "text" | "link"; text: string; href?: string }[] {
        if (!text) return [];
        const str = String(text);
        const urlRegex = /(https?:\/\/[^\s]+)/g;
        const parts: { kind: "text" | "link"; text: string; href?: string }[] = [];
        let lastIndex = 0;
        let match;
        while ((match = urlRegex.exec(str)) !== null) {
            if (match.index > lastIndex) {
                parts.push({ kind: "text", text: str.slice(lastIndex, match.index) });
            }
            parts.push({ kind: "link", text: match[0], href: match[0] });
            lastIndex = match.index + match[0].length;
        }
        if (lastIndex < str.length) {
            parts.push({ kind: "text", text: str.slice(lastIndex) });
        }
        return parts;
    }
</script>

{#if payload}
    <div
        class="bg-sem-surface rounded-xl shadow-2xl border border-sem-border p-3 max-h-[min(28rem,70vh)] overflow-y-auto scrollbar-thin {isMobileScreen
            ? 'w-[min(100vw-2rem,22rem)]'
            : 'w-72 md:w-80'} pointer-events-auto transform -translate-x-1/2 -translate-y-full mb-6"
        role="region"
        aria-label="Feature Info"
        onpointerdown={(e) => e.stopPropagation()}
        ontouchstart={(e) => e.stopPropagation()}
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
                        onclick={(e) => {
                            e.stopPropagation();
                            onstartedit?.();
                        }}
                    >
                        <MaterialDesignIcon iconName="pencil" class="size-3.5" />
                    </button>
                {/if}
                <button
                    type="button"
                    class="p-1 rounded-md text-sem-fg-muted hover:text-sem-fg hover:bg-sem-surface-muted cursor-pointer"
                    title={t("common.close")}
                    onclick={(e) => {
                        e.stopPropagation();
                        onclose?.();
                    }}
                >
                    <MaterialDesignIcon iconName="close" class="size-3.5" />
                </button>
            </div>
        </div>

        {#if editing}
            <label
                for="draw-feature-name-input"
                class="block text-[10px] font-bold text-sem-fg-muted uppercase tracking-wider mb-0.5"
            >
                {t("map.feature_name")}
            </label>
            <input
                id="draw-feature-name-input"
                bind:value={editName}
                type="text"
                class="w-full mb-2 px-2 py-1.5 text-xs rounded-lg border border-sem-border bg-sem-surface text-sem-fg"
                oninput={(e) => onupdatename?.((e.target as HTMLInputElement).value)}
            />
            <label
                for="draw-feature-desc-input"
                class="block text-[10px] font-bold text-sem-fg-muted uppercase tracking-wider mb-0.5"
            >
                {t("map.feature_description")}
            </label>
            <textarea
                id="draw-feature-desc-input"
                bind:value={editDescription}
                rows="5"
                class="w-full mb-2 px-2 py-1.5 text-[11px] rounded-lg border border-sem-border bg-sem-surface text-sem-fg resize-y"
                oninput={(e) => onupdatedescription?.((e.target as HTMLTextAreaElement).value)}></textarea>
            <div class="flex justify-end gap-2">
                <button
                    type="button"
                    class="px-2 py-1 text-[10px] font-semibold rounded-lg text-sem-fg-muted hover:bg-sem-surface-muted cursor-pointer"
                    onclick={(e) => {
                        e.stopPropagation();
                        oncanceledit?.();
                    }}
                >
                    {t("common.cancel")}
                </button>
                <button
                    type="button"
                    class="px-2 py-1 text-[10px] font-semibold rounded-lg bg-blue-500 text-white hover:bg-blue-600 cursor-pointer"
                    onclick={(e) => {
                        e.stopPropagation();
                        onsaveedit?.();
                    }}
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
                <div
                    class="text-[11px] text-sem-fg-muted prose prose-sm dark:prose-invert max-w-none leading-snug [&_*]:bg-transparent! [&_*]:text-inherit!"
                >
                    <!-- eslint-disable-next-line svelte/no-at-html-tags -->
                    {@html descriptionSanitized}
                </div>
            {/if}

            {#if (payload.extended || []).length > 0}
                <dl class="mt-2 space-y-1.5 border-t border-sem-border pt-2">
                    {#each payload.extended || [] as row (row.key)}
                        <div class="grid grid-cols-[minmax(0,38%)_1fr] gap-x-2 gap-y-0.5 text-[10px] min-w-0">
                            <dt class="font-semibold text-sem-fg-muted wrap-break-word" title={row.key}>
                                {row.key}
                            </dt>
                            <dd class="text-sem-fg m-0 wrap-break-word min-w-0">
                                {#each splitTextWithLinks(row.value) as part, pIdx (row.key + pIdx)}
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
