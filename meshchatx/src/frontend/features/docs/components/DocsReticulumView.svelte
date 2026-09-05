<!-- SPDX-License-Identifier: 0BSD -->

<script lang="ts">
    import MaterialDesignIcon from "../../../ui/svelte/MaterialDesignIcon.svelte";
    import { t } from "../../../js/i18n.js";

    interface Props {
        hasDocs: boolean;
        isExtracting: boolean;
        localDocsUrl: string;
        onZipUpload: (event: Event) => void;
    }

    let { hasDocs, isExtracting, localDocsUrl, onZipUpload }: Props = $props();

    let frameEl = $state<HTMLIFrameElement | null>(null);

    export function revealFrame(): void {
        if (frameEl && frameEl.style) {
            frameEl.style.opacity = "1";
        }
    }

    export function reloadFrame(): void {
        if (frameEl?.contentWindow) {
            frameEl.contentWindow.location.reload();
        }
    }

    function handleLoad(): void {
        revealFrame();
    }
</script>

{#if hasDocs}
    {#key localDocsUrl}
        <iframe
            bind:this={frameEl}
            src={localDocsUrl}
            title="Reticulum Documentation"
            class="w-full flex-1 min-h-0 border-none opacity-0 transition-opacity duration-1000"
            onload={handleLoad}
        ></iframe>
    {/key}
{:else if !isExtracting}
    <div class="flex-1 flex flex-col items-center justify-center p-8 text-center space-y-4">
        <div class="w-16 h-16 bg-gray-50 dark:bg-zinc-800/50 rounded-full flex items-center justify-center">
            <MaterialDesignIcon iconName="book-outline" class="w-8 h-8 text-gray-300 dark:text-zinc-600" />
        </div>
        <div>
            <h3 class="text-sm font-medium text-sem-fg">
                {t("docs.reticulum_manual")}
            </h3>
            <p class="text-xs text-sem-fg-muted mt-1 max-w-[260px]">
                {t("docs.empty_state_hint")}
            </p>
        </div>
        <label
            class="px-6 py-2 bg-blue-600 text-white rounded-full text-xs font-bold hover:bg-blue-700 transition-colors shadow-lg shadow-blue-500/20 cursor-pointer flex items-center gap-2"
        >
            <MaterialDesignIcon iconName="upload" class="w-3.5 h-3.5" />
            <span>{t("docs.btn_upload")}</span>
            <input type="file" accept=".zip" class="hidden" onchange={onZipUpload} />
        </label>
    </div>
{/if}

<style>
    iframe {
        color-scheme: light dark;
    }
</style>
