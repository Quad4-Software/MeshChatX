<!-- SPDX-License-Identifier: 0BSD -->

<script lang="ts">
    import MaterialDesignIcon from "../../../ui/svelte/MaterialDesignIcon.svelte";
    import { t } from "../../../js/i18n.js";
    import { BTN_PRIMARY, BTN_SECONDARY } from "../lib/constants.js";

    interface Props {
        show?: boolean;
        onclose?: () => void;
        onsubmit?: (payload: { hub_hash: string; name?: string; dest_name?: string }) => void;
    }

    let { show = false, onclose, onsubmit }: Props = $props();

    let hubHash = $state("");
    let name = $state("");
    let destName = $state("");
    let advancedOpen = $state(false);

    function handleSubmit() {
        if (!hubHash.trim()) return;
        onsubmit?.({
            hub_hash: hubHash.trim(),
            name: name.trim() || undefined,
            dest_name: destName.trim() || undefined,
        });
    }
</script>

{#if show}
    <!-- svelte-ignore a11y_click_events_have_key_events -->
    <!-- svelte-ignore a11y_no_static_element_interactions -->
    <div
        class="fixed inset-0 z-50 flex items-center justify-center bg-black/50 p-4"
        onclick={(e) => {
            if (e.target === e.currentTarget) onclose?.();
        }}
    >
        <div class="w-full max-w-md rounded-2xl border border-sem-border-card bg-sem-surface p-5 shadow-xl text-sem-fg">
            <h2 class="mb-4 text-lg font-semibold">{t("relay_chat.add_hub_title")}</h2>
            <form
                class="space-y-4"
                onsubmit={(e) => {
                    e.preventDefault();
                    handleSubmit();
                }}
            >
                <div class="space-y-1.5">
                    <label class="block text-sm font-semibold text-sem-fg-secondary" for="add-hub-hash-input">
                        {t("relay_chat.hub_hash")}
                    </label>
                    <input
                        id="add-hub-hash-input"
                        bind:value={hubHash}
                        type="text"
                        placeholder={t("relay_chat.hub_hash_placeholder")}
                        class="input-field font-mono"
                    />
                </div>
                <div class="space-y-1.5">
                    <label class="block text-sm font-semibold text-sem-fg-secondary" for="add-hub-name-input">
                        {t("relay_chat.hub_name")}
                    </label>
                    <input
                        id="add-hub-name-input"
                        bind:value={name}
                        type="text"
                        placeholder={t("relay_chat.hub_name_placeholder")}
                        class="input-field"
                    />
                </div>
                <div class="rounded-lg border border-sem-border/70">
                    <button
                        type="button"
                        class="flex w-full items-center gap-2 px-3 py-2 text-left text-sm font-medium text-sem-fg-secondary transition-colors hover:bg-sem-surface/40 cursor-pointer"
                        onclick={() => {
                            advancedOpen = !advancedOpen;
                        }}
                    >
                        <MaterialDesignIcon
                            iconName={advancedOpen ? "chevron-down" : "chevron-right"}
                            class="size-4 shrink-0"
                        />
                        {t("relay_chat.advanced")}
                    </button>
                    {#if advancedOpen}
                        <div class="space-y-1.5 border-t border-sem-border/70 px-3 py-3">
                            <label class="block text-sm font-semibold text-sem-fg-secondary" for="add-hub-dest-input">
                                {t("relay_chat.dest_name")}
                            </label>
                            <input
                                id="add-hub-dest-input"
                                bind:value={destName}
                                type="text"
                                placeholder="rrc.hub"
                                class="input-field font-mono"
                            />
                        </div>
                    {/if}
                </div>
                <div class="flex justify-end gap-2 pt-1">
                    <button type="button" class={BTN_SECONDARY} onclick={() => onclose?.()}>
                        {t("common.cancel")}
                    </button>
                    <button type="submit" class={BTN_PRIMARY}>{t("relay_chat.add_hub")}</button>
                </div>
            </form>
        </div>
    </div>
{/if}
