<!-- SPDX-License-Identifier: 0BSD -->

<script lang="ts">
    import MaterialDesignIcon from "../../../ui/svelte/MaterialDesignIcon.svelte";
    import { t } from "../../../js/i18n.js";
    import {
        buildPublishSiteEntries,
        sanitizePublishFilename,
        type PublishSiteEntry,
        type PublishSitePayload,
    } from "../lib/micronPublish.js";
    import type { MicronTab, PageNodeItem } from "../lib/types.js";

    const NEW_SERVER = "__new";

    interface Props {
        show?: boolean;
        tabs?: MicronTab[];
        pageNodes?: PageNodeItem[];
        busy?: boolean;
        onclose?: () => void;
        onpublish?: (payload: PublishSitePayload) => void;
    }

    let { show = false, tabs = [], pageNodes = [], busy = false, onclose, onpublish }: Props = $props();

    let selectedNodeId = $state("");
    let newServerName = $state("");
    let entries = $state<PublishSiteEntry[]>([]);
    let generateIndex = $state(true);
    let dragIndex = $state(-1);
    let dragOverIndex = $state(-1);

    const includedCount = $derived(entries.filter((e) => e.include && e.filename.trim()).length);
    const canSubmit = $derived(
        selectedNodeId === NEW_SERVER ? newServerName.trim().length > 0 : Boolean(selectedNodeId)
    );

    function reset(): void {
        selectedNodeId = pageNodes[0]?.node_id || NEW_SERVER;
        newServerName = "";
        generateIndex = true;
        dragIndex = -1;
        dragOverIndex = -1;
        entries = buildPublishSiteEntries(tabs);
    }

    $effect(() => {
        if (show) {
            reset();
        }
    });

    function moveEntry(index: number, delta: number): void {
        const target = index + delta;
        if (target < 0 || target >= entries.length) {
            return;
        }
        const [item] = entries.splice(index, 1);
        entries.splice(target, 0, item);
    }

    function onDragStart(index: number): void {
        dragIndex = index;
    }

    function onDrop(index: number): void {
        if (dragIndex < 0 || dragIndex === index) {
            return;
        }
        const [item] = entries.splice(dragIndex, 1);
        entries.splice(index, 0, item);
        dragIndex = -1;
    }

    function close(): void {
        if (busy) {
            return;
        }
        onclose?.();
    }

    function submit(): void {
        const pages = entries
            .filter((e) => e.include && e.filename.trim())
            .map((e) => ({
                name: e.filename.trim(),
                content: e.content,
                label: e.tabName,
            }));
        if (pages.length === 0 || !canSubmit) {
            return;
        }
        onpublish?.({
            nodeId: selectedNodeId === NEW_SERVER ? null : selectedNodeId,
            newServerName: selectedNodeId === NEW_SERVER ? newServerName.trim() : "",
            pages,
            generateIndex,
        });
    }
</script>

{#if show}
    <!-- svelte-ignore a11y_click_events_have_key_events -->
    <!-- svelte-ignore a11y_no_static_element_interactions -->
    <div
        class="fixed inset-0 z-100 flex items-end sm:items-center justify-center p-0 sm:p-4 bg-black/50"
        onclick={(e) => {
            if (e.target === e.currentTarget) close();
        }}
    >
        <div
            class="w-full sm:max-w-xl flex flex-col max-sm:h-[92dvh] max-sm:max-h-[92dvh] sm:max-h-[90vh] rounded-t-2xl sm:rounded-lg border border-sem-border bg-sem-surface shadow-xl touch-pan-y min-h-0"
        >
            <div class="flex justify-between items-start gap-2 p-3 sm:p-5 border-b border-sem-border shrink-0">
                <div class="min-w-0 pr-2">
                    <h3 class="text-lg sm:text-xl font-bold text-sem-fg">
                        {t("tools.micron_editor.publish_site_title")}
                    </h3>
                    <p class="text-sm text-sem-fg-muted mt-0.5">
                        {t("tools.micron_editor.publish_site_hint")}
                    </p>
                </div>
                <button
                    type="button"
                    class="p-2 rounded-lg text-sem-fg-muted hover:text-sem-fg hover:bg-sem-surface-muted shrink-0"
                    disabled={busy}
                    onclick={close}
                >
                    <MaterialDesignIcon iconName="close" class="size-5" />
                </button>
            </div>

            <div class="flex-1 min-h-0 overflow-y-auto p-3 sm:p-5 space-y-4">
                <div>
                    <label
                        for="publish-site-server"
                        class="block text-xs font-bold uppercase tracking-wider text-sem-fg-muted mb-1.5"
                    >
                        {t("tools.micron_editor.publish_site_server")}
                    </label>
                    <select
                        id="publish-site-server"
                        bind:value={selectedNodeId}
                        class="w-full rounded-lg border border-sem-border bg-sem-surface text-sem-fg px-3 py-2 text-sm focus:outline-hidden focus:ring-2 focus:ring-sem-focus"
                        disabled={busy}
                    >
                        {#each pageNodes as pn (pn.node_id)}
                            <option value={pn.node_id}>
                                {pn.name}{pn.running ? "" : " · " + t("tools.micron_editor.publish_will_start")}
                            </option>
                        {/each}
                        <option value={NEW_SERVER}>{t("tools.micron_editor.publish_site_new_server")}</option>
                    </select>
                    {#if selectedNodeId === NEW_SERVER}
                        <input
                            bind:value={newServerName}
                            type="text"
                            class="mt-2 w-full rounded-lg border border-sem-border bg-sem-surface text-sem-fg px-3 py-2 text-sm focus:outline-hidden focus:ring-2 focus:ring-sem-focus"
                            placeholder={t("tools.micron_editor.publish_site_new_server_name")}
                            disabled={busy}
                        />
                    {/if}
                </div>

                <div>
                    <div class="text-xs font-bold uppercase tracking-wider text-sem-fg-muted mb-1.5">
                        {t("tools.micron_editor.publish_site_pages")}
                    </div>
                    <ul class="space-y-1">
                        {#each entries as entry, index (entry.tabId)}
                            <li
                                draggable="true"
                                class="flex items-center gap-2 rounded-lg border border-sem-border bg-sem-surface-muted px-2 py-1.5 transition-colors {!entry.include
                                    ? 'opacity-50'
                                    : ''} {dragOverIndex === index ? 'ring-2 ring-sem-accent' : ''}"
                                ondragstart={() => onDragStart(index)}
                                ondragover={(e) => {
                                    e.preventDefault();
                                    dragOverIndex = index;
                                }}
                                ondragleave={() => (dragOverIndex = -1)}
                                ondrop={(e) => {
                                    e.preventDefault();
                                    onDrop(index);
                                }}
                                ondragend={() => (dragOverIndex = -1)}
                            >
                                <MaterialDesignIcon
                                    iconName="drag-vertical"
                                    class="size-4 text-sem-fg-muted cursor-grab shrink-0"
                                />
                                <input
                                    bind:checked={entry.include}
                                    type="checkbox"
                                    class="size-4 shrink-0 accent-sem-accent"
                                    disabled={busy}
                                    title={t("tools.micron_editor.publish_site_include")}
                                />
                                <span class="text-xs text-sem-fg-muted truncate w-24 shrink-0" title={entry.tabName}>
                                    {entry.tabName}
                                </span>
                                <input
                                    bind:value={entry.filename}
                                    type="text"
                                    spellcheck="false"
                                    class="flex-1 min-w-0 rounded-md border border-sem-border bg-sem-surface text-sem-fg px-2 py-1 text-xs font-mono focus:outline-hidden focus:ring-2 focus:ring-sem-focus"
                                    disabled={busy || !entry.include}
                                    oninput={() => {
                                        entry.filename = sanitizePublishFilename(entry.filename);
                                    }}
                                />
                                <button
                                    type="button"
                                    class="p-1 rounded-md text-sem-fg-muted hover:text-sem-fg hover:bg-sem-surface disabled:opacity-30"
                                    disabled={busy || index === 0}
                                    title={t("tools.micron_editor.publish_site_move_up")}
                                    onclick={() => moveEntry(index, -1)}
                                >
                                    <MaterialDesignIcon iconName="arrow-up" class="size-3.5" />
                                </button>
                                <button
                                    type="button"
                                    class="p-1 rounded-md text-sem-fg-muted hover:text-sem-fg hover:bg-sem-surface disabled:opacity-30"
                                    disabled={busy || index === entries.length - 1}
                                    title={t("tools.micron_editor.publish_site_move_down")}
                                    onclick={() => moveEntry(index, 1)}
                                >
                                    <MaterialDesignIcon iconName="arrow-down" class="size-3.5" />
                                </button>
                            </li>
                        {/each}
                    </ul>
                </div>

                <label class="flex items-start gap-2 text-sm text-sem-fg cursor-pointer">
                    <input
                        bind:checked={generateIndex}
                        type="checkbox"
                        class="size-4 mt-0.5 shrink-0 accent-sem-accent"
                        disabled={busy}
                    />
                    <span>
                        {t("tools.micron_editor.publish_site_index")}
                        <span class="block text-xs text-sem-fg-muted">
                            {t("tools.micron_editor.publish_site_index_hint")}
                        </span>
                    </span>
                </label>
            </div>

            <div class="flex items-center justify-end gap-2 p-3 sm:p-5 border-t border-sem-border shrink-0">
                <button type="button" class="secondary-chip py-1.5! px-3!" disabled={busy} onclick={close}>
                    {t("common.cancel")}
                </button>
                <button
                    type="button"
                    class="primary-chip py-1.5! px-3!"
                    disabled={busy || includedCount === 0 || !canSubmit}
                    onclick={submit}
                >
                    {t("tools.micron_editor.publish_site_publish", { count: includedCount })}
                </button>
            </div>
        </div>
    </div>
{/if}
