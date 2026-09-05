<!-- SPDX-License-Identifier: 0BSD -->

<script lang="ts">
    import MaterialDesignIcon from "../../../ui/svelte/MaterialDesignIcon.svelte";
    import { t } from "../../../js/i18n.js";

    interface ConversationOption {
        hash: string;
        label: string;
    }

    interface Props {
        show?: boolean;
        summary?: string;
        conversationOptions?: ConversationOption[];
        onclose?: () => void;
        onsend?: (destinationHash: string) => void;
    }

    let { show = false, summary = "", conversationOptions = [], onclose, onsend }: Props = $props();

    let selectedHash = $state("");
</script>

{#if show}
    <!-- svelte-ignore a11y_no_noninteractive_element_interactions, a11y_click_events_have_key_events -->
    <div
        class="fixed inset-0 z-50 bg-black/50 backdrop-blur-xs flex items-center justify-center p-4"
        role="dialog"
        tabindex="-1"
        aria-modal="true"
        onclick={(e) => {
            if (e.target === e.currentTarget) onclose?.();
        }}
        onkeydown={(e) => {
            if (e.key === "Escape") onclose?.();
        }}
    >
        <div class="bg-sem-surface rounded-xl shadow-2xl max-w-md w-full p-4 border border-sem-border text-sem-fg">
            <div class="flex items-center justify-between mb-3">
                <h3 class="font-bold text-lg">{t("map.ping_modal_title")}</h3>
                <button
                    type="button"
                    class="p-1 rounded-lg hover:bg-sem-surface-muted cursor-pointer"
                    onclick={() => onclose?.()}
                >
                    <MaterialDesignIcon iconName="close" class="size-5" />
                </button>
            </div>
            <p class="text-xs text-sem-fg-muted mb-2">
                {summary}
            </p>
            <label for="ping-dest-select" class="block text-[10px] font-bold text-gray-400 uppercase mb-1">
                {t("map.ping_destination")}
            </label>
            <select
                id="ping-dest-select"
                bind:value={selectedHash}
                class="w-full mb-2 bg-gray-50 dark:bg-zinc-800 border border-sem-border rounded-lg px-3 py-2 text-sm text-sem-fg"
            >
                <option value="">{t("map.ping_pick_conversation")}</option>
                {#each conversationOptions as p (p.hash)}
                    <option value={p.hash}>
                        {p.label}
                    </option>
                {/each}
            </select>
            <button
                type="button"
                class="w-full py-2 mb-3 text-sm font-bold bg-blue-500 hover:bg-blue-600 text-white rounded-lg disabled:opacity-40 cursor-pointer"
                disabled={!selectedHash}
                onclick={() => {
                    if (selectedHash) onsend?.(selectedHash);
                }}
            >
                {t("map.ping_send")}
            </button>
            <button
                type="button"
                class="w-full py-2 text-sm font-semibold bg-sem-surface-muted rounded-lg cursor-pointer"
                onclick={() => onclose?.()}
            >
                {t("common.cancel")}
            </button>
        </div>
    </div>
{/if}
