<!-- SPDX-License-Identifier: 0BSD -->

<script>
    import MaterialDesignIcon from "../../../ui/svelte/MaterialDesignIcon.svelte";
    import { t } from "../../../js/i18n.js";

    /**
     * @type {{
     *   totalContactsCount?: number,
     *   onShareIdentity?: () => void,
     *   onExport?: () => void,
     *   onImport?: () => void,
     *   onAdd?: () => void,
     * }}
     */
    let { totalContactsCount = 0, onShareIdentity, onExport, onImport, onAdd } = $props();
</script>

<div class="flex flex-col gap-3 lg:flex-row lg:items-center lg:justify-between">
    <div>
        <h1 class="text-2xl font-bold text-sem-fg">{t("contacts.title")}</h1>
        <p class="text-sm text-sem-fg-muted">{t("contacts.description")}</p>
    </div>
    <div class="flex flex-wrap items-center gap-2">
        <button type="button" class="secondary-chip" onclick={() => onShareIdentity?.()}>
            <MaterialDesignIcon iconName="qrcode" class="size-4" />
            {t("contacts.share_my_identity")}
        </button>
        <button
            type="button"
            class="secondary-chip justify-center px-3 sm:px-4"
            disabled={totalContactsCount === 0}
            title={t("contacts.export_contacts")}
            onclick={() => onExport?.()}
        >
            <MaterialDesignIcon iconName="file-export" class="size-4" />
            <span class="hidden sm:inline">{t("contacts.export_contacts")}</span>
        </button>
        <button
            type="button"
            class="secondary-chip justify-center px-3 sm:px-4"
            title={t("contacts.import_contacts")}
            onclick={() => onImport?.()}
        >
            <MaterialDesignIcon iconName="file-import" class="size-4" />
            <span class="hidden sm:inline">{t("contacts.import_contacts")}</span>
        </button>
        <button type="button" class="primary-chip hidden sm:inline-flex" onclick={() => onAdd?.()}>
            <MaterialDesignIcon iconName="plus" class="size-4" />
            {t("contacts.add_contact")}
        </button>
    </div>
</div>
