<!-- SPDX-License-Identifier: 0BSD -->

<script lang="ts">
    import MaterialDesignIcon from "../../../../ui/svelte/MaterialDesignIcon.svelte";
    import { t } from "../../../../js/i18n.js";
    import {
        exportMessages,
        importMessagesFile,
        exportFolders,
        importFoldersFile,
        exportNomadnetFavouritesLayout,
        importNomadnetFavouritesFile,
    } from "../../lib/maintenanceActions.js";

    let importFileEl: HTMLInputElement | undefined = $state();
    let importFolderFileEl: HTMLInputElement | undefined = $state();
    let nomadnetFavouritesImportFileEl: HTMLInputElement | undefined = $state();

    function onImportMessages(event: Event) {
        const target = event.target as HTMLInputElement;
        const file = target.files?.[0];
        if (!file) return;
        importMessagesFile(file);
        target.value = "";
    }

    function onImportFolders(event: Event) {
        const target = event.target as HTMLInputElement;
        const file = target.files?.[0];
        if (!file) return;
        importFoldersFile(file);
        target.value = "";
    }

    function onImportNomadnetFavourites(event: Event) {
        const target = event.target as HTMLInputElement;
        const file = target.files?.[0];
        if (!file) return;
        importNomadnetFavouritesFile(file);
        target.value = "";
    }
</script>

<div class="grid grid-cols-2 gap-3 mt-4">
    <button
        type="button"
        class="flex flex-col items-center justify-center gap-2 p-4 rounded-2xl border border-blue-200 dark:border-zinc-800 bg-sem-surface-muted/50 hover:border-blue-500 transition group cursor-pointer"
        onclick={() => exportMessages()}
    >
        <MaterialDesignIcon iconName="export" class="size-6 text-blue-500 group-hover:scale-110 transition" />
        <div class="text-sm font-bold">{t("maintenance.export_messages")}</div>
        <div class="text-xs opacity-70 text-center px-1">{t("maintenance.export_messages_desc")}</div>
    </button>
    <button
        type="button"
        class="flex flex-col items-center justify-center gap-2 p-4 rounded-2xl border border-emerald-200 dark:border-zinc-800 bg-sem-surface-muted/50 hover:border-emerald-500 transition group cursor-pointer"
        onclick={() => importFileEl?.click()}
    >
        <MaterialDesignIcon iconName="import" class="size-6 text-emerald-500 group-hover:scale-110 transition" />
        <div class="text-sm font-bold">{t("maintenance.import_messages")}</div>
        <div class="text-xs opacity-70 text-center px-1">{t("maintenance.import_messages_desc")}</div>
    </button>
    <input bind:this={importFileEl} type="file" accept=".json" class="hidden" onchange={onImportMessages} />
</div>

<div class="grid grid-cols-2 gap-3 mt-2 pt-4 border-t border-sem-border">
    <button
        type="button"
        class="flex flex-col items-center justify-center gap-2 p-4 rounded-2xl border border-purple-200 dark:border-zinc-800 bg-sem-surface-muted/50 hover:border-purple-500 transition group cursor-pointer"
        onclick={() => exportFolders()}
    >
        <MaterialDesignIcon
            iconName="folder-download-outline"
            class="size-6 text-purple-500 group-hover:scale-110 transition"
        />
        <div class="text-sm font-bold">Export Folders</div>
    </button>
    <button
        type="button"
        class="flex flex-col items-center justify-center gap-2 p-4 rounded-2xl border border-indigo-200 dark:border-zinc-800 bg-sem-surface-muted/50 hover:border-indigo-500 transition group cursor-pointer"
        onclick={() => importFolderFileEl?.click()}
    >
        <MaterialDesignIcon
            iconName="folder-upload-outline"
            class="size-6 text-indigo-500 group-hover:scale-110 transition"
        />
        <div class="text-sm font-bold">Import Folders</div>
    </button>
    <input bind:this={importFolderFileEl} type="file" accept=".json" class="hidden" onchange={onImportFolders} />
</div>

<div class="grid grid-cols-2 gap-3 mt-2 pt-4 border-t border-sem-border">
    <button
        type="button"
        class="flex flex-col items-center justify-center gap-2 p-4 rounded-2xl border border-teal-200 dark:border-zinc-800 bg-sem-surface-muted/50 hover:border-teal-500 transition group cursor-pointer"
        onclick={() => exportNomadnetFavouritesLayout()}
    >
        <MaterialDesignIcon iconName="file-export" class="size-6 text-teal-500 group-hover:scale-110 transition" />
        <div class="text-sm font-bold">{t("maintenance.export_nomadnet_favourites")}</div>
    </button>
    <button
        type="button"
        class="flex flex-col items-center justify-center gap-2 p-4 rounded-2xl border border-cyan-200 dark:border-zinc-800 bg-sem-surface-muted/50 hover:border-cyan-500 transition group cursor-pointer"
        onclick={() => nomadnetFavouritesImportFileEl?.click()}
    >
        <MaterialDesignIcon iconName="import" class="size-6 text-cyan-500 group-hover:scale-110 transition" />
        <div class="text-sm font-bold">{t("maintenance.import_nomadnet_favourites")}</div>
    </button>
    <input
        bind:this={nomadnetFavouritesImportFileEl}
        type="file"
        accept=".json"
        class="hidden"
        onchange={onImportNomadnetFavourites}
    />
</div>
