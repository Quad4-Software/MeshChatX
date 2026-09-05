<!-- SPDX-License-Identifier: 0BSD -->

<script lang="ts">
    import MaterialDesignIcon from "../../../../ui/svelte/MaterialDesignIcon.svelte";
    import { t } from "../../../../js/i18n.js";
    import {
        handleClearMessages,
        handleClearDuplicates,
        handleClearAnnounces,
        handleClearNomadnetFavorites,
        handleClearLxmfIcons,
        handleClearStickers,
        handleClearGifs,
        handleClearArchives,
        handleClearReticulumDocs,
        handleClearPathTable,
    } from "../../lib/maintenanceActions.js";
</script>

<div class="grid grid-cols-1 gap-3">
    <button
        type="button"
        class="btn-maintenance border-red-200 dark:border-red-900/30 text-red-700 dark:text-red-300 bg-red-50 dark:bg-red-900/10 hover:bg-red-100 dark:hover:bg-red-900/20 cursor-pointer"
        onclick={() => handleClearMessages()}
    >
        <div class="flex flex-col items-start text-left">
            <div class="font-bold flex items-center gap-2">
                <MaterialDesignIcon iconName="forum-remove-outline" class="size-4" />
                {t("maintenance.clear_messages")}
            </div>
            <div class="text-xs opacity-80">{t("maintenance.clear_messages_desc")}</div>
        </div>
    </button>

    <button
        type="button"
        class="btn-maintenance border-violet-200 dark:border-violet-900/30 text-violet-800 dark:text-violet-200 bg-violet-50 dark:bg-violet-900/10 hover:bg-violet-100 dark:hover:bg-violet-900/20 cursor-pointer"
        onclick={() => handleClearDuplicates()}
    >
        <div class="flex flex-col items-start text-left">
            <div class="font-bold flex items-center gap-2">
                <MaterialDesignIcon iconName="content-duplicate" class="size-4" />
                {t("maintenance.clear_duplicates")}
            </div>
            <div class="text-xs opacity-80">{t("maintenance.clear_duplicates_desc")}</div>
        </div>
    </button>

    <button
        type="button"
        class="btn-maintenance border-orange-200 dark:border-orange-900/30 text-orange-700 dark:text-orange-300 bg-orange-50 dark:bg-orange-900/10 hover:bg-orange-100 dark:hover:bg-orange-900/20 cursor-pointer"
        onclick={() => handleClearAnnounces()}
    >
        <div class="flex flex-col items-start text-left">
            <div class="font-bold flex items-center gap-2">
                <MaterialDesignIcon iconName="broadcast-off" class="size-4" />
                {t("maintenance.clear_announces")}
            </div>
            <div class="text-xs opacity-80">{t("maintenance.clear_announces_desc")}</div>
        </div>
    </button>

    <button
        type="button"
        class="btn-maintenance border-indigo-200 dark:border-indigo-900/30 text-indigo-700 dark:text-indigo-300 bg-indigo-50 dark:bg-indigo-900/10 hover:bg-indigo-100 dark:hover:bg-indigo-900/20 cursor-pointer"
        onclick={() => handleClearNomadnetFavorites()}
    >
        <div class="flex flex-col items-start text-left">
            <div class="font-bold flex items-center gap-2">
                <MaterialDesignIcon iconName="bookmark-remove" class="size-4" />
                {t("maintenance.clear_nomadnet_favs")}
            </div>
            <div class="text-xs opacity-80">{t("maintenance.clear_nomadnet_favs_desc")}</div>
        </div>
    </button>

    <button
        type="button"
        class="btn-maintenance border-emerald-200 dark:border-emerald-900/30 text-emerald-700 dark:text-emerald-300 bg-emerald-50 dark:bg-emerald-900/10 hover:bg-emerald-100 dark:hover:bg-emerald-900/20 cursor-pointer"
        onclick={() => handleClearLxmfIcons()}
    >
        <div class="flex flex-col items-start text-left">
            <div class="font-bold flex items-center gap-2">
                <MaterialDesignIcon iconName="account-off" class="size-4" />
                {t("maintenance.clear_lxmf_icons")}
            </div>
            <div class="text-xs opacity-80">{t("maintenance.clear_lxmf_icons_desc")}</div>
        </div>
    </button>

    <button
        type="button"
        class="btn-maintenance border-amber-200 dark:border-amber-900/30 text-amber-800 dark:text-amber-300 bg-amber-50 dark:bg-amber-900/10 hover:bg-amber-100 dark:hover:bg-amber-900/20 cursor-pointer"
        onclick={() => handleClearStickers()}
    >
        <div class="flex flex-col items-start text-left">
            <div class="font-bold flex items-center gap-2">
                <MaterialDesignIcon iconName="emoticon-outline" class="size-4" />
                {t("maintenance.clear_stickers")}
            </div>
            <div class="text-xs opacity-80">{t("maintenance.clear_stickers_desc")}</div>
        </div>
    </button>

    <button
        type="button"
        class="btn-maintenance border-pink-200 dark:border-pink-900/30 text-pink-700 dark:text-pink-300 bg-pink-50 dark:bg-pink-900/10 hover:bg-pink-100 dark:hover:bg-pink-900/20 cursor-pointer"
        onclick={() => handleClearGifs()}
    >
        <div class="flex flex-col items-start text-left">
            <div class="font-bold flex items-center gap-2">
                <MaterialDesignIcon iconName="file-gif-box" class="size-4" />
                {t("maintenance.clear_gifs")}
            </div>
            <div class="text-xs opacity-80">{t("maintenance.clear_gifs_desc")}</div>
        </div>
    </button>

    <button
        type="button"
        class="btn-maintenance border-blue-200 dark:border-blue-900/30 text-blue-700 dark:text-blue-300 bg-blue-50 dark:bg-blue-900/10 hover:bg-blue-100 dark:hover:bg-blue-900/20 cursor-pointer"
        onclick={() => handleClearArchives()}
    >
        <div class="flex flex-col items-start text-left">
            <div class="font-bold flex items-center gap-2">
                <MaterialDesignIcon iconName="delete-sweep" class="size-4" />
                {t("maintenance.clear_archives")}
            </div>
            <div class="text-xs opacity-80">{t("maintenance.clear_archives_desc")}</div>
        </div>
    </button>

    <button
        type="button"
        class="btn-maintenance border-orange-200 dark:border-orange-900/30 text-orange-700 dark:text-orange-300 bg-orange-50 dark:bg-orange-900/10 hover:bg-orange-100 dark:hover:bg-orange-900/20 cursor-pointer"
        onclick={() => handleClearReticulumDocs()}
    >
        <div class="flex flex-col items-start text-left">
            <div class="font-bold flex items-center gap-2">
                <MaterialDesignIcon iconName="book-remove" class="size-4" />
                {t("maintenance.clear_reticulum_docs")}
            </div>
            <div class="text-xs opacity-80">{t("maintenance.clear_reticulum_docs_desc")}</div>
        </div>
    </button>

    <button
        type="button"
        class="btn-maintenance border-teal-200 dark:border-teal-900/30 text-teal-800 dark:text-teal-300 bg-teal-50 dark:bg-teal-900/10 hover:bg-teal-100 dark:hover:bg-teal-900/20 cursor-pointer"
        onclick={() => handleClearPathTable()}
    >
        <div class="flex flex-col items-start text-left">
            <div class="font-bold flex items-center gap-2">
                <MaterialDesignIcon iconName="map-marker-remove" class="size-4" />
                {t("maintenance.clear_path_table")}
            </div>
            <div class="text-xs opacity-80">{t("maintenance.clear_path_table_desc")}</div>
        </div>
    </button>
</div>
