<!-- SPDX-License-Identifier: 0BSD -->

<script lang="ts">
    import MaterialDesignIcon from "../../../ui/svelte/MaterialDesignIcon.svelte";
    import { t } from "../../../js/i18n.js";
    import type { DocsStatus } from "../lib/types.js";

    interface Props {
        status: DocsStatus;
        onDismissError: () => void;
        onZipUpload: (event: Event) => void;
    }

    let { status, onDismissError, onZipUpload }: Props = $props();
</script>

{#if status.status === "extracting"}
    <div class="w-full h-1 bg-gray-200 dark:bg-zinc-800 overflow-hidden relative shrink-0">
        <div class="bg-blue-500 h-full transition-all duration-300" style="width: {status.progress}%"></div>
        <div class="absolute inset-0 bg-blue-500/30 animate-pulse"></div>
    </div>
{/if}

{#if status.last_error}
    <div
        class="absolute inset-0 z-10 flex items-center justify-center p-6 bg-white/90 dark:bg-zinc-900/90 backdrop-blur-xs"
    >
        <div
            class="max-w-md w-full p-6 bg-red-50 dark:bg-red-900/20 border border-red-100 dark:border-red-900/30 rounded-2xl text-red-600 dark:text-red-400 text-center shadow-xl"
        >
            <MaterialDesignIcon iconName="alert-circle-outline" class="w-12 h-12 mx-auto mb-3" />
            <div class="text-lg font-bold mb-2">{t("docs.error")}</div>
            <div class="text-sm opacity-80">{status.last_error}</div>
            <div class="flex flex-col gap-4 mt-6">
                <label
                    class="w-full px-6 py-2.5 bg-zinc-900 dark:bg-white text-white dark:text-zinc-900 rounded-xl text-xs font-bold hover:opacity-90 transition-opacity cursor-pointer flex items-center justify-center gap-2"
                >
                    <MaterialDesignIcon iconName="upload" class="w-3.5 h-3.5" />
                    <span>{t("docs.btn_upload")}</span>
                    <input type="file" accept=".zip" class="hidden" onchange={onZipUpload} />
                </label>
                <button
                    type="button"
                    class="text-[10px] font-bold text-red-500/60 hover:text-red-500 uppercase tracking-widest transition-colors"
                    onclick={onDismissError}
                >
                    {t("docs.dismiss")}
                </button>
            </div>
        </div>
    </div>
{/if}

{#if status.status === "extracting"}
    <div
        class="absolute inset-0 z-10 flex flex-col items-center justify-center bg-white/80 dark:bg-zinc-900/80 backdrop-blur-md"
    >
        <div class="relative w-24 h-24 mb-6">
            <div class="absolute inset-0 border-4 border-blue-100 dark:border-blue-900/30 rounded-full"></div>
            <div
                class="absolute inset-0 border-4 border-blue-600 rounded-full transition-all duration-300"
                style="clip-path: inset(0 0 0 0); transform: rotate({status.progress *
                    3.6}deg); border-color: transparent; border-top-color: currentColor;"
            ></div>
            <div class="absolute inset-0 flex items-center justify-center">
                <MaterialDesignIcon iconName="folder-zip-outline" class="w-10 h-10 text-blue-600 animate-bounce" />
            </div>
        </div>
        <h3 class="text-lg font-bold text-sem-fg mb-1">
            {t("docs.status_extracting")}
        </h3>
        <p class="text-sm text-sem-fg-muted">
            {t("docs.complete_percent", { percent: status.progress })}
        </p>
    </div>
{/if}
