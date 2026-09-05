<!-- SPDX-License-Identifier: 0BSD AND MIT -->

<script lang="ts">
    import MaterialDesignIcon from "../../../ui/svelte/MaterialDesignIcon.svelte";
    import { t } from "../../../js/i18n.js";

    type Props = {
        open?: boolean;
        address?: string;
        onclose?: () => void;
        onsubmit?: () => void;
        oningest?: () => void;
        onupdateAddress?: (value: string) => void;
    };

    let { open = false, address = "", onclose, onsubmit, oningest, onupdateAddress }: Props = $props();
</script>

{#if open}
    <div
        class="fixed inset-0 z-95 flex items-end justify-center sm:items-center p-0 sm:p-4 pt-[max(0.75rem,env(safe-area-inset-top))] pb-[max(0px,env(safe-area-inset-bottom))] bg-black/50 backdrop-blur-xs sm:bg-black/50"
        onclick={(e) => {
            if (e.target === e.currentTarget) onclose?.();
        }}
        role="presentation"
    >
        <div
            class="w-full sm:max-w-md bg-sem-surface rounded-t-2xl sm:rounded-2xl shadow-2xl overflow-hidden max-h-[90dvh] flex flex-col"
            role="dialog"
            aria-modal="true"
        >
            <div class="px-5 py-4 border-b border-sem-border flex items-center justify-between shrink-0">
                <h3 class="text-lg font-bold text-sem-fg">{t("messages.mobile_compose_title")}</h3>
                <button
                    type="button"
                    class="text-gray-400 hover:text-gray-500 dark:hover:text-zinc-300 transition-colors min-h-[44px] min-w-[44px] flex items-center justify-center -mr-2"
                    onclick={() => onclose?.()}
                >
                    <MaterialDesignIcon iconName="close" class="size-6" />
                </button>
            </div>
            <div class="p-5 overflow-y-auto space-y-4">
                <p class="text-sm text-sem-fg-muted">{t("messages.select_peer_or_enter_address")}</p>
                <div>
                    <label
                        class="block text-xs font-medium text-sem-fg-muted uppercase tracking-wider mb-1"
                        for="mobile-compose-destination"
                    >
                        {t("app.lxmf_address_hash")}
                    </label>
                    <input
                        id="mobile-compose-destination"
                        type="text"
                        autocomplete="off"
                        autocorrect="off"
                        spellcheck="false"
                        value={address}
                        placeholder={t("messages.mobile_compose_destination_placeholder")}
                        class="input-field w-full"
                        oninput={(e) => onupdateAddress?.((e.currentTarget as HTMLInputElement).value)}
                        onkeydown={(e) => {
                            if (e.key === "Enter") onsubmit?.();
                        }}
                    />
                </div>
                <div class="flex flex-col gap-2">
                    <button
                        type="button"
                        class="primary-chip w-full! rounded-xl! py-2.5! text-sm! focus-ring-sem disabled:opacity-50 disabled:pointer-events-none"
                        disabled={!address.trim()}
                        onclick={() => onsubmit?.()}
                    >
                        {t("app.compose")}
                    </button>
                    <button
                        type="button"
                        class="secondary-chip w-full! rounded-xl! py-2.5! text-sm! focus-ring-sem"
                        onclick={() => oningest?.()}
                    >
                        <MaterialDesignIcon iconName="qrcode" class="size-5 shrink-0" />
                        {t("messages.ingest_paper_message")}
                    </button>
                </div>
            </div>
        </div>
    </div>
{/if}
