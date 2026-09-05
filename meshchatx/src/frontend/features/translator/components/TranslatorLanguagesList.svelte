<!-- SPDX-License-Identifier: 0BSD -->

<script lang="ts">
    import MaterialDesignIcon from "../../../ui/svelte/MaterialDesignIcon.svelte";
    import { t } from "../../../js/i18n.js";
    import type { TranslationMode, TranslatorLanguage } from "../lib/types.js";

    interface Props {
        languages: TranslatorLanguage[];
        translationMode: TranslationMode;
        hasArgos: boolean;
        isInstallingLanguages: boolean;
        onLoadLanguages: () => void;
        onInstallLanguages: (packageName: string) => void;
    }

    let { languages, translationMode, hasArgos, isInstallingLanguages, onLoadLanguages, onInstallLanguages }: Props =
        $props();
</script>

<div class="glass-card space-y-3">
    <div class="text-sm font-semibold text-sem-fg">
        {t("translator.available_languages")}
    </div>
    <div class="text-xs text-sem-fg-muted mb-2">
        {t("translator.languages_loaded_from")}
    </div>
    <div class="flex flex-wrap gap-2">
        {#each languages as lang (lang.code)}
            <span class="px-2 py-1 rounded-sm text-xs bg-sem-surface-muted text-gray-700 dark:text-gray-300">
                {lang.name} ({lang.code})
                <span class="text-gray-500 dark:text-gray-500">- {lang.source}</span>
            </span>
        {/each}
    </div>
    <div class="flex gap-2 mt-2">
        <button
            type="button"
            class="secondary-chip focus-ring-sem px-4 py-2 text-sm inline-flex items-center gap-1.5"
            onclick={onLoadLanguages}
        >
            <MaterialDesignIcon iconName="refresh" class="w-4 h-4" />
            {t("translator.refresh_languages")}
        </button>
        {#if translationMode === "argos" && hasArgos}
            <button
                type="button"
                class="primary-chip focus-ring-sem px-4 py-2 text-sm inline-flex items-center gap-1.5"
                disabled={isInstallingLanguages}
                onclick={() => onInstallLanguages("translate")}
            >
                {#if isInstallingLanguages}
                    <span
                        class="inline-block w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin mr-1"
                    ></span>
                {:else}
                    <MaterialDesignIcon iconName="download" class="w-4 h-4" />
                {/if}
                {t("translator.install_all_languages")}
            </button>
        {/if}
    </div>
</div>
