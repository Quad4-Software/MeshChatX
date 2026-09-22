<!-- SPDX-License-Identifier: 0BSD -->

<script lang="ts">
    import Modal from "../../../ui/svelte/Modal.svelte";
    import MaterialDesignIcon from "../../../ui/svelte/MaterialDesignIcon.svelte";
    import { t } from "../../../js/i18n.js";

    let {
        open = $bindable(false),
        name = $bindable(""),
        input = $bindable(""),
        isSubmitting = false,
        cameraSupported = false,
        onClose,
        onSubmit,
        onPaste,
        onScan,
    }: {
        open?: boolean;
        name?: string;
        input?: string;
        isSubmitting?: boolean;
        cameraSupported?: boolean;
        onClose?: () => void;
        onSubmit?: () => void;
        onPaste?: () => void;
        onScan?: () => void;
    } = $props();

    function onKeydown(event: KeyboardEvent) {
        if (event.key === "Enter") {
            event.preventDefault();
            onSubmit?.();
        }
    }

    function handleClose() {
        open = false;
        onClose?.();
    }
</script>

<Modal bind:open title={t("contacts.add_contact")} onClose={handleClose} showClose={true}>
    <div class="p-5 space-y-4">
        <div>
            <label
                class="block text-xs uppercase tracking-wider font-semibold text-sem-fg-muted mb-1"
                for="contact-name"
            >
                {t("contacts.contact_name_optional")}
            </label>
            <input
                id="contact-name"
                bind:value={name}
                type="text"
                class="input-field"
                placeholder={t("contacts.contact_name_placeholder")}
            />
        </div>
        <div>
            <label
                class="block text-xs uppercase tracking-wider font-semibold text-sem-fg-muted mb-1"
                for="contact-hash"
            >
                {t("contacts.hash_or_uri")}
            </label>
            <div class="relative">
                <input
                    id="contact-hash"
                    bind:value={input}
                    type="text"
                    class="input-field font-mono {cameraSupported ? 'pr-12!' : ''}"
                    placeholder={t("contacts.hash_or_uri_placeholder")}
                    onkeydown={onKeydown}
                />
                {#if cameraSupported}
                    <button
                        type="button"
                        class="absolute right-2 top-1/2 -translate-y-1/2 inline-flex items-center justify-center w-8 h-8 rounded-lg text-sem-fg-muted hover:text-sem-accent hover:bg-sem-surface-muted transition focus-ring-sem"
                        title={t("contacts.scan_qr")}
                        onclick={() => onScan?.()}
                    >
                        <MaterialDesignIcon iconName="qrcode-scan" class="size-5" />
                    </button>
                {/if}
            </div>
        </div>
        <div class="flex flex-wrap gap-2">
            <button type="button" class="secondary-chip focus-ring-sem" onclick={() => onPaste?.()}>
                <MaterialDesignIcon iconName="clipboard-text-outline" class="size-4" />
                {t("contacts.paste")}
            </button>
            {#if cameraSupported}
                <button type="button" class="secondary-chip focus-ring-sem" onclick={() => onScan?.()}>
                    <MaterialDesignIcon iconName="qrcode-scan" class="size-4" />
                    {t("contacts.scan_qr")}
                </button>
            {/if}
        </div>
    </div>
    {#snippet footer()}
        <div class="flex justify-end gap-2">
            <button type="button" class="secondary-chip focus-ring-sem" onclick={handleClose}>
                {t("common.cancel")}
            </button>
            <button
                type="button"
                class="primary-chip focus-ring-sem"
                disabled={!input || isSubmitting}
                onclick={() => onSubmit?.()}
            >
                <MaterialDesignIcon
                    iconName={isSubmitting ? "loading" : "check"}
                    class="size-4 {isSubmitting ? 'animate-spin motion-reduce:animate-none' : ''}"
                />
                {t("contacts.add_contact")}
            </button>
        </div>
    {/snippet}
</Modal>
