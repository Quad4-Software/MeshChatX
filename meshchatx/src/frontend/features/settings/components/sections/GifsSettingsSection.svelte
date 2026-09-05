<!-- SPDX-License-Identifier: 0BSD -->

<script lang="ts">
    import MaterialDesignIcon from "../../../../ui/svelte/MaterialDesignIcon.svelte";
    import SettingsSectionBlock from "../SettingsSectionBlock.svelte";
    import { t } from "../../../../js/i18n.js";

    interface Props {
        visible?: boolean;
        gifCount?: number;
        replaceDuplicates?: boolean;
        onexport?: () => void;
        onimport?: (event: Event) => void;
        onupdateReplaceDuplicates?: (val: boolean) => void;
    }

    let {
        visible = true,
        gifCount = 0,
        replaceDuplicates = false,
        onexport,
        onimport,
        onupdateReplaceDuplicates,
    }: Props = $props();

    let importFileEl: HTMLInputElement | undefined = $state();
</script>

<SettingsSectionBlock
    show={visible}
    eyebrow="Messages"
    title={t("gifs.settings_title")}
    description={t("gifs.settings_description")}
    bodyClass="space-y-4"
>
    <div class="text-sm text-gray-600 dark:text-gray-400">
        {t("gifs.count", { count: gifCount })}
    </div>
    <label class="flex items-center gap-2 text-sm text-gray-800 dark:text-gray-200 cursor-pointer">
        <input
            checked={replaceDuplicates}
            type="checkbox"
            class="rounded-sm"
            onchange={(e) => onupdateReplaceDuplicates?.((e.target as HTMLInputElement).checked)}
        />
        {t("gifs.replace_duplicates")}
    </label>
    <div class="grid grid-cols-1 sm:grid-cols-2 gap-3">
        <button
            type="button"
            class="flex flex-col items-center justify-center gap-2 p-4 rounded-2xl border border-amber-200 dark:border-zinc-800 bg-white/50 dark:bg-zinc-800/50 hover:border-amber-500 transition group cursor-pointer"
            onclick={onexport}
        >
            <MaterialDesignIcon iconName="export" class="size-6 text-amber-500 group-hover:scale-110 transition" />
            <div class="text-sm font-bold">{t("gifs.export")}</div>
        </button>
        <button
            type="button"
            class="flex flex-col items-center justify-center gap-2 p-4 rounded-2xl border border-teal-200 dark:border-zinc-800 bg-white/50 dark:bg-zinc-800/50 hover:border-teal-500 transition group cursor-pointer"
            onclick={() => importFileEl?.click()}
        >
            <MaterialDesignIcon iconName="import" class="size-6 text-teal-500 group-hover:scale-110 transition" />
            <div class="text-sm font-bold">{t("gifs.import")}</div>
        </button>
        <input
            bind:this={importFileEl}
            type="file"
            accept=".json,application/json"
            class="hidden"
            onchange={onimport}
        />
    </div>
</SettingsSectionBlock>
