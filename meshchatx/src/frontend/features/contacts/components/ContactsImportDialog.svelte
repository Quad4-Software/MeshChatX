<!-- SPDX-License-Identifier: 0BSD -->

<script>
    import MaterialDesignIcon from "../../../ui/svelte/MaterialDesignIcon.svelte";
    import { t } from "../../../js/i18n.js";

    /**
     * @type {{
     *   open?: boolean,
     *   importError?: string | null,
     *   onClose?: () => void,
     *   onFileSelected?: (file: File) => void,
     * }}
     */
    let { open = false, importError = null, onClose, onFileSelected } = $props();

    /** @type {HTMLInputElement | undefined} */
    let fileInput = $state();

    /**
     * @param {Event} event
     */
    function onChange(event) {
        const target = /** @type {HTMLInputElement} */ (event.target);
        const file = target.files?.[0];
        if (file) {
            onFileSelected?.(file);
        }
        target.value = "";
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
                <h3 class="text-lg font-bold text-sem-fg">{t("contacts.import_modal_title")}</h3>
                <button type="button" class="text-sem-fg-muted hover:text-sem-fg" onclick={() => onClose?.()}>
                    <MaterialDesignIcon iconName="close" class="size-5" />
                </button>
            </div>
            <div class="p-5 space-y-4">
                <p class="text-sm text-sem-fg-muted">{t("contacts.import_file_hint")}</p>
                <input
                    bind:this={fileInput}
                    type="file"
                    accept=".json,application/json"
                    class="hidden"
                    onchange={onChange}
                />
                <button type="button" class="secondary-chip w-full justify-center" onclick={() => fileInput?.click()}>
                    <MaterialDesignIcon iconName="file-upload" class="size-4" />
                    {t("contacts.import_contacts")}
                </button>
                {#if importError}
                    <p class="text-sm text-red-600 dark:text-red-400">{importError}</p>
                {/if}
            </div>
        </div>
    </div>
{/if}
