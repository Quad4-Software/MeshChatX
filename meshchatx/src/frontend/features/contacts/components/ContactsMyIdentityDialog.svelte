<!-- SPDX-License-Identifier: 0BSD -->

<script lang="ts">
    import Modal from "../../../ui/svelte/Modal.svelte";
    import MaterialDesignIcon from "../../../ui/svelte/MaterialDesignIcon.svelte";
    import { t } from "../../../js/i18n.js";

    let {
        open = $bindable(false),
        myIdentityUri = null as string | null,
        myQrDataUrl = null as string | null,
        onClose,
        onCopy,
        onShare,
    }: {
        open?: boolean;
        myIdentityUri?: string | null;
        myQrDataUrl?: string | null;
        onClose?: () => void;
        onCopy?: () => void;
        onShare?: () => void;
    } = $props();

    function handleClose() {
        open = false;
        onClose?.();
    }
</script>

<Modal bind:open title={t("contacts.share_my_identity")} maxWidth={448} onClose={handleClose}>
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
            <button type="button" class="secondary-chip focus-ring-sem" onclick={() => onCopy?.()}>
                <MaterialDesignIcon iconName="content-copy" class="size-4" />
                {t("common.copy")}
            </button>
            <button type="button" class="primary-chip focus-ring-sem" onclick={() => onShare?.()}>
                <MaterialDesignIcon iconName="share-variant" class="size-4" />
                {t("contacts.share")}
            </button>
        </div>
    </div>
</Modal>
