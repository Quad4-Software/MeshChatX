<!-- SPDX-License-Identifier: 0BSD -->

<script lang="ts">
    import Modal from "../../../ui/svelte/Modal.svelte";
    import MaterialDesignIcon from "../../../ui/svelte/MaterialDesignIcon.svelte";
    import { t } from "../../../js/i18n.js";

    let {
        open = $bindable(false),
        importError = null as string | null,
        onClose,
        onFileSelected,
    }: {
        open?: boolean;
        importError?: string | null;
        onClose?: () => void;
        onFileSelected?: (file: File) => void;
    } = $props();

    let fileInput: HTMLInputElement | undefined = $state();

    function onChange(event: Event) {
        const target = event.target as HTMLInputElement;
        const file = target.files?.[0];
        if (file) {
            onFileSelected?.(file);
        }
        target.value = "";
    }

    function handleClose() {
        open = false;
        onClose?.();
    }
</script>

<Modal bind:open title={t("contacts.import_modal_title")} onClose={handleClose}>
    <div class="p-5 space-y-4">
        <p class="text-sm text-sem-fg-muted">{t("contacts.import_file_hint")}</p>
        <input bind:this={fileInput} type="file" accept=".json,application/json" class="hidden" onchange={onChange} />
        <button
            type="button"
            class="secondary-chip w-full justify-center focus-ring-sem"
            onclick={() => fileInput?.click()}
        >
            <MaterialDesignIcon iconName="file-upload" class="size-4" />
            {t("contacts.import_contacts")}
        </button>
        {#if importError}
            <p class="text-sm text-sem-danger">{importError}</p>
        {/if}
    </div>
</Modal>
