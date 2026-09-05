<!-- SPDX-License-Identifier: 0BSD -->

<script>
    import MaterialDesignIcon from "../../../ui/svelte/MaterialDesignIcon.svelte";
    import { t } from "../../../js/i18n.js";

    /**
     * @type {{
     *   open?: boolean,
     *   name?: string,
     *   input?: string,
     *   isSubmitting?: boolean,
     *   cameraSupported?: boolean,
     *   onClose?: () => void,
     *   onSubmit?: () => void,
     *   onPaste?: () => void,
     *   onScan?: () => void,
     *   onNameChange?: (value: string) => void,
     *   onInputChange?: (value: string) => void,
     * }}
     */
    let {
        open = false,
        name = $bindable(""),
        input = $bindable(""),
        isSubmitting = false,
        cameraSupported = false,
        onClose,
        onSubmit,
        onPaste,
        onScan,
    } = $props();

    /**
     * @param {KeyboardEvent} event
     */
    function onKeydown(event) {
        if (event.key === "Enter") {
            event.preventDefault();
            onSubmit?.();
        }
    }
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
            class="w-full max-w-lg rounded-2xl bg-sem-surface shadow-2xl overflow-hidden"
            role="dialog"
            aria-modal="true"
        >
            <div class="px-5 py-4 border-b border-sem-border flex items-center justify-between">
                <h3 class="text-lg font-bold text-sem-fg">{t("contacts.add_contact")}</h3>
                <button type="button" class="text-sem-fg-muted hover:text-sem-fg" onclick={() => onClose?.()}>
                    <MaterialDesignIcon iconName="close" class="size-5" />
                </button>
            </div>
            <div class="p-5 space-y-4">
                <div>
                    <label
                        class="block text-xs uppercase tracking-wider font-semibold text-gray-500 mb-1"
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
                        class="block text-xs uppercase tracking-wider font-semibold text-gray-500 mb-1"
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
                                class="absolute right-2 top-1/2 -translate-y-1/2 inline-flex items-center justify-center w-8 h-8 rounded-lg text-gray-500 hover:text-blue-600 hover:bg-blue-50 dark:hover:bg-blue-900/40 transition"
                                title={t("contacts.scan_qr")}
                                onclick={() => onScan?.()}
                            >
                                <MaterialDesignIcon iconName="qrcode-scan" class="size-5" />
                            </button>
                        {/if}
                    </div>
                </div>
                <div class="flex flex-wrap gap-2">
                    <button type="button" class="secondary-chip" onclick={() => onPaste?.()}>
                        <MaterialDesignIcon iconName="clipboard-text-outline" class="size-4" />
                        {t("contacts.paste")}
                    </button>
                    {#if cameraSupported}
                        <button type="button" class="secondary-chip" onclick={() => onScan?.()}>
                            <MaterialDesignIcon iconName="qrcode-scan" class="size-4" />
                            {t("contacts.scan_qr")}
                        </button>
                    {/if}
                </div>
            </div>
            <div class="px-5 py-4 border-t border-sem-border flex justify-end gap-2">
                <button type="button" class="secondary-chip" onclick={() => onClose?.()}>
                    {t("common.cancel")}
                </button>
                <button
                    type="button"
                    class="primary-chip"
                    disabled={!input || isSubmitting}
                    onclick={() => onSubmit?.()}
                >
                    <MaterialDesignIcon
                        iconName={isSubmitting ? "loading" : "check"}
                        class="size-4 {isSubmitting ? 'animate-spin' : ''}"
                    />
                    {t("contacts.add_contact")}
                </button>
            </div>
        </div>
    </div>
{/if}
