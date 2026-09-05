<!-- SPDX-License-Identifier: 0BSD -->

<script>
    import MaterialDesignIcon from "../../../ui/svelte/MaterialDesignIcon.svelte";
    import { t } from "../../../js/i18n.js";

    /**
     * @type {{
     *   open?: boolean,
     *   myIdentityUri?: string | null,
     *   myQrDataUrl?: string | null,
     *   onClose?: () => void,
     *   onCopy?: () => void,
     *   onShare?: () => void,
     * }}
     */
    let { open = false, myIdentityUri = null, myQrDataUrl = null, onClose, onCopy, onShare } = $props();
</script>

{#if open}
    <div
        class="fixed inset-0 z-200 flex items-center justify-center p-4 bg-black/50 backdrop-blur-xs"
        onclick={(e) => {
            if (e.target === e.currentTarget) onClose?.();
        }}
        onkeydown={(e) => {
            if (e.key === "Escape") onClose?.();
        }}
        role="presentation"
    >
        <div
            class="w-full max-w-md rounded-2xl bg-sem-surface shadow-2xl overflow-hidden"
            role="dialog"
            aria-modal="true"
        >
            <div class="px-5 py-4 border-b border-sem-border flex items-center justify-between">
                <h3 class="text-lg font-bold text-sem-fg">{t("contacts.share_my_identity")}</h3>
                <button type="button" class="text-sem-fg-muted hover:text-sem-fg" onclick={() => onClose?.()}>
                    <MaterialDesignIcon iconName="close" class="size-5" />
                </button>
            </div>
            <div class="p-5 space-y-4">
                <div class="flex justify-center">
                    {#if myQrDataUrl}
                        <img
                            src={myQrDataUrl}
                            alt="Identity QR"
                            class="w-52 h-52 rounded-xl border border-sem-border bg-white"
                        />
                    {/if}
                </div>
                <div class="text-xs font-mono break-all text-center text-sem-fg-muted">{myIdentityUri || ""}</div>
                <div class="flex justify-center gap-2">
                    <button type="button" class="secondary-chip" onclick={() => onCopy?.()}>
                        <MaterialDesignIcon iconName="content-copy" class="size-4" />
                        {t("common.copy")}
                    </button>
                    <button type="button" class="primary-chip" onclick={() => onShare?.()}>
                        <MaterialDesignIcon iconName="share-variant" class="size-4" />
                        {t("contacts.share")}
                    </button>
                </div>
            </div>
        </div>
    </div>
{/if}
