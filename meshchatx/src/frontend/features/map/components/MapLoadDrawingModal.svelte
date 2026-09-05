<!-- SPDX-License-Identifier: 0BSD -->

<script lang="ts">
    import MaterialDesignIcon from "../../../ui/svelte/MaterialDesignIcon.svelte";
    import { t } from "../../../js/i18n.js";

    interface Drawing {
        id: string | number;
        name: string;
        updated_at: string | number;
        [key: string]: unknown;
    }

    interface Props {
        show?: boolean;
        loading?: boolean;
        drawings?: Drawing[];
        onclose?: () => void;
        onload?: (drawing: Drawing) => void;
        ondelete?: (drawing: Drawing) => void;
    }

    let { show = false, loading = false, drawings = [], onclose, onload, ondelete }: Props = $props();
</script>

{#if show}
    <div class="fixed inset-0 z-100 flex items-center justify-center p-4 bg-black/40 backdrop-blur-xs">
        <div
            class="bg-sem-surface w-full max-w-lg rounded-2xl shadow-2xl overflow-hidden animate-in fade-in zoom-in duration-200"
        >
            <div class="p-6">
                <div class="flex items-center justify-between mb-6">
                    <h2 class="text-xl font-bold text-sem-fg flex items-center gap-2">
                        <MaterialDesignIcon iconName="folder-open-outline" class="size-6 text-blue-500" />
                        {t("map.load_drawing_title")}
                    </h2>
                    <button
                        type="button"
                        class="text-gray-400 hover:text-gray-600 cursor-pointer"
                        onclick={() => onclose?.()}
                    >
                        <MaterialDesignIcon iconName="close" class="size-6" />
                    </button>
                </div>

                {#if loading}
                    <div class="py-12 flex flex-col items-center justify-center">
                        <MaterialDesignIcon iconName="loading" class="size-10 animate-spin text-blue-500 mb-4" />
                        <span class="text-sm font-medium text-gray-500">{t("map.loading_drawings")}</span>
                    </div>
                {:else if drawings.length === 0}
                    <div class="py-12 flex flex-col items-center justify-center text-center">
                        <div class="size-16 bg-sem-surface-muted rounded-full flex items-center justify-center mb-4">
                            <MaterialDesignIcon iconName="folder-outline" class="size-8 text-gray-400" />
                        </div>
                        <h3 class="text-lg font-bold text-sem-fg">{t("map.no_drawings")}</h3>
                        <p class="text-sm text-sem-fg-muted mt-1">{t("map.no_drawings_desc")}</p>
                    </div>
                {:else}
                    <div class="max-h-[400px] overflow-y-auto space-y-2 pr-2">
                        {#each drawings as drawing (drawing.id)}
                            <!-- svelte-ignore a11y_click_events_have_key_events -->
                            <!-- svelte-ignore a11y_no_static_element_interactions -->
                            <div
                                class="group p-4 bg-gray-50 dark:bg-zinc-800/50 hover:bg-blue-50 dark:hover:bg-blue-900/20 rounded-2xl border border-transparent hover:border-blue-200 dark:hover:border-blue-800 transition-all cursor-pointer flex items-center justify-between"
                                onclick={() => onload?.(drawing)}
                            >
                                <div class="flex-1 min-w-0 mr-4">
                                    <div class="font-bold text-sem-fg truncate">{drawing.name}</div>
                                    <div class="text-xs text-sem-fg-muted mt-0.5">
                                        {t("map.saved_on")}
                                        {new Date(drawing.updated_at).toLocaleString()}
                                    </div>
                                </div>
                                <button
                                    type="button"
                                    class="p-2 text-gray-400 hover:text-red-500 transition-colors cursor-pointer"
                                    title={t("common.delete")}
                                    onclick={(e) => {
                                        e.stopPropagation();
                                        ondelete?.(drawing);
                                    }}
                                >
                                    <MaterialDesignIcon iconName="trash-can-outline" class="size-5" />
                                </button>
                            </div>
                        {/each}
                    </div>
                {/if}

                <div class="mt-8 flex justify-end">
                    <button
                        type="button"
                        class="px-6 py-2.5 rounded-xl border border-sem-border text-sm font-semibold text-gray-700 dark:text-gray-300 hover:bg-sem-surface-muted transition cursor-pointer"
                        onclick={() => onclose?.()}
                    >
                        {t("common.close")}
                    </button>
                </div>
            </div>
        </div>
    </div>
{/if}
