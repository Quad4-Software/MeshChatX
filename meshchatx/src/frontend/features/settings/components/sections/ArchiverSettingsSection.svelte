<!-- SPDX-License-Identifier: 0BSD -->

<script lang="ts">
    import Toggle from "../Toggle.svelte";
    import MaterialDesignIcon from "../../../../ui/svelte/MaterialDesignIcon.svelte";

    interface Props {
        visible?: boolean;
        config?: Record<string, any>;
        onenabledchange?: (val: boolean) => void;
        onconfigchange?: (patch: Record<string, any>) => void;
        onflush?: () => void;
    }

    let { visible = true, config = {}, onenabledchange, onconfigchange, onflush }: Props = $props();
</script>

{#if visible}
    <section class="settings-section break-inside-avoid">
        <header class="settings-section__header">
            <div>
                <div class="settings-section__eyebrow">Browsing</div>
                <h2>Page Archiver</h2>
                <p>Automatically save copies of visited NomadNetwork pages.</p>
            </div>
        </header>
        <div class="settings-section__body space-y-3">
            <label class="setting-toggle">
                <Toggle
                    id="page-archiver-enabled"
                    checked={Boolean(config.page_archiver_enabled)}
                    onchange={onenabledchange}
                />
                <span class="setting-toggle__label">
                    <span class="setting-toggle__title">Enable Archiver</span>
                    <span class="setting-toggle__description"
                        >Automatically archive pages for offline viewing and fallback.</span
                    >
                </span>
            </label>
            <div class="grid grid-cols-1 sm:grid-cols-2 gap-4">
                <div class="space-y-2">
                    <label for="archiver-max-versions" class="text-sm font-medium text-sem-fg block">
                        Max Versions per Page
                    </label>
                    <input
                        id="archiver-max-versions"
                        value={config.page_archiver_max_versions}
                        type="number"
                        min="1"
                        max="50"
                        class="input-field"
                        oninput={(e) =>
                            onconfigchange?.({
                                page_archiver_max_versions: Number((e.target as HTMLInputElement).value),
                            })}
                    />
                    <div class="text-xs text-sem-fg-muted">How many versions of each page to keep.</div>
                </div>
                <div class="space-y-2">
                    <label for="archiver-max-storage" class="text-sm font-medium text-sem-fg block">
                        Max Total Storage (GB)
                    </label>
                    <input
                        id="archiver-max-storage"
                        value={config.archives_max_storage_gb}
                        type="number"
                        min="1"
                        class="input-field"
                        oninput={(e) =>
                            onconfigchange?.({
                                archives_max_storage_gb: Number((e.target as HTMLInputElement).value),
                            })}
                    />
                    <div class="text-xs text-sem-fg-muted">Total storage for all archived pages.</div>
                </div>
            </div>
            <button
                type="button"
                class="w-full flex items-center justify-center gap-2 rounded-xl border border-red-200 dark:border-red-900/30 bg-red-50 dark:bg-red-900/20 px-4 py-2 text-sm font-semibold text-red-700 dark:text-red-300 hover:bg-red-100 dark:hover:bg-red-900/40 transition cursor-pointer"
                onclick={onflush}
            >
                <MaterialDesignIcon iconName="delete-sweep" class="w-4 h-4" />
                Flush All Archived Pages
            </button>
        </div>
    </section>
{/if}
