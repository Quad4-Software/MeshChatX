<!-- SPDX-License-Identifier: 0BSD -->

<script lang="ts">
    import Modal from "../../../ui/svelte/Modal.svelte";
    import MaterialDesignIcon from "../../../ui/svelte/MaterialDesignIcon.svelte";
    import ToastUtils from "../../../js/ToastUtils.js";
    import Utils from "../../../js/Utils.js";
    import { t } from "../../../js/i18n.js";

    interface Props {
        destinationHash?: string;
        hops?: number;
        open?: boolean;
        onclose?: () => void;
        onClose?: () => void;
    }

    let { destinationHash = "", hops = 0, open = true, onclose, onClose }: Props = $props();

    function handleClose() {
        onclose?.();
        onClose?.();
    }

    function copyDestinationHash() {
        if (!destinationHash) return;
        navigator.clipboard.writeText(destinationHash);
        ToastUtils.success("Address copied to clipboard");
    }
</script>

<Modal {open} title={t("nomadnet.title")} onClose={handleClose} maxWidth={460}>
    <div class="space-y-4">
        <div>
            <div class="glass-label mb-1">
                {t("common.destination")}
            </div>
            <div class="flex items-center gap-2 rounded-lg border border-sem-border bg-sem-surface-muted p-2.5">
                <div class="min-w-0 flex-1">
                    <div class="text-xs font-mono font-medium text-sem-fg break-all select-all">
                        {destinationHash}
                    </div>
                    {#if destinationHash}
                        <div class="mt-0.5 text-[11px] text-sem-fg-muted">
                            {Utils.formatDestinationHash(destinationHash)}
                        </div>
                    {/if}
                </div>
                <button
                    type="button"
                    class="secondary-chip focus-ring-sem shrink-0 p-2 text-xs"
                    title={t("common.copy_to_clipboard")}
                    onclick={copyDestinationHash}
                >
                    <MaterialDesignIcon iconName="content-copy" class="size-4" />
                </button>
            </div>
        </div>

        <div>
            <div class="glass-label mb-1">
                {t("rnprobe.hops")}
            </div>
            <div
                class="flex items-center gap-2 rounded-lg border border-sem-border bg-sem-surface-muted px-3 py-2 text-sm text-sem-fg"
            >
                <MaterialDesignIcon iconName="map-marker-path" class="size-4 text-sem-fg-muted" />
                <span>
                    {hops}
                    {hops === 1 ? t("app.hop") : t("app.hops_plural")}
                </span>
            </div>
        </div>

        <div class="flex justify-end pt-2">
            <button type="button" class="secondary-chip focus-ring-sem px-4 py-2 text-sm" onclick={handleClose}>
                {t("common.close")}
            </button>
        </div>
    </div>
</Modal>
