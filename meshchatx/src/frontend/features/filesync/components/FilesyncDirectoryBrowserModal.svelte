<!-- SPDX-License-Identifier: 0BSD -->

<script lang="ts">
    import MaterialDesignIcon from "../../../ui/svelte/MaterialDesignIcon.svelte";
    import ToastUtils from "../../../js/ToastUtils.js";
    import { t } from "../../../js/i18n.js";
    import { createFilesyncDirectory, fetchFilesyncDirectories } from "../lib/filesyncApi.js";
    import type { FilesyncDirectoryEntry } from "../lib/types.js";

    interface Props {
        open: boolean;
        initialPath?: string;
        onClose: () => void;
        onSelect: (path: string) => void;
    }

    let { open = false, initialPath = "", onClose, onSelect }: Props = $props();

    let busy = $state(false);
    let current = $state("");
    let parent = $state<string | null>(null);
    let directories = $state<FilesyncDirectoryEntry[]>([]);
    let newFolderName = $state("");

    async function load(path?: string): Promise<boolean> {
        busy = true;
        try {
            const data = await fetchFilesyncDirectories(path);
            current = data.current;
            parent = data.parent;
            directories = data.directories;
            return true;
        } catch (err: unknown) {
            const error = err as { message?: string };
            ToastUtils.error(error?.message || t("rns_filesync.error"));
            return false;
        } finally {
            busy = false;
        }
    }

    $effect(() => {
        if (open) {
            newFolderName = "";
            const start = String(initialPath || "").trim();
            void (async () => {
                const loaded = await load(start || undefined);
                if (!loaded && start) {
                    await load(undefined);
                }
            })();
        }
    });

    async function enterDirectory(path: string): Promise<void> {
        await load(path);
    }

    async function goParent(): Promise<void> {
        if (!parent) {
            return;
        }
        await load(parent);
    }

    async function createFolder(): Promise<void> {
        const name = String(newFolderName || "").trim();
        if (!name) {
            return;
        }
        busy = true;
        try {
            const res = await createFilesyncDirectory(current, name);
            newFolderName = "";
            ToastUtils.success(t("rns_filesync.browser_created"));
            if (res.path) {
                await load(res.path);
            } else {
                await load(current);
            }
        } catch (err: unknown) {
            const error = err as { message?: string };
            ToastUtils.error(error?.message || t("rns_filesync.error"));
        } finally {
            busy = false;
        }
    }

    function confirmSelection(): void {
        const path = String(current || "").trim();
        if (!path) {
            return;
        }
        onSelect(path);
        onClose();
    }
</script>

{#if open}
    <!-- svelte-ignore a11y_click_events_have_key_events -->
    <!-- svelte-ignore a11y_no_static_element_interactions -->
    <div
        class="fixed inset-0 z-[60] flex items-center justify-center bg-black/50 p-4"
        onclick={(e) => {
            if (e.target === e.currentTarget) {
                onClose();
            }
        }}
    >
        <div
            class="flex w-full max-w-lg max-h-[min(36rem,90vh)] flex-col rounded-2xl border border-sem-border-card bg-sem-surface shadow-xl"
            role="dialog"
            aria-label={t("rns_filesync.browser_title")}
        >
            <div class="flex items-center justify-between gap-2 border-b border-sem-border px-5 py-4">
                <h2 class="text-lg font-semibold text-sem-fg">{t("rns_filesync.browser_title")}</h2>
                <button
                    type="button"
                    class="rounded-lg p-1 text-sem-fg-muted hover:bg-sem-surface-muted"
                    title={t("common.close")}
                    onclick={onClose}
                >
                    <MaterialDesignIcon iconName="close" class="size-5" />
                </button>
            </div>

            <div class="px-5 pt-3 space-y-2">
                <p class="text-xs text-sem-fg-muted">{t("rns_filesync.browser_hint")}</p>
                <div class="flex items-center gap-2">
                    <button
                        type="button"
                        class="secondary-chip px-2.5 py-1.5 text-xs shrink-0"
                        disabled={busy || !parent}
                        title={t("rns_filesync.browser_up")}
                        onclick={goParent}
                    >
                        <MaterialDesignIcon iconName="arrow-up" class="w-4 h-4" />
                        {t("rns_filesync.browser_up")}
                    </button>
                    <div class="input-field flex-1 min-w-0 py-2! font-mono text-xs truncate" title={current}>
                        {current || "..."}
                    </div>
                </div>
            </div>

            <div class="flex-1 overflow-y-auto custom-scrollbar px-5 py-3">
                {#if busy && directories.length === 0}
                    <div class="py-8 text-center text-sm text-sem-fg-muted">
                        {t("rns_filesync.browser_loading")}
                    </div>
                {:else if directories.length === 0}
                    <div class="py-8 text-center text-sm text-sem-fg-muted">
                        {t("rns_filesync.browser_empty")}
                    </div>
                {:else}
                    <ul class="space-y-1">
                        {#each directories as entry (entry.path)}
                            <li>
                                <button
                                    type="button"
                                    class="flex w-full items-center gap-2 rounded-lg border border-sem-border px-3 py-2 text-left text-sm transition-colors hover:bg-sem-surface-muted"
                                    onclick={() => enterDirectory(entry.path)}
                                >
                                    <MaterialDesignIcon
                                        iconName="folder"
                                        class="w-5 h-5 shrink-0 text-emerald-600 dark:text-emerald-400"
                                    />
                                    <span class="min-w-0 truncate">{entry.name}</span>
                                </button>
                            </li>
                        {/each}
                    </ul>
                {/if}
            </div>

            <div class="border-t border-sem-border px-5 py-3 space-y-3">
                <div class="flex flex-col sm:flex-row gap-2">
                    <input
                        bind:value={newFolderName}
                        type="text"
                        class="input-field flex-1 min-w-0 py-2! text-sm"
                        placeholder={t("rns_filesync.browser_new_placeholder")}
                        disabled={busy}
                        onkeydown={(e) => {
                            if (e.key === "Enter") {
                                e.preventDefault();
                                void createFolder();
                            }
                        }}
                    />
                    <button
                        type="button"
                        class="secondary-chip px-3 py-2 text-xs shrink-0"
                        disabled={busy || !newFolderName.trim()}
                        onclick={createFolder}
                    >
                        <MaterialDesignIcon iconName="folder-plus-outline" class="w-4 h-4" />
                        {t("rns_filesync.browser_new")}
                    </button>
                </div>
                <div class="flex justify-end gap-2">
                    <button type="button" class="secondary-chip px-4 py-2 text-sm" onclick={onClose}>
                        {t("common.cancel")}
                    </button>
                    <button
                        type="button"
                        class="primary-chip px-4 py-2 text-sm"
                        disabled={busy || !current}
                        onclick={confirmSelection}
                    >
                        {t("rns_filesync.browser_select")}
                    </button>
                </div>
            </div>
        </div>
    </div>
{/if}
