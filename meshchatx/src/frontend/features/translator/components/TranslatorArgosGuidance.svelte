<!-- SPDX-License-Identifier: 0BSD -->

<script lang="ts">
    import MaterialDesignIcon from "../../../ui/svelte/MaterialDesignIcon.svelte";
    import { t } from "../../../js/i18n.js";
    import {
        ARGOS_INSTALL_PIP_CMD,
        ARGOS_INSTALL_PIPX_CMD,
        ARGOSPM_INSTALL_ALL_CMD,
        ARGOSPM_INSTALL_PAIR_CMD,
    } from "../lib/constants.js";

    interface Props {
        hasArgos: boolean;
        hasArgosLanguages: boolean;
        isInstallingLanguages: boolean;
        onCopy: (text: string) => void;
        onInstallLanguages: (packageName: string) => void;
    }

    let {
        hasArgos,
        hasArgosLanguages,
        isInstallingLanguages,
        onCopy,
        onInstallLanguages,
    }: Props = $props();
</script>

{#if !hasArgos}
    <div
        class="p-4 rounded-xl bg-amber-50 dark:bg-amber-900/10 border border-amber-200/50 dark:border-amber-800/30"
    >
        <div class="flex items-start gap-3">
            <div class="p-2 bg-amber-100 dark:bg-amber-900/30 rounded-lg shrink-0">
                <MaterialDesignIcon
                    iconName="information-outline"
                    class="size-5 text-amber-600 dark:text-amber-400"
                />
            </div>
            <div class="flex-1 text-sm text-amber-800 dark:text-amber-200 min-w-0">
                <p class="font-bold mb-1">{t("translator.argos_not_detected")}</p>
                <p class="mb-4 opacity-90">
                    {t("translator.argos_not_detected_desc")}
                </p>

                <div class="grid sm:grid-cols-2 gap-4">
                    <div class="space-y-2">
                        <div class="flex items-center justify-between">
                            <span class="text-xs font-semibold uppercase tracking-wider opacity-70">
                                {t("translator.method_pip_venv")}
                            </span>
                            <button
                                type="button"
                                class="text-amber-600 dark:text-amber-400 hover:scale-110 transition-transform"
                                onclick={() => onCopy(ARGOS_INSTALL_PIP_CMD)}
                                aria-label="Copy pip install command"
                            >
                                <MaterialDesignIcon iconName="content-copy" class="size-4" />
                            </button>
                        </div>
                        <div
                            class="bg-amber-100/50 dark:bg-black/30 p-2 rounded-sm font-mono text-xs break-all"
                        >
                            {ARGOS_INSTALL_PIP_CMD}
                        </div>
                    </div>

                    <div class="space-y-2">
                        <div class="flex items-center justify-between">
                            <span class="text-xs font-semibold uppercase tracking-wider opacity-70">
                                {t("translator.method_pipx")}
                            </span>
                            <button
                                type="button"
                                class="text-amber-600 dark:text-amber-400 hover:scale-110 transition-transform"
                                onclick={() => onCopy(ARGOS_INSTALL_PIPX_CMD)}
                                aria-label="Copy pipx install command"
                            >
                                <MaterialDesignIcon iconName="content-copy" class="size-4" />
                            </button>
                        </div>
                        <div
                            class="bg-amber-100/50 dark:bg-black/30 p-2 rounded-sm font-mono text-xs break-all"
                        >
                            {ARGOS_INSTALL_PIPX_CMD}
                        </div>
                    </div>
                </div>
                <p class="mt-4 text-xs opacity-70 italic">
                    {t("translator.note_restart_required")}
                </p>
            </div>
        </div>
    </div>
{:else if !hasArgosLanguages}
    <div
        class="p-4 rounded-xl bg-blue-50 dark:bg-blue-900/10 border border-blue-200/50 dark:border-blue-800/30"
    >
        <div class="flex items-start gap-3">
            <div class="p-2 bg-blue-100 dark:bg-blue-900/30 rounded-lg shrink-0">
                <MaterialDesignIcon iconName="information-outline" class="size-5 text-sem-accent" />
            </div>
            <div class="flex-1 text-sm text-blue-800 dark:text-blue-200 min-w-0">
                <p class="font-bold mb-1">{t("translator.no_language_packages")}</p>
                <p class="mb-4 opacity-90">
                    {t("translator.no_language_packages_desc")}
                </p>

                <div class="space-y-3">
                    <div class="space-y-2">
                        <div class="flex items-center justify-between">
                            <span class="text-xs font-semibold uppercase tracking-wider opacity-70">
                                {t("translator.install_all_languages")}
                            </span>
                            <div class="flex gap-2">
                                <button
                                    type="button"
                                    class="text-sem-accent hover:scale-110 transition-transform"
                                    onclick={() => onCopy(ARGOSPM_INSTALL_ALL_CMD)}
                                    aria-label="Copy install all command"
                                >
                                    <MaterialDesignIcon iconName="content-copy" class="size-4" />
                                </button>
                            </div>
                        </div>
                        <div class="flex gap-2">
                            <button
                                type="button"
                                class="primary-chip px-3 py-1.5 text-xs inline-flex items-center"
                                disabled={isInstallingLanguages}
                                onclick={() => onInstallLanguages("translate")}
                            >
                                {#if isInstallingLanguages}
                                    <span
                                        class="inline-block w-3 h-3 border-2 border-white border-t-transparent rounded-full animate-spin mr-1"
                                    ></span>
                                {:else}
                                    <MaterialDesignIcon iconName="download" class="w-3 h-3 mr-1" />
                                {/if}
                                Install All
                            </button>
                            <div
                                class="bg-blue-100/50 dark:bg-black/30 p-2 rounded-sm font-mono text-xs break-all flex-1"
                            >
                                {ARGOSPM_INSTALL_ALL_CMD}
                            </div>
                        </div>
                    </div>

                    <div class="space-y-2">
                        <div class="flex items-center justify-between">
                            <span class="text-xs font-semibold uppercase tracking-wider opacity-70">
                                {t("translator.install_specific_pair")}
                            </span>
                            <button
                                type="button"
                                class="text-sem-accent hover:scale-110 transition-transform"
                                onclick={() => onCopy(ARGOSPM_INSTALL_PAIR_CMD)}
                                aria-label="Copy install pair command"
                            >
                                <MaterialDesignIcon iconName="content-copy" class="size-4" />
                            </button>
                        </div>
                        <div
                            class="bg-blue-100/50 dark:bg-black/30 p-2 rounded-sm font-mono text-xs break-all"
                        >
                            {ARGOSPM_INSTALL_PAIR_CMD}
                        </div>
                    </div>
                </div>
                <p class="mt-4 text-xs opacity-70 italic">
                    {t("translator.after_install_note")}
                </p>
            </div>
        </div>
    </div>
{/if}
