<!-- SPDX-License-Identifier: 0BSD -->

<script lang="ts">
    import { tick } from "svelte";
    import MaterialDesignIcon from "../../../ui/svelte/MaterialDesignIcon.svelte";
    import { t } from "../../../js/i18n.js";

    interface Props {
        show?: boolean;
        name?: string;
        onclose?: () => void;
        onsave?: () => void;
    }

    let { show = false, name = $bindable(""), onclose, onsave }: Props = $props();

    let nameInput = $state<HTMLInputElement | null>(null);

    $effect(() => {
        if (show) {
            tick().then(() => {
                nameInput?.focus?.();
            });
        }
    });

    export function focusNameInput() {
        tick().then(() => {
            nameInput?.focus?.();
        });
    }
</script>

{#if show}
    <div class="fixed inset-0 z-100 flex items-center justify-center p-4 bg-black/40 backdrop-blur-xs">
        <div
            class="bg-sem-surface w-full max-w-md rounded-2xl shadow-2xl overflow-hidden animate-in fade-in zoom-in duration-200"
        >
            <div class="p-6">
                <h2 class="text-xl font-bold text-sem-fg flex items-center gap-2">
                    <MaterialDesignIcon iconName="content-save-outline" class="size-6 text-blue-500" />
                    {t("map.save_drawing_title")}
                </h2>
                <p class="text-sm text-sem-fg-muted mt-1">{t("map.save_drawing_desc")}</p>

                <div class="mt-6">
                    <label
                        for="drawing-name-input"
                        class="block text-xs font-bold text-sem-fg-muted uppercase tracking-widest mb-2"
                    >
                        {t("map.drawing_name")}
                    </label>
                    <input
                        id="drawing-name-input"
                        bind:this={nameInput}
                        bind:value={name}
                        type="text"
                        class="w-full px-4 py-3 bg-gray-50 dark:bg-zinc-800 border-none rounded-xl text-sm focus:ring-2 focus:ring-blue-500 transition-all dark:text-white"
                        placeholder={t("map.drawing_name_placeholder")}
                        onkeydown={(e) => {
                            if (e.key === "Enter" && String(name || "").trim()) {
                                onsave?.();
                            }
                        }}
                    />
                </div>

                <div class="mt-8 flex gap-3">
                    <button
                        type="button"
                        class="flex-1 px-4 py-2.5 rounded-xl border border-sem-border text-sm font-semibold text-gray-700 dark:text-gray-300 hover:bg-sem-surface-muted transition cursor-pointer"
                        onclick={() => onclose?.()}
                    >
                        {t("common.close")}
                    </button>
                    <button
                        type="button"
                        class="flex-1 px-4 py-2.5 rounded-xl bg-blue-600 text-white text-sm font-semibold shadow-lg shadow-blue-500/25 hover:bg-blue-500 transition active:scale-95 disabled:opacity-50 cursor-pointer"
                        disabled={!String(name || "").trim()}
                        onclick={() => onsave?.()}
                    >
                        {t("common.save")}
                    </button>
                </div>
            </div>
        </div>
    </div>
{/if}
